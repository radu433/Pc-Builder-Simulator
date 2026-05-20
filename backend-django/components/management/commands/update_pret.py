
import re
import time
import random
import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional
from urllib.parse import quote, urljoin

from django.core.management.base import BaseCommand
from django.db import transaction

from components.models import CPU, GPU, Motherboard, RAM, PSU, Case, Cooler, Storage, Blacklist

try:
    from scrapling.fetchers import DynamicSession
except ImportError:
    raise ImportError(
        "Ruleaza: pip install 'scrapling[fetchers]' && scrapling install"
    )

logger = logging.getLogger(__name__)

# ─────────────────────────── CONFIG ──────────────────────────────────────────

DELAY_BETWEEN_PRODUCTS = (3.0, 7.0)
DELAY_BETWEEN_SITES    = (1.5, 4.0)
DELAY_BETWEEN_BATCHES  = (15, 30)

MAX_RESULTS_PER_SITE = 5
PAGE_TIMEOUT_MS      = 30_000
BATCH_SIZE           = 20

ALL_MODELS = [CPU, GPU, Motherboard, RAM, PSU, Case, Cooler, Storage]


# ─────────────────────────── DATA CLASSES ────────────────────────────────────

@dataclass
class PriceResult:
    site:           str
    price:          Decimal
    in_stoc:        bool
    url:            str
    title:          str           = field(default="")
    viteza_citire:  Optional[int] = field(default=None)
    viteza_scriere: Optional[int] = field(default=None)
    poza_url:       Optional[str] = field(default=None)


# ─────────────────────────── HELPERS ─────────────────────────────────────────

def _rand_delay(min_s: float, max_s: float):
    time.sleep(random.uniform(min_s, max_s))


def _clean_price(text: str) -> Optional[Decimal]:
    if not text:
        return None

    cleaned = re.sub(r"[^\d,.]", "", text)
    if not cleaned:
        return None

    if "." in cleaned and "," not in cleaned:
        parts = cleaned.split(".")
        if len(parts) == 2 and len(parts[1]) >= 4:
            numar_fara_puncte = parts[0] + parts[1]
            cleaned = numar_fara_puncte[:-2] + "." + numar_fara_puncte[-2:]
            return Decimal(cleaned)

    if re.search(r"\d{1,3}\.\d{3},\d{2}$", cleaned):
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif re.search(r"\d{1,3},\d{3}\.\d{2}$", cleaned):
        cleaned = cleaned.replace(",", "")
    elif "," in cleaned and "." not in cleaned:
        parts = cleaned.split(",")
        if len(parts[-1]) == 3:
            cleaned = cleaned.replace(",", "")
        else:
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


def _normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"(rtx|rx)(\d{3,4})", r"\1 \2", text)
    text = re.sub(r"(\d{3,4})(ti|xtx|xt|super|gre)", r"\1 \2", text)
    text = re.sub(r"\bo(\d{1,2})g\b", r"\1gb", text)
    text = re.sub(r"\b(\d{1,2})g\b", r"\1gb", text)
    text = re.sub(r"[-_/]", " ", text)
    return text


def _tokenize(text: str) -> set[str]:
    text = _normalize_text(text)
    tokens = re.findall(r"[a-z0-9]+", text)
    stopwords = {"the", "and", "with", "for", "de", "si", "cu"}
    return {t for t in tokens if len(t) > 1 and t not in stopwords}


def _similarity(query_name: str, result_text: str) -> float:
    q_tokens = _tokenize(query_name)
    r_tokens = _tokenize(result_text)
    if not q_tokens:
        return 0.0
    return len(q_tokens & r_tokens) / len(q_tokens)


# ─────────────────────────── QUERY BUILDING ──────────────────────────────────

_CATEGORY_PREFIX = {
    CPU:         "Procesor",
    GPU:         "Placa video",
    RAM:         "Kit RAM",
    Motherboard: "Placa de baza",
    PSU:         "Sursa",
    Case:        "Carcasa",
    Cooler:      "Cooler procesor",
}

_STORAGE_PREFIX = {
    "SSD":  "SSD",
    "NVME": "SSD NVMe",
    "HDD":  "HDD",
}


def build_query(obj, site: str = None) -> str:
    prefix = _CATEGORY_PREFIX.get(type(obj), "")

    if isinstance(obj, RAM):
        ram_prefixes = {
            "altex": "Memorie desktop",
            "emag":  "Memorie",
            "cel":   "Kit RAM",
        }
        prefix = ram_prefixes.get(site, "Kit RAM") if site else "Kit RAM"

    if isinstance(obj, GPU):
        brand = str(obj.brand).strip()
        name_lower = obj.nume.lower()

        # detectam familia chipset-ului (RTX / RX / Arc)
        if re.search(r'\brtx\b', name_lower):
            chipset_prefix = "RTX"
        elif re.search(r'\brx\b', name_lower):
            chipset_prefix = "RX"
        elif re.search(r'\barc\b', name_lower):
            chipset_prefix = "Arc"
        else:
            chipset_prefix = ""

        match_model = re.search(r'(\d{3,4})\s*(ti|xtx|xt|super|gre)?', name_lower)

        if match_model:
            baza = match_model.group(1)
            sufix = match_model.group(2) if match_model.group(2) else ""
            chipset_curat = f"{chipset_prefix} {baza} {sufix}".strip().upper()
        else:
            chipset_curat = str(obj.model_chipset).strip()
            chipset_curat = re.sub(rf"(?i)\b{brand}\b", "", chipset_curat).strip()

        vram_curat = f"{obj.vram_gb}GB" if obj.vram_gb else ""

        db_has_o_sku = bool(re.search(r"(?:-|_|\b)o\d+g\b", name_lower))
        words = re.findall(r'[a-z0-9]+', name_lower)
        is_oc = "oc" in words or db_has_o_sku
        oc_str = "OC" if is_oc else ""

        variant_words = [
            "dual", "strix", "tuf", "gaming", "ventus",
            "eagle", "aorus", "taichi", "challenger",
        ]

        variant = ""
        for v in variant_words:
            if v in name_lower:
                variant = v.upper()
                break

        query = f"{prefix} {brand} {chipset_curat} {vram_curat} {variant} {oc_str}".strip()
        return re.sub(r'\s+', ' ', query)

    elif isinstance(obj, CPU):
        return f"{prefix} {obj.nume}".strip()

    elif isinstance(obj, Motherboard):
        socket_str = obj.socket if obj.socket else ""
        wifi_str   = "WiFi" if obj.are_wifi else ""

        short_name = " ".join(obj.nume.split()[:4])

        if site == "cel":
            query = f"{prefix} {socket_str} {short_name} {wifi_str}"
        else:
            query = f"{prefix} {short_name} {socket_str} {wifi_str}"

        return re.sub(r'\s+', ' ', query.strip())

    elif isinstance(obj, Storage):
        prefix = _STORAGE_PREFIX.get(obj.tip, "SSD")
        cap = f"{obj.capacitate_gb // 1000}TB" if obj.capacitate_gb >= 1000 else f"{obj.capacitate_gb}GB"
        return f"{prefix} {obj.brand} {cap}".strip()

    elif isinstance(obj, Case):
        nume_curat = obj.nume.lower()

        fluff = [
            "tempered glass", "window", "midi-tower", "mid-tower", "midi tower", "mid tower",
            "full-tower", "full tower", "mini-tower", "mini tower", "micro-atx", "e-atx", "atx",
            "tg", "fara sursa", "cu sursa", "usb 3.0", "usb 3.1",
        ]
        for f in fluff:
            nume_curat = nume_curat.replace(f, " ")

        nume_curat = re.sub(r'-\s*(white|black|blue|red|yellow|pink|alb|negru).*', '', nume_curat)

        cuvinte = [w for w in nume_curat.split() if len(w) > 1]
        short_name = " ".join(cuvinte[:4])

        query = f"Carcasa {short_name}"
        return re.sub(r'\s+', ' ', query).strip()

    base = " ".join(obj.nume.split()[:4])
    if isinstance(obj, RAM):
        kit_name = obj.nume.strip()
        cap_str = f"{obj.capacitate_totala_gb}GB" if hasattr(obj, 'capacitate_totala_gb') and obj.capacitate_totala_gb else ""
        freq_str = f"{obj.frecventa_mhz}HZ" if hasattr(obj, 'frecventa_mhz') and obj.frecventa_mhz else ""
        latency_str = f"CL{obj.latenta_cl}" if hasattr(obj, 'latenta_cl') and obj.latenta_cl else ""
        query = f"Kit RAM {kit_name} {cap_str} {freq_str} {latency_str}"
        return re.sub(r'\s+', ' ', query.strip())

    if isinstance(obj, PSU):
        brand = str(obj.brand).strip()
        psu_name = obj.nume.strip()
        power_str = f"{obj.putere_w}W" if getattr(obj, 'putere_w', None) else ""
        cert_str = str(obj.certificare).strip() if getattr(obj, 'certificare', None) else ""
        modular_str = "Modulara" if getattr(obj, 'este_modulara', None) and str(obj.este_modulara).strip().lower() != "non" else ""

        if site == "cel":
            query = f"{prefix} {brand} {power_str} {cert_str} {psu_name} {modular_str}".strip()
        else:
            query = f"{prefix} {brand} {psu_name} {cert_str} {power_str} {modular_str}".strip()

        return re.sub(r'\s+', ' ', query)

    return re.sub(r'\s+', ' ', f"{prefix} {base}".strip())


# ─────────────────────────── VALIDARE TITLU ──────────────────────────────────

def _is_valid_title_match(title: str, obj) -> Optional[bool]:
    title_original_lower = title.lower()
    title_lower = _normalize_text(title)
    title_tokens = _tokenize(title)

    reference_str = _normalize_text(f"{obj.nume} {obj.brand}")

    if isinstance(obj, GPU) and hasattr(obj, 'model_chipset') and obj.model_chipset:
        reference_str += f" {obj.model_chipset}".lower()
    elif isinstance(obj, CPU) and hasattr(obj, 'serie') and obj.serie:
        reference_str += f" {obj.serie}".lower()

    name_lower = reference_str
    name_tokens = _tokenize(reference_str)

    cuvinte_iertate = ["radeon", "geforce", "amd", "nvidia", "intel", "rtx", "rx", "core"]

    if hasattr(obj, 'brand') and obj.brand:
        brand_real = str(obj.brand).lower().strip()
        if brand_real not in cuvinte_iertate:
            if brand_real not in title_lower:
                return False

    db_numbers = re.findall(r"\d{3,4}", name_lower)
    title_numbers = re.findall(r"\d{3,4}", title_lower)

    for num in db_numbers:
        if num not in title_numbers:
            return False

    if isinstance(obj, GPU):
        if obj.vram_gb:
            vram = str(obj.vram_gb)
            if not ((vram + "gb") in title_tokens or (vram + "g") in title_tokens):
                return False

        gpu_suffixes = ["xtx", "xt", "ti", "super", "gre"]
        for suf in gpu_suffixes:
            db_has = bool(re.search(rf"(?:\b|\d){suf}\b", name_lower))
            title_has = bool(re.search(rf"(?:\b|\d){suf}\b", title_lower))
            if db_has != title_has:
                return False

        if "white" in title_lower and "white" not in name_lower:
            return False

        nume_original_db = obj.nume.lower()
        db_has_o_sku = bool(re.search(r"(?:-|_|\b)o\d+g\b", nume_original_db))
        db_oc = "oc" in name_tokens or db_has_o_sku

        title_has_o_sku = bool(re.search(r"(?:-|_|\b)o\d+g\b", title_original_lower))
        title_oc = "oc" in title_tokens or title_has_o_sku

        if not db_oc and title_oc:
            return False
        if db_oc and not title_oc:
            return False

        gpu_variants = [
            "strix", "tuf", "dual", "phoenix", "evo",
            "gaming", "ventus", "suprim",
            "aorus", "eagle", "windforce",
            "taichi", "challenger", "phantom", "steel",
            "pulse", "nitro",
            "merc", "qick", "swift",
            "trinity", "amp",
            "founders",
        ]

        for variant in gpu_variants:
            if variant in name_lower and variant not in title_lower:
                return False

    elif isinstance(obj, CPU):
        cpu_suffixes = ["x", "xt", "k", "kf", "f", "g", "ge"]

        for suf in cpu_suffixes:
            if re.search(rf"\b{suf}\b", name_lower) and not re.search(rf"\b{suf}\b", title_lower):
                return False

    elif isinstance(obj, RAM):
        if hasattr(obj, 'capacitate_totala_gb') and obj.capacitate_totala_gb:
            cap = str(obj.capacitate_totala_gb)
            if not ((cap + "gb") in title_tokens or cap in title_tokens):
                return False

        freq = str(obj.frecventa_mhz)
        if not (freq in title_tokens or (freq + "mhz") in title_tokens):
            return False

        cl = str(obj.latenta_cl)
        if not (("cl" + cl) in title_tokens or (cl in title_tokens and "cl" in title_tokens)):
            return False

    elif isinstance(obj, PSU):
        if getattr(obj, 'putere_w', None):
            power_token = f"{obj.putere_w}w"
            if power_token not in title_lower and str(obj.putere_w) not in title_tokens:
                return False

        if getattr(obj, 'certificare', None):
            cert_text = str(obj.certificare).lower()
            cert_terms = re.findall(r"[a-z0-9]+", cert_text)
            if cert_terms and not any(term in title_lower for term in cert_terms):
                return False

        modular_value = str(getattr(obj, 'este_modulara', '')).strip().lower()
        if modular_value and modular_value != "non":
            if "modular" not in title_lower:
                return False

        return True

    elif isinstance(obj, Motherboard):
        if obj.socket:
            if obj.socket.lower() not in title_lower:
                return False

        has_wifi_in_title = "wifi" in title_tokens or "wi-fi" in title_lower
        if not obj.are_wifi and has_wifi_in_title:
            return False
        if obj.are_wifi and not has_wifi_in_title:
            return None

        if obj.format:
            format_lower = obj.format.lower()
            if format_lower in title_lower:
                pass
            else:
                return None

        return True

    elif isinstance(obj, Storage):
        if obj.capacitate_gb >= 1000:
            tb = str(obj.capacitate_gb // 1000)
            if not ((tb + "tb") in title_tokens or tb in title_tokens):
                return False
        else:
            gb = str(obj.capacitate_gb)
            if not ((gb + "gb") in title_tokens or gb in title_tokens):
                return False

    elif isinstance(obj, Case):
        name_lower = obj.nume.lower()

        model_identifiers = re.findall(r'\b[a-z]*\d+[a-z]*\b', name_lower)
        for identifier in model_identifiers:
            if identifier in ["v1", "v2", "30", "31"]:
                continue
            if identifier not in title_lower:
                return False

        db_is_white = "white" in name_lower or "alb" in name_lower
        db_is_black = "black" in name_lower or "negru" in name_lower

        title_is_white = "white" in title_lower or "alb" in title_lower
        title_is_black = "black" in title_lower or "negru" in title_lower

        if db_is_white and title_is_black and not title_is_white:
            return False
        if db_is_black and title_is_white and not title_is_black:
            return False

        if "airflow" in name_lower and "airflow" not in title_lower:
            return False
        if "airflow" not in name_lower and "airflow" in title_lower:
            return False

        db_has_rgb = "rgb" in name_lower
        title_has_rgb = "rgb" in title_lower
        if not db_has_rgb and title_has_rgb:
            return False

        if "v2" in name_lower and "v2" not in title_lower:
            return False
        if "v2" not in name_lower and "v2" in title_lower:
            return False

        return True

    return True


# ─────────────────────────── RAM HELPERS ─────────────────────────────────────

def _parse_ram_kit_info(text: str) -> tuple[Optional[int], Optional[int]]:
    if not text:
        return None, None

    normalized = text.lower()
    normalized = normalized.replace('×', 'x').replace('*', 'x')
    normalized = re.sub(r"[^0-9a-z x]", " ", normalized)

    match = re.search(r"\b\d+gb\s*\(\s*(\d+)x(\d+)gb\s*\)", normalized)
    if match:
        return int(match.group(1)), int(match.group(2))

    match = re.search(r"\b(\d+)x(\d+)gb\b", normalized)
    if match:
        return int(match.group(1)), int(match.group(2))

    match = re.search(r"\b(?:set|kit|pachet)\s*(?:de\s*)?(\d+)\b", normalized)
    if match:
        return int(match.group(1)), None

    match = re.search(r"\b(\d+)\s*(?:module|modul|stick|stickuri|bucati)\b", normalized)
    if match:
        return int(match.group(1)), None

    if "dual kit" in normalized or ("2x" in normalized and "gb" in normalized):
        return 2, None
    if "quad kit" in normalized or ("4x" in normalized and "gb" in normalized):
        return 4, None

    return None, None


def _matches_ram_module_count(text: str, obj: RAM) -> Optional[bool]:
    modules, module_gb = _parse_ram_kit_info(text)
    if modules is None:
        return None

    if obj.numar_module and modules != obj.numar_module:
        return False
    if module_gb is not None and obj.capacitate_totala_gb is not None:
        if module_gb * modules != obj.capacitate_totala_gb:
            return False
    return True


# ─────────────────────────── PAGE HELPERS ────────────────────────────────────

def _get_page_text(session, url: str) -> Optional[str]:
    try:
        page = session.fetch(url, network_idle=True)
        return " ".join(page.css("body *::text").getall())
    except Exception:
        return None


def _verify_motherboard_details(session, result: PriceResult, obj: Motherboard) -> bool:
    if not result.url:
        return False
    try:
        page = session.fetch(result.url, network_idle=True)
        _rand_delay(0.5, 1.5)
        page_text = " ".join(page.css("body *::text").getall()).lower()

        if obj.chipset:
            if obj.chipset.lower() not in page_text:
                return False

        if obj.format:
            if obj.format.lower() not in page_text:
                return False

        has_wifi = "wifi" in page_text or "wi-fi" in page_text or "wireless" in page_text
        if obj.are_wifi != has_wifi:
            return False

        has_bluetooth = "bluetooth" in page_text
        if obj.are_bluetooth != has_bluetooth:
            return False

        return True
    except Exception as e:
        logger.debug("Eroare verificare detalii MB (%s): %s", result.url, e)
        return False


def _verify_ram_module_count(session, result: PriceResult, obj: RAM) -> bool:
    if not hasattr(obj, 'numar_module') or not obj.numar_module:
        return True

    title_text = result.title or ""
    title_match = _matches_ram_module_count(title_text, obj)
    if title_match is False:
        return False
    if title_match is True:
        return True

    if result.url:
        page_text = _get_page_text(session, result.url)
        if page_text:
            page_match = _matches_ram_module_count(page_text, obj)
            if page_match is False:
                return False
            if page_match is True:
                return True

    return True


def _extract_storage_speeds_emag(session, prod_url: str) -> tuple[Optional[int], Optional[int]]:
    viteza_citire  = None
    viteza_scriere = None
    try:
        page = session.fetch(prod_url, network_idle=True)
        _rand_delay(1.0, 2.5)
        page_text = " ".join(page.css("::text").getall())

        m_citire = re.search(
            r'(?:viteza\s+(?:de\s+)?citire|read\s+speed|citire\s+secventiala)[^\d]{0,30}(\d{2,4})\s*MB',
            page_text, re.IGNORECASE,
        )
        if m_citire:
            viteza_citire = int(m_citire.group(1))

        m_scriere = re.search(
            r'(?:viteza\s+(?:de\s+)?scriere|write\s+speed|scriere\s+secventiala)[^\d]{0,30}(\d{2,4})\s*MB',
            page_text, re.IGNORECASE,
        )
        if m_scriere:
            viteza_scriere = int(m_scriere.group(1))

    except Exception as e:
        logger.debug("Eroare extragere viteze SSD eMag (%s): %s", prod_url, e)

    return viteza_citire, viteza_scriere


# ─────────────────────────── SITE SCRAPERS ───────────────────────────────────

def _card_text(card) -> str:
    return " ".join(card.css("::text").getall()).lower()


def scrape_emag(session, query: str) -> list[PriceResult]:
    """
    Selectori verificati mai 2025 din HTML real emag.ro:
    - Card:   div.card-item
    - Pret:   .product-new-price::text (int, ex "685" sau "1.259") +
              .product-new-price sup::text (zecimale, ex "90")
    - Titlu:  a.card-v2-title::text
    - URL:    a.card-v2-title::attr(href)
    - Imagine: .card-v2-thumb-inner img::attr(src)
    """
    results = []
    try:
        url = f"https://www.emag.ro/search/{quote(query, safe='')}"
        page = session.fetch(url, network_idle=True)

        cards = page.css("div.card-item")[:MAX_RESULTS_PER_SITE]
        for card in cards:
            try:
                # Pret: nodul text direct al .product-new-price = partea intreaga
                # (ex: "685" sau "1.259" cu punct separator mii)
                # Zecimalele sunt in <sup>: ex "90"
                int_text = card.css(".product-new-price::text").get("").strip()
                dec_text = card.css(".product-new-price sup::text").get("").strip()

                int_part = re.sub(r"\D", "", int_text)
                dec_part = re.sub(r"\D", "", dec_text)

                if int_part and dec_part:
                    price = Decimal(f"{int_part}.{dec_part[:2].ljust(2, '0')}")
                elif int_part:
                    price = Decimal(int_part)
                else:
                    continue

                ct = _card_text(card)
                in_stoc = "stoc epuizat" not in ct and "indisponibil" not in ct

                title = card.css(".card-v2-title::text").get("").strip()

                prod_url = card.css(".card-v2-title::attr(href)").get("").strip()
                if prod_url and not prod_url.startswith("http"):
                    prod_url = "https://www.emag.ro" + prod_url

                img_src = card.css(".card-v2-thumb-inner img::attr(src)").get("")
                poza_url = re.sub(r"\?.*", "", img_src) if img_src else None

                results.append(PriceResult("eMag", price, in_stoc, prod_url or url, title, poza_url=poza_url))
            except Exception:
                continue
    except Exception as e:
        logger.debug("eMag eroare: %s", e)
    return results


def scrape_altex(session, query: str) -> list[PriceResult]:
    """
    Selectori verificati mai 2025 din HTML real altex.ro:
    - Card:   div.Product
    - Pret:   div.text-red-brand > span.Price-int (integer) + sup (zecimale)
              ATENTIE: produsele cu reducere au doua span.Price-int — cel taiat (vechi)
              si cel din div.text-red-brand (pretul real curent). Luam DOAR pe cel din
              div.text-red-brand, altfel luam pretul gresit.
    - Titlu:  span.Product-name
    - URL:    a[href*='/cpd/'] (ambele ancore de pe card duc la acelasi produs)
    - Imagine: div.Product-photoWrapper img
    - Stoc:   div.text-green = "in stoc" | altfel text-check
    """
    results = []
    try:
        url = f"https://altex.ro/cauta/?q={quote(query, safe='')}"
        page = session.fetch(url, network_idle=True)

        cards = page.css("div.Product")[:MAX_RESULTS_PER_SITE]
        for card in cards:
            try:
                # Pretul REAL este intotdeauna in div.text-red-brand.
                # Pretul taiat (vechi) este in div.has-line-through — il ignoram.
                red_div = card.css("div.text-red-brand")
                if not red_div:
                    continue

                raw_int = red_div.css("span.Price-int::text").get("").strip()
                raw_dec = red_div.css("sup::text").get("").strip()

                # raw_int poate fi "913" sau "1.259" (punct = separator mii)
                # raw_dec este ",49" sau ",99" (virgula prefix)
                int_part = re.sub(r"\D", "", raw_int)   # "1.259" → "1259"
                dec_part = re.sub(r"\D", "", raw_dec)   # ",99"  → "99"

                if int_part and dec_part:
                    price = Decimal(f"{int_part}.{dec_part[:2].ljust(2, '0')}")
                elif int_part:
                    price = _clean_price(int_part)
                else:
                    continue

                if not price:
                    continue

                ct = _card_text(card)
                in_stoc = "stoc epuizat" not in ct and "indisponibil" not in ct

                title = card.css("span.Product-name::text").get("").strip()

                href = card.css("a[href*='/cpd/']::attr(href)").get("").strip()
                prod_url = urljoin("https://altex.ro", href) if href else url

                poza_url = (
                    card.css("div.Product-photoWrapper img::attr(src)").get("")
                    or card.css("img::attr(src)").get("")
                ) or None

                results.append(PriceResult("Altex", price, in_stoc, prod_url, title, poza_url=poza_url))
            except Exception:
                continue
    except Exception as e:
        logger.debug("Altex eroare: %s", e)
    return results


def scrape_cel(session, query: str) -> list[PriceResult]:
    """
    Selectori verificati mai 2025 din HTML real cel.ro:
    - Card:    div.product_data
    - Pret:    span.price::attr(content)  (ex: "819" — valoare intreaga, fara "lei")
    - Titlu:   h2.productTitle a span::text
    - URL:     div.productListing-poza a::attr(href)  (URL complet)
    - Imagine: div.productListing-poza img::attr(src)
    - Stoc:    strong.info_stoc cu text "In stoc" sau "In stoc furnizor"
    """
    results = []
    try:
        url = f"https://www.cel.ro/cauta/{quote(query, safe='')}/"
        page = session.fetch(url, network_idle=True)

        cards = page.css("div.product_data")[:MAX_RESULTS_PER_SITE]
        for card in cards:
            try:
                raw = card.css("span.price::attr(content)").get("").strip()
                if not raw:
                    raw = card.css("div.pret_n::text").get("").strip()
                price = _clean_price(raw)
                if not price:
                    continue

                ct = _card_text(card)
                in_stoc = "in stoc" in ct or "disponibil" in ct

                title = (
                    card.css("h2.productTitle a span::text").get("")
                    or card.css("img[alt]::attr(alt)").get("")
                ).strip()

                prod_url = (
                    card.css(".productListing-poza a::attr(href)").get("")
                    or card.css("a.product_link::attr(href)").get("")
                ).strip()
                if prod_url and not prod_url.startswith("http"):
                    prod_url = "https://www.cel.ro" + prod_url

                poza_url = card.css(".productListing-poza img::attr(src)").get("") or None

                results.append(PriceResult("CEL", price, in_stoc, prod_url or url, title, poza_url=poza_url))
            except Exception:
                continue
    except Exception as e:
        logger.debug("CEL eroare: %s", e)
    return results


def scrape_pcgarage(session, query: str) -> list[PriceResult]:
    """
    Selectori verificati mai 2025 din HTML real pcgarage.ro:
    - Card:   div.product_box_parent
    - Pret:   .pb-price .price::text  (ex: "2.699,99 RON" → _clean_price)
              Pretul vechi (taiat) este in .pbe-price-old — il ignoram.
    - Titlu:  .product_box_name h2 a::text
    - URL:    .product_box_name h2 a::attr(href)
    - Imagine: .product_box_image img::attr(src)
    - Stoc:   .product_box_availability::attr(class) contine "instock"
    """
    results = []
    try:
        url = f"https://www.pcgarage.ro/search/?search_query={quote(query, safe='')}"
        page = session.fetch(url, network_idle=True)

        cards = page.css("div.product_box_parent")[:MAX_RESULTS_PER_SITE]

        for card in cards:
            try:
                raw = card.css(".pb-price .price::text").get("").strip()
                price = _clean_price(raw)
                if not price:
                    continue

                avail_class = card.css(".product_box_availability::attr(class)").get("").lower()
                if avail_class:
                    in_stoc = "instock" in avail_class
                else:
                    ct = _card_text(card)
                    in_stoc = "stoc epuizat" not in ct and "indisponibil" not in ct

                title = card.css(".product_box_name h2 a::text").get("").strip()

                href = card.css(".product_box_name h2 a::attr(href)").get("").strip()
                prod_url = href or url
                if prod_url and not prod_url.startswith("http"):
                    prod_url = "https://www.pcgarage.ro" + prod_url

                poza_url = card.css(".product_box_image img::attr(src)").get("") or None

                results.append(PriceResult("PCGarage", price, in_stoc, prod_url, title, poza_url=poza_url))
            except Exception:
                continue
    except Exception as e:
        logger.debug("PCGarage eroare: %s", e)
    return results


def scrape_vexio(session, query: str) -> list[PriceResult]:
    """
    Selectori verificati mai 2025 din HTML real vexio.ro:
    - Card:    article.grid-group-item
    - Pret:    div.price strong::text  (ex: "3.299,99 lei" → _clean_price)
               ATENTIE: produsele cu discount au si <del> cu pretul vechi —
               div.price strong ia INTOTDEAUNA pretul curent (nu <del>).
    - Titlu:   h2.name a::text
    - URL:     h2.name a::attr(href)  (URL complet)
    - Imagine: div.image img::attr(src)
    - Stoc:    .availability::attr(class) contine "instock"
    """
    results = []
    try:
        url = f"https://www.vexio.ro/cauta/{quote(query, safe='')}/"
        page = session.fetch(url, network_idle=True)

        cards = page.css("article.grid-group-item")[:MAX_RESULTS_PER_SITE]

        for card in cards:
            try:
                raw = card.css("div.price strong::text").get("").strip()
                price = _clean_price(raw)
                if not price:
                    continue

                avail_class = card.css(".availability::attr(class)").get("").lower()
                if avail_class:
                    in_stoc = "instock" in avail_class
                else:
                    ct = _card_text(card)
                    in_stoc = "stoc epuizat" not in ct and "indisponibil" not in ct

                title = card.css("h2.name a::text").get("").strip()
                prod_url = card.css("h2.name a::attr(href)").get("").strip()
                if prod_url and not prod_url.startswith("http"):
                    prod_url = "https://www.vexio.ro" + prod_url
                poza_url = card.css("div.image img::attr(src)").get("") or None

                results.append(PriceResult("Vexio", price, in_stoc, prod_url or url, title, poza_url=poza_url))
            except Exception:
                continue
    except Exception as e:
        logger.debug("Vexio eroare: %s", e)
    return results


SITE_SCRAPERS = [
    scrape_emag,
    scrape_altex,
    scrape_cel,
    scrape_pcgarage,
    scrape_vexio,
]


# ─────────────────────────── MAIN SEARCH LOGIC ───────────────────────────────

def find_all_valid_prices(
    session,
    obj,
    min_similarity: float = 0.55,
    verbose: bool = False,
) -> list[PriceResult]:
    all_valid: list[PriceResult] = []

    for scrape_fn in SITE_SCRAPERS:
        site_name = scrape_fn.__name__.replace("scrape_", "")
        query = build_query(obj, site_name)
        if verbose:
            print(f"  [{site_name}] query: '{query}'")

        try:
            site_results = scrape_fn(session, query)

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
                        print(f"    [{site_name}] RESPINS sim={sim:.2f}<{min_similarity}: {match_text[:60]}")
                    continue

                match_result = _is_valid_title_match(match_text, obj)
                if match_result is False:
                    if verbose:
                        print(f"    [{site_name}] RESPINS spec: {r.title[:60]}")
                    continue

                if match_result is None and isinstance(obj, Motherboard):
                    if not _verify_motherboard_details(session, r, obj):
                        if verbose:
                            print(f"    [{site_name}] RESPINS page details: {r.title[:60]}")
                        continue

                if isinstance(obj, RAM) and not _verify_ram_module_count(session, r, obj):
                    if verbose:
                        print(f"    [{site_name}] RESPINS module count: {r.title[:60]}")
                    continue

                if isinstance(obj, Storage) and r.site == "eMag" and r.url:
                    if verbose:
                        print(f"    [eMag] Extrag viteze SSD...")
                    vc, vs = _extract_storage_speeds_emag(session, r.url)
                    r.viteza_citire  = vc
                    r.viteza_scriere = vs
                    if verbose:
                        print(f"    [eMag] Citire: {vc} MB/s | Scriere: {vs} MB/s")

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
    help = "Updateaza preturile tuturor componentelor din DB de pe eMag/Altex/CEL/PCGarage/Vexio"

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
        self.stdout.write("Price Updater - eMag / Altex / CEL / PCGarage / Vexio")
        if dry_run:
            self.stdout.write("  *** DRY RUN - nu se scrie in DB ***")
        self.stdout.write("=" * 65)

        models_to_process = ALL_MODELS
        if only_model:
            models_to_process = [
                m for m in ALL_MODELS
                if m.__name__.lower() == only_model.lower()
            ]
            if not models_to_process:
                self.stderr.write(f"Model necunoscut: {only_model}")
                return

        with DynamicSession(headless=headless) as session:
            batch_counter = 0

            for model_class in models_to_process:
                count = model_class.objects.count()
                self.stdout.write(f"\n{'─'*65}")
                self.stdout.write(f"Model: {model_class.__name__} ({count} produse)")
                self.stdout.write("─" * 65)

                for obj in model_class.objects.all().iterator(chunk_size=50):
                    stats["procesate"] += 1
                    batch_counter += 1

                    self.stdout.write(
                        f"[{stats['procesate']:>5}] {obj.nume[:55]:<55}",
                        ending=" ",
                    )

                    try:
                        valid_results = find_all_valid_prices(session, obj, verbose=verbose)
                    except Exception as e:
                        self.stdout.write(f"EXCEPTIE: {e}")
                        stats["eroare"] += 1
                        continue

                    if not valid_results:
                        self.stdout.write("-> NU GASIT - mutat in Blacklist si sters")

                        if not dry_run:
                            if obj.part_number:
                                Blacklist.objects.get_or_create(
                                    part_number=obj.part_number,
                                    defaults={'nume': obj.nume},
                                )
                            else:
                                Blacklist.objects.get_or_create(
                                    nume=obj.nume,
                                    defaults={'part_number': None},
                                )
                            obj.delete()

                        stats["sterse"] += 1
                    else:
                        best = valid_results[0]
                        self.stdout.write(f"-> {best.price:.2f} Lei ({best.site})")

                        if isinstance(obj, Storage):
                            citire_str  = f"{best.viteza_citire} MB/s"  if best.viteza_citire  is not None else "N/A"
                            scriere_str = f"{best.viteza_scriere} MB/s" if best.viteza_scriere is not None else "N/A"
                            self.stdout.write(
                                f"       Viteze SSD -> citire: {citire_str:<12} scriere: {scriere_str}"
                            )

                        if not dry_run:
                            update_fields = ["pret", "magazin", "url_produs", "stoc"]
                            obj.pret       = best.price
                            obj.magazin    = best.site
                            obj.url_produs = best.url
                            obj.stoc       = True

                            if (
                                isinstance(obj, Storage)
                                and best.viteza_citire is not None
                                and hasattr(obj, 'viteza_citire')
                            ):
                                obj.viteza_citire  = best.viteza_citire
                                obj.viteza_scriere = best.viteza_scriere
                                update_fields += ["viteza_citire", "viteza_scriere"]

                            if (
                                hasattr(obj, 'imagine_url')
                                and not obj.imagine_url
                                and best.poza_url
                            ):
                                obj.imagine_url = best.poza_url
                                update_fields.append("imagine_url")
                                self.stdout.write(f"       URL imagine salvat: {best.poza_url[:60]}...")

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

        self.stdout.write("\n" + "=" * 65)
        self.stdout.write("RAPORT FINAL")
        self.stdout.write("=" * 65)
        self.stdout.write(f"  Procesate:   {stats['procesate']}")
        self.stdout.write(f"  Actualizate: {stats['actualizate']}")
        self.stdout.write(f"  Sterse (-> Blacklist): {stats['sterse']}")
        self.stdout.write(f"  Erori:       {stats['eroare']}")
        self.stdout.write("=" * 65)
