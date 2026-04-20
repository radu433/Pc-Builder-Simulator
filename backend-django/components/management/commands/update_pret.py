"""
Scraper preturi pentru PC Builder Simulator.

Dependinte extra fata de ce ai deja:
    pip install playwright
    playwright install chromium

Cauta fiecare componenta din DB pe: eMag, Altex, CEL
Ia primele 5 rezultate, verifica stoc, compara preturi, updateaza DB.
Daca nu e gasit pe niciun site -> sterge din DB.
"""

import re
import time
import random
import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional

from django.core.management.base import BaseCommand
from django.db import transaction

from components.models import CPU, GPU, Motherboard, RAM, PSU, Case, Cooler, Storage

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
except ImportError:
    raise ImportError("Ruleaza: pip install playwright && playwright install chromium")

try:
    from playwright_stealth import stealth_sync
    _STEALTH_AVAILABLE = True
except ImportError:
    _STEALTH_AVAILABLE = False

import os
from pathlib import Path

logger = logging.getLogger(__name__)

BROWSER_PROFILE_DIR = Path.home() / ".playwright-profile"

# ─────────────────────────── CONFIG ──────────────────────────────────────────

DELAY_BETWEEN_PRODUCTS = (3.0, 7.0)
DELAY_BETWEEN_SITES    = (1.5, 4.0)
DELAY_BETWEEN_BATCHES  = (15, 30)

MAX_RESULTS_PER_SITE = 5
PAGE_TIMEOUT_MS      = 20_000
BATCH_SIZE           = 20

ALL_MODELS = [CPU, GPU, Motherboard, RAM, PSU, Case, Cooler, Storage]

# ─────────────────────────── ANTI-BOT ────────────────────────────────────────

# User agents reale de Chrome/Firefox actualizate periodic
_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

# Rezolutii comune de monitoare — variatie usoara de fingerprint
_VIEWPORTS = [
    {"width": 1920, "height": 1080},
    {"width": 1440, "height": 900},
    {"width": 1366, "height": 768},
    {"width": 1280, "height": 800},
]

_EXTRA_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "ro-RO,ro;q=0.9,en-US;q=0.8,en;q=0.7",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
}


def _new_context(browser):
    """Creeaza un context browser cu UA si viewport aleatorii + headers realiste."""
    ctx = browser.new_context(
        user_agent=random.choice(_USER_AGENTS),
        viewport=random.choice(_VIEWPORTS),
        locale="ro-RO",
        timezone_id="Europe/Bucharest",
        extra_http_headers=_EXTRA_HEADERS,
    )
    return ctx

# ─────────────────────────── DATA CLASSES ────────────────────────────────────

@dataclass
class PriceResult:
    site:    str
    price:   Decimal
    in_stoc: bool
    url:     str
    title:   str = field(default="")


# ─────────────────────────── HELPERS ─────────────────────────────────────────

def _rand_delay(min_s: float, max_s: float):
    time.sleep(random.uniform(min_s, max_s))


def _clean_price(text: str) -> Optional[Decimal]:
    """Extrage primul numar dintr-un string de pret. '1.299,99 Lei' -> 1299.99"""
    if not text:
        return None
    cleaned = re.sub(r"[^\d,.]", "", text)
    if re.search(r"\d{1,3}\.\d{3},\d{2}$", cleaned):
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif "," in cleaned and "." not in cleaned:
        cleaned = cleaned.replace(",", ".")
    elif "." in cleaned and "," not in cleaned:
        parts = cleaned.split(".")
        if len(parts[-1]) == 3:
            cleaned = cleaned.replace(".", "")
    m = re.search(r"\d+(\.\d+)?", cleaned)
    try:
        return Decimal(m.group()) if m else None
    except Exception:
        return None


def _tokenize(text: str) -> set[str]:
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    stopwords = {"the", "and", "with", "for", "de", "si", "cu"}
    return {t for t in tokens if len(t) > 1 and t not in stopwords}


def _similarity(query_name: str, result_text: str) -> float:
    """Proportia de tokeni din query_name care apar in result_text."""
    q_tokens = _tokenize(query_name)
    r_tokens = _tokenize(result_text)
    if not q_tokens:
        return 0.0
    return len(q_tokens & r_tokens) / len(q_tokens)


# ─────────────────────────── QUERY BUILDING ──────────────────────────────────

_CATEGORY_PREFIX = {
    CPU:         "Procesor",
    GPU:         "Placa video",
    RAM:         "Memorie RAM",
    Motherboard: "Placa de baza",
    PSU:         "Sursa",
    Case:        "Carcasa",
    Cooler:      "Cooler",
}

_STORAGE_PREFIX = {
    "SSD":  "SSD",
    "NVME": "SSD NVMe",
    "HDD":  "HDD",
}


def build_query(obj) -> str:
    """Construieste query-ul de cautare adaptat tipului de componenta."""
    # Prefixul categoriei impiedica site-urile sa returneze laptopuri/prebuilturi
    prefix = _CATEGORY_PREFIX.get(type(obj), "")
    if isinstance(obj, Storage):
        prefix = _STORAGE_PREFIX.get(obj.tip, "SSD")

    base = " ".join(obj.nume.split()[:6])

    if isinstance(obj, GPU):
        base = f"{base} {obj.vram_gb}GB"
    elif isinstance(obj, RAM):
        base = f"{base} {obj.frecventa_mhz}MHz CL{obj.latenta_cl}"
    elif isinstance(obj, Storage):
        cap = f"{obj.capacitate_gb // 1000}TB" if obj.capacitate_gb >= 1000 else f"{obj.capacitate_gb}GB"
        base = f"{base} {cap}"

    return f"{prefix} {base}".strip()


def _is_valid_title_match(title: str, obj) -> bool:
    """
    Verifica daca titlul rezultatului corespunde componentei din DB.
    Aplica filtre specifice tipului de componenta.
    """
    title_tokens = _tokenize(title)

    # Regula generala: tokenii cu cifre din DB name trebuie sa apara in titlu.
    # Ex: DB="5600X" → "5600x" trebuie in titlu; respinge "5600" si "9600X".
    # Nu aplicam pentru GPU/RAM/Storage care au verificari dedicate mai flexibile.
    if not isinstance(obj, (GPU, RAM, Storage)):
        model_tokens = {t for t in _tokenize(obj.nume) if re.search(r"\d", t)}
        if model_tokens and not model_tokens.issubset(title_tokens):
            return False

    if isinstance(obj, GPU):
        # Trebuie sa contina VRAM-ul corect (ex: "8gb" sau "8g")
        vram = str(obj.vram_gb)
        has_vram = (vram + "gb") in title_tokens or (vram + "g") in title_tokens
        if not has_vram:
            return False

        # Daca produsul din DB nu e OC, excludem variantele OC
        db_name_lower = obj.nume.lower()
        product_is_oc = bool(re.search(r'\boc\b', db_name_lower))
        result_is_oc  = bool(re.search(r'\boc\b', title.lower()))
        if not product_is_oc and result_is_oc:
            return False

    elif isinstance(obj, RAM):
        # Frecventa trebuie sa apara in titlu
        freq = str(obj.frecventa_mhz)
        has_freq = freq in title_tokens or (freq + "mhz") in title_tokens
        if not has_freq:
            return False

        # CL trebuie sa apara: "cl30" combinat SAU "cl" + "30" separat
        cl = str(obj.latenta_cl)
        has_cl = (
            ("cl" + cl) in title_tokens
            or (cl in title_tokens and "cl" in title_tokens)
        )
        if not has_cl:
            return False

    elif isinstance(obj, Storage):
        # Capacitatea trebuie sa apara in titlu
        if obj.capacitate_gb >= 1000:
            tb = str(obj.capacitate_gb // 1000)
            has_cap = (tb + "tb") in title_tokens or tb in title_tokens
        else:
            gb = str(obj.capacitate_gb)
            has_cap = (gb + "gb") in title_tokens or gb in title_tokens
        if not has_cap:
            return False

    return True


# ─────────────────────────── URL DISCOVERY ───────────────────────────────────
#
# Modifica doar aceste 3 dictionare cand un site isi schimba URL-ul sau selectoarele.
# {q} = query cu spatii inlocuite de "+"
# "FORM_FILL" = sentinel special pentru PCGarage (bara de cautare din JS)

_SEARCH_URL_PATTERNS: dict[str, list[str]] = {
    "emag": [
        "https://www.emag.ro/search/{q}",
        "https://www.emag.ro/cautare/{q}",
    ],
    "pcgarage": [
        "https://www.pcgarage.ro/cauta/?search_query={q}",
        "FORM_FILL",
    ],
    "altex": [
        "https://altex.ro/cauta/?q={q}",
        "https://altex.ro/search?q={q}",
        "https://altex.ro/cautare/{q}/",
    ],
    "vexio": [
        "https://www.vexio.ro/search?q={q}",
        "https://www.vexio.ro/cautare/{q}/",
        "https://www.vexio.ro/cauta/?q={q}",
    ],
    "cel": [
        "https://www.cel.ro/cauta/{q}/",
        "https://www.cel.ro/search/{q}/",
        "https://www.cel.ro/cautare/?q={q}",
    ],
}

_CARD_SELECTORS: dict[str, list[str]] = {
    "emag":     ["div.card-item", "div.product-card", "article.product"],
    "pcgarage": ["div.product_box", "div.product-item", "li.product-item"],
    "altex":    ["div.Product", "div.product-card", "article.product"],
    "vexio":    ["article.product-box", "div.product-item", "div.product-card"],
    "cel":      ["div.product_data", "div.productListing-item", "article.product"],
}

_COOKIE_BTN: dict[str, str] = {
    "emag":     "button:has-text('Sunt de acord'), button:has-text('Accept')",
    "pcgarage": "button:has-text('Accept'), button:has-text('De acord'), button:has-text('OK')",
    "altex":    "button:has-text('Acceptati tot'), button:has-text('Accept all'), button:has-text('Accept')",
    "vexio":    "button:has-text('Permite toate'), button:has-text('Accept toate'), button:has-text('Accept')",
    "cel":      "button:has-text('Accept'), button:has-text('OK'), button:has-text('Accepta')",
}

# Cache per sesiune: site -> (url_template_care_a_functionat, card_selector_care_a_functionat)
_url_session_cache: dict[str, tuple[str, str]] = {}


def _dismiss_cookie(page, site: str):
    """Inchide popup-ul de cookies. Silent daca nu e gasit."""
    sel = _COOKIE_BTN.get(site, "")
    if not sel:
        return
    try:
        btn = page.wait_for_selector(sel, timeout=2500)
        if btn:
            btn.click()
            page.wait_for_timeout(300)
    except Exception:
        pass


def _navigate_results(page, site: str, query: str) -> tuple[Optional[str], Optional[str]]:
    """
    Navigheza pe pagina de rezultate si returneaza (url_actual, card_selector).
    Prima apelare: testeaza patternurile in ordine pana gaseste unul cu rezultate.
    Apelari ulterioare: foloseste patternul din cache, daca esueaza re-detecteaza.
    Returneaza (None, None) daca niciun pattern nu functioneaza.
    """
    q = query.replace(" ", "+")

    def _try_patterns(skip_cache=False):
        patterns = _SEARCH_URL_PATTERNS.get(site, [])
        selectors = _CARD_SELECTORS.get(site, [])

        for url_tpl in patterns:
            # Daca avem cache si nu skipam, sarim direct la pattern-ul cunoscut
            if not skip_cache and site in _url_session_cache:
                cached_tpl, cached_sel = _url_session_cache[site]
                if url_tpl != cached_tpl and url_tpl != "FORM_FILL":
                    continue

            if url_tpl == "FORM_FILL":
                try:
                    page.goto("https://www.pcgarage.ro/", timeout=PAGE_TIMEOUT_MS, wait_until="domcontentloaded")
                    _dismiss_cookie(page, site)
                    search_el = page.wait_for_selector("input[name='search_query']", timeout=5000)
                    search_el.fill(query)
                    search_el.press("Enter")
                    for sel in selectors:
                        try:
                            page.wait_for_selector(sel, timeout=8000)
                            logger.debug("[%s] FORM_FILL ok | sel: %s", site, sel)
                            _url_session_cache[site] = ("FORM_FILL", sel)
                            return page.url, sel
                        except PWTimeout:
                            continue
                except Exception:
                    pass
                continue

            url = url_tpl.replace("{q}", q)
            try:
                page.goto(url, timeout=PAGE_TIMEOUT_MS, wait_until="domcontentloaded")
                _dismiss_cookie(page, site)
                # Vexio: scroll pentru lazy-load
                if site == "vexio":
                    page.evaluate("window.scrollTo(0, 300)")
                    page.wait_for_timeout(500)
                for sel in selectors:
                    try:
                        page.wait_for_selector(sel, timeout=6000)
                        logger.debug("[%s] URL ok: %s | sel: %s", site, url_tpl, sel)
                        _url_session_cache[site] = (url_tpl, sel)
                        return url, sel
                    except PWTimeout:
                        continue
            except Exception:
                continue

        return None, None

    # Incearca cu cache
    page_url, card_sel = _try_patterns(skip_cache=False)
    if page_url:
        return page_url, card_sel

    # Cache-ul s-a demodat — curatam si re-detectam
    if site in _url_session_cache:
        logger.debug("[%s] Pattern cacheuit nu mai functioneaza, re-detectez...", site)
        del _url_session_cache[site]
        page_url, card_sel = _try_patterns(skip_cache=True)

    return page_url, card_sel


# ─────────────────────────── SITE SCRAPERS ───────────────────────────────────

def scrape_emag(page, query: str) -> list[PriceResult]:
    results = []
    try:
        url, card_sel = _navigate_results(page, "emag", query)
        if not url:
            logger.debug("eMag: niciun URL pattern nu a functionat pentru: %s", query)
            return results

        cards = page.query_selector_all(card_sel)[:MAX_RESULTS_PER_SITE]
        for card in cards:
            try:
                price_el = card.query_selector(".product-new-price")
                if not price_el:
                    continue
                # eMag afiseaza pretul ca "659<sup>99</sup><span>Lei</span>"
                # Extragem partea intreaga din primul text node si zecimalele din <sup>
                integer_part = price_el.evaluate("el => el.firstChild ? el.firstChild.nodeValue : ''").strip()
                sup_el = price_el.query_selector("sup")
                decimal_part = sup_el.inner_text().strip() if sup_el else "00"
                price = _clean_price(f"{integer_part},{decimal_part}")
                if not price:
                    # fallback la inner_text standard
                    price = _clean_price(price_el.inner_text())
                if not price:
                    continue

                # data-availability-id="3" inseamna "in stoc" pe eMag (confirmat din API)
                avail_id = card.get_attribute("data-availability-id")
                in_stoc = (avail_id == "3") if avail_id else True

                # Titlul si URL-ul sunt direct pe card ca atribute data-*
                title    = card.get_attribute("data-name") or ""
                prod_url = card.get_attribute("data-url") or ""

                if not title or not prod_url:
                    # fallback: link-ul imaginii are aria-label si href
                    link_el = card.query_selector("a.js-product-url, a[aria-label][href]")
                    if link_el:
                        if not title:
                            title = link_el.get_attribute("aria-label") or ""
                        if not prod_url:
                            prod_url = link_el.get_attribute("href") or url

                if prod_url and not prod_url.startswith("http"):
                    prod_url = "https://www.emag.ro" + prod_url

                results.append(PriceResult("eMag", price, in_stoc, prod_url or url, title))
            except Exception:
                continue
    except PWTimeout:
        logger.debug("eMag timeout pentru: %s", query)
    except Exception as e:
        logger.debug("eMag eroare: %s", e)
    return results


def scrape_pcgarage(page, query: str) -> list[PriceResult]:
    results = []
    try:
        url, card_sel = _navigate_results(page, "pcgarage", query)
        if not url:
            logger.debug("PCGarage: niciun URL pattern nu a functionat pentru: %s", query)
            return results

        cards = page.query_selector_all(card_sel)[:MAX_RESULTS_PER_SITE]
        for card in cards:
            try:
                # Selector confirmat din DevTools: div.pb-price > p.price (text: "209,99 RON")
                price_el = card.query_selector("div.pb-price p.price")
                if not price_el:
                    price_el = card.query_selector("p.price")
                if not price_el:
                    continue
                price = _clean_price(price_el.inner_text())
                if not price:
                    continue

                # Stoc confirmat din DevTools: div.product_box_availability cu clasa "instoc"
                stoc_el = card.query_selector("div.product_box_availability")
                stoc_class = (stoc_el.get_attribute("class") or "").lower() if stoc_el else ""
                stoc_text  = (stoc_el.inner_text() if stoc_el else "").lower()
                in_stoc = "instoc" in stoc_class or "stoc" in stoc_text or "disponibil" in stoc_text

                # Titlul: atributul title de pe link-ul imaginii (confirmat din DOM)
                # ex: title="Procesor AMD Ryzen 5 5600 3.5GHz Box"
                link_el = card.query_selector("a[title][href]")
                title = ""
                prod_url = url
                if link_el:
                    title = link_el.get_attribute("title") or ""
                    prod_url = link_el.get_attribute("href") or url

                if not title:
                    # fallback: text din primul link din card
                    fallback = card.query_selector("a[href]")
                    if fallback:
                        title = fallback.inner_text().strip()
                        prod_url = fallback.get_attribute("href") or url

                if prod_url and not prod_url.startswith("http"):
                    prod_url = "https://www.pcgarage.ro" + prod_url

                results.append(PriceResult("PCGarage", price, in_stoc, prod_url, title))
            except Exception:
                continue
    except PWTimeout:
        logger.debug("PCGarage timeout pentru: %s", query)
        if 'url' in dir():
            logger.debug("  URL: %s", url)
    except Exception as e:
        logger.debug("PCGarage eroare: %s", e)
    return results


def scrape_altex(page, query: str) -> list[PriceResult]:
    results = []
    try:
        # URL corect confirmat din browser (nu /search/ ci /cauta/?q=)
        url = f"https://altex.ro/cauta/?q={query.replace(' ', '%20')}"
        page.goto(url, timeout=PAGE_TIMEOUT_MS, wait_until="domcontentloaded")
        # Dismiss cookie popup (blocheaza networkidle prin tracking scripts)
        try:
            btn = page.wait_for_selector("button:has-text('Acceptati tot')", timeout=3000)
            if btn:
                btn.click()
                page.wait_for_timeout(300)
        except Exception:
            pass
        # Card confirmat din DevTools: div.Product (Tailwind, nu clase semantice)
        page.wait_for_selector("div.Product", timeout=15000)

        cards = page.query_selector_all("div.Product")[:MAX_RESULTS_PER_SITE]
        for card in cards:
            try:
                # Altex: "2.599<sup>99</sup> lei"
                # sup trebuie cautat in parintele span.Price-int, nu in tot cardul
                price_int_el = card.query_selector("span.Price-int")
                if price_int_el:
                    int_part = price_int_el.inner_text().strip()
                    dec_part = price_int_el.evaluate(
                        "el => el.parentElement?.querySelector('sup')?.innerText || '00'"
                    ).strip()
                    price = _clean_price(f"{int_part},{dec_part}")
                else:
                    price = None
                if not price:
                    continue

                # Stoc: "stoc epuizat" sau "indisponibil" in textul cardului = indisponibil
                card_text = card.inner_text().lower()
                in_stoc = "stoc epuizat" not in card_text and "indisponibil" not in card_text

                # Titlul: span.Product-name (confirmat din DOM)
                title    = ""
                prod_url = url
                title_el = card.query_selector("span.Product-name")
                if title_el:
                    title = title_el.inner_text().strip()

                link_el = card.query_selector("a[title][href]")
                if link_el:
                    if not title:
                        title = link_el.get_attribute("title") or ""
                    prod_url = link_el.get_attribute("href") or url

                if prod_url and not prod_url.startswith("http"):
                    prod_url = "https://altex.ro" + prod_url

                results.append(PriceResult("Altex", price, in_stoc, prod_url, title))
            except Exception:
                continue
    except PWTimeout:
        logger.debug("Altex timeout pentru: %s", query)
    except Exception as e:
        logger.debug("Altex eroare: %s", e)
    return results



def scrape_vexio(page, query: str) -> list[PriceResult]:
    results = []
    try:
        url, card_sel = _navigate_results(page, "vexio", query)
        if not url:
            logger.debug("Vexio: niciun URL pattern nu a functionat pentru: %s", query)
            return results

        cards = page.query_selector_all(card_sel)[:MAX_RESULTS_PER_SITE]
        for card in cards:
            try:
                # Selector confirmat din DevTools: div.price > div.pull-left > strong (text: "662,99 lei")
                price_el = card.query_selector("div.price .pull-left strong")
                if not price_el:
                    price_el = card.query_selector("div.price strong")
                if not price_el:
                    continue
                price = _clean_price(price_el.inner_text())
                if not price:
                    continue

                # Stoc confirmat din DevTools: div.availability cu clasa "instock"
                stoc_el = card.query_selector("div.availability")
                stoc_class = (stoc_el.get_attribute("class") or "").lower() if stoc_el else ""
                in_stoc = "instock" in stoc_class

                # Titlul: atribut title pe link-ul imaginii (confirmat din DOM)
                # ex: title="AMD Procesor Ryzen 5 5600 3.50GHz, Socket AM4, Tray, fara cooler"
                link_el = card.query_selector("a[title][href]")
                title = ""
                prod_url = url
                if link_el:
                    title    = link_el.get_attribute("title") or ""
                    prod_url = link_el.get_attribute("href") or url

                if prod_url and not prod_url.startswith("http"):
                    prod_url = "https://www.vexio.ro" + prod_url

                results.append(PriceResult("Vexio", price, in_stoc, prod_url, title))
            except Exception:
                continue
    except PWTimeout:
        logger.debug("Vexio timeout pentru: %s", query)
    except Exception as e:
        logger.debug("Vexio eroare: %s", e)
    return results


def scrape_cel(page, query: str) -> list[PriceResult]:
    results = []
    try:
        # URL confirmat din browser: /cauta/{query}/ (query in path, nu querystring)
        url = f"https://www.cel.ro/cauta/{query.replace(' ', '+')}/"
        page.goto(url, timeout=PAGE_TIMEOUT_MS, wait_until="domcontentloaded")
        # Dismiss cookie popup daca exista
        try:
            btn = page.wait_for_selector("button:has-text('Accept'), button:has-text('OK'), button:has-text('Accepta')", timeout=3000)
            if btn:
                btn.click()
                page.wait_for_timeout(300)
        except Exception:
            pass
        # Card confirmat din DevTools: div.product_data (clasa completa: product_data productListing-tot)
        page.wait_for_selector("div.product_data", timeout=15000)

        cards = page.query_selector_all("div.product_data")[:MAX_RESULTS_PER_SITE]
        for card in cards:
            try:
                # Selector confirmat din DevTools: span.price cu content="609"
                price_el = card.query_selector("span.price[content]")
                if price_el:
                    # content= are valoarea numerica curata, fara "lei"
                    raw = price_el.get_attribute("content") or price_el.inner_text()
                else:
                    price_el = card.query_selector("div.pret_n")
                    if not price_el:
                        continue
                    raw = price_el.inner_text()
                price = _clean_price(raw)
                if not price:
                    continue

                # "In stoc" si "In stoc furnizor" = disponibil
                card_text = card.inner_text().lower()
                in_stoc = "in stoc" in card_text or "disponibil" in card_text

                # Titlul: h2.productTitle (confirmat din DOM)
                title = ""
                title_el = card.query_selector("h2.productTitle")
                if title_el:
                    title = title_el.inner_text().strip()

                if not title:
                    img_el = card.query_selector("img[alt]")
                    if img_el:
                        title = img_el.get_attribute("alt") or ""

                # URL: link-ul din zona imaginii
                link_el = card.query_selector(".productListing-poza a[href], a[href]")
                prod_url = link_el.get_attribute("href") if link_el else url
                if prod_url and not prod_url.startswith("http"):
                    prod_url = "https://www.cel.ro" + prod_url

                results.append(PriceResult("CEL", price, in_stoc, prod_url or url, title))
            except Exception:
                continue
    except PWTimeout:
        logger.debug("CEL timeout pentru: %s", query)
    except Exception as e:
        logger.debug("CEL eroare: %s", e)
    return results


SITE_SCRAPERS = [
    scrape_emag,
    scrape_altex,
    scrape_cel,
]


# ─────────────────────────── STORAGE SPEEDS ──────────────────────────────────

def fetch_storage_speeds_pcgarage(page, url: str) -> tuple[Optional[int], Optional[int]]:
    """
    Deschide pagina produsului pe PCGarage si extrage vitezele de citire/scriere.
    Returneaza (viteza_citire_mb_s, viteza_scriere_mb_s) sau (None, None).
    """
    try:
        page.goto(url, timeout=PAGE_TIMEOUT_MS, wait_until="domcontentloaded")
        page.wait_for_selector(
            ".specifications, .specs, #specifications, table.spec-table, .product-specifications",
            timeout=6000,
        )
        rows = page.query_selector_all(
            ".specifications tr, .specs tr, #specifications tr, "
            "table.spec-table tr, .product-specifications tr"
        )

        citire = scriere = None
        for row in rows:
            try:
                text = row.inner_text().lower()
                # Extragem numarul din randul respectiv (cel mai mare, minim 50 MB/s)
                nums = [int(n) for n in re.findall(r"\d+", text) if int(n) > 50]
                if not nums:
                    continue
                val = max(nums)

                if any(kw in text for kw in ("citire", "read", "lectura")):
                    citire = val
                elif any(kw in text for kw in ("scriere", "write")):
                    scriere = val
            except Exception:
                continue

        return citire, scriere
    except PWTimeout:
        logger.debug("PCGarage speeds timeout: %s", url)
    except Exception as e:
        logger.debug("PCGarage speeds eroare: %s", e)
    return None, None


# ─────────────────────────── MAIN SEARCH LOGIC ───────────────────────────────

def find_all_valid_prices(
    page,
    obj,
    min_similarity: float = 0.55,
    verbose: bool = False,
) -> list[PriceResult]:
    """
    Cauta componenta pe toate site-urile.
    Filtreaza dupa: stoc, similaritate titlu, specificatii specifice tipului.
    Returneaza lista sortata dupa pret (cel mai mic primul).
    """
    query = build_query(obj)
    all_valid: list[PriceResult] = []

    if verbose:
        print(f"  Query: '{query}'")

    for scrape_fn in SITE_SCRAPERS:
        site_name = scrape_fn.__name__.replace("scrape_", "")
        try:
            site_results = scrape_fn(page, query)

            if verbose and not site_results:
                print(f"    [{site_name}] 0 rezultate (timeout sau selector negasit)")

            for r in site_results:
                if not r.in_stoc:
                    if verbose:
                        print(f"    [{site_name}] RESPINS stoc: {r.price} | {r.title[:60]}")
                    continue

                match_text = r.title if r.title else r.url
                sim = _similarity(obj.nume, match_text)

                if sim < min_similarity:
                    if verbose:
                        print(f"    [{site_name}] RESPINS sim={sim:.2f}<{min_similarity}: {r.title[:60] or r.url[:60]}")
                    continue

                if not _is_valid_title_match(match_text, obj):
                    if verbose:
                        print(f"    [{site_name}] RESPINS spec: {r.title[:60]}")
                    continue

                if verbose:
                    print(f"    [{site_name}] OK {r.price:.2f} Lei | {r.title[:60]}")
                all_valid.append(r)
        except Exception as e:
            logger.debug("Eroare la %s pentru '%s': %s", scrape_fn.__name__, obj.nume, e)
            if verbose:
                print(f"    [{site_name}] EXCEPTIE: {e}")

        _rand_delay(*DELAY_BETWEEN_SITES)

    all_valid.sort(key=lambda r: r.price)
    return all_valid


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
            default=False,
            help="Ruleaza browserul in mod headless (implicit False = browser vizibil)",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            default=False,
            help="Afiseaza detalii despre fiecare rezultat (respins/acceptat + motiv)",
        )

    def handle(self, *args, **options):
        # sync_playwright creeaza un event loop asyncio intern; Django refuza ORM sincron
        # in acel context -> DJANGO_ALLOW_ASYNC_UNSAFE dezactiveaza verificarea pt scripturi
        import os
        os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

        dry_run    = options["dry_run"]
        headless   = options["headless"]
        only_model = options.get("model")
        verbose    = options["verbose"]

        stats = {
            "procesate":   0,
            "actualizate": 0,
            "sterse":      0,
            "eroare":      0,
        }

        self.stdout.write("=" * 65)
        self.stdout.write("Price Updater - eMag / PCGarage / Altex / Vexio / CEL")
        if dry_run:
            self.stdout.write("  *** DRY RUN - nu se scrie in DB ***")
        self.stdout.write("=" * 65)

        with sync_playwright() as pw:
            # Profil persistent: cookies/sesiuni salvate intre rulari
            # Prima rulare: accepta manual cookies pe fiecare site
            # Rularile ulterioare: site-urile te recunosc ca vizitator real
            BROWSER_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
            context = pw.chromium.launch_persistent_context(
                user_data_dir=str(BROWSER_PROFILE_DIR),
                headless=headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                ],
                user_agent=random.choice(_USER_AGENTS),
                viewport=random.choice(_VIEWPORTS),
                locale="ro-RO",
                timezone_id="Europe/Bucharest",
                extra_http_headers=_EXTRA_HEADERS,
            )
            page = context.new_page()
            if _STEALTH_AVAILABLE:
                stealth_sync(page)
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
                    context.close()
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
                        valid_results = find_all_valid_prices(page, obj, verbose=verbose)
                    except Exception as e:
                        self.stdout.write(f"EXCEPTIE: {e}")
                        stats["eroare"] += 1
                        continue

                    if not valid_results:
                        # Negasit pe niciun site -> se sterge
                        self.stdout.write("-> NU GASIT - se sterge")
                        to_delete.append(obj.pk)
                        stats["sterse"] += 1
                    else:
                        best = valid_results[0]  # sortat dupa pret, cel mai mic primul
                        sites_found = len({r.site for r in valid_results})
                        self.stdout.write(f"-> {best.price:.2f} Lei ({best.site})")

                        if not dry_run:
                            update_fields = ["pret", "magazin", "url_produs", "stoc"]

                            obj.pret       = best.price
                            obj.magazin    = best.site
                            obj.url_produs = best.url
                            obj.stoc       = True

                            # Pentru Storage incercam sa luam vitezele de pe PCGarage
                            if isinstance(obj, Storage):
                                pcgarage_results = [r for r in valid_results if r.site == "PCGarage"]
                                if pcgarage_results:
                                    citire, scriere = fetch_storage_speeds_pcgarage(
                                        page, pcgarage_results[0].url
                                    )
                                    if citire is not None:
                                        obj.viteza_citire_mb_s = citire
                                        update_fields.append("viteza_citire_mb_s")
                                        self.stdout.write(f"       Viteza citire:  {citire} MB/s")
                                    if scriere is not None:
                                        obj.viteza_scriere_mb_s = scriere
                                        update_fields.append("viteza_scriere_mb_s")
                                        self.stdout.write(f"       Viteza scriere: {scriere} MB/s")

                            with transaction.atomic():
                                obj.save(update_fields=update_fields)

                        stats["actualizate"] += 1

                    _rand_delay(*DELAY_BETWEEN_PRODUCTS)

                    if batch_counter % BATCH_SIZE == 0:
                        wait = random.randint(*DELAY_BETWEEN_BATCHES)
                        self.stdout.write(
                            f"\n  [Pauza antibot {wait}s dupa {BATCH_SIZE} produse...]\n"
                        )
                        time.sleep(wait)

                if to_delete and not dry_run:
                    deleted, _ = model_class.objects.filter(pk__in=to_delete).delete()
                    self.stdout.write(f"  Sterse {deleted} produse din {model_class.__name__}")
                elif to_delete and dry_run:
                    self.stdout.write(f"  [DRY RUN] S-ar sterge {len(to_delete)} produse")

            context.close()

        self.stdout.write("\n" + "=" * 65)
        self.stdout.write("RAPORT FINAL")
        self.stdout.write("=" * 65)
        self.stdout.write(f"  Procesate:   {stats['procesate']}")
        self.stdout.write(f"  Actualizate: {stats['actualizate']}")
        self.stdout.write(f"  Sterse:      {stats['sterse']}")
        self.stdout.write(f"  Erori:       {stats['eroare']}")
        self.stdout.write("=" * 65)