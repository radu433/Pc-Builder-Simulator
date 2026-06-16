import re
import time
import random
import logging
from decimal import Decimal, InvalidOperation
from typing import Optional, Dict, Any, List

from django.core.management.base import BaseCommand
from django.db import transaction

# Importăm toate componentele
from components.models import (
    CPU, GPU, Motherboard, RAM, PSU, Case, Cooler, Storage, Monitor, Fan
)

try:
    from scrapling.fetchers import DynamicSession
except ImportError:
    raise ImportError(
        "Ruleaza: pip install 'scrapling[fetchers]' && scrapling install"
    )

logger = logging.getLogger(__name__)

# ─────────────────────────── CONFIG ──────────────────────────────────────────

DELAY_PRODUCT  = 3.0      
DELAY_PAGE     = (2.0, 5.0)
DELAY_BATCH    = (15, 30)
BATCH_SIZE     = 20       

KNOWN_BRANDS = [
    "amd", "intel", "nvidia", "asus", "msi", "gigabyte", "asrock", "sapphire", 
    "powercolor", "xfx", "zotac", "palit", "gainward", "inno3d", "pny", "evga",
    "corsair", "kingston", "g.skill", "crucial", "adata", "teamgroup", "patriot",
    "seasonic", "be quiet!", "thermaltake", "cooler master", "nzxt", "fractal design",
    "deepcool", "noctua", "arctic", "lian li", "phanteks", "aerocool", "zalman",
    "seagate", "western digital", "wd", "samsung"
]

# Mapping Componente -> (Model_Django, URL_eMag)
CATEGORIES_MAP = {
    "CPU":         (CPU, "https://www.emag.ro/procesoare/p{}/c"),
    "GPU":         (GPU, "https://www.emag.ro/placi_video/p{}/c"),
    "Motherboard": (Motherboard, "https://www.emag.ro/placi_baza/p{}/c"),
    "RAM":         (RAM, "https://www.emag.ro/memorii/p{}/c"),
    "PSU":         (PSU, "https://www.emag.ro/surse-pc/p{}/c"),
    "Case":        (Case, "https://www.emag.ro/carcase/p{}/c"),
    "Cooler":      (Cooler, "https://www.emag.ro/coolere_procesor/p{}/c"),
    "Storage":     (Storage, "https://www.emag.ro/solid-state_drive_ssd_/p{}/c"),
}

# ─────────────────────────── HELPERS ─────────────────────────────────────────

def _parse_price(int_text: str, dec_text: str) -> Optional[Decimal]:
    try:
        int_clean = re.sub(r"[^\d]", "", int_text or "")
        dec_clean = re.sub(r"[^\d]", "", dec_text or "0")
        if not int_clean:
            return None
        return Decimal(f"{int_clean}.{dec_clean[:2]}")
    except (InvalidOperation, ValueError):
        return None

def _extract_brand(title: str, specs: dict) -> str:
    for key in ("brand", "producator", "manufacturer"):
        if key in specs:
            return specs[key].strip()

    title_l = title.lower()
    for brand in KNOWN_BRANDS:
        if brand in title_l:
            return brand.title() if " " not in brand else brand.title()

    words = title.split()
    return words[0] if words else "Unknown"

def _find_spec(specs: dict, *keywords) -> Optional[str]:
    for kw in keywords:
        kw_l = kw.lower()
        for key, val in specs.items():
            if kw_l in key:
                return val
    return None

def _extract_number(text: str) -> Optional[int]:
    if not text:
        return None
    m = re.search(r"(\d+)", text.replace(".", "").replace(",", ""))
    if m:
        return int(m.group(1))
    return None

def _extract_float(text: str) -> Optional[float]:
    if not text:
        return None
    m = re.search(r"(\d+(?:[.,]\d+)?)", text)
    if m:
        return float(m.group(1).replace(",", "."))
    return None

def _extract_specs(page) -> dict:
    specs = {}
    dts = page.css("dt")
    dds = page.css("dd")
    for dt, dd in zip(dts, dds):
        key = " ".join(dt.css("::text").getall()).strip().lower()
        val = " ".join(dd.css("::text").getall()).strip()
        if key and val:
            specs[key] = val

    if not specs:
        rows = page.css("table.specifications-body tr, .product-page-specifications tr, .product-specs tr, table.specifications-table tr")
        for row in rows:
            cells = row.css("td, th")
            if len(cells) >= 2:
                key = " ".join(cells[0].css("::text").getall()).strip().lower()
                val = " ".join(cells[1].css("::text").getall()).strip()
                if key and val:
                    specs[key] = val
    return specs

def _parse_io_ports(text: str) -> dict:
    if not text:
        return {}
        
    parts = re.split(r'(\d+)\s*[xX]\s+', text)
    ports = {}
    
    for i in range(1, len(parts)-1, 2):
        count_str = parts[i]
        name_str = parts[i+1]
        
        # Curățăm numele portului (scoatem paranteze de la început/sfârșit, virgule și plusuri)
        name_clean = re.sub(r'^[,\s\(]+|[,\s\)]+$', '', name_str).strip()
        name_clean = re.sub(r'\+$', '', name_clean).strip()
        
        if count_str.isdigit() and name_clean:
            if name_clean in ports:
                ports[name_clean] += int(count_str)
            else:
                ports[name_clean] = int(count_str)
                
    # Fallback dacă string-ul are alt format
    if not ports and text.strip():
        ports["Altele"] = text.strip()
        
    return ports

def _rand_delay(min_s: float, max_s: float):
    time.sleep(random.uniform(min_s, max_s))


# ─────────────────────────── PARSERS SPECIFICE ──────────────────────────────

def _parse_cpu(specs: dict, title: str) -> dict:
    socket = _find_spec(specs, "socket", "soclu") or "Unknown"
    serie = _find_spec(specs, "serie", "familie", "family") or "Unknown"
    
    nuclee = _extract_number(_find_spec(specs, "numar nuclee", "cores", "nuclee")) or 4
    threaduri = _extract_number(_find_spec(specs, "numar thread-uri", "threads", "fire")) or nuclee * 2
    
    freq_str = _find_spec(specs, "frecventa", "frecvenţă", "frequency")
    frecventa_ghz = _extract_float(freq_str) or 3.0
    if frecventa_ghz > 100:  # eMag pune in MHz uneori
        frecventa_ghz = frecventa_ghz / 1000.0
        
    tdp = _extract_number(_find_spec(specs, "putere", "tdp", "consum")) or 65

    return {
        "socket": socket,
        "serie": serie,
        "nuclee": nuclee,
        "threaduri": threaduri,
        "frecventa_ghz": Decimal(str(round(frecventa_ghz, 2))),
        "consum_tdp": tdp
    }

def _parse_gpu(specs: dict, title: str) -> dict:
    title_l = title.lower()

    # 1. Determină Chipset Brand
    chipset_brand = "Unknown"
    if "geforce" in title_l or "rtx " in title_l or "gtx " in title_l:
        chipset_brand = "NVIDIA"
    elif "radeon" in title_l or "rx " in title_l:
        chipset_brand = "AMD"
    elif "arc" in title_l or "intel" in title_l:
        chipset_brand = "Intel"

    # 2. Extrage Serie și Model din titlu
    serie = "Unknown"
    model_chipset = "Unknown"

    if chipset_brand == "NVIDIA":
        # ex: RTX 4060 Ti, 5060
        m = re.search(r'(?:rtx|gtx)\s*(\d{4})\s*(ti|super)?', title_l)
        if m:
            num = int(m.group(1))
            suf = m.group(2)
            serie = f"{num // 1000 * 1000}"
            model_chipset = f"{num}{suf.title() if suf else ''}"

    elif chipset_brand == "AMD":
        # ex: RX 7900 XTX, 9060 XT
        m = re.search(r'rx\s*(\d{4})\s*(xtx|xt|gre)?', title_l)
        if m:
            num = int(m.group(1))
            suf = m.group(2)
            serie = f"{num // 1000 * 1000}"
            model_chipset = f"{num}{suf.upper() if suf else ''}"

    elif chipset_brand == "Intel":
        # ex: Arc A770, B580
        m = re.search(r'\b([a-b])(\d{3})\b', title_l)
        if m:
            litera = m.group(1).upper()
            num = m.group(2)
            serie = litera
            model_chipset = num

    # 3. Fallback la specs dacă e un model vechi/ciudat și nu a prins regex-ul
    if serie == "Unknown":
        serie = _find_spec(specs, "serie procesor", "serie") or "Unknown"
    if model_chipset == "Unknown":
        model_chipset = _find_spec(specs, "model", "procesor video") or "Unknown"
    
    vram_str = _find_spec(specs, "capacitate memorie", "memorie") or ""
    vram_gb = _extract_number(vram_str) or 8
    if "mb" in vram_str.lower() and vram_gb >= 1024:
        vram_gb = vram_gb // 1024
        
    tip_vram = _find_spec(specs, "tip memorie") or "GDDR6"
    consum = _extract_number(_find_spec(specs, "sursa minima", "tdp", "consum")) or 200
    
    # Defaults pentru dimensiuni daca lipsesc
    lungime = _extract_number(_find_spec(specs, "lungime", "length")) or 250
    latime = _extract_number(_find_spec(specs, "latime", "width")) or 120
    inaltime = _extract_number(_find_spec(specs, "inaltime", "height", "grosime")) or 45

    return {
        "serie": serie,
        "model_chipset": model_chipset,
        "chipset_brand": chipset_brand,
        "vram_gb": vram_gb,
        "tip_vram": tip_vram,
        "consum_tdp": consum,
        "lungime_mm": lungime,
        "latime_mm": latime,
        "inaltime_mm": inaltime
    }

def _parse_motherboard(specs: dict, title: str) -> dict:
    # 1. Extragere Socket din titlu
    socket_mb = "Unknown"
    m_socket = re.search(r'socket\s+([a-zA-Z0-9\-]+)', title, re.IGNORECASE)
    if m_socket:
        socket_mb = m_socket.group(1).upper()
    else:
        socket_mb = _find_spec(specs, "socket", "soclu") or "Unknown"

    # 2. Extragere Chipset din titlu (ex: B550-F, A520M, Z790, X670E)
    chipset = "Unknown"
    m_chipset = re.search(r'\b([ABXHZ]\d{3}[A-Z]?(?:-[A-Z0-9]+)?)\b', title, re.IGNORECASE)
    if m_chipset:
        chipset = m_chipset.group(1).upper()
    else:
        chipset = _find_spec(specs, "chipset") or "Unknown"

    format_mb = _find_spec(specs, "format", "factor de forma") or "ATX"
    tip_memorie = _find_spec(specs, "tip memorie", "memorie suportata") or "DDR4"
    
    sloturi = _extract_number(_find_spec(specs, "sloturi memorie", "numar sloturi")) or 4
    cap_max = _extract_number(_find_spec(specs, "capacitate maxima", "memorie maxima")) or 128
    m2 = _extract_number(_find_spec(specs, "m.2", "sloturi m.2")) or 1
    
    are_wifi = bool(_find_spec(specs, "wireless", "wi-fi", "wifi")) or ("wifi" in title.lower())
    are_bt = bool(_find_spec(specs, "bluetooth")) or are_wifi
    
    # 3. Parsare Porturi I/O din string brut
    io_text = _find_spec(specs, "conectivitate", "panou spate", "porturi spate", "rear panel") or ""
    porturi_json = _parse_io_ports(io_text)
    
    return {
        "socket": socket_mb,
        "chipset": chipset,
        "format": format_mb,
        "tip_memorie": tip_memorie,
        "sloturi_ram": sloturi,
        "capacitate_max_ram_gb": cap_max,
        "nr_sloturi_m2": m2,
        "are_wifi": are_wifi,
        "are_bluetooth": are_bt,
        "porturi_io": porturi_json
    }

def _parse_ram(specs: dict, title: str) -> dict:
    cap_str = _find_spec(specs, "capacitate", "capacity") or ""
    cap_tot = _extract_number(cap_str) or 16
    
    nr_module_din_cap = None
    if "x" in cap_str.lower():
        parts = cap_str.lower().split("x")
        try:
            mod_count = int(re.sub(r'[^\d]', '', parts[0]))
            mod_cap = _extract_number(parts[1])
            if mod_count and mod_cap:
                cap_tot = mod_count * mod_cap
                nr_module_din_cap = mod_count
        except: pass

    module_text = _find_spec(specs, "module", "numar module", "kit") or ""
    module_text_l = module_text.lower()

    if nr_module_din_cap:
        nr_module = nr_module_din_cap
    elif "quad" in module_text_l:
        nr_module = 4
    elif "dual" in module_text_l:
        nr_module = 2
    elif "single" in module_text_l:
        nr_module = 1
    else:
        nr_module = _extract_number(module_text) or (2 if "kit" in title.lower() else 1)

    tip_memorie = _find_spec(specs, "tip", "tip memorie") or "DDR4"
    freq = _extract_number(_find_spec(specs, "frecventa", "frequency")) or 3200
    latenta = _extract_number(_find_spec(specs, "latenta", "cas latency", "cl")) or 16

    return {
        "capacitate_totala_gb": cap_tot,
        "capacitate_modul_gb": cap_tot // nr_module if nr_module > 0 else cap_tot,
        "numar_module": nr_module,
        "tip_memorie": tip_memorie,
        "frecventa_mhz": freq,
        "latenta_cl": latenta,
        "inaltime_mm": 35.0
    }

def _parse_psu(specs: dict, title: str) -> dict:
    putere = _extract_number(_find_spec(specs, "putere", "power")) or 500
    cert = _find_spec(specs, "certificare", "eficienta", "80 plus") or "80 Plus"
    
    modulara = "Non"
    if "full modular" in title.lower() or "100% modular" in str(specs).lower():
        modulara = "Full"
    elif "semi modular" in title.lower():
        modulara = "Semi"

    format_psu = _find_spec(specs, "format", "factor de forma") or "ATX"

    return {
        "putere_w": putere,
        "certificare": cert,
        "este_modulara": modulara,
        "format": format_psu,
        "lungime_mm": 150
    }

def _parse_case(specs: dict, title: str) -> dict:
    tip = _find_spec(specs, "tip carcasa", "tip") or "Middle Tower"
    
    # Map tip_carcasa to CHOICES
    tip_mapped = 'MID'
    if 'full' in tip.lower(): tip_mapped = 'FULL'
    elif 'mini' in tip.lower(): tip_mapped = 'MINI'

    gpu_max = _extract_number(_find_spec(specs, "lungime video", "placa video maxima")) or 300
    cooler_max = _extract_number(_find_spec(specs, "inaltime cooler", "cooler maxim")) or 160
    inc_sursa = bool(_find_spec(specs, "sursa inclusa"))

    formate_text = _find_spec(specs, "compatibilitate", "placi de baza", "placi compatibile") or ""
    formate_text_l = formate_text.lower()
    formate = []
    
    # Caută exact ca un cuvânt întreg (\b) ca să nu citească "atx" din "matx"
    if re.search(r'\be-atx\b|\beatx\b', formate_text_l): formate.append("E-ATX")
    if re.search(r'\batx\b', formate_text_l): formate.append("ATX")
    if re.search(r'\bmicro\b|\bmatx\b|\bm-atx\b', formate_text_l): formate.append("mATX")
    if re.search(r'\bmini\b|\bitx\b', formate_text_l): formate.append("Mini-ITX")
    
    # Fallback 1: caută și în titlu dacă eMag n-a pus nimic în tabel
    if not formate:
        t_l = title.lower()
        if re.search(r'\be-atx\b|\beatx\b', t_l): formate.append("E-ATX")
        if re.search(r'\batx\b', t_l): formate.append("ATX")
        if re.search(r'\bmicro\b|\bmatx\b|\bm-atx\b', t_l): formate.append("mATX")
        if re.search(r'\bmini\b|\bitx\b', t_l): formate.append("Mini-ITX")

    # Fallback 2: Dacă efectiv nu scrie nimic nicăieri, punem ATX pentru Full/Mid și Mini-ITX pentru Mini
    if not formate:
        if tip_mapped == 'MINI':
            formate = ["Mini-ITX"]
        else:
            formate = ["ATX"]
        
    dim_str = _find_spec(specs, "dimensiuni") or ""
    m_dims = [int(x) for x in re.findall(r'(\d+)', dim_str)]
    inaltime, latime, lungime = 450, 200, 400
    
    if len(m_dims) >= 3:
        m_dims = sorted(m_dims[:3])
        latime = m_dims[0]   # Cea mai mică dimensiune e lățimea la carcase
        lungime = m_dims[1]
        inaltime = m_dims[2]

    return {
        "tip_carcasa": tip_mapped,
        "include_sursa": inc_sursa,
        "lungime_max_gpu_mm": gpu_max,
        "inaltime_max_cooler_mm": cooler_max,
        "pozitie_sursa": "Jos",
        "inaltime_mm": inaltime,
        "lungime_mm": lungime,
        "latime_mm": latime,
        "formate_suportate": formate,
        "suport_radiator_mm": []
    }

def _parse_cooler(specs: dict, title: str) -> dict:
    tip = "Aer"
    if "lichid" in str(specs).lower() or "water" in title.lower() or "aio" in title.lower():
        tip = "Lichid"
    
    inaltime = _extract_number(_find_spec(specs, "inaltime", "height")) or 150
    radiator = _extract_number(_find_spec(specs, "dimensiuni radiator", "lungime radiator")) or 0

    return {
        "tip_racire": tip,
        "socket_suportate": ["AM4", "AM5", "LGA1700", "LGA1200"],
        "inaltime_mm": inaltime if tip == "Aer" else None,
        "lungime_radiator_mm": radiator if tip == "Lichid" else None
    }

def _parse_capacity(text: str) -> Optional[int]:
    if not text: return None
    text_l = text.lower().replace(" ", "")
    m_tb = re.search(r"(\d+(?:\.\d+)?)tb", text_l)
    if m_tb: return int(float(m_tb.group(1)) * 1024)
    m_gb = re.search(r"(\d+)gb", text_l)
    if m_gb: return int(m_gb.group(1))
    return None

def _parse_storage(specs: dict, title: str) -> dict:
    cap_text = _find_spec(specs, "capacitate", "capacity") or title
    cap_gb = _parse_capacity(cap_text) or 500

    iface_text  = _find_spec(specs, "interfata", "interface") or "M.2 NVMe"
    read_text   = _find_spec(specs, "rata de transfer la citire", "viteza de citire", "citire max", "read speed", "citire") or ""
    write_text  = _find_spec(specs, "rata de transfer la scriere", "viteza de scriere", "scriere max", "write speed", "scriere") or ""
    format_text = _find_spec(specs, "format", "form factor") or "M.2"
    pn_text     = _find_spec(specs, "part number", "model number") or ""

    return {
        "tip": "SSD",
        "capacitate_gb": cap_gb,
        "interfata": iface_text[:50],
        "viteza_citire_mb_s": _extract_number(read_text),
        "viteza_scriere_mb_s": _extract_number(write_text),
        "format": format_text[:50],
        "part_number": pn_text[:50]
    }


# Dictionar care trimite catre functia de parsare corecta in functie de Model
PARSERS = {
    "CPU": _parse_cpu,
    "GPU": _parse_gpu,
    "Motherboard": _parse_motherboard,
    "RAM": _parse_ram,
    "PSU": _parse_psu,
    "Case": _parse_case,
    "Cooler": _parse_cooler,
    "Storage": _parse_storage,
}

# ─────────────────────────── CORE SCRAPER ────────────────────────────────────

def _scrape_listing_page(session, url: str) -> list[dict]:
    try:
        page = session.fetch(url, network_idle=True)
    except Exception as e:
        logger.warning("Eroare listing %s: %s", url, e)
        return []

    cards = page.css("div.card-item, .product-holder, .js-product-data")
    results = []
    
    for card in cards:
        title_el = card.css("a.card-v2-title, a.product-title, h2 a")
        if not title_el: continue

        title    = " ".join(title_el.css("::text").getall()).strip()
        prod_url = title_el.css("::attr(href)").get("") or ""

        price_int = " ".join(card.css(".product-new-price::text").getall()).strip()
        price_dec = " ".join(card.css(".product-new-price sup::text").getall()).strip()

        img_url = card.css(".card-v2-thumb-inner img::attr(src)").get("") or ""
        if not img_url or img_url.startswith("data:"):
            img_url = card.css(".card-v2-thumb-inner img::attr(data-src)").get("") or ""

        if title and prod_url:
            results.append({
                "title":     title,
                "url":       prod_url if prod_url.startswith("http") else f"https://www.emag.ro{prod_url}",
                "price_int": price_int,
                "price_dec": price_dec,
                "img":       img_url,
            })

    return results

# ─────────────────────────── COMMAND ─────────────────────────────────────────

class Command(BaseCommand):
    help = "Populează DB-ul cu până la 150 produse noi din fiecare categorie eMag"

    def add_arguments(self, parser):
        parser.add_argument("--headless", action="store_true", default=False)
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--model", type=str, choices=CATEGORIES_MAP.keys(), 
                            help="Rulează doar pentru un model anume")
        parser.add_argument("--limit", type=int, default=150,
                            help="Câte produse NOI să salveze per categorie")
        parser.add_argument("--verbose", action="store_true",
                            help="Afișează specificațiile extrase pentru fiecare produs")

    def handle(self, *args, **options):
        import os
        os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

        headless = options["headless"]
        dry_run  = options["dry_run"]
        target   = options["model"]
        limit    = options["limit"]
        verbose  = options["verbose"]

        categories = {k: v for k, v in CATEGORIES_MAP.items() if not target or k == target}

        self.stdout.write("=" * 65)
        self.stdout.write("  Universal Populator — eMag (150 noi/categorie)")
        if dry_run: self.stdout.write("  *** DRY RUN ***")
        self.stdout.write("=" * 65)

        with DynamicSession(headless=headless) as session:
            for cat_name, (ModelClass, url_template) in categories.items():
                self.stdout.write(f"\n{'─'*65}")
                self.stdout.write(f"  Procesare categorie: {cat_name}")
                self.stdout.write(f"{'─'*65}")

                parser_func = PARSERS.get(cat_name)
                if not parser_func:
                    self.stdout.write(f"Skipping {cat_name} - Niciun parser definit.")
                    continue

                noi_adaugate = 0
                page_num = 1
                total_processed = 0

                while noi_adaugate < limit:
                    page_url = url_template.format(page_num)
                    self.stdout.write(f"\n[Pagina {page_num}] {page_url}")

                    cards = _scrape_listing_page(session, page_url)
                    if not cards:
                        self.stdout.write("  → Pagină goală sau eroare. Trecem la următoarea categorie.")
                        break

                    _rand_delay(*DELAY_PAGE)

                    for card in cards:
                        if noi_adaugate >= limit:
                            break

                        total_processed += 1
                        if total_processed % BATCH_SIZE == 0:
                            p = random.uniform(*DELAY_BATCH)
                            self.stdout.write(f"  [Antibot] Pauză {p:.0f}s...")
                            time.sleep(p)

                        title = card["title"]
                        prod_url = card["url"]
                        price = _parse_price(card["price_int"], card["price_dec"])
                        prefix = f"[{noi_adaugate}/{limit}] {title[:50]:<50}"

                        # Verificare existență DB
                        existing = ModelClass.objects.filter(nume=title).first()
                        if existing:
                            if (existing.magazin or "").lower() == "emag":
                                if price: existing.pret = price
                                existing.url_produs = prod_url
                                existing.stoc = True
                                if not dry_run:
                                    existing.save(update_fields=["pret", "url_produs", "stoc", "ultima_actualizare"])
                                self.stdout.write(f"{prefix} UPDATE (eMag existent)")
                            else:
                                self.stdout.write(f"{prefix} SKIP (existent la {existing.magazin})")
                            
                            _rand_delay(DELAY_PRODUCT, DELAY_PRODUCT*1.5)
                            continue

                        # Nu există, preluăm specs
                        try:
                            page = session.fetch(prod_url, network_idle=True)
                            specs = _extract_specs(page)
                        except Exception as e:
                            self.stdout.write(f"{prefix} EROARE fetch specs: {e}")
                            _rand_delay(DELAY_PRODUCT, DELAY_PRODUCT*1.5)
                            continue

                        brand = _extract_brand(title, specs)
                        parsed_data = parser_func(specs, title)

                        if dry_run or verbose:
                            self.stdout.write(f"\n{prefix} Extrase -> Brand: {brand} | Preț: {price}")
                            for k, v in parsed_data.items():
                                self.stdout.write(f"    - {k}: {v}")

                        if dry_run:
                            self.stdout.write(f"  --> [DRY] NOU!\n")
                            noi_adaugate += 1
                        else:
                            try:
                                with transaction.atomic():
                                    ModelClass.objects.create(
                                        nume=title, brand=brand, pret=price,
                                        magazin="eMag", url_produs=prod_url,
                                        imagine_url=card["img"] or None,
                                        stoc=True, regiune="Romania",
                                        **parsed_data
                                    )
                                self.stdout.write(f"  --> NOU! (salvat în DB)\n")
                                noi_adaugate += 1
                            except Exception as e:
                                self.stdout.write(f"{prefix} EROARE DB: {e}")

                        _rand_delay(DELAY_PRODUCT, DELAY_PRODUCT*2)

                    page_num += 1

        self.stdout.write("\n" + "=" * 65)
        self.stdout.write("  FINALIZAT GATA")
        self.stdout.write("=" * 65)
