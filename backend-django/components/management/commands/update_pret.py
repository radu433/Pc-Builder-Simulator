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
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional

from django.core.management.base import BaseCommand
from django.db import transaction

from components.models import CPU, GPU, Motherboard, RAM, PSU, Case, Cooler, Storage, Blacklist

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

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

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
    site:           str
    price:          Decimal
    in_stoc:        bool
    url:            str
    title:          str           = field(default="")
    viteza_citire:  Optional[int] = field(default=None)  # MB/s
    viteza_scriere: Optional[int] = field(default=None)  # MB/s


# ─────────────────────────── HELPERS ─────────────────────────────────────────

def _rand_delay(min_s: float, max_s: float):
    time.sleep(random.uniform(min_s, max_s))


def _clean_price(text: str) -> Optional[Decimal]:
    if not text:
        return None

    cleaned = re.sub(r"[^\d,.]", "", text)

    # Romanian format: 1.299,99
    if "," in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    else:
        parts = cleaned.split(".")
        if len(parts) > 1 and len(parts[-1]) == 3:
            cleaned = "".join(parts)

    try:
        return Decimal(cleaned)
    except Exception:
        pass
    
    """Extrage primul numar dintr-un string de pret. '1.299,99 Lei' -> 1299.99"""
    if not text:
        return None
    cleaned = re.sub(r"[^\d,.]", "", text)
    if re.search(r"\d{1,3}\.\d{3},\d{2}$", cleaned):
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif re.search(r"\d{1,3},\d{3}\.\d{2}$", cleaned):
        cleaned = cleaned.replace(",", "")
    elif re.search(r"^\d{1,3},\d{3},\d{2}$", cleaned):
        parts = cleaned.split(",")
        cleaned = parts[0] + parts[1] + "." + parts[2]
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

    # ───────── RAM: prefix diferit per site ─────────
    if isinstance(obj, RAM):
        ram_prefixes = {
            "altex": "Memorie desktop",
            "emag":  "Memorie",
            "cel":    "Kit RAM",
        }
        prefix = ram_prefixes.get(site, "Kit RAM") if site else "Kit RAM"

    # ───────── GPU ─────────
    if isinstance(obj, GPU):
        brand = str(obj.brand).strip()
        name_lower = obj.nume.lower()
        
        match_model = re.search(r'(\d{3,4})\s*(ti|xtx|xt|super|gre)?', name_lower)
        
        if match_model:
            baza = match_model.group(1)
            sufix = match_model.group(2) if match_model.group(2) else ""
            chipset_curat = f"{baza} {sufix}".strip().upper()
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
            "eagle", "aorus", "taichi", "challenger"
        ]

        variant = ""
        for v in variant_words:
            if v in name_lower:
                variant = v.upper()
                break

        query = f"{prefix} {brand} {chipset_curat} {vram_curat} {variant} {oc_str}".strip()
        return re.sub(r'\s+', ' ', query)

    # ───────── CPU ─────────
    elif isinstance(obj, CPU):
        brand = str(obj.brand).strip()
        name_lower = obj.nume.lower()
        
        match_cpu = re.search(r'(\d{4,5})\s*([a-z0-9]{1,3})?', name_lower)
        if match_cpu:
            baza = match_cpu.group(1)
            sufix = match_cpu.group(2) if match_cpu.group(2) else ""
            serie_curata = f"{baza} {sufix}".strip().upper()
        else:
            serie_curata = str(obj.serie).strip()
            
        query = f"{prefix} {brand} {serie_curata}".strip()
        return re.sub(r'\s+', ' ', query)

    # ───────── MOTHERBOARD ─────────
    elif isinstance(obj, Motherboard):
        socket_str = obj.socket if obj.socket else ""
        wifi_str   = "WiFi" if obj.are_wifi else ""

        short_name = " ".join(obj.nume.split()[:4])

        if site == "cel":
            query = f"{prefix} {socket_str} {short_name} {wifi_str}"
        else:
            query = f"{prefix} {short_name} {socket_str} {wifi_str}"

        return re.sub(r'\s+', ' ', query.strip())

    # ───────── STORAGE ─────────
    elif isinstance(obj, Storage):
        prefix = _STORAGE_PREFIX.get(obj.tip, "SSD")
        cap = f"{obj.capacitate_gb // 1000}TB" if obj.capacitate_gb >= 1000 else f"{obj.capacitate_gb}GB"
        return f"{prefix} {obj.brand} {cap}".strip()

    # ───────── CARCASE ─────────
    elif isinstance(obj, Case):
        nume_curat = obj.nume.lower()

        # 1. Ștergem cuvintele de umplutură care strică search-ul pe eMag/Altex/CEL
        fluff = [
            "tempered glass", "window", "midi-tower", "mid-tower", "midi tower", "mid tower",
            "full-tower", "full tower", "mini-tower", "mini tower", "micro-atx", "e-atx", "atx",
            "tg", "fara sursa", "cu sursa", "usb 3.0", "usb 3.1"
        ]
        for f in fluff:
            nume_curat = nume_curat.replace(f, " ")

        # 2. Ștergem culorile de la coadă (ex: "- white", "- blue/black") 
        nume_curat = re.sub(r'-\s*(white|black|blue|red|yellow|pink|alb|negru).*', '', nume_curat)

        # 3. Extragem primele 3-4 cuvinte relevante (Ex: "Corsair 4000D Airflow")
        cuvinte = [w for w in nume_curat.split() if len(w) > 1]
        short_name = " ".join(cuvinte[:4])

        # Formăm query-ul curat
        query = f"Carcasa {short_name}"
        return re.sub(r'\s+', ' ', query).strip()

    # ───────── FALLBACK PENTRU RESTUL ─────────
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

    # ───────── BRAND CHECK ─────────
    cuvinte_iertate = ["radeon", "geforce", "amd", "nvidia", "intel", "rtx", "rx", "core"]

    if hasattr(obj, 'brand') and obj.brand:
        brand_real = str(obj.brand).lower().strip()
        if brand_real not in cuvinte_iertate:
            if brand_real not in title_lower:
                return False

    # ───────── MODEL STRICT ─────────
    db_numbers = re.findall(r"\d{3,4}", name_lower)
    title_numbers = re.findall(r"\d{3,4}", title_lower)
    
    for num in db_numbers:
        if num not in title_numbers:
            return False

    # ───────── GPU ─────────
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
            "founders"
        ]

        for variant in gpu_variants:
            if variant in name_lower and variant not in title_lower:
                return False

    # ───────── CPU ─────────
    elif isinstance(obj, CPU):
        cpu_suffixes = ["x", "xt", "k", "kf", "f", "g", "ge"]

        for suf in cpu_suffixes:
            if re.search(rf"\b{suf}\b", name_lower) and not re.search(rf"\b{suf}\b", title_lower):
                return False

    # ───────── RAM ─────────
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

    # ───────── PSU ─────────
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

    # ───────── MOTHERBOARD ─────────
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

    # ───────── STORAGE ─────────
    elif isinstance(obj, Storage):
        if obj.capacitate_gb >= 1000:
            tb = str(obj.capacitate_gb // 1000)
            if not ((tb + "tb") in title_tokens or tb in title_tokens):
                return False
        else:
            gb = str(obj.capacitate_gb)
            if not ((gb + "gb") in title_tokens or gb in title_tokens):
                return False

    # ───────── CARCASE ─────────
    elif isinstance(obj, Case):
        name_lower = obj.nume.lower()
        
        # 1. Verificare Strictă Model (Căutăm coduri cu cifre ex: 4000d, 500dx, gt301)
        model_identifiers = re.findall(r'\b[a-z]*\d+[a-z]*\b', name_lower)
        for identifier in model_identifiers:
            # Ignorăm versiunile și porturile USB din seria principală
            if identifier in ["v1", "v2", "30", "31"]: 
                continue
            if identifier not in title_lower:
                return False

        # 2. Verificare Culoare (Alb vs Negru)
        db_is_white = "white" in name_lower or "alb" in name_lower
        db_is_black = "black" in name_lower or "negru" in name_lower

        title_is_white = "white" in title_lower or "alb" in title_lower
        title_is_black = "black" in title_lower or "negru" in title_lower

        # Respingem carcasele negre dacă noi căutăm alb
        if db_is_white and title_is_black and not title_is_white:
            return False
        # Respingem carcasele albe dacă noi căutăm negru
        if db_is_black and title_is_white and not title_is_black:
            return False

        # 3. Verificare "Airflow" (Sunt structuri fizice diferite)
        if "airflow" in name_lower and "airflow" not in title_lower:
            return False
        if "airflow" not in name_lower and "airflow" in title_lower:
            return False

        # 4. Verificare RGB/ARGB
        db_has_rgb = "rgb" in name_lower # Prinde și 'argb'
        title_has_rgb = "rgb" in title_lower
        # Respingem dacă varianta listată are RGB, dar baza noastră de date cere una simplă (RGB-ul e mereu mai scump)
        if not db_has_rgb and title_has_rgb:
            return False

        # 5. Verificare Versiune (V2)
        if "v2" in name_lower and "v2" not in title_lower:
            return False
        if "v2" not in name_lower and "v2" in title_lower:
            return False

        return True

    return True


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

    if "dual kit" in normalized or "2x" in normalized and "gb" in normalized:
        return 2, None
    if "quad kit" in normalized or "4x" in normalized and "gb" in normalized:
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


def _get_page_text(page, url: str) -> Optional[str]:
    try:
        page.goto(url, timeout=PAGE_TIMEOUT_MS, wait_until="domcontentloaded")
        return page.inner_text("body")
    except Exception:
        return None


def _verify_motherboard_details(page, result: PriceResult, obj: Motherboard) -> bool:
    if not result.url:
        return False

    try:
        page.goto(result.url, timeout=PAGE_TIMEOUT_MS, wait_until="domcontentloaded")
        _rand_delay(0.5, 1.5)
        page_text = page.inner_text("body").lower()

        if obj.chipset:
            if obj.chipset.lower() not in page_text:
                return False

        if obj.format:
            if obj.format.lower() not in page_text:
                return False

        has_wifi = (
            "wifi"     in page_text or
            "wi-fi"    in page_text or
            "wireless" in page_text
        )
        if obj.are_wifi != has_wifi:
            return False

        has_bluetooth = "bluetooth" in page_text
        if obj.are_bluetooth != has_bluetooth:
            return False

        return True

    except Exception as e:
        logger.debug("Eroare verificare detalii MB (%s): %s", result.url, e)
        return False


def _verify_ram_module_count(page, result: PriceResult, obj: RAM) -> bool:
    if not hasattr(obj, 'numar_module') or not obj.numar_module:
        return True

    title_text = result.title or ""
    title_match = _matches_ram_module_count(title_text, obj)
    if title_match is False:
        return False
    if title_match is True:
        return True

    if result.url:
        page_text = _get_page_text(page, result.url)
        if page_text:
            page_match = _matches_ram_module_count(page_text, obj)
            if page_match is False:
                return False
            if page_match is True:
                return True

    return True

#─────────── URL DISCOVERY ───────────────────────────────────

_SEARCH_URL_PATTERNS: dict[str, list[str]] = {
    "emag": [
        "https://www.emag.ro/search/{q}",
        "https://www.emag.ro/cautare/{q}",
    ],
    "altex": [
        "https://altex.ro/cauta/?q={q}",
        "https://altex.ro/search?q={q}",
        "https://altex.ro/cautare/{q}/",
    ],
    "cel": [
        "https://www.cel.ro/cauta/{q}/",
        "https://www.cel.ro/search/{q}/",
        "https://www.cel.ro/cautare/?q={q}",
    ],
}

_CARD_SELECTORS: dict[str, list[str]] = {
    "emag":  ["div.card-item", "div.product-card", "article.product"],
    "altex": ["div.Product", "div.product-card", "article.product"],
    "cel":   ["div.product_data", "div.productListing-item", "article.product"],
}

_COOKIE_BTN: dict[str, str] = {
    "emag":  "button:has-text('Sunt de acord'), button:has-text('Accept')",
    "altex": "button:has-text('Acceptati tot'), button:has-text('Accept all'), button:has-text('Accept')",
    "cel":   "button:has-text('Accept'), button:has-text('OK'), button:has-text('Accepta')",
}

_url_session_cache: dict[str, tuple[str, str]] = {}


def _dismiss_cookie(page, site: str):
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
    q = query.replace(" ", "+")

    def _try_patterns(skip_cache=False):
        patterns = _SEARCH_URL_PATTERNS.get(site, [])
        selectors = _CARD_SELECTORS.get(site, [])

        for url_tpl in patterns:
            if not skip_cache and site in _url_session_cache:
                cached_tpl, cached_sel = _url_session_cache[site]
                if url_tpl != cached_tpl:
                    continue

            url = url_tpl.replace("{q}", q)
            try:
                page.goto(url, timeout=PAGE_TIMEOUT_MS, wait_until="domcontentloaded")
                _dismiss_cookie(page, site)
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

    page_url, card_sel = _try_patterns(skip_cache=False)
    if page_url:
        return page_url, card_sel

    if site in _url_session_cache:
        logger.debug("[%s] Pattern cacheuit nu mai functioneaza, re-detectez...", site)
        del _url_session_cache[site]
        page_url, card_sel = _try_patterns(skip_cache=True)

    return page_url, card_sel


# ─────────────────────────── VITEZE SSD DIN PAGINA EMAG ──────────────────────

def _extract_storage_speeds_emag(page, prod_url: str) -> tuple[Optional[int], Optional[int]]:
    viteza_citire  = None
    viteza_scriere = None

    try:
        page.goto(prod_url, timeout=PAGE_TIMEOUT_MS, wait_until="domcontentloaded")
        _rand_delay(1.0, 2.5)

        page_text = page.inner_text("body")

        m_citire = re.search(
            r'(?:viteza\s+(?:de\s+)?citire|read\s+speed|citire\s+secventiala)[^\d]{0,30}(\d{2,4})\s*MB',
            page_text,
            re.IGNORECASE,
        )
        if m_citire:
            viteza_citire = int(m_citire.group(1))

        m_scriere = re.search(
            r'(?:viteza\s+(?:de\s+)?scriere|write\s+speed|scriere\s+secventiala)[^\d]{0,30}(\d{2,4})\s*MB',
            page_text,
            re.IGNORECASE,
        )
        if m_scriere:
            viteza_scriere = int(m_scriere.group(1))

        if not viteza_citire or not viteza_scriere:
            rows = page.query_selector_all(
                ".specifications-section dl dt, "
                ".product-page-specs dt, "
                "table.specifications td:first-child"
            )
            for row in rows:
                label = row.inner_text().strip().lower()
                value_el = row.evaluate(
                    "el => el.nextElementSibling ? el.nextElementSibling.innerText : ''"
                )
                if not value_el:
                    continue
                m_val = re.search(r'(\d{2,4})', value_el)
                if not m_val:
                    continue
                val = int(m_val.group(1))

                if not viteza_citire and "citire" in label:
                    viteza_citire = val
                elif not viteza_scriere and "scriere" in label:
                    viteza_scriere = val

    except Exception as e:
        logger.debug("Eroare extragere viteze SSD eMag (%s): %s", prod_url, e)

    return viteza_citire, viteza_scriere


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
                integer_part = price_el.evaluate("el => el.firstChild ? el.firstChild.nodeValue : ''").strip()
                sup_el = price_el.query_selector("sup")
                decimal_part = sup_el.inner_text().strip() if sup_el else "00"
                price = _clean_price(f"{integer_part},{decimal_part}")
                if not price:
                    price = _clean_price(price_el.inner_text())
                if not price:
                    continue

                avail_id = card.get_attribute("data-availability-id")
                in_stoc = (avail_id == "3") if avail_id else True

                title    = card.get_attribute("data-name") or ""
                prod_url = card.get_attribute("data-url") or ""

                if not title or not prod_url:
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


def scrape_altex(page, query: str) -> list[PriceResult]:
    results = []
    try:
        url = f"https://altex.ro/cauta/?q={query.replace(' ', '%20')}"
        page.goto(url, timeout=PAGE_TIMEOUT_MS, wait_until="domcontentloaded")
        try:
            btn = page.wait_for_selector("button:has-text('Acceptati tot')", timeout=3000)
            if btn:
                btn.click()
                page.wait_for_timeout(300)
        except Exception:
            pass
        page.wait_for_selector("div.Product", timeout=15000)

        cards = page.query_selector_all("div.Product")[:MAX_RESULTS_PER_SITE]
        for card in cards:
            try:
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

                card_text = card.inner_text().lower()
                in_stoc = "stoc epuizat" not in card_text and "indisponibil" not in card_text

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


def scrape_cel(page, query: str) -> list[PriceResult]:
    results = []
    try:
        url = f"https://www.cel.ro/cauta/{query.replace(' ', '+')}/"
        page.goto(url, timeout=PAGE_TIMEOUT_MS, wait_until="domcontentloaded")
        try:
            btn = page.wait_for_selector("button:has-text('Accept'), button:has-text('OK'), button:has-text('Accepta')", timeout=3000)
            if btn:
                btn.click()
                page.wait_for_timeout(300)
        except Exception:
            pass
        page.wait_for_selector("div.product_data", timeout=15000)

        cards = page.query_selector_all("div.product_data")[:MAX_RESULTS_PER_SITE]
        for card in cards:
            try:
                price_el = card.query_selector("span.price[content]")
                if price_el:
                    raw = price_el.get_attribute("content") or price_el.inner_text()
                else:
                    price_el = card.query_selector("div.pret_n")
                    if not price_el:
                        continue
                    raw = price_el.inner_text()
                price = _clean_price(raw)
                if not price:
                    continue

                card_text = card.inner_text().lower()
                in_stoc = "in stoc" in card_text or "disponibil" in card_text

                title = ""
                title_el = card.query_selector("h2.productTitle")
                if title_el:
                    title = title_el.inner_text().strip()

                if not title:
                    img_el = card.query_selector("img[alt]")
                    if img_el:
                        title = img_el.get_attribute("alt") or ""

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


# ─────────────────────────── MAIN SEARCH LOGIC ───────────────────────────────

def find_all_valid_prices(
    page,
    obj,
    min_similarity: float = 0.55,
    verbose: bool = False,
) -> list[PriceResult]:
    all_valid: list[PriceResult] = []

    for scrape_fn in SITE_SCRAPERS:
        site_name = scrape_fn.__name__.replace("scrape_", "")
        query = build_query(obj, site_name)
        if verbose:
            print(f"  Query for {site_name}: '{query}'")

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

                match_result = _is_valid_title_match(match_text, obj)
                if match_result is False:
                    if verbose:
                        print(f"    [{site_name}] RESPINS spec: {r.title[:60]}")
                    continue

                if match_result is None and isinstance(obj, Motherboard):
                    if not _verify_motherboard_details(page, r, obj):
                        if verbose:
                            print(f"    [{site_name}] RESPINS page details: {r.title[:60]}")
                        continue

                if isinstance(obj, RAM) and not _verify_ram_module_count(page, r, obj):
                    if verbose:
                        print(f"    [{site_name}] RESPINS module count: {r.title[:60]}")
                    continue

                if isinstance(obj, Storage) and r.site == "eMag" and r.url:
                    if verbose:
                        print(f"    [eMag] Extrag viteze SSD de pe pagina produsului...")
                    viteza_citire, viteza_scriere = _extract_storage_speeds_emag(page, r.url)
                    r.viteza_citire  = viteza_citire
                    r.viteza_scriere = viteza_scriere
                    if verbose:
                        print(f"    [eMag] Citire: {viteza_citire} MB/s | Scriere: {viteza_scriere} MB/s")

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
    help = "Updateaza preturile tuturor componentelor din DB de pe eMag/Altex/CEL"

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
            self.stdout.write("Price Updater - eMag / Altex / CEL")
            if dry_run:
                self.stdout.write("  *** DRY RUN - nu se scrie in DB ***")
            self.stdout.write("=" * 65)

            with sync_playwright() as pw:
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

                    # AM STERS to_delete = []

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

                        # ──────── LOGICA NOUA: BLACKLIST SI STERGERE ────────
                        if not valid_results:
                            self.stdout.write("-> NU GASIT - mutat in Blacklist si sters")
                            
                            if not dry_run:
                                # 1. Adaugam in Blacklist pe baza part_number-ului
                                if obj.part_number:
                                    Blacklist.objects.get_or_create(
                                        part_number=obj.part_number,
                                        defaults={'nume': obj.nume}
                                    )
                                
                                # 2. Stergem obiectul din DB
                                obj.delete()
                                
                            stats["sterse"] += 1
                        # ───────────────────────────────────────────────────
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

                    # AM STERS if to_delete: ...

                context.close()

            self.stdout.write("\n" + "=" * 65)
            self.stdout.write("RAPORT FINAL")
            self.stdout.write("=" * 65)
            self.stdout.write(f"  Procesate:   {stats['procesate']}")
            self.stdout.write(f"  Actualizate: {stats['actualizate']}")
            self.stdout.write(f"  Sterse (-> Blacklist): {stats['sterse']}")
            self.stdout.write(f"  Erori:       {stats['eroare']}")
            self.stdout.write("=" * 65)