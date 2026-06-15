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

MAX_RESULTS_PER_SITE = 15
PAGE_TIMEOUT_MS      = 30_000
BATCH_SIZE           = 20

ALL_MODELS = [CPU, GPU, Motherboard, RAM, PSU, Case, Cooler, Storage]

# ── Scoring ───────────────────────────────────────────────────────────────────────────────
MIN_SCORE         = 70    # sub acest scor = balivearnă, ignorat
SCORE_TOLERANCE   = 10    # diferență scor sub care prețul decide
MAX_PRICE_PREMIUM = 0.15  # max 15% premium pentru un scor mai bun


# ─────────────────────────── DATA CLASSES ────────────────────────────────────

@dataclass
class PriceResult:
    site:                 str
    price:                Decimal
    in_stoc:              bool
    url:                  str
    title:                str           = field(default="")
    viteza_citire:        Optional[int] = field(default=None)
    viteza_scriere:       Optional[int] = field(default=None)
    poza_url:             Optional[str] = field(default=None)
    compatibility_score:  int           = field(default=0)    # 0–100


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
    # Normalizare variante WiFi: wifi6e, wifi6, wifi7, wi-fi 6e, wi fi 6e -> "wifi"
    text = re.sub(r"wi[- ]?fi[- ]?\d*[a-z]*", "wifi", text)
    # Normalizare pentru memorii RAM: transformăm MT/s în mhz
    text = re.sub(r'(?i)mt/s?', 'mhz', text)
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
        # 1. Prefix corect pe magazin
        ram_prefixes = {
            "altex": "Memorie",
            "emag":  "Memorie",
            "cel":   "Kit RAM",
        }
        prefix = ram_prefixes.get(site, "Memorie")

        # 2. Curățare "gunoaie" din numele bazei de date
        name_clean = obj.nume.lower()
        fluff = ["series", "kit", "weiße led", "blaue led", "red", "black", "white", "grey", "blue"]
        for f in fluff:
            name_clean = name_clean.replace(f, " ")
        
        # 3. Păstrăm doar brandul și seria (ex: ADATA XPG Spectrix)
        words = [w.upper() for w in name_clean.split() if len(w) > 1 and not '-' in w]
        short_name = " ".join(words[:3])

        # 4. Adăugăm datele tehnice esențiale pt căutare
        cap_str = f"{obj.capacitate_totala_gb}GB" if getattr(obj, 'capacitate_totala_gb', None) else ""
        
        # Extragem generația (DDR4/DDR5) dacă există în numele original
        ddr_match = re.search(r'(ddr\d)', obj.nume.lower())
        ddr_str = ddr_match.group(1).upper() if ddr_match else ""

        query = f"{prefix} {short_name} {ddr_str} {cap_str}"
        return re.sub(r'\s+', ' ', query.strip())

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

        # Suportă chipset-uri care încep cu literă (B580, A770)
        match_model = re.search(r'([a-z]?\d{3,4})\s*(ti|xtx|xt|super|gre)?', name_lower)

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
            "dual", "strix", "tuf", "gaming", "ventus", "eagle", "aorus", "taichi", "challenger",
            "prime", "shadow", "proart", "ai", "windforce"
        ]

        variant = ""
        for v in variant_words:
            if v in name_lower:
                variant = v.upper()
                break

        query = f"{prefix} {brand} {chipset_curat} {vram_curat} {variant} {oc_str}".strip()
        
        # Stergem O-ul de dinainte de memorie si adaugam OC la final daca e nevoie
        if re.search(r"(?i)([-_])o(\d+g)\b", query):
            query = re.sub(r"(?i)([-_])o(\d+g)\b", r"\1\2", query)
            if not re.search(r"(?i)\boc\b", query):
                query += " OC"
                
        return re.sub(r'\s+', ' ', query)

    elif isinstance(obj, CPU):
        return f"{prefix} {obj.nume}".strip()

    elif isinstance(obj, Motherboard):
        short_name = " ".join(obj.nume.split()[:4]) 
        short_name = re.sub(r'(?i)\bwi[-\s]?fi\b', '', short_name).strip()
        
        # Trimitem doar elementele de bază motorului de căutare al magazinului
        query = f"{prefix} {short_name}"
        return re.sub(r'\s+', ' ', query.strip())

    elif isinstance(obj, Storage):
        # 1. Normalizare Brand (magazinele folosesc "WD")
        brand = str(obj.brand).strip()
        brand_search = "WD" if brand.lower() == "western digital" else brand

        # 2. Setare Prefix + hint interfata (ajuta motorul de cautare)
        if obj.tip == "HDD":
            prefix = "HDD"
            iface_hint = ""
        elif obj.tip in ("NVME", "NVMe"):
            prefix = "SSD"
            iface_hint = "NVMe"
        else:
            prefix = "SSD"
            iface_hint = ""
            
        # 3. Formatare curată a capacității pentru căutare (1000 / 1024 devin 1TB)
        cap_val = obj.capacitate_gb
        if cap_val >= 1000:
            tb = cap_val // 1000 if cap_val % 1000 == 0 else cap_val // 1024
            if tb == 0: tb = cap_val / 1000
            cap_str = f"{tb:g}TB"
        else:
            cap_str = f"{cap_val}GB"
        
        # 4. Curățarea numelui de "gunoaie"
        name_clean = obj.nume.lower().replace(str(obj.brand).lower(), "")
        name_clean = re.sub(r'[-_/]', ' ', name_clean) # Spargem codurile lipite
        
        # Eliminăm capacitățile din string ca să nu avem dubluri (ex: MX500 1000GB 1TB)
        name_clean = re.sub(r'\b\d+(\.\d+)?\s*(tb|gb)\b', ' ', name_clean)
        
        stop_w = {'ssd', 'hdd', 'nvme', 'm.2', 'pcie', 'sata', 'solid', 'state', 'drive', 'hard',
                  'disk', 'technology', 'gen', 'plus', 'internal', 'intern', 'series', '2280', '2230'}
        
        # Păstrăm cuvintele relevante — inclusiv combinații litere+cifre (MX500, SN750, A400)
        # și cuvinte pur alfabetice scurte care fac parte din model (Pro, EVO, Blue, Red, Black)
        words = []
        for w in name_clean.split():
            w = w.strip('.,')
            if w in stop_w or len(w) <= 1:
                continue
            if re.match(r'^\d+$', w):  # cifre pure (rpm, latenta) — skip
                continue
            words.append(w)
        
        # Luăm primele 3 identificatoare pentru a acoperi modele ca "990 PRO", "SN750 SE", "FURY Renegade"
        model_str = " ".join(words[:3]).upper()

        query = f"{prefix} {brand_search} {model_str} {cap_str} {iface_hint}"
        return re.sub(r'\s+', ' ', query.strip())

    elif isinstance(obj, Case):
        nume_curat = obj.nume.lower()

        # Adăugăm la fluff și cuvintele de marketing
        fluff = [
            "tempered glass", "window", "midi-tower", "mid-tower", "midi tower", "mid tower",
            "full-tower", "full tower", "mini-tower", "mini tower", "micro-atx", "e-atx", "atx",
            "tg", "fara sursa", "cu sursa", "usb 3.0", "usb 3.1", "rgb", "argb", "led", "airflow"
        ]
        for f in fluff:
            nume_curat = nume_curat.replace(f, " ")

        # Ștergem culorile și tot ce e după cratimă
        nume_curat = re.sub(r'-\s*(white|black|blue|red|yellow|pink|alb|negru).*', '', nume_curat)

        # Asigurăm prezența brandului
        brand = str(obj.brand).lower()
        if brand not in nume_curat:
            nume_curat = f"{brand} {nume_curat}"

        cuvinte = [w for w in nume_curat.split() if len(w) > 1]
        
        # Luăm doar primele 3 cuvinte relevante (ex: "Carcasa Corsair 4000D")
        short_name = " ".join(cuvinte[:3]).title()

        query = f"Carcasa {short_name}"
        return re.sub(r'\s+', ' ', query).strip()

    if isinstance(obj, PSU):
        brand = str(obj.brand).strip()
        
        # Eliminăm brandul din nume pentru a nu-l dubla
        nume_curat = obj.nume.lower().replace(brand.lower(), "")
        
        # Scoatem termenii descriptivi și semnele de punctuație
        fluff = ["80 plus", "80+", "gold", "bronze", "platinum", "titanium", "silver", "semi-modular", "modular", "fully", "cybenetics", ","]
        for f in fluff:
            nume_curat = nume_curat.replace(f, " ")
            
        # Păstrăm doar seria exactă (primele 2 cuvinte valide)
        cuvinte = [w.upper() for w in nume_curat.split() if len(w) > 1]
        short_name = " ".join(cuvinte[:2])
        
        power_str = f"{obj.putere_w}W" if getattr(obj, 'putere_w', None) else ""
        
        query = f"Sursa {brand} {short_name} {power_str}".strip()
        return re.sub(r'\s+', ' ', query)

    elif isinstance(obj, Cooler):
        name_clean = obj.nume.lower()
        
        # Curățăm dimensiunile ventilatoarelor care încurcă căutarea (ex: "2x 120mm", "135mm")
        # Dar lăsăm numerele de radiatoare AIO intacte
        name_clean = re.sub(r'\b\d{1,2}x\s*\d{2,3}mm\b', '', name_clean) 
        name_clean = re.sub(r'\b\d{2,3}mm\b', '', name_clean)
        
        # Scoatem cuvintele descriptive inutile pentru search
        fluff = ["red", "white", "black", "alb", "negru", "rgb", "a-rgb", "argb", "esports", "duo", "-", ","]
        for f in fluff:
            name_clean = name_clean.replace(f, " ")
            
        brand = str(obj.brand).lower()
        if brand not in name_clean:
            name_clean = f"{brand} {name_clean}"
            
        cuvinte = [w for w in name_clean.split() if len(w) > 1]
        
        # Luăm primele 3-4 cuvinte esențiale (ex: "Arctic Liquid Freezer III")
        short_name = " ".join(cuvinte[:4]).title()
        
        query = f"Cooler {short_name}"
        return re.sub(r'\s+', ' ', query).strip()

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

    cuvinte_iertate = ["radeon", "geforce", "amd", "nvidia", "intel", "rtx", "rx", "core", "wd", "western digital"]

    if hasattr(obj, 'brand') and obj.brand:
        brand_real = str(obj.brand).lower().strip()
        if brand_real not in cuvinte_iertate:
            if brand_real == "western digital" and ("wd" in title_tokens or "wd" in title_lower):
                pass
            elif brand_real not in title_lower:
                if isinstance(obj, Storage) or isinstance(obj, Case):
                    pass # Iertam lipsa brandului pt Storage si Case (des omis in titluri)
                elif isinstance(obj, Motherboard):
                    # Exceptie pentru Gigabyte / Aorus / ROG etc, uneori nu pun brandul principal
                    pass
                else:
                    return False

    # Verificarea generala cu numere o facem doar pt CPU si GPU, pentru restul avem logica specifica
    if isinstance(obj, (CPU, GPU)):
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
            "strix", "tuf", "dual", "phoenix", "evo", "gaming", "ventus", "suprim",
            "aorus", "eagle", "windforce", "taichi", "challenger", "phantom", "steel",
            "pulse", "nitro", "merc", "qick", "swift", "trinity", "amp", "founders",
            "prime", "shadow", "proart", "ai"
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
        # 1. Verificare Generație (DDR3/DDR4/DDR5) - extrem de important!
        ddr_db_match = re.search(r'(ddr\d)', obj.nume.lower())
        if ddr_db_match:
            ddr_gen = ddr_db_match.group(1) # ex: 'ddr4'
            if ddr_gen not in title_lower:
                return False

        # 2. Verificare Capacitate
        if hasattr(obj, 'capacitate_totala_gb') and obj.capacitate_totala_gb:
            cap = str(obj.capacitate_totala_gb)
            # Acoperim cazurile "32gb"
            if not (f"{cap}gb" in title_lower or f"{cap} gb" in title_lower):
                # Dacă nu e explicit (rar), calculăm din module ex: 2x16gb pt 32
                modules_title, module_gb_title = _parse_ram_kit_info(title_lower)
                if not (modules_title and module_gb_title and (modules_title * module_gb_title == obj.capacitate_totala_gb)):
                    return False

        # 3. Verificare Frecvență
        if hasattr(obj, 'frecventa_mhz') and obj.frecventa_mhz:
            freq = str(obj.frecventa_mhz)
            # Funcționează și pt MT/s pt că am adăugat regula în _normalize_text
            if not (f"{freq}mhz" in title_lower or f"{freq} mhz" in title_lower or freq in title_tokens):
                return False

        # 4. Verificare Latență (CL)
        if hasattr(obj, 'latenta_cl') and obj.latenta_cl:
            cl = str(obj.latenta_cl)
            if not (f"cl{cl}" in title_lower or f"cl {cl}" in title_lower or f"c{cl}" in title_lower):
                return False
                
        return True

    elif isinstance(obj, PSU):
        title_lower = title.lower()

        # 1. Verificare Putere (cu suport pentru "750 Watt" și "750 W")
        if getattr(obj, 'putere_w', None):
            w_val = str(obj.putere_w)
            valid_power_formats = [f"{w_val}w", f"{w_val} w", f"{w_val} watt"]
            if not any(fmt in title_lower for fmt in valid_power_formats):
                return False

        # 2. Verificare Serie/Model (Cea mai importantă parte)
        # Extragem ID-urile din nume (ex: "CX750", "RM850e", "A850GL", "P11")
        nume_curat = obj.nume.lower()
        model_ids = re.findall(r'\b[a-z]+\d+[a-z]*\b', nume_curat)
        
        # Cuvinte generice pe care nu vrem să le forțăm ca fiind "modele"
        ignore_ids = {"plus", "gold", "bronze", "platinum", "core", "pure", "dark", "power"}
        
        for mid in model_ids:
            if mid not in ignore_ids:
                if mid not in title_lower:
                    # Fallback: extragem doar cifrele (în caz că magazinul scrie RM 850e separat)
                    digits = re.sub(r'\D', '', mid)
                    if digits and digits not in title_lower:
                        return False

        # 3. Verificare Certificare (Atenție doar la calitatea metalului)
        if getattr(obj, 'certificare', None):
            cert_text = str(obj.certificare).lower()
            cert_keywords = [w for w in re.findall(r"[a-z]+", cert_text) if w in ["gold", "bronze", "platinum", "titanium", "silver"]]
            
            for kw in cert_keywords:
                if kw not in title_lower:
                    return False

        # Eliminăm respingerea bazată pe cuvântul "modular". 
        # Identificarea corectă a seriei (ex: RM850e) garantează automat modularitatea fără să depindem de SEO-ul magazinului.
        
        return True

    elif isinstance(obj, Motherboard):
        # Tracker: daca socket-ul nu e confirmat din titlu, deferam la pagina
        needs_page_check = False

        if obj.chipset:
            chipset_lower = obj.chipset.lower()
            chipset_num = re.sub(r'[^0-9]', '', chipset_lower)
            if chipset_num and chipset_num not in title_lower:
                # Verificam daca macar numarul chipsetului e in titlu (ex 650 din B650)
                return False
                
            # Verificare sufix E, M, etc. (ex: B650E)
            chipset_suffix = re.sub(r'^[a-z]+|[0-9]+', '', chipset_lower).strip()
            if chipset_suffix and chipset_num:
                # Cautam numarul urmat de sufix, cu sau fara spatiu
                has_suffix = re.search(rf'{chipset_num}\s*{chipset_suffix}\b', title_lower)
                if not has_suffix and chipset_lower not in title_lower:
                    return False

        # Socket check: daca nu e in titlu, marcam pt verificare pe pagina
        # Multi retaileri (eMag) nu pun socketul in titlu
        if obj.socket:
            socket_lower = obj.socket.lower()
            # Extragem doar numerele din socket pt fallback (ex: AM5 -> 5, 1700 -> 1700)
            socket_num = re.sub(r'[^0-9]', '', socket_lower)
            socket_in_title = (
                socket_lower in title_lower
                or (socket_num and len(socket_num) >= 3 and socket_num in title_lower)
                or (socket_lower == "am4" and "am4" in title_lower)
                or (socket_lower == "am5" and "am5" in title_lower)
            )
            if not socket_in_title:
                needs_page_check = True

        # WiFi: normalizarea din _normalize_text face wifi6e/wi-fi 6e -> "wifi"
        has_wifi_in_title = "wifi" in title_tokens or "wifi" in title_lower
        if not obj.are_wifi and has_wifi_in_title:
            return False
        if obj.are_wifi and not has_wifi_in_title:
            needs_page_check = True



        # Daca avem info lipsa din titlu, returnam None => se verifica pe pagina
        return None if needs_page_check else True

    elif isinstance(obj, Storage):
        title_lower = title.lower()
        cap_gb = obj.capacitate_gb

        # 1. Verificare Flexibilă a Capacității
        valid_caps = [f"{cap_gb}gb", f"{cap_gb} gb"]
        
        # Tratăm manual confuziile clasice din SEO-ul magazinelor
        if cap_gb in (1000, 1024):
            valid_caps.extend(["1tb", "1 tb", "1 t"])
        elif cap_gb in (2000, 2048):
            valid_caps.extend(["2tb", "2 tb", "2 t"])
        elif cap_gb >= 1000:
            tb_1000 = cap_gb / 1000
            tb_1024 = cap_gb / 1024
            valid_caps.extend([f"{tb_1000:g}tb", f"{tb_1000:g} tb", f"{tb_1024:g}tb", f"{tb_1024:g} tb"])
            
        found_cap = any(cap in title_lower for cap in valid_caps)
        if not found_cap:
            return False

        # 2. Validare Western Digital vs WD
        brand = str(obj.brand).lower()
        if brand == "western digital" and "wd" not in title_lower and "western" not in title_lower:
            return False

        # 3. Verificare interfata (SATA vs NVMe — confuzie frecventa)
        tip_lower = obj.tip.lower() if hasattr(obj, "tip") and obj.tip else ""
        if "nvme" in tip_lower:
            if "sata" in title_lower and "nvme" not in title_lower and "m.2" not in title_lower and "pcie" not in title_lower:
                return False  # SATA când noi vrem NVMe
        elif "sata" in tip_lower:
            if "nvme" in title_lower and "sata" not in title_lower:
                return False  # NVMe când noi vrem SATA

        # 4. Verificare Serii Modele (ex: SN750, A400, 990 Pro, BarraCuda)
        name_clean = obj.nume.lower()
        
        # Extragem ID-uri de model: litere+cifre, cifre pure 3-4 chars, si cuvinte model fara cifre
        model_ids = re.findall(r'\b[a-z]+\d+[a-z]*\b', name_clean)
        model_ids.extend(re.findall(r'\b\d{3,4}\b', name_clean))
        
        # Ignorăm specificații tehnice comune ca să nu dea fals-negative
        skip_ids = {str(cap_gb), "m2", "gen3", "gen4", "gen5", "sata3", "sata2",
                    "2280", "2230", "2242", "7200", "5400", "5900", "128", "256", "512"}
        
        for mid in set(model_ids):
            if mid in skip_ids:
                continue
            
            if mid not in title_lower:
                # Dacă nu găsim "sn750", căutăm măcar "750" ca failsafe
                digits = re.sub(r'\D', '', mid)
                if digits and digits not in title_lower:
                    return False
                    
        return True

    elif isinstance(obj, Case):
        name_lower = obj.nume.lower()
        title_lower = title.lower()

        # 1. Extragere și verificare identificatori de model (litere+cifre)
        # Ex: "4000D", "500DX", "M100A", "CC560"
        model_identifiers = re.findall(r'\b[a-z]*\d+[a-z]*\b', name_lower)
        for identifier in model_identifiers:
            if identifier in ["v1", "v2", "30", "31", "120mm", "140mm"]:
                continue
            if identifier not in title_lower:
                # Fallback: căutăm doar cifrele dacă literele au fost separate (ex: 4000 D)
                digits = re.sub(r'\D', '', identifier)
                if digits and digits not in title_lower:
                    return False

        # 2. Verificare culori (Alb vs Negru)
        db_is_white = "white" in name_lower or "alb" in name_lower
        db_is_black = "black" in name_lower or "negru" in name_lower

        title_is_white = "white" in title_lower or "alb" in title_lower
        title_is_black = "black" in title_lower or "negru" in title_lower

        if db_is_white and title_is_black and not title_is_white:
            return False
        if db_is_black and title_is_white and not title_is_black:
            return False

        # Nu verifica RGB, Airflow sau V2 bidirecțional. 
        # Lăsăm scorul de similaritate (_similarity) să decidă dacă e produsul corect.
        
        return True

    elif isinstance(obj, Cooler):
        name_lower = obj.nume.lower()
        title_lower = title.lower()
        
        # 1. Validare strictă a radiatoarelor AIO (240, 280, 360, 420)
        aio_sizes = ["240", "280", "360", "420"]
        for size in aio_sizes:
            if size in name_lower and size not in title_lower:
                return False
            # Prevenim potrivirea unui cooler pe aer cu un AIO din greșeală
            if size not in name_lower and size in title_lower:
                if "liquid" in name_lower or "aio" in name_lower or "aqua" in name_lower:
                    return False

        # 2. Validare strictă a versiunii (ex: Freezer 34 vs 36, Liquid Freezer II vs III)
        versions = re.findall(r'\b(?:ii|iii|iv|v|\d{1,2})\b', name_lower)
        for v in versions:
            # Ne interesează doar numerele/cifrele romane folosite de obicei în modele
            if v not in ["2", "3", "4", "5", "ii", "iii", "iv", "34", "35", "36", "620", "500", "400"]:
                continue
            if re.search(rf'\b{v}\b', name_lower) and not re.search(rf'\b{v}\b', title_lower):
                return False

        # 3. Validare Culori
        db_is_white = "white" in name_lower or "alb" in name_lower
        db_is_black = "black" in name_lower or "negru" in name_lower
        
        title_is_white = "white" in title_lower or "alb" in title_lower
        title_is_black = "black" in title_lower or "negru" in title_lower
        
        if db_is_white and title_is_black and not title_is_white:
            return False
        if db_is_black and title_is_white and not title_is_black:
            return False
            
        return True

    return True


# ─────────────────────── COMPATIBILITY SCORING ───────────────────────────────────────

BRAND_ALIASES = {
    "western digital": ["wd", "western"],
    "be quiet!":       ["be quiet", "bequiet"],
    "gigabyte":        ["aorus"],
    "asus":            ["rog", "tuf", "proart"],
}


def _brand_in_title(brand: str, title: str) -> bool:
    if brand in title:
        return True
    for canonical, aliases in BRAND_ALIASES.items():
        if brand == canonical:
            return any(a in title for a in aliases)
    return False


def _compute_compatibility_score(result: "PriceResult", obj) -> int:
    """
    Calculează un scor de compatibilitate 0–100 între un PriceResult
    și obiectul din DB.

    Structură:
      +25  Brand corect (dacă lipsește → return 0 imediat)
      +25  Chipset / Serie / Model principal corect
      +30  Cod model specific (tie-breaker)
      +10  Atribut bonus #1 (specific per categorie)
      +10  Atribut bonus #2 (specific per categorie)
      −50  Penalizare fatală (variație incompatibilă detectată)

    Scor maxim: 100. Prag minim acceptat: MIN_SCORE (70).
    """
    title_lower  = _normalize_text(result.title)
    title_tokens = _tokenize(result.title)
    name_lower   = _normalize_text(obj.nume)
    brand_lower  = str(obj.brand).lower().strip() if hasattr(obj, "brand") and obj.brand else ""
    score        = 0

    # ═════════════════════════════════════════════════════════════════════════════════
    if isinstance(obj, GPU):
    # ═════════════════════════════════════════════════════════════════════════════════
        if not _brand_in_title(brand_lower, title_lower):
            return 0
        score += 25

        db_numbers = re.findall(r"\d{3,4}", name_lower)
        title_nums = re.findall(r"\d{3,4}", title_lower)
        family_ok  = any(f in title_lower for f in ["rtx", "rx", "arc"] if f in name_lower)
        nums_ok    = all(n in title_nums for n in db_numbers)
        if family_ok and nums_ok:
            score += 25

        GPU_MODEL_CODES = [
            "strix", "tuf", "dual", "phoenix", "evo", "ventus", "suprim",
            "aorus", "eagle", "windforce", "taichi", "challenger", "phantom",
            "pulse", "nitro", "merc", "qick", "swift", "trinity", "amp",
            "prime", "shadow", "proart", "gaming"
        ]
        for code in GPU_MODEL_CODES:
            if code in name_lower and code in title_lower:
                score += 30
                break

        if obj.vram_gb:
            vram = str(obj.vram_gb)
            if f"{vram}gb" in title_tokens or f"{vram}g" in title_tokens:
                score += 10

        db_oc    = "oc" in _tokenize(obj.nume) or bool(re.search(r"(?:-|_|\b)o\d+g\b", obj.nume.lower()))
        title_oc = "oc" in title_tokens or bool(re.search(r"(?:-|_|\b)o\d+g\b", result.title.lower()))
        if db_oc == title_oc:
            score += 10

        gpu_suffixes = ["xtx", "xt", "ti", "super", "gre"]
        for suf in gpu_suffixes:
            db_has    = bool(re.search(rf"(?:\b|\d){suf}\b", name_lower))
            title_has = bool(re.search(rf"(?:\b|\d){suf}\b", title_lower))
            if db_has != title_has:
                score -= 50
                break

        if obj.vram_gb:
            vram = str(obj.vram_gb)
            if f"{vram}gb" not in title_tokens and f"{vram}g" not in title_tokens:
                other_vrams = [str(v) for v in [4, 6, 8, 10, 12, 16, 20, 24] if str(v) != vram]
                if any(f"{v}gb" in title_tokens for v in other_vrams):
                    score -= 50

        if "white" in title_lower and "white" not in name_lower:
            score -= 50

    # ═════════════════════════════════════════════════════════════════════════════════
    elif isinstance(obj, CPU):
    # ═════════════════════════════════════════════════════════════════════════════════
        if not _brand_in_title(brand_lower, title_lower):
            return 0
        score += 25

        db_numbers = re.findall(r"\d{3,5}", name_lower)
        title_nums = re.findall(r"\d{3,5}", title_lower)
        if all(n in title_nums for n in db_numbers):
            score += 25

        CPU_SERIES = ["ryzen 5", "ryzen 7", "ryzen 9", "core i3", "core i5",
                      "core i7", "core i9", "core ultra 5", "core ultra 7", "core ultra 9"]
        for series in CPU_SERIES:
            if series in name_lower and series in title_lower:
                score += 30
                break

        if hasattr(obj, "socket") and obj.socket:
            if obj.socket.lower() in title_lower:
                score += 10

        if brand_lower in title_lower:
            score += 10

        cpu_suffixes = ["kf", "k", "f", "xt", "x", "g", "ge", "x3d"]
        for suf in sorted(cpu_suffixes, key=len, reverse=True):
            db_has    = bool(re.search(rf"\b{re.escape(suf)}\b", name_lower))
            title_has = bool(re.search(rf"\b{re.escape(suf)}\b", title_lower))
            if db_has != title_has:
                score -= 50
                break

    # ═════════════════════════════════════════════════════════════════════════════════
    elif isinstance(obj, Motherboard):
    # ═════════════════════════════════════════════════════════════════════════════════
        if not _brand_in_title(brand_lower, title_lower):
            return 0
        score += 25

        if obj.chipset:
            chipset_num = re.sub(r"[^0-9]", "", obj.chipset.lower())
            if chipset_num and chipset_num in title_lower:
                score += 25

        MB_MODEL_CODES = [
            "tomahawk", "pro rs", "gaming x", "aorus elite", "aorus pro",
            "aorus master", "aorus ultra", "prime", "rog strix", "rog maximus",
            "tuf gaming", "proart", "rog crosshair", "formula", "unify",
            "mag mortar", "mag tomahawk", "msi pro", "carbon", "steel legend",
            "phantom gaming", "taichi", "creator", "xtreme"
        ]
        matched_code = False
        for code in MB_MODEL_CODES:
            if code in name_lower and code in title_lower:
                score += 30
                matched_code = True
                break
        if not matched_code:
            name_words = [w for w in name_lower.split() if len(w) > 2]
            chipset_words = {re.sub(r"[^a-z]", "", obj.chipset.lower())} if obj.chipset else set()
            brand_words   = set(brand_lower.split())
            meaningful    = [w for w in name_words if w not in chipset_words and w not in brand_words]
            matches = sum(1 for w in meaningful if w in title_lower)
            if matches >= 2:
                score += 20

        mb_formats = {"matx": ["matx", "micro-atx", "m-atx"], "eatx": ["eatx", "e-atx"]}
        db_format  = "matx" if any(x in name_lower for x in ["matx", "micro", " m ", "m-atx"]) else \
                     "eatx" if any(x in name_lower for x in ["eatx", "e-atx"]) else "atx"
        if any(f in title_lower for f in mb_formats.get(db_format, ["atx"])):
            score += 10

        has_wifi_title = "wifi" in title_tokens or "wifi" in title_lower
        if hasattr(obj, "are_wifi") and obj.are_wifi == has_wifi_title:
            score += 10

        title_is_matx = any(x in title_lower for x in ["matx", "micro-atx", "m-atx"]) or \
                        bool(re.search(r"\b[a-z]\d{3,4}m\b", title_lower))
        if db_format == "atx" and title_is_matx:
            score -= 50
        if db_format == "matx" and not title_is_matx and "atx" in title_lower:
            score -= 50

        if obj.chipset:
            chipset_suffix = re.sub(r"[^a-z]", "", obj.chipset.lower())
            chipset_num    = re.sub(r"[^0-9]", "", obj.chipset.lower())
            if chipset_suffix and chipset_num and chipset_suffix in ["e", "x", "xi", "f"]:
                has_suffix = bool(re.search(rf"{chipset_num}\s*{chipset_suffix}\b", title_lower))
                if not has_suffix:
                    score -= 50

    # ═════════════════════════════════════════════════════════════════════════════════
    elif isinstance(obj, RAM):
    # ═════════════════════════════════════════════════════════════════════════════════
        if not _brand_in_title(brand_lower, title_lower):
            return 0
        score += 25

        ddr_match = re.search(r"(ddr\d)", obj.nume.lower())
        ddr_gen   = ddr_match.group(1) if ddr_match else ""
        freq      = str(obj.frecventa_mhz) if hasattr(obj, "frecventa_mhz") and obj.frecventa_mhz else ""
        if ddr_gen and ddr_gen in title_lower:
            score += 15
        if freq and (f"{freq}mhz" in title_lower or freq in title_tokens):
            score += 10

        RAM_SERIES = [
            "vengeance", "trident z", "fury beast", "fury renegade",
            "dominator", "ripjaws", "spectrix", "lancer", "ares",
            "rgb pro", "value ram", "sodimm"
        ]
        for series in RAM_SERIES:
            if series in name_lower and series in title_lower:
                score += 30
                break

        if hasattr(obj, "capacitate_totala_gb") and obj.capacitate_totala_gb:
            cap = str(obj.capacitate_totala_gb)
            if f"{cap}gb" in title_lower or f"{cap} gb" in title_lower:
                score += 10

        if hasattr(obj, "latenta_cl") and obj.latenta_cl:
            cl = str(obj.latenta_cl)
            if f"cl{cl}" in title_lower or f"c{cl}" in title_lower:
                score += 10

        if ddr_gen:
            wrong_ddr = [d for d in ["ddr3", "ddr4", "ddr5"] if d != ddr_gen and d in title_lower]
            if wrong_ddr:
                score -= 50

        if freq and hasattr(obj, "frecventa_mhz") and obj.frecventa_mhz:
            title_freqs = re.findall(r"\d{3,5}", title_lower)
            for tf in title_freqs:
                tf_int = int(tf)
                if 2000 < tf_int < 10000:
                    diff_pct = abs(tf_int - obj.frecventa_mhz) / obj.frecventa_mhz
                    if diff_pct > 0.05 and tf_int != obj.frecventa_mhz:
                        score -= 50
                        break

    # ═════════════════════════════════════════════════════════════════════════════════
    elif isinstance(obj, Storage):
    # ═════════════════════════════════════════════════════════════════════════════════
        if not _brand_in_title(brand_lower, title_lower):
            return 0
        score += 25

        name_clean = obj.nume.lower()
        cap_gb     = obj.capacitate_gb

        # Extragem ID-uri de model: litere+cifre (mx500, sn750), cifre>=3 (990, 870),
        # sau cuvinte alfa scurte ce apar în modele (pro, evo, blue, red, black, plus, se, ultra)
        model_alpha_num = re.findall(r"\b[a-z]+\d+[a-z]*\b", name_clean)
        model_numeric   = re.findall(r"\b\d{3,4}\b", name_clean)
        # Cuvinte de model "pure" fără cifre care apar în titluri (Pro, EVO, Blue, etc.)
        MODEL_WORDS = {"pro", "evo", "blue", "red", "black", "plus", "ultra", "se",
                       "fury", "renegade", "barracuda", "firecuda", "ironwolf", "red",
                       "gold", "purple", "a400", "870", "860", "850", "990", "980", "970"}
        model_name_words = [w for w in name_clean.split() if w in MODEL_WORDS]

        skip_ids = {str(cap_gb), "m2", "gen3", "gen4", "gen5", "sata3", "sata2",
                    "128", "256", "512", "2280", "2230"}

        all_model_ids = set(model_alpha_num + model_numeric + model_name_words) - skip_ids

        if any(mid in title_lower for mid in all_model_ids):
            score += 25

        valid_caps = [f"{cap_gb}gb", f"{cap_gb} gb"]
        if cap_gb in (1000, 1024): valid_caps.extend(["1tb", "1 tb"])
        elif cap_gb in (2000, 2048): valid_caps.extend(["2tb", "2 tb"])
        elif cap_gb >= 1000:
            tb = cap_gb / 1000
            valid_caps.extend([f"{tb:g}tb", f"{tb:g} tb"])
        if any(c in title_lower for c in valid_caps):
            score += 30

        tip_lower = obj.tip.lower() if hasattr(obj, "tip") and obj.tip else ""

        # Bonus interfata (+10): SSD NVMe trebuie sa aiba nvme/m.2/pcie in titlu
        INTERFACES = {"nvme": ["nvme", "m.2", "pcie"], "sata": ["sata", "2.5"], "hdd": ["hdd"]}
        for iface, keywords in INTERFACES.items():
            if iface in tip_lower and any(k in title_lower for k in keywords):
                score += 10
                break

        # Bonus tip explicit (+5) — "SSD" in titlu pt SSD, "HDD" pt HDD
        if "hdd" in tip_lower and "hdd" in title_lower:
            score += 5
        elif "ssd" in tip_lower and "ssd" in title_lower:
            score += 5

        # ── Penalizări fatale ──────────────────────────────────────────────────────
        if not any(c in title_lower for c in valid_caps):
            if re.findall(r"\d+\s*(?:tb|gb)", title_lower):
                score -= 50

        if "hdd" in tip_lower and ("ssd" in title_lower or "nvme" in title_lower):
            score -= 50
        if "ssd" in tip_lower and "hdd" in title_lower and "ssd" not in title_lower:
            score -= 50

        # Penalizare: interfata gresita (NVMe in DB dar SATA in titlu si invers)
        if "nvme" in tip_lower and "sata" in title_lower and "nvme" not in title_lower and "m.2" not in title_lower:
            score -= 50
        if "sata" in tip_lower and ("nvme" in title_lower or "pcie" in title_lower) and "sata" not in title_lower:
            score -= 30  # Nu fatal — unele magazine scriu ambele

    # ═════════════════════════════════════════════════════════════════════════════════
    elif isinstance(obj, PSU):
    # ═════════════════════════════════════════════════════════════════════════════════
        if not _brand_in_title(brand_lower, title_lower):
            return 0
        score += 25

        nu_curat   = obj.nume.lower()
        model_ids  = re.findall(r"\b[a-z]+\d+[a-z]*\b", nu_curat)
        ignore_ids = {"plus", "gold", "bronze", "platinum", "core", "pure", "dark", "power"}
        if any(mid not in ignore_ids and mid in title_lower for mid in model_ids):
            score += 25

        if getattr(obj, "putere_w", None):
            w_val = str(obj.putere_w)
            if any(fmt in title_lower for fmt in [f"{w_val}w", f"{w_val} w", f"{w_val} watt"]):
                score += 30

        if getattr(obj, "certificare", None):
            cert_text = str(obj.certificare).lower()
            cert_kw   = [w for w in re.findall(r"[a-z]+", cert_text)
                         if w in ["gold", "bronze", "platinum", "titanium", "silver"]]
            if all(kw in title_lower for kw in cert_kw):
                score += 10

        PSU_MOD_KW = ["full modular", "fully modular", "modular", "semi-modular", "semi modular"]
        db_mod    = any(k in name_lower for k in PSU_MOD_KW)
        title_mod = any(k in title_lower for k in PSU_MOD_KW)
        if db_mod == title_mod:
            score += 10

        if getattr(obj, "putere_w", None):
            w_val = str(obj.putere_w)
            has_power = any(fmt in title_lower for fmt in [f"{w_val}w", f"{w_val} w", f"{w_val} watt"])
            if not has_power and re.findall(r"(\d{3,4})\s*(?:w|watt)", title_lower):
                score -= 50

        CERT_RANK = {"titanium": 5, "platinum": 4, "gold": 3, "silver": 2, "bronze": 1}
        if getattr(obj, "certificare", None):
            cert_text  = str(obj.certificare).lower()
            db_cert_kw = [w for w in re.findall(r"[a-z]+", cert_text) if w in CERT_RANK]
            if db_cert_kw:
                db_rank = CERT_RANK[db_cert_kw[0]]
                title_certs = [w for w in title_lower.split() if w in CERT_RANK]
                if title_certs and CERT_RANK[title_certs[0]] < db_rank:
                    score -= 50

    # ═════════════════════════════════════════════════════════════════════════════════
    elif isinstance(obj, Case):
    # ═════════════════════════════════════════════════════════════════════════════════
        if not _brand_in_title(brand_lower, title_lower):
            return 0
        score += 25

        name_lower_c = obj.nume.lower()
        model_ids    = re.findall(r"\b[a-z]*\d+[a-z]*\b", name_lower_c)
        skip_v       = ["v1", "v2", "30", "31"]
        found_id     = any(mid not in skip_v and mid in title_lower for mid in model_ids)
        if found_id:
            score += 25

        CASE_SUBCODES = [
            "airflow", "tempered", "tg", "elite", "mesh", "rgb", "pro",
            "compact", "nano", "shift", "define", "pop", "torrent"
        ]
        for code in CASE_SUBCODES:
            if code in name_lower_c and code in title_lower:
                score += 30
                break

        db_is_white = "white" in name_lower_c or "alb" in name_lower_c
        db_is_black = "black" in name_lower_c or "negru" in name_lower_c
        title_white = "white" in title_lower or "alb" in title_lower
        title_black = "black" in title_lower or "negru" in title_lower
        color_match = ((db_is_white and title_white) or (db_is_black and title_black)
                       or (not db_is_white and not db_is_black))
        if color_match:
            score += 10

        FORMATS = {"full": ["full tower", "full-tower"], "mini": ["mini", "itx"]}
        db_fmt = "mini" if any(x in name_lower_c for x in ["mini", "itx"]) else \
                 "full" if "full" in name_lower_c else "midi"
        if any(f in title_lower for f in FORMATS.get(db_fmt, ["midi", "mid tower", "atx"])):
            score += 10

        if db_is_white and title_black and not title_white:
            score -= 50
        if db_is_black and title_white and not title_black:
            score -= 50
        if not found_id and model_ids:
            score -= 50

    # ═════════════════════════════════════════════════════════════════════════════════
    elif isinstance(obj, Cooler):
    # ═════════════════════════════════════════════════════════════════════════════════
        if not _brand_in_title(brand_lower, title_lower):
            return 0
        score += 25

        name_lower_c = obj.nume.lower()
        model_ids    = re.findall(r"\b[a-z]+\d+[a-z]*\b", name_lower_c)
        COOLER_MODEL_WORDS = [
            "liquid freezer", "dark rock", "shadow rock", "pure rock",
            "peerless", "assassin", "phantom spirit", "neptwin", "master air", "hyper"
        ]
        found_model = any(mid in title_lower for mid in model_ids) or \
                      any(code in name_lower_c and code in title_lower for code in COOLER_MODEL_WORDS)
        if found_model:
            score += 25

        IMPORTANT_VERSIONS = ["ii", "iii", "iv", "34", "35", "36", "360", "240", "280", "420"]
        version_match = all(
            not (re.search(rf"\b{v}\b", name_lower_c) and not re.search(rf"\b{v}\b", title_lower))
            for v in IMPORTANT_VERSIONS
        )
        if version_match:
            score += 30

        aio_sizes = ["240", "280", "360", "420"]
        db_aio    = next((s for s in aio_sizes if s in name_lower_c), None)
        if db_aio and db_aio in title_lower:
            score += 10
        elif not db_aio and not any(s in title_lower for s in aio_sizes):
            score += 10

        db_is_white = "white" in name_lower_c or "alb" in name_lower_c
        if (db_is_white and ("white" in title_lower or "alb" in title_lower)) or \
           (not db_is_white and "white" not in title_lower):
            score += 10

        if db_aio:
            other_aio = [s for s in aio_sizes if s != db_aio and s in title_lower]
            if other_aio:
                score -= 50

        for v in ["ii", "iii"]:
            db_has    = bool(re.search(rf"\b{v}\b", name_lower_c))
            title_has = bool(re.search(rf"\b{v}\b", title_lower))
            if db_has != title_has:
                score -= 50
                break

    return max(0, score)


def _select_best_result(results: list["PriceResult"]) -> "PriceResult | None":
    """
    Selectează cel mai bun PriceResult dintr-o listă de candidați valizi
    (toți cu compatibility_score ≥ MIN_SCORE).

    Reguli (in ordine):
    1. Dacă există un singur candidat → el câștigă.
    2. Dacă diferența de scor e ≤ SCORE_TOLERANCE → câștigă cel mai ieftin.
    3. Dacă cel cu scor mai mare e cu > MAX_PRICE_PREMIUM mai scump → câștigă prețul.
    4. Altfel → câștigă scorul mai mare.
    """
    if not results:
        return None
    if len(results) == 1:
        return results[0]

    best_score = max(results, key=lambda r: r.compatibility_score)
    cheapest   = min(results, key=lambda r: r.price)

    if best_score is cheapest:
        return best_score

    score_diff     = best_score.compatibility_score - cheapest.compatibility_score
    price_diff_pct = float(best_score.price - cheapest.price) / float(cheapest.price)

    if score_diff <= SCORE_TOLERANCE:
        return cheapest
    if price_diff_pct > MAX_PRICE_PREMIUM:
        return cheapest
    return best_score


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

        # Verificam socket-ul pe pagina produsului
        if obj.socket:
            socket_lower = obj.socket.lower()
            socket_num = re.sub(r'[^0-9]', '', socket_lower)
            socket_on_page = (
                socket_lower in page_text
                or (socket_num and len(socket_num) >= 3 and socket_num in page_text)
            )
            if not socket_on_page:
                return False

        if obj.chipset:
            if obj.chipset.lower() not in page_text:
                return False



        # Verificam WiFi doar cand DB zice ca placa ARE WiFi —
        # confirmam ca specificatiile paginii mentioneaza WiFi.
        # Daca DB zice ca NU are WiFi, nu respingem pe baza paginii
        # (cuvantul "wifi" apare des in produse recomandate, ads, footer).
        # Cazul "DB fara WiFi + titlu cu WiFi" e deja prins de _is_valid_title_match.
        if obj.are_wifi:
            has_wifi = "wifi" in page_text or "wi-fi" in page_text or "wireless" in page_text
            if not has_wifi:
                return False

        # Nu mai verificam Bluetooth pe pagina intreaga —
        # apare prea des in texte irelevante (related products, footer).
        # Bluetooth coreleaza aproape intotdeauna cu WiFi pe placi de baza.

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


SITE_SCRAPERS = [
    scrape_emag,
    scrape_cel,
]


# ─────────────────────────── MAIN SEARCH LOGIC ───────────────────────────────

def _build_motherboard_fallback_query(obj, site: str) -> Optional[str]:
    """Query simplificat de fallback pentru placi de baza:
       brand + chipset + model keywords."""
    if not isinstance(obj, Motherboard):
        return None

    brand = str(obj.brand).strip()
    chipset = str(obj.chipset).strip() if obj.chipset else ""
    wifi_str = "WiFi" if obj.are_wifi else ""

    # Extragem cuvinte-cheie de model din nume (fara brand si chipset)
    name_words = obj.nume.split()
    model_keywords = []
    skip_words = {brand.lower(), chipset.lower(), "wifi", "wi-fi"}
    for w in name_words:
        if w.lower() not in skip_words and not re.match(r'^[A-Z]{1,3}\d{3,4}$', w):
            model_keywords.append(w)

    model_str = " ".join(model_keywords[:3])

    query = f"Placa de baza {brand} {chipset} {model_str} {wifi_str}"
    return re.sub(r'\s+', ' ', query.strip())


def _evaluate_site_results(
    site_results: list[PriceResult],
    obj,
    session,
    site_name: str,
    min_similarity: float,
    verbose: bool,
) -> list[PriceResult]:
    """Evalueaza rezultatele de pe un site si returneaza cele valide."""
    valid = []
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

        # Calculează scorul de compatibilitate și filtrează sub prag
        r.compatibility_score = _compute_compatibility_score(r, obj)
        if r.compatibility_score < MIN_SCORE:
            if verbose:
                print(f"    [{site_name}] RESPINS scor={r.compatibility_score}/100 (sub {MIN_SCORE}): {r.title[:60]}")
            continue

        if verbose:
            print(f"    [{site_name}] OK scor={r.compatibility_score}/100 {r.price:.2f} Lei | {r.title[:60]}")
        valid.append(r)

    return valid


def find_all_valid_prices(
    session,
    obj,
    min_similarity: float = 0.55,
    verbose: bool = False,
) -> list[PriceResult]:
    
    if isinstance(obj, (Case, Storage, Motherboard)):
        min_similarity = 0.35
    elif isinstance(obj, (RAM, PSU)):
        min_similarity = 0.45
        
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

            site_valid = _evaluate_site_results(
                site_results, obj, session, site_name, min_similarity, verbose
            )
            all_valid.extend(site_valid)

            # Retry cu query simplificat daca nu am gasit nimic pt motherboard
            if not site_valid and isinstance(obj, Motherboard):
                fallback_q = _build_motherboard_fallback_query(obj, site_name)
                if fallback_q and fallback_q != query:
                    if verbose:
                        print(f"  [{site_name}] RETRY cu query simplificat: '{fallback_q}'")
                    _rand_delay(1.0, 2.5)
                    retry_results = scrape_fn(session, fallback_q)
                    if retry_results:
                        # La retry, scadem similarity threshold putin
                        retry_valid = _evaluate_site_results(
                            retry_results, obj, session, site_name,
                            max(0.40, min_similarity - 0.10), verbose
                        )
                        all_valid.extend(retry_valid)

            # Retry simplificat si pentru Storage — daca nu am gasit nimic
            if not site_valid and isinstance(obj, Storage):
                brand = str(obj.brand).strip()
                brand_search = "WD" if brand.lower() == "western digital" else brand
                cap_val = obj.capacitate_gb
                if cap_val >= 1000:
                    tb = cap_val // 1000 if cap_val % 1000 == 0 else cap_val // 1024
                    cap_str = f"{tb:g}TB"
                else:
                    cap_str = f"{cap_val}GB"
                prefix_fb = "HDD" if obj.tip == "HDD" else "SSD"
                # Query ultra-simplu: doar tip + brand + capacitate
                fallback_q = f"{prefix_fb} {brand_search} {cap_str}"
                if fallback_q.strip() != query.strip():
                    if verbose:
                        print(f"  [{site_name}] RETRY storage simplificat: '{fallback_q}'")
                    _rand_delay(1.0, 2.5)
                    retry_results = scrape_fn(session, fallback_q)
                    if retry_results:
                        retry_valid = _evaluate_site_results(
                            retry_results, obj, session, site_name,
                            max(0.30, min_similarity - 0.10), verbose
                        )
                        all_valid.extend(retry_valid)

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
        self.stdout.write("Price Updater - eMag / CEL")
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
                            # if obj.part_number:
                            #     Blacklist.objects.get_or_create(
                            #         part_number=obj.part_number,
                            #         defaults={'nume': obj.nume},
                            #     )
                            # else:
                            #     Blacklist.objects.get_or_create(
                            #         nume=obj.nume,
                            #         defaults={'part_number': None},
                            #     )
                            # obj.delete()
                            pass

                        stats["sterse"] += 1
                    else:
                        best = _select_best_result(valid_results)
                        if best is None:
                            self.stdout.write("-> NU GASIT (toate sub scor)")
                            stats["sterse"] += 1
                        else:
                            self.stdout.write(f"-> {best.price:.2f} Lei ({best.site}) [scor: {best.compatibility_score}/100]")

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