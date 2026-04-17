"""
Scraper CPU - pc-kombo.com -> Django DB
Ruleaza din folderul backend-django/:
    python ../scraper_cpu_pckombo.py

Sau seteaza manual DJANGO_SETTINGS_MODULE mai jos.
"""

import os
import sys
import time
import re
from decimal import Decimal, InvalidOperation

# ── Configurare Django ──────────────────────────────────────────────────────
# Ajusteaza path-ul daca scriptul nu e in backend-django/
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BACKEND_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend_django.settings")
# Daca nu merge, incearca una din variantele de mai jos (comenteaza/decommenteaza):
# os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"
# os.environ["DJANGO_SETTINGS_MODULE"] = "pcbuilder.settings"
# os.environ["DJANGO_SETTINGS_MODULE"] = "settings"

import django
django.setup()

from components.models import CPU

# ── Librarii scraping ───────────────────────────────────────────────────────
try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Lipsesc dependentele. Ruleaza: pip install requests beautifulsoup4")
    sys.exit(1)

# ── Constante ───────────────────────────────────────────────────────────────
BASE_URL = "https://www.pc-kombo.com"
LIST_URL = f"{BASE_URL}/us/components/cpus"
DELAY_BETWEEN_REQUESTS = 0.8  # secunde - politicos cu serverul

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# Serie detectata din numele produsului
SERII_CPU = [
    "Core Ultra 9", "Core Ultra 7", "Core Ultra 5", "Core Ultra 3",
    "Core i9", "Core i7", "Core i5", "Core i3",
    "Ryzen Threadripper", "Ryzen 9", "Ryzen 7", "Ryzen 5", "Ryzen 3",
    "Xeon", "Athlon", "Pentium", "Celeron", "EPYC",
]


# ── Functii helper ───────────────────────────────────────────────────────────

def get_session():
    session = requests.Session()
    session.headers.update(HEADERS)
    return session


def fetch(session, url, retries=3):
    for attempt in range(retries):
        try:
            resp = session.get(url, timeout=20)
            if resp.status_code == 200:
                return resp
            print(f"  HTTP {resp.status_code} pentru {url}")
        except requests.RequestException as e:
            print(f"  Eroare retea (attempt {attempt+1}): {e}")
            time.sleep(2)
    return None


def extract_spec(soup, *labels):
    """
    Cauta o valoare in pagina dupa eticheta.
    Incearca: dl/dt/dd, table th/td, li span/span, div cu text.
    """
    for label in labels:
        label_lower = label.lower()

        # Structura dl > dt + dd
        for dt in soup.find_all("dt"):
            if label_lower in dt.get_text(strip=True).lower():
                dd = dt.find_next_sibling("dd")
                if dd:
                    return dd.get_text(strip=True)

        # Structura table > tr > th + td
        for th in soup.find_all("th"):
            if label_lower in th.get_text(strip=True).lower():
                td = th.find_next_sibling("td")
                if td:
                    return td.get_text(strip=True)

        # Structura: orice element cu textul etichetei urmat de sibling
        for el in soup.find_all(["span", "strong", "b", "label", "p"]):
            text = el.get_text(strip=True)
            if text.lower() == label_lower or text.lower().startswith(label_lower + ":"):
                sibling = el.find_next_sibling()
                if sibling:
                    return sibling.get_text(strip=True)
                # valoarea poate fi in acelasi element dupa ":"
                if ":" in text:
                    return text.split(":", 1)[1].strip()

        # Fallback: cauta in tot textul paginii un pattern "Label: Valoare"
        match = re.search(
            rf"{re.escape(label)}\s*[:\-]\s*([^\n<]+)",
            soup.get_text(),
            re.IGNORECASE,
        )
        if match:
            return match.group(1).strip()

    return None


def parse_number(text, cast=int):
    """Extrage primul numar dintr-un string, ex: '65 W' -> 65"""
    if not text:
        return None
    match = re.search(r"[\d.,]+", text)
    if not match:
        return None
    try:
        cleaned = match.group().replace(",", ".")
        return cast(cleaned) if cast == int else Decimal(cleaned)
    except (ValueError, InvalidOperation):
        return None


def detect_serie(name):
    for serie in SERII_CPU:
        if serie.lower() in name.lower():
            return serie
    # Fallback: al doilea cuvant din nume (ex: "AMD Ryzen..." -> "Ryzen")
    parts = name.split()
    return parts[1] if len(parts) > 1 else parts[0]


# ── Scraping lista produse ───────────────────────────────────────────────────

def get_all_cpu_urls(session):
    """Parcurge toate paginile listei de CPU si returneaza URL-urile produselor."""
    urls = []
    page = 1

    while True:
        url = f"{LIST_URL}?page={page}" if page > 1 else LIST_URL
        print(f"  Pagina {page}: {url}")

        resp = fetch(session, url)
        if not resp:
            break

        soup = BeautifulSoup(resp.text, "html.parser")

        # Gasim toate link-urile catre produse individuale
        found_on_page = 0
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "/us/product/cpu/" in href:
                full_url = BASE_URL + href if href.startswith("/") else href
                if full_url not in urls:
                    urls.append(full_url)
                    found_on_page += 1

        print(f"    -> {found_on_page} produse gasite pe pagina {page}")

        if found_on_page == 0:
            break

        # Verificam daca exista pagina urmatoare
        next_link = soup.find("a", string=str(page + 1))
        # Alternativ: link cu ?page=N+1
        if not next_link:
            next_link = soup.find("a", href=re.compile(rf"page={page+1}"))
        if not next_link:
            break

        page += 1
        time.sleep(DELAY_BETWEEN_REQUESTS)

    return urls


# ── Scraping pagina produs ───────────────────────────────────────────────────

def scrape_cpu(session, url):
    """Scrapeaza o pagina de produs CPU si returneaza un dict cu datele."""
    resp = fetch(session, url)
    if not resp:
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    # Nume produs
    h1 = soup.find("h1")
    if h1:
        name = h1.get_text(strip=True)
    else:
        # Fallback din URL: ".../cpu/0730143312042_AMD-Ryzen-5-5600X" -> "AMD Ryzen 5 5600X"
        slug = url.rstrip("/").split("/")[-1]
        name = slug.split("_", 1)[-1].replace("-", " ") if "_" in slug else slug

    # EAN din URL (primul segment numeric dupa /cpu/)
    ean_match = re.search(r"/cpu/(\d+)_", url)
    ean = ean_match.group(1) if ean_match else None

    # Specs
    mpn       = extract_spec(soup, "MPN", "Part Number", "Model Number")
    producer  = extract_spec(soup, "Producer", "Brand", "Manufacturer")
    socket    = extract_spec(soup, "Socket")
    base_clk  = extract_spec(soup, "Base Clock", "Base Frequency", "Base Speed")
    cores_raw = extract_spec(soup, "Cores", "Core Count")
    threads_r = extract_spec(soup, "Threads", "Thread Count")
    tdp_raw   = extract_spec(soup, "TDP", "Thermal Design Power", "Power")

    # Conversii
    part_number = mpn or ean  # MPN preferat, EAN ca fallback
    brand       = producer or ("AMD" if "ryzen" in name.lower() or "athlon" in name.lower()
                               else "Intel" if "intel" in name.lower() or "core" in name.lower()
                               else "Unknown")
    socket_val  = socket or ""
    nuclee      = parse_number(cores_raw, int) or 0
    threaduri   = parse_number(threads_r, int)
    tdp         = parse_number(tdp_raw, int) or 0
    serie       = detect_serie(name)

    # Base clock: "3.7 GHz" -> Decimal("3.7")
    frecventa = parse_number(base_clk, Decimal) or Decimal("0.0")

    return {
        "nume":          name,
        "brand":         brand,
        "part_number":   part_number,
        "socket":        socket_val,
        "serie":         serie,
        "nuclee":        nuclee,
        "threaduri":     threaduri,
        "frecventa_ghz": frecventa,
        "consum_tdp":    tdp,
        # Lasat intentionat gol - va fi completat de scraperul de preturi RO
        "pret":          None,
        "magazin":       None,
        "url_produs":    None,
        "stoc":          True,
        "regiune":       "Romania",
    }


# ── Salvare in DB ────────────────────────────────────────────────────────────

def save_cpu(data):
    """
    Upsert in DB dupa part_number.
    Returneaza (obiect, created: bool).
    """
    part_number = data.pop("part_number")
    obj, created = CPU.objects.update_or_create(
        part_number=part_number,
        defaults=data,
    )
    return obj, created


# ── Main ─────────────────────────────────────────────────────────────────────

def run():
    session = get_session()

    print("=" * 60)
    print("Scraper CPU - pc-kombo.com")
    print("=" * 60)

    print("\n[1] Colectam URL-urile produselor...")
    urls = get_all_cpu_urls(session)
    print(f"\nTotal CPU-uri gasite: {len(urls)}")

    if not urls:
        print("Nu s-au gasit produse. Verifica conexiunea sau structura site-ului.")
        return

    print("\n[2] Scrapam fiecare produs si salvam in DB...\n")

    stats = {"salvat": 0, "actualizat": 0, "sarit": 0, "eroare": 0}

    for i, url in enumerate(urls, 1):
        print(f"[{i:>4}/{len(urls)}] {url.split('/')[-1][:60]}")

        try:
            data = scrape_cpu(session, url)

            if not data:
                print("         -> EROARE fetch")
                stats["eroare"] += 1
                continue

            if not data.get("part_number"):
                print("         -> SARIT (fara part_number/EAN)")
                stats["sarit"] += 1
                continue

            _, created = save_cpu(data)
            action = "NOU" if created else "ACTUALIZAT"
            print(f"         -> {action}: {data.get('nume', '?')}")
            stats["salvat" if created else "actualizat"] += 1

        except Exception as e:
            print(f"         -> EXCEPTIE: {e}")
            stats["eroare"] += 1

        time.sleep(DELAY_BETWEEN_REQUESTS)

    print("\n" + "=" * 60)
    print(f"Gata!")
    print(f"  Noi:        {stats['salvat']}")
    print(f"  Actualizate: {stats['actualizat']}")
    print(f"  Sarite:     {stats['sarit']}")
    print(f"  Erori:      {stats['eroare']}")
    print("=" * 60)


if __name__ == "__main__":
    run()