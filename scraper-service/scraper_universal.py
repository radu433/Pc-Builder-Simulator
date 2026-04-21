import re
import sys
import time
import random
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright
from config import MAGAZINE


def curata_pret(pret_raw: str) -> float:
    try:
        curat = re.sub(r"[^\d.,]", "", pret_raw)
        if not curat:
            return 0.0
        if "," in curat and "." in curat:
            curat = curat.replace(".", "").replace(",", ".")
        elif "," in curat:
            curat = curat.replace(",", ".")
        return float(curat)
    except Exception:
        return 0.0


def titlu_contine_termen(titlu: str, termen: str) -> bool:
    titlu_lower = titlu.lower()
    cuvinte = termen.lower().split()
    return all(cuv in titlu_lower for cuv in cuvinte)


def detecteaza_stoc(text_card: str, config: dict) -> str:
    text = text_card.lower()
    texte_epuizat = [
        "stoc epuizat", "nu este in stoc", "indisponibil", "out of stock", "unavailable",
    ]
    if "stoc_text_epuizat" in config:
        texte_epuizat.append(config["stoc_text_epuizat"].lower())
    if any(t in text for t in texte_epuizat):
        return "Epuizat"
    if "precomanda" in text or "pre-order" in text:
        return "Precomanda"
    return "In stoc"


def creeaza_context_antibot(p):
    browser = p.chromium.launch(
        headless=True,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-infobars",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--window-size=1280,800",
        ]
    )
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    context = browser.new_context(
        user_agent=user_agent,
        viewport={"width": 1280, "height": 800},
        locale="ro-RO",
        timezone_id="Europe/Bucharest",
        extra_http_headers={
            "Accept-Language": "ro-RO,ro;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://www.google.com/",
        }
    )
    # patch ca sa nu fie detectat ca headless
    context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});
        Object.defineProperty(navigator, 'languages', {get: () => ['ro-RO', 'ro', 'en-US']});
        window.chrome = { runtime: {} };
    """)
    return browser, context

def naviga_cu_retry(page, url: str, nume_magazin: str, retries: int = 2) -> bool:
    for attempt in range(retries):
        try:
            wait = "networkidle" if attempt == 0 else "domcontentloaded"
            page.goto(url, wait_until=wait, timeout=60000)
            page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.3)")
            time.sleep(random.uniform(0.5, 1.0))
            page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.6)")
            time.sleep(random.uniform(1.0, 2.0))
            return True
        except Exception as e:
            eroare = str(e)
            if "chrome-error://" in eroare:
                print(f"  ⚠️  {nume_magazin}: redirect gresit (attempt {attempt+1}/{retries})")
            elif "ERR_NAME_NOT_RESOLVED" in eroare:
                print(f"  ⚠️  {nume_magazin}: domeniu inaccesibil — sarim.")
                return False
            else:
                print(f"  ⚠️  {nume_magazin}: {eroare[:120]} (attempt {attempt+1}/{retries})")
            time.sleep(2)
    return False


def extrage_produse_magazin(page, nume_magazin: str, config: dict, termen_cautare: str) -> list:
    print(f"\n🔍 Scanam {nume_magazin} pentru '{termen_cautare}'...")

    query = termen_cautare.replace(" ", "%20")
    url = config["url_search"].format(query=query)

    if not naviga_cu_retry(page, url, nume_magazin):
        return []

    continut = page.content().lower()
   
    produse_locator = page.locator(config["selector_card"])

    try:
        produse_locator.first.wait_for(timeout=10000)
    except Exception:
        pass

    nr_produse = produse_locator.count()

    if nr_produse == 0:
        print(f"  ❌ Niciun card gasit pe {nume_magazin}. (selector: {config['selector_card']})")
        print(f"     Titlu pagina: '{page.title()}'")
        return []

    lista_rezultate = []

    for i in range(nr_produse):
        try:
            prod = produse_locator.nth(i)

            titlu_el = prod.locator(config["selector_titlu"])
            if titlu_el.count() == 0:
                continue
            titlu = titlu_el.first.inner_text().strip()
            if not titlu:
                continue

            if not titlu_contine_termen(titlu, termen_cautare):
                continue

            pret_el = prod.locator(config["selector_pret"])
            if pret_el.count() == 0:
                continue
            pret_raw = pret_el.first.inner_text()
            pret_final = curata_pret(pret_raw)
            if pret_final <= 0:
                continue

            link_el = prod.locator(config["selector_link"])
            link = link_el.first.get_attribute("href") if link_el.count() > 0 else "N/A"
            if link and link.startswith("/"):
                parsed = urlparse(url)
                link = f"{parsed.scheme}://{parsed.netloc}{link}"

            text_card = prod.inner_text()
            status_stoc = detecteaza_stoc(text_card, config)

            print(f"  ✅ {titlu[:55]} | {pret_final:.2f} Lei | {status_stoc}")

            lista_rezultate.append({
                "Magazin": nume_magazin,
                "Nume Produs": titlu,
                "Pret (Lei)": pret_final,
                "Status Stoc": status_stoc,
                "Link": link,
            })

        except Exception:
            continue

    print(f"  📦 {len(lista_rezultate)} produs(e) relevante gasite.")
    return lista_rezultate


def gaseste_cel_mai_ieftin(termen_cautare: str):
    toate_produsele = []

    with sync_playwright() as p:
        for nume_magazin, config in MAGAZINE.items():
            browser, context = creeaza_context_antibot(p)
            page = context.new_page()
            

            try:
                produse = extrage_produse_magazin(page, nume_magazin, config, termen_cautare)
                toate_produsele.extend(produse)
            finally:
                browser.close()

            time.sleep(random.uniform(3.0, 6.0))

    if not toate_produsele:
        print("\n❌ Nu am gasit niciun produs relevant.")
        return None, []

    in_stoc = [p for p in toate_produsele if p["Status Stoc"] == "In stoc"]
    pool = in_stoc if in_stoc else toate_produsele

    if not in_stoc:
        print("\n⚠️  Toate produsele sunt epuizate. Afisam cel mai ieftin indiferent de stoc.")

    cel_mai_ieftin = min(pool, key=lambda x: x["Pret (Lei)"])
    return cel_mai_ieftin, toate_produsele


def main():
    if len(sys.argv) < 2:
        print("Utilizare: python scraper_universal.py \"<produs de cautat>\"")
        print('Exemplu:   python scraper_universal.py "RTX 5060"')
        sys.exit(1)

    termen = " ".join(sys.argv[1:])
    print(f"\n{'='*60}")
    print(f"  CAUTAM: {termen}")
    print(f"{'='*60}")

    cel_mai_ieftin, toate = gaseste_cel_mai_ieftin(termen)

    if cel_mai_ieftin is None:
        return

    print(f"\n{'='*60}")
    print(f"  🏆 CEL MAI IEFTIN PRODUS GASIT:")
    print(f"{'='*60}")
    print(f"  Magazin : {cel_mai_ieftin['Magazin']}")
    print(f"  Produs  : {cel_mai_ieftin['Nume Produs']}")
    print(f"  Pret    : {cel_mai_ieftin['Pret (Lei)']:.2f} Lei")
    print(f"  Stoc    : {cel_mai_ieftin['Status Stoc']}")
    print(f"  URL     : {cel_mai_ieftin['Link']}")
    print(f"{'='*60}")

    if len(toate) > 1:
        print(f"\n📊 TOATE PRODUSELE RELEVANTE ({len(toate)} total, sortate dupa pret):\n")
        for p in sorted(toate, key=lambda x: x["Pret (Lei)"]):
            icon = "✅" if p["Status Stoc"] == "In stoc" else "❌"
            print(f"  {icon} {p['Magazin']:<12} | {p['Pret (Lei)']:>10.2f} Lei | {p['Nume Produs'][:45]}")


if __name__ == "__main__":
    main()