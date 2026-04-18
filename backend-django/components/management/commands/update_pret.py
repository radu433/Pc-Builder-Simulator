"""
Scraper preturi pentru PC Builder Simulator.
Copiaza in: components/management/commands/update_prices.py
Ruleaza cu: python manage.py update_prices

Dependinte extra fata de ce ai deja:
    pip install playwright
    playwright install chromium

Cauta fiecare componenta din DB pe: eMag, PCGarage, Altex, Vexio, CEL
Ia primele 5 rezultate, verifica stoc, compara preturi, updateaza DB.
Daca nu e gasit pe niciun site -> sterge din DB.
"""

import re
import time
import random
import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from django.core.management.base import BaseCommand
from django.db import transaction

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
except ImportError:
    raise ImportError("Ruleaza: pip install playwright && playwright install chromium")

from components.models import CPU, GPU, Motherboard, RAM, PSU, Case, Cooler, Storage

logger = logging.getLogger(__name__)

# ─────────────────────────── CONFIG ──────────────────────────────────────────

DELAY_BETWEEN_PRODUCTS = (3.0, 7.0)   # secunde random intre produse
DELAY_BETWEEN_SITES    = (1.5, 4.0)   # secunde random intre site-uri pt acelasi produs
DELAY_BETWEEN_BATCHES  = (15, 30)     # secunde dupa fiecare 20 produse

MAX_RESULTS_PER_SITE = 5              # primele N rezultate din pagina de search
PAGE_TIMEOUT_MS      = 20_000         # timeout playwright per pagina
BATCH_SIZE           = 20             # produse inainte de pauza lunga

ALL_MODELS = [CPU, GPU, Motherboard, RAM, PSU, Case, Cooler, Storage]

# ─────────────────────────── DATA CLASSES ────────────────────────────────────

@dataclass
class PriceResult:
    site:    str
    price:   Decimal
    in_stoc: bool
    url:     str


# ─────────────────────────── SITE SCRAPERS ───────────────────────────────────
# Fiecare functie primeste un Playwright Page si query-ul de cautat.
# Returneaza lista de PriceResult (maxim MAX_RESULTS_PER_SITE).

def _rand_delay(min_s: float, max_s: float):
    time.sleep(random.uniform(min_s, max_s))


def _clean_price(text: str) -> Optional[Decimal]:
    """Extrage primul numar dintr-un string de pret. '1.299,99 Lei' -> 1299.99"""
    if not text:
        return None
    # elimina separatoarele de mii si normalizeaza virgula decimala
    cleaned = re.sub(r"[^\d,.]", "", text)
    # format romanesc: 1.299,99
    if re.search(r"\d{1,3}\.\d{3},\d{2}$", cleaned):
        cleaned = cleaned.replace(".", "").replace(",", ".")
    # format cu virgula simpla: 1299,99
    elif "," in cleaned and "." not in cleaned:
        cleaned = cleaned.replace(",", ".")
    # format cu punct simplu ca separator mii: 1.299
    elif "." in cleaned and "," not in cleaned:
        parts = cleaned.split(".")
        if len(parts[-1]) == 3:  # e separator de mii, nu zecimale
            cleaned = cleaned.replace(".", "")
    m = re.search(r"\d+(\.\d+)?", cleaned)
    try:
        return Decimal(m.group()) if m else None
    except Exception:
        return None


# ── eMag ─────────────────────────────────────────────────────────────────────

def scrape_emag(page, query: str) -> list[PriceResult]:
    results = []
    try:
        url = f"https://www.emag.ro/search/{query.replace(' ', '+')}"
        page.goto(url, timeout=PAGE_TIMEOUT_MS, wait_until="domcontentloaded")
        page.wait_for_selector(".card-item", timeout=8000)

        cards = page.query_selector_all(".card-item")[:MAX_RESULTS_PER_SITE]
        for card in cards:
            try:
                # pret
                price_el = card.query_selector(".product-new-price")
                if not price_el:
                    continue
                price = _clean_price(price_el.inner_text())
                if not price:
                    continue

                # stoc
                stoc_el = card.query_selector(".stoc-flag, .label-in-stock, .availability")
                stoc_text = (stoc_el.inner_text() if stoc_el else "").lower()
                in_stoc = "stoc" in stoc_text or "disponibil" in stoc_text or stoc_el is None

                # url produs
                link_el = card.query_selector("a.js-product-url, a[data-url], h2 a, .card-section-title a")
                prod_url = link_el.get_attribute("href") if link_el else url
                if prod_url and not prod_url.startswith("http"):
                    prod_url = "https://www.emag.ro" + prod_url

                results.append(PriceResult("eMag", price, in_stoc, prod_url or url))
            except Exception:
                continue
    except PWTimeout:
        logger.debug("eMag timeout pentru: %s", query)
    except Exception as e:
        logger.debug("eMag eroare: %s", e)
    return results


# ── PCGarage ──────────────────────────────────────────────────────────────────

def scrape_pcgarage(page, query: str) -> list[PriceResult]:
    results = []
    try:
        url = f"https://www.pcgarage.ro/cauta/?search_query={query.replace(' ', '+')}"
        page.goto(url, timeout=PAGE_TIMEOUT_MS, wait_until="domcontentloaded")
        page.wait_for_selector(".product-list-item, .product-item", timeout=8000)

        cards = page.query_selector_all(".product-list-item, .product-item")[:MAX_RESULTS_PER_SITE]
        for card in cards:
            try:
                price_el = card.query_selector(".price, .product-price")
                if not price_el:
                    continue
                price = _clean_price(price_el.inner_text())
                if not price:
                    continue

                stoc_el = card.query_selector(".stock, .availability, .in-stock")
                stoc_text = (stoc_el.inner_text() if stoc_el else "").lower()
                in_stoc = "stoc" in stoc_text or "disponibil" in stoc_text or stoc_el is None

                link_el = card.query_selector("a.product-title, h2 a, h3 a, .title a")
                prod_url = link_el.get_attribute("href") if link_el else url
                if prod_url and not prod_url.startswith("http"):
                    prod_url = "https://www.pcgarage.ro" + prod_url

                results.append(PriceResult("PCGarage", price, in_stoc, prod_url or url))
            except Exception:
                continue
    except PWTimeout:
        logger.debug("PCGarage timeout pentru: %s", query)
    except Exception as e:
        logger.debug("PCGarage eroare: %s", e)
    return results


# ── Altex ─────────────────────────────────────────────────────────────────────

def scrape_altex(page, query: str) -> list[PriceResult]:
    results = []
    try:
        url = f"https://altex.ro/search/{query.replace(' ', '%20')}/"
        page.goto(url, timeout=PAGE_TIMEOUT_MS, wait_until="domcontentloaded")
        page.wait_for_selector(".Product, .ProductCard", timeout=8000)

        cards = page.query_selector_all(".Product, .ProductCard")[:MAX_RESULTS_PER_SITE]
        for card in cards:
            try:
                price_el = card.query_selector(".Price, .ProductCard-price, [class*='price']")
                if not price_el:
                    continue
                price = _clean_price(price_el.inner_text())
                if not price:
                    continue

                stoc_el = card.query_selector("[class*='stock'], [class*='availability'], [class*='Stock']")
                stoc_text = (stoc_el.inner_text() if stoc_el else "").lower()
                in_stoc = "stoc" in stoc_text or "disponibil" in stoc_text or stoc_el is None

                link_el = card.query_selector("a[href]")
                prod_url = link_el.get_attribute("href") if link_el else url
                if prod_url and not prod_url.startswith("http"):
                    prod_url = "https://altex.ro" + prod_url

                results.append(PriceResult("Altex", price, in_stoc, prod_url or url))
            except Exception:
                continue
    except PWTimeout:
        logger.debug("Altex timeout pentru: %s", query)
    except Exception as e:
        logger.debug("Altex eroare: %s", e)
    return results


# ── Vexio ─────────────────────────────────────────────────────────────────────

def scrape_vexio(page, query: str) -> list[PriceResult]:
    results = []
    try:
        url = f"https://www.vexio.ro/cautare/?q={query.replace(' ', '+')}"
        page.goto(url, timeout=PAGE_TIMEOUT_MS, wait_until="domcontentloaded")
        page.wait_for_selector(".product-item, .product-card, .item", timeout=8000)

        cards = page.query_selector_all(".product-item, .product-card, .item")[:MAX_RESULTS_PER_SITE]
        for card in cards:
            try:
                price_el = card.query_selector(".price, .pret, [class*='price']")
                if not price_el:
                    continue
                price = _clean_price(price_el.inner_text())
                if not price:
                    continue

                stoc_el = card.query_selector("[class*='stock'], [class*='stoc'], [class*='availability']")
                stoc_text = (stoc_el.inner_text() if stoc_el else "").lower()
                in_stoc = "stoc" in stoc_text or "disponibil" in stoc_text or stoc_el is None

                link_el = card.query_selector("a[href]")
                prod_url = link_el.get_attribute("href") if link_el else url
                if prod_url and not prod_url.startswith("http"):
                    prod_url = "https://www.vexio.ro" + prod_url

                results.append(PriceResult("Vexio", price, in_stoc, prod_url or url))
            except Exception:
                continue
    except PWTimeout:
        logger.debug("Vexio timeout pentru: %s", query)
    except Exception as e:
        logger.debug("Vexio eroare: %s", e)
    return results


# ── CEL ───────────────────────────────────────────────────────────────────────

def scrape_cel(page, query: str) -> list[PriceResult]:
    results = []
    try:
        url = f"https://www.cel.ro/cauta/?q={query.replace(' ', '+')}"
        page.goto(url, timeout=PAGE_TIMEOUT_MS, wait_until="domcontentloaded")
        page.wait_for_selector(".product-item, .produs, .item-produs", timeout=8000)

        cards = page.query_selector_all(".product-item, .produs, .item-produs")[:MAX_RESULTS_PER_SITE]
        for card in cards:
            try:
                price_el = card.query_selector(".price, .pret, [class*='price'], [class*='pret']")
                if not price_el:
                    continue
                price = _clean_price(price_el.inner_text())
                if not price:
                    continue

                stoc_el = card.query_selector("[class*='stoc'], [class*='stock'], [class*='availability']")
                stoc_text = (stoc_el.inner_text() if stoc_el else "").lower()
                in_stoc = "stoc" in stoc_text or "disponibil" in stoc_text or stoc_el is None

                link_el = card.query_selector("a[href]")
                prod_url = link_el.get_attribute("href") if link_el else url
                if prod_url and not prod_url.startswith("http"):
                    prod_url = "https://www.cel.ro" + prod_url

                results.append(PriceResult("CEL", price, in_stoc, prod_url or url))
            except Exception:
                continue
    except PWTimeout:
        logger.debug("CEL timeout pentru: %s", query)
    except Exception as e:
        logger.debug("CEL eroare: %s", e)
    return results


SITE_SCRAPERS = [
    scrape_emag,
    scrape_pcgarage,
    scrape_altex,
    scrape_vexio,
    scrape_cel,
]


# ─────────────────────────── MATCH LOGIC ─────────────────────────────────────

def _tokenize(text: str) -> set[str]:
    """Imparte numele in tokeni relevanti: 'RTX 4070 Ti 12GB' -> {'rtx','4070','ti','12gb'}"""
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    # ignora tokeni generici
    stopwords = {"the", "and", "with", "for", "de", "si", "cu", "gb", "tb", "mhz", "ghz"}
    return {t for t in tokens if len(t) > 1 and t not in stopwords}


def _similarity(query_name: str, result_text: str) -> float:
    """
    Scor simplu de similaritate intre numele produsului din DB si textul din rezultat.
    Returneaza proportia de tokeni din query care apar in result.
    """
    q_tokens = _tokenize(query_name)
    r_tokens = _tokenize(result_text)
    if not q_tokens:
        return 0.0
    common = q_tokens & r_tokens
    return len(common) / len(q_tokens)


def find_best_price(
    page,
    product_name: str,
    min_similarity: float = 0.55,
) -> Optional[PriceResult]:
    """
    Cauta produsul pe toate site-urile, verifica similaritatea cu numele din DB,
    filtreaza doar produsele in stoc, returneaza cel mai ieftin.
    """
    # Simplificam query-ul: primele 5-6 cuvinte din nume
    query_words = product_name.split()[:6]
    query = " ".join(query_words)

    all_valid: list[PriceResult] = []

    for scrape_fn in SITE_SCRAPERS:
        try:
            site_results = scrape_fn(page, query)
            for r in site_results:
                # Verifica daca rezultatul e in stoc
                if not r.in_stoc:
                    continue
                # Verifica similaritatea numelui (evita false positives)
                # Folosim URL-ul si pretul ca sunt deja extrase, similaritatea
                # o facem pe query vs numele extrase din URL/titlu
                sim = _similarity(product_name, r.url)
                if sim >= min_similarity or _similarity(query, r.url) >= 0.4:
                    all_valid.append(r)
        except Exception as e:
            logger.debug("Eroare la %s pentru '%s': %s", scrape_fn.__name__, product_name, e)

        _rand_delay(*DELAY_BETWEEN_SITES)

    if not all_valid:
        return None

    # Cel mai mic pret
    return min(all_valid, key=lambda r: r.price)


# ─────────────────────────── PRODUCT ITERATOR ────────────────────────────────

def iter_all_products():
    """Yield (model_class, instance) pentru toate componentele din toate modelele."""
    for model in ALL_MODELS:
        for obj in model.objects.all().iterator(chunk_size=50):
            yield model, obj


# ─────────────────────────── COMMAND ─────────────────────────────────────────

class Command(BaseCommand):
    help = "Updateaza preturile tuturor componentelor din DB de pe eMag/PCGarage/Altex/Vexio/CEL"

    def add_arguments(self, parser):
        parser.add_argument(
            "--model",
            type=str,
            default=None,
            help="Proceseaza doar un model specific (ex: GPU, CPU, RAM)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Nu scrie in DB, doar afiseaza ce ar face",
        )
        parser.add_argument(
            "--headless",
            action="store_true",
            default=True,
            help="Ruleaza browserul in mod headless (implicit True)",
        )

    def handle(self, *args, **options):
        dry_run  = options["dry_run"]
        headless = options["headless"]
        only_model = options.get("model")

        stats = {
            "procesate":  0,
            "actualizate": 0,
            "sterse":     0,
            "eroare":     0,
            "sarite":     0,
        }

        self.stdout.write("=" * 65)
        self.stdout.write("Price Updater - eMag / PCGarage / Altex / Vexio / CEL")
        if dry_run:
            self.stdout.write("  *** DRY RUN - nu se scrie in DB ***")
        self.stdout.write("=" * 65)

        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                ],
            )
            # Un singur context cu user-agent realist
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1280, "height": 800},
                locale="ro-RO",
                timezone_id="Europe/Bucharest",
            )
            page = context.new_page()
            # Blocheaza resurse inutile (imagini, fonturi) ca sa fie mai rapid
            page.route(
                "**/*.{png,jpg,jpeg,gif,webp,svg,ico,woff,woff2,ttf,eot}",
                lambda route: route.abort(),
            )

            models_to_process = ALL_MODELS
            if only_model:
                models_to_process = [
                    m for m in ALL_MODELS
                    if m.__name__.lower() == only_model.lower()
                ]
                if not models_to_process:
                    self.stderr.write(f"Model necunoscut: {only_model}")
                    return

            batch_counter = 0

            for model_class in models_to_process:
                count = model_class.objects.count()
                self.stdout.write(f"\n{'─'*65}")
                self.stdout.write(f"Model: {model_class.__name__} ({count} produse)")
                self.stdout.write("─" * 65)

                to_delete = []

                for obj in model_class.objects.all().iterator(chunk_size=50):
                    stats["procesate"] += 1
                    batch_counter += 1

                    self.stdout.write(
                        f"[{stats['procesate']:>5}] {obj.nume[:55]:<55}",
                        ending=" ",
                    )

                    try:
                        best = find_best_price(page, obj.nume)
                    except Exception as e:
                        self.stdout.write(f"EXCEPTIE: {e}")
                        stats["eroare"] += 1
                        continue

                    if best is None:
                        self.stdout.write("-> NU GASIT - se sterge")
                        to_delete.append(obj.pk)
                        stats["sterse"] += 1
                    else:
                        self.stdout.write(
                            f"-> {best.price:.2f} Lei ({best.site})"
                        )
                        if not dry_run:
                            with transaction.atomic():
                                obj.pret     = best.price
                                obj.magazin  = best.site
                                obj.url_produs = best.url
                                obj.stoc     = True
                                obj.save(update_fields=["pret", "magazin", "url_produs", "stoc"])
                        stats["actualizate"] += 1

                    # pauza intre produse
                    _rand_delay(*DELAY_BETWEEN_PRODUCTS)

                    # pauza lunga dupa un batch
                    if batch_counter % BATCH_SIZE == 0:
                        wait = random.randint(*DELAY_BETWEEN_BATCHES)
                        self.stdout.write(
                            f"\n  [Pauza antibot {wait}s dupa {BATCH_SIZE} produse...]\n"
                        )
                        time.sleep(wait)

                # Sterge produsele negasite (dupa ce am iterat modelul)
                if to_delete and not dry_run:
                    deleted, _ = model_class.objects.filter(pk__in=to_delete).delete()
                    self.stdout.write(f"  Sterse {deleted} produse din {model_class.__name__}")
                elif to_delete and dry_run:
                    self.stdout.write(f"  [DRY RUN] S-ar sterge {len(to_delete)} produse")

            context.close()
            browser.close()

        # Raport final
        self.stdout.write("\n" + "=" * 65)
        self.stdout.write("RAPORT FINAL")
        self.stdout.write("=" * 65)
        self.stdout.write(f"  Procesate:   {stats['procesate']}")
        self.stdout.write(f"  Actualizate: {stats['actualizate']}")
        self.stdout.write(f"  Sterse:      {stats['sterse']}")
        self.stdout.write(f"  Erori:       {stats['eroare']}")
        self.stdout.write("=" * 65)