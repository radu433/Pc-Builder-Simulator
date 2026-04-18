"""
Scraper all-in-one pentru PC Builder Simulator.
Copiaza in: components/management/commands/import_all.py
Ruleaza cu: python manage.py import_all

FIX-URI APLICATE:
  1. get_ean() - fallback la slug URL cand nu exista cifre => rezolva motherboard + cooler
  2. PSU certificare - regex corectat sa prinda "80 PLUS GOLD" nu doar "80"
  3. PSU putere - labele extinse + fallback regex direct in text
  4. Case - adaugat lungime_maxima_gpu_mm si inaltime_maxima_cooler_mm
  5. RAM - fix parse capacitate module, fix swap frecventa/latenta
  6. Storage - model inregistrat in admin (vezi admin.py la sfarsit)
"""

import time
import re
import random
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    raise ImportError("Ruleaza: pip install requests beautifulsoup4")

from components.models import GPU, Motherboard, RAM, PSU, Case, Cooler, Storage

BASE_URL = "https://www.pc-kombo.com"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]


# ─────────────────────────── UTILITARE COMUNE ────────────────────────────────

def random_delay(min_s=0.8, max_s=2.2):
    time.sleep(random.uniform(min_s, max_s))


def get_session():
    s = requests.Session()
    s.headers.update({
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    })
    return s


def rotate_ua(session):
    session.headers.update({"User-Agent": random.choice(USER_AGENTS)})


def fetch(session, url, retries=3):
    for attempt in range(retries):
        try:
            rotate_ua(session)
            resp = session.get(url, timeout=20)
            if resp.status_code == 200:
                return resp
            if resp.status_code == 429:
                wait = 45 + random.randint(0, 30)
                print(f"  Rate limited! Asteptam {wait}s...")
                time.sleep(wait)
        except requests.RequestException as e:
            print(f"  Eroare retea (attempt {attempt+1}): {e}")
            time.sleep(2 ** attempt)
    return None


def extract_spec(soup, *labels):
    for label in labels:
        ll = label.lower()

        for dt in soup.find_all("dt"):
            if ll in dt.get_text(strip=True).lower():
                dd = dt.find_next_sibling("dd")
                if dd:
                    return dd.get_text(strip=True)

        for th in soup.find_all("th"):
            if ll in th.get_text(strip=True).lower():
                td = th.find_next_sibling("td")
                if td:
                    return td.get_text(strip=True)

        for el in soup.find_all(["span", "strong", "b", "label", "p"]):
            text = el.get_text(strip=True)
            if text.lower() == ll or text.lower().startswith(ll + ":"):
                sibling = el.find_next_sibling()
                if sibling:
                    return sibling.get_text(strip=True)
                if ":" in text:
                    return text.split(":", 1)[1].strip()

        # FIX: cauta si in div-uri cu clase de tip spec/detail
        for div in soup.find_all(["div", "li"], class_=re.compile(r"spec|detail|prop|feature|attr", re.I)):
            text = div.get_text(strip=True)
            if ll in text.lower() and ":" in text:
                parts = text.split(":", 1)
                if ll in parts[0].lower():
                    return parts[1].strip()

        match = re.search(
            rf"{re.escape(label)}\s*[:\-]\s*([^\n<]+)",
            soup.get_text(),
            re.IGNORECASE,
        )
        if match:
            return match.group(1).strip()

    return None


def parse_int(text):
    if not text:
        return None
    m = re.search(r"\d[\d,]*", text.replace(".", "").replace(",", ""))
    if not m:
        m = re.search(r"\d+", text)
    try:
        return int(m.group().replace(",", "")) if m else None
    except (ValueError, TypeError):
        return None


def parse_decimal(text):
    if not text:
        return None
    m = re.search(r"[\d.,]+", text)
    if not m:
        return None
    try:
        return Decimal(m.group().replace(",", "."))
    except InvalidOperation:
        return None


def get_urls(session, list_path, product_keyword):
    urls = []
    page = 1
    list_url = BASE_URL + list_path
    while True:
        url = f"{list_url}?page={page}" if page > 1 else list_url
        print(f"  Pagina {page}: {url}")
        resp = fetch(session, url)
        if not resp:
            break

        soup = BeautifulSoup(resp.text, "html.parser")
        found = 0
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if product_keyword in href:
                full = BASE_URL + href if href.startswith("/") else href
                if full not in urls:
                    urls.append(full)
                    found += 1

        print(f"    -> {found} gasite pe pagina {page}")
        if found == 0:
            break

        next_link = (
            soup.find("a", string=str(page + 1))
            or soup.find("a", href=re.compile(rf"page={page+1}"))
        )
        if not next_link:
            break

        page += 1
        random_delay()

    return urls


def get_name(soup, url):
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(strip=True)
    slug = url.rstrip("/").split("/")[-1]
    return slug.split("_", 1)[-1].replace("-", " ") if "_" in slug else slug


# ─────────────────────────── FIX 1: get_ean cu fallback la slug ──────────────
# PROBLEMA VECHE: regex cerea cifre in URL => motherboard + cooler aveau slug text
# => part_number = None => toate produsele sarite
# FIX: daca nu gasim cifre, folosim slug-ul URL ca identificator unic
def get_ean(url, keyword):
    m = re.search(rf"/{keyword}/(\d+)_", url)
    if m:
        return m.group(1)
    # Fallback: slug-ul complet e unic per produs
    slug = url.rstrip("/").split("/")[-1]
    return slug if slug else None


# ─────────────────────────── GPU ─────────────────────────────────────────────

GPU_SERIES = [
    "RTX 4090", "RTX 4080 Super", "RTX 4080", "RTX 4070 Ti Super",
    "RTX 4070 Ti", "RTX 4070 Super", "RTX 4070", "RTX 4060 Ti", "RTX 4060",
    "RTX 3090 Ti", "RTX 3090", "RTX 3080 Ti", "RTX 3080", "RTX 3070 Ti",
    "RTX 3070", "RTX 3060 Ti", "RTX 3060", "RTX 3050",
    "GTX 1660 Super", "GTX 1660 Ti", "GTX 1660", "GTX 1650",
    "RX 7900 XTX", "RX 7900 XT", "RX 7900 GRE", "RX 7800 XT", "RX 7700 XT",
    "RX 7600 XT", "RX 7600", "RX 6950 XT", "RX 6900 XT", "RX 6800 XT",
    "RX 6800", "RX 6700 XT", "RX 6700", "RX 6650 XT", "RX 6600 XT", "RX 6600",
    "Arc A770", "Arc A750", "Arc A580",
]


def detect_gpu_serie(name):
    for serie in GPU_SERIES:
        if serie.upper() in name.upper():
            return serie
    m = re.search(r"(RTX|GTX|RX|Arc)\s+[\w\s]+", name, re.IGNORECASE)
    return m.group().strip() if m else name.split()[0]


def scrape_gpu(session, url):
    resp = fetch(session, url)
    if not resp:
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    name = get_name(soup, url)
    ean  = get_ean(url, "gpu")

    mpn      = extract_spec(soup, "MPN", "Part Number")
    producer = extract_spec(soup, "Producer", "Brand", "Manufacturer")
    vram     = extract_spec(soup, "VRAM", "Video Memory", "Memory Size", "Memory")
    tdp      = extract_spec(soup, "TDP", "Power Consumption", "Power")
    length   = extract_spec(soup, "Length", "Card Length")
    width    = extract_spec(soup, "Width", "Card Width")
    height   = extract_spec(soup, "Height", "Slot Width", "Thickness")
    chipset  = extract_spec(soup, "GPU Chip", "Chipset", "Graphics Processor", "GPU")

    brand = producer or (
        "NVIDIA" if any(x in name.upper() for x in ["RTX", "GTX", "QUADRO", "TITAN"]) else
        "AMD"    if any(x in name.upper() for x in ["RX ", "RADEON"]) else
        "Intel"  if "ARC" in name.upper() else
        "Unknown"
    )

    return {
        "part_number":   mpn or ean,
        "nume":          name,
        "brand":         brand,
        "serie":         detect_gpu_serie(name),
        "model_chipset": chipset or detect_gpu_serie(name),
        "vram_gb":       parse_int(vram) or 0,
        "consum_tdp":    parse_int(tdp) or 0,
        "lungime_mm":    parse_int(length) or 0,
        "latime_mm":     parse_int(width) or 0,
        "inaltime_mm":   parse_int(height) or 0,
        "pret":          None,
        "magazin":       None,
        "url_produs":    None,
        "stoc":          True,
        "regiune":       "Romania",
    }


# ─────────────────────────── MOTHERBOARD ─────────────────────────────────────
PORT_MAP = [
    (r"usb\s*2\.0",               "USB2"),
    (r"usb\s*3\.2\s*gen\s*2x2",  "USB3_Gen2x2"),
    (r"usb\s*3\.2\s*gen\s*2",    "USB3_Gen2"),
    (r"usb\s*3\.2\s*gen\s*1",    "USB3_Gen1"),
    (r"usb\s*3\.0",               "USB3_Gen1"),
    (r"usb\s*3\.1\s*gen\s*2",    "USB3_Gen2"),
    (r"usb\s*3\.1\s*gen\s*1",    "USB3_Gen1"),
    (r"usb\s*type.?c|usb-c",     "USB_C"),
    (r"thunderbolt\s*4",          "Thunderbolt4"),
    (r"thunderbolt\s*3",          "Thunderbolt3"),
    (r"thunderbolt",              "Thunderbolt"),
    (r"displayport|dp\b",         "DisplayPort"),
    (r"hdmi",                     "HDMI"),
    (r"vga|d-sub",                "VGA"),
    (r"dvi",                      "DVI"),
    (r"rj.?45|2\.5gbe|2\.5g\s*lan|10gbe|10g\s*lan|ethernet|lan", "LAN"),
    (r"optical\s*audio|s/pdif|spdif", "Optical_Audio"),
    (r"audio\s*jack|3\.5mm|audio|headphone", "Audio_jacks"),
    (r"ps/?2",                    "PS2"),
    (r"com\s*port|\bcom\b",       "COM"),
]
 
 
def parse_porturi_io(soup):
    ports = {}
    page_text = soup.get_text("\n")
 
    for line in page_text.splitlines():
        line = line.strip()
        if not line or len(line) > 200:
            continue
 
        for pattern, key in PORT_MAP:
            if not re.search(pattern, line, re.IGNORECASE):
                continue
 
            num_match = re.search(
                r"(\d+)\s*[xX×]\s*" + pattern
                + r"|" + pattern + r"\s*[xX×]\s*(\d+)"
                + r"|" + pattern + r"\s*[:\-\(]\s*(\d+)"
                + r"|^(\d+)\s",
                line,
                re.IGNORECASE,
            )
 
            if num_match:
                val = next((int(g) for g in num_match.groups() if g is not None), None)
                if val and 0 < val <= 20:
                    ports[key] = max(ports.get(key, 0), val)
            else:
                if key not in ports:
                    ports[key] = 1
            break
 
    for dt in soup.find_all("dt"):
        label = dt.get_text(strip=True)
        for pattern, key in PORT_MAP:
            if re.search(pattern, label, re.IGNORECASE):
                dd = dt.find_next_sibling("dd")
                if dd:
                    val = parse_int(dd.get_text(strip=True))
                    if val and 0 < val <= 20:
                        ports[key] = val
                break
 
    return ports
 
 
def normalize_form_factor(text):
    t = (text or "").upper()
    if "MINI-ITX" in t or "M-ITX" in t or "MINI ITX" in t:
        return "Mini-ITX"
    if "MICRO-ATX" in t or "MATX" in t or "M-ATX" in t or "MICRO ATX" in t or "UATX" in t:
        return "Micro-ATX"
    if "E-ATX" in t or "EATX" in t or "EXTENDED ATX" in t:
        return "E-ATX"
    if "ATX" in t:
        return "ATX"
    return text or ""
 
 
def normalize_memory_type(text, fallback_name=""):
    t = (text or fallback_name).upper()
    if "DDR5" in t:
        return "DDR5"
    if "DDR4" in t:
        return "DDR4"
    if "DDR3" in t:
        return "DDR3"
    return text or ""
 
 
def extract_icon_bool(soup, dt_label):
    """
    Pe pc-kombo, campurile boolean (Wifi, Bluetooth) nu sunt text ci iconite:
      <dt>Wifi</dt><dd><i class="icon icon-check" title="Wifi"></i></dd>  -> True
      <dt>Wifi</dt><dd><i class="icon icon-stop"  title="None"></i></dd>  -> False
    """
    ll = dt_label.lower()
    for dt in soup.find_all("dt"):
        if ll in dt.get_text(strip=True).lower():
            dd = dt.find_next_sibling("dd")
            if dd:
                icon = dd.find("i")
                if icon:
                    return "icon-check" in icon.get("class", [])
                text = dd.get_text(strip=True).lower()
                return text in ("yes", "true", "1", "da")
    return False
 
 
def parse_porturi_io_mb(soup):
    """
    Varianta specializata pentru pc-kombo.
    Toate porturile sunt in <dt>/<dd> cu valori numerice directe.
    Ex: <dt>USB 3 Slots</dt><dd>7</dd>
        <dt>Display Port</dt><dd>1</dd>
    Ignora campuri goale sau cu valoarea 0.
    """
    ports = {}
 
    PORT_LABEL_MAP = [
        ("usb 3 slots",     "USB3_Slots"),
        ("usb 3 headers",   "USB3_Headers"),
        ("usb 3 type-c",    "USB3_TypeC"),
        ("usb 2",           "USB2"),
        ("display port",    "DisplayPort"),
        ("hdmi",            "HDMI"),
        ("vga",             "VGA"),
        ("dvi",             "DVI"),
        ("thunderbolt",     "Thunderbolt"),
        ("sata",            "SATA"),
        ("m.2 (pci-e 5.0)", "M2_PCIe5"),
        ("m.2 (pci-e 4.0)", "M2_PCIe4"),
        ("m.2 (pci-e 3.0)", "M2_PCIe3"),
        ("pci-e 5.0 x16",   "PCIe5_x16"),
        ("pci-e 4.0 x16",   "PCIe4_x16"),
        ("pci-e 4.0 x1",    "PCIe4_x1"),
        ("pci-e 3.0 x16",   "PCIe3_x16"),
        ("pci-e 3.0 x1",    "PCIe3_x1"),
    ]
 
    for dt in soup.find_all("dt"):
        dt_text = dt.get_text(strip=True).lower()
        for label, key in PORT_LABEL_MAP:
            if label in dt_text:
                dd = dt.find_next_sibling("dd")
                if dd:
                    try:
                        val = int(dd.get_text(strip=True))
                        if val > 0:
                            ports[key] = val
                    except (ValueError, TypeError):
                        pass
                break
 
    return ports
 
 
def scrape_motherboard(session, url):
    resp = fetch(session, url)
    if not resp:
        return None
 
    soup = BeautifulSoup(resp.text, "html.parser")
    name = get_name(soup, url)
    ean  = get_ean(url, "motherboard")
 
    mpn      = extract_spec(soup, "MPN", "Part Number")
    producer = extract_spec(soup, "Producer", "Brand", "Manufacturer")
    socket   = extract_spec(soup, "Socket", "CPU Socket")
    chipset  = extract_spec(soup, "Chipset", "Northbridge", "PCH")
    form     = extract_spec(soup, "Form Factor", "Format", "Motherboard Size")
    memory   = extract_spec(soup, "Memory Type", "RAM Type", "Memory Standard")
 
    # Campuri noi cu labelele corecte de pe pc-kombo
    max_ram_gb = extract_spec(soup, "Memory Capacity", "Max Memory", "Maximum Memory")
    ram_slots  = extract_spec(soup, "Ramslots", "RAM Slots", "Memory Slots", "DIMM Slots")
 
    # Wifi/BT: pe pc-kombo sunt iconite icon-check/icon-stop, nu text
    are_wifi = extract_icon_bool(soup, "Wifi")
    are_bt   = extract_icon_bool(soup, "Bluetooth")
    # Fallback text pentru cazuri rare
    if not are_wifi:
        are_wifi = bool(re.search(r"\bwi.?fi\b|\bwlan\b|\b802\.11\b", soup.get_text().lower()))
    if not are_bt:
        are_bt = bool(re.search(r"\bbluetooth\b", soup.get_text().lower()))
 
    brand = producer or (
        "ASUS"     if "asus" in name.lower() else
        "MSI"      if "msi" in name.lower() else
        "Gigabyte" if "gigabyte" in name.lower() or "aorus" in name.lower() else
        "ASRock"   if "asrock" in name.lower() else
        "EVGA"     if "evga" in name.lower() else
        "Unknown"
    )
 
    return {
        "part_number":           mpn or ean,
        "nume":                  name,
        "brand":                 brand,
        "socket":                socket or "",
        "chipset":               chipset or "",
        "format":                normalize_form_factor(form),
        "tip_memorie":           normalize_memory_type(memory, name),
        "capacitate_max_ram_gb": parse_int(max_ram_gb) or 0,
        "numar_sloturi_ram":     parse_int(ram_slots) or 0,
        "are_wifi":              are_wifi,
        "are_bluetooth":         are_bt,
        "porturi_io":            parse_porturi_io_mb(soup),
        "pret":                  None,
        "magazin":               None,
        "url_produs":            None,
        "stoc":                  True,
        "regiune":               "Romania",
    }
 
# ─────────────────────────── RAM ─────────────────────────────────────────────

def scrape_ram(session, url):
    resp = fetch(session, url)
    if not resp:
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    name = get_name(soup, url)
    ean  = get_ean(url, "ram")

    mpn      = extract_spec(soup, "MPN", "Part Number")
    producer = extract_spec(soup, "Producer", "Brand", "Manufacturer")
    capacity = extract_spec(soup, "Size", "Capacity", "Total Capacity", "Memory Size", "Kit Size")
    modules  = extract_spec(soup, "Sticks", "Number of Modules", "Modules", "Kit")
    tip      = extract_spec(soup, "Ram Type", "Memory Type", "Type", "Standard")
    freq     = extract_spec(soup, "Clock", "Frequency", "Speed", "Data Rate", "MHz")
    cl_raw   = extract_spec(soup, "Timings", "CAS Latency", "CL", "Latency")
    height   = extract_spec(soup, "Height", "Module Height", "Heatspreader Height")

    brand = producer or (
        "Corsair"   if "corsair" in name.lower() else
        "G.Skill"   if "g.skill" in name.lower() or "gskill" in name.lower() else
        "Kingston"  if "kingston" in name.lower() or "fury" in name.lower() else
        "Crucial"   if "crucial" in name.lower() else
        "TeamGroup" if "team" in name.lower() else
        "Unknown"
    )

    # ── FIX 5a: capacitate totala si pe modul ────────────────────────────────
    # PROBLEMA VECHE: parse_int("2x16GB") nu returna nimic util pentru capacitate_modul_gb
    # FIX: calculam explicit capacitate_modul si capacitate_totala din acelasi string
    cap_total = None
    cap_modul = None

    kit_match = re.search(r"(\d+)\s*[xX×]\s*(\d+)\s*(?:GB|gb)", capacity or "")
    if kit_match:
        num_mod  = int(kit_match.group(1))
        cap_mod  = int(kit_match.group(2))
        cap_total = num_mod * cap_mod
        cap_modul = cap_mod
    else:
        # format simplu "32GB" sau "32 GB"
        gb_match = re.search(r"(\d+)\s*(?:GB|gb)", capacity or "")
        if gb_match:
            cap_total = int(gb_match.group(1))

    # numar module
    num_modules = parse_int(modules)
    if not num_modules:
        km = re.search(r"(\d+)\s*[xX×]", capacity or "")
        num_modules = int(km.group(1)) if km else 2

    # capacitate pe modul daca nu am detectat-o deja
    if not cap_modul and cap_total and num_modules:
        cap_modul = cap_total // num_modules

    # ── FIX 5b: frecventa si latenta ─────────────────────────────────────────
    # PROBLEMA VECHE: parse_int() lua primul numar din orice string, deci
    # din "CL40" extrăgea 40 dar il punea si la frecventa, si invers
    # FIX: parsam frecventa DOAR din campul de frecventa, CL DOAR din campul CL

    freq_val = None
    if freq:
        # "DDR5-6000", "6000 MHz", "PC5-48000", "6000"
        m = re.search(r"DDR\d?[45]?-(\d{3,5})", freq, re.IGNORECASE)
        if m:
            freq_val = int(m.group(1))
        else:
            # extrage numarul care arata a frecventa (>= 800 MHz)
            nums = re.findall(r"\d+", freq)
            for n in nums:
                if int(n) >= 800:
                    freq_val = int(n)
                    break

    if not freq_val:
        # fallback: cauta in numele produsului (ex: "Trident Z5 DDR5-6000")
        m = re.search(r"DDR\d?[45]?-(\d{3,5})", name, re.IGNORECASE)
        if m:
            freq_val = int(m.group(1))
        else:
            # ultima resursa: orice numar >= 800 din nume
            nums = re.findall(r"\b(\d{4,5})\b", name)
            for n in nums:
                if int(n) >= 800:
                    freq_val = int(n)
                    break

    freq_val = freq_val or 0

    # CL - extragem DOAR primul numar din campul CAS Latency
    # "CL40", "40", "40-40-40-76" => 40
    cl_val = 0
    if cl_raw:
        m = re.search(r"\d+", cl_raw)
        cl_val = int(m.group()) if m else 0

    h = float(parse_decimal(height) or 0)

    return {
        "part_number":          mpn or ean,
        "nume":                 name,
        "brand":                brand,
        "capacitate_totala_gb": cap_total or 0,
        "capacitate_modul_gb":  cap_modul or 0,   # FIX: camp nou
        "numar_module":         num_modules,
        "tip_memorie":          normalize_memory_type(tip, name),
        "frecventa_mhz":        freq_val,          # FIX: nu mai confunda cu CL
        "latenta_cl":           cl_val,            # FIX: acum e corect
        "inaltime_mm":          h if h > 0 else None,
        "pret":                 None,
        "magazin":              None,
        "url_produs":           None,
        "stoc":                 True,
        "regiune":              "Romania",
    }


# ─────────────────────────── PSU ─────────────────────────────────────────────
def scrape_psu(session, url):
    resp = fetch(session, url)
    if not resp:
        return None
 
    soup = BeautifulSoup(resp.text, "html.parser")
    name = get_name(soup, url)
    ean  = get_ean(url, "psu")
 
    mpn      = extract_spec(soup, "MPN", "Part Number")
    producer = extract_spec(soup, "Producer", "Brand", "Manufacturer")
 
    # Label corect pe pc-kombo: "Watt" (nu "Wattage", "Power", etc.)
    power = extract_spec(soup, "Watt", "Wattage", "Power Output", "Watts")
 
    # Fallback: cauta pattern "850W" sau "850 Watt" direct in text
    if not power:
        m = re.search(r"(\d{2,4})\s*(?:W\b|Watt|watt)", soup.get_text())
        if m:
            power = m.group(0)
 
    # Label corect pe pc-kombo: "Efficiency Rating" -> "80 PLUS Platinum"
    # Valoarea e deja text complet in <dd>, nu mai avem nevoie de regex complex
    cert = extract_spec(soup, "Efficiency Rating", "80 Plus", "Certification", "Efficiency")
 
    # "Size" pe pc-kombo = formatul sursei (ATX/SFX), nu lungimea in mm
    # Lungimea fizica nu e disponibila pe acest site, folosim default
    modular = extract_spec(soup, "Modularity", "Modular", "Cable Management")
    length  = extract_spec(soup, "Depth", "Length", "Dimension")
 
    brand = producer or "Unknown"
 
    # Modular: nu exista camp dedicat pe pc-kombo
    # -> detectam din numele produsului care contine "modular" / "semi-modular"
    mod_text = (modular or name).lower()
    if "full modular" in mod_text or "full-modular" in mod_text:
        este_modulara = "Full"
    elif "semi modular" in mod_text or "semi-modular" in mod_text:
        este_modulara = "Semi"
    elif "modular" in mod_text:
        este_modulara = "Full"
    else:
        este_modulara = "Non"
 
    # Certificarea vine deja ca text complet din <dd>: "80 PLUS Platinum"
    # Normalizam doar formatul pentru consistenta
    cert_out = (cert or "").strip()
    if not cert_out:
        # Fallback: cauta in toata pagina
        m = re.search(
            r"80[\s\+]*PLUS[\s\+]*(TITANIUM|PLATINUM|GOLD|SILVER|BRONZE|WHITE)?",
            soup.get_text(), re.IGNORECASE
        )
        if m:
            nivel = m.group(1)
            cert_out = f"80 PLUS {nivel.capitalize()}" if nivel else "80 PLUS"
 
    # Formatul sursei (ATX/SFX) din campul "Size"
    form_psu = extract_spec(soup, "Size", "Form Factor", "Format") or "ATX"
 
    return {
        "part_number":   mpn or ean,
        "nume":          name,
        "brand":         brand,
        "putere_w":      parse_int(power) or 0,
        "certificare":   cert_out,
        "este_modulara": este_modulara,
        "format":        form_psu,
        "lungime_mm":    parse_int(length) or 150,
        "pret":          None,
        "magazin":       None,
        "url_produs":    None,
        "stoc":          True,
        "regiune":       "Romania",
    }
 
# ─────────────────────────── CASE ────────────────────────────────────────────

FORM_FACTORS_CASE = ["E-ATX", "ATX", "Micro-ATX", "Mini-ITX", "XL-ATX", "SSI EEB"]


def detect_tip_carcasa(name, soup):
    text = (name + " " + soup.get_text()[:600]).upper()
    if re.search(r"FULL.?TOWER", text):
        return "FULL"
    if re.search(r"MINI.?TOWER|MINI.?ITX CASE", text):
        return "MINI"
    if re.search(r"\bSFF\b|SMALL FORM FACTOR", text):
        return "SFF"
    if re.search(r"AQUARIUM", text):
        return "AQ"
    return "MID"


def parse_formate_suportate(soup):
    text = soup.get_text()
    found = []
    for ff in FORM_FACTORS_CASE:
        if re.search(rf"\b{re.escape(ff)}\b", text, re.IGNORECASE):
            found.append(ff)
    return found or ["ATX"]


def parse_radiator_support(soup):
    """
    Extrage dimensiunile de radiatoare suportate din sectiunea Cooling.
    Ex: <dt>240mm Radiator Support</dt><dd>1</dd> -> [240]
    """
    radiator_support = []
    for size in [120, 140, 240, 280, 360]:
        for dt in soup.find_all("dt"):
            if f"{size}mm radiator" in dt.get_text(strip=True).lower():
                dd = dt.find_next_sibling("dd")
                if dd:
                    try:
                        if int(dd.get_text(strip=True)) > 0:
                            radiator_support.append(size)
                    except (ValueError, TypeError):
                        pass
                break
    return radiator_support


def scrape_case(session, url):
    resp = fetch(session, url)
    if not resp:
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    name = get_name(soup, url)
    ean  = get_ean(url, "case")

    mpn      = extract_spec(soup, "MPN", "Part Number")
    producer = extract_spec(soup, "Producer", "Brand", "Manufacturer")
    height   = extract_spec(soup, "Height")
    length   = extract_spec(soup, "Length", "Depth")
    width    = extract_spec(soup, "Width")
    psu_inc  = extract_spec(soup, "Included PSU", "Power Supply Included", "Bundled PSU", "PSU Included")
    psu_pos  = extract_spec(soup, "PSU Position", "Power Supply Position", "PSU Location")

    # FIX: label-uri reale de pe pc-kombo adaugate primul
    max_gpu_length = extract_spec(
        soup,
        "Supported GPU length",         # ← label real din HTML
        "Max GPU Length", "Maximum GPU Length", "GPU Clearance",
        "Graphics Card Length", "Max Graphics Card Length",
        "Maximum Graphics Card", "GPU Length",
    )
    if not max_gpu_length:
        m = re.search(
            r"(?:supported\s*gpu\s*length|gpu|graphics\s*card|video\s*card)[^\n]{0,30}?(\d{2,3})\s*mm",
            soup.get_text(),
            re.IGNORECASE,
        )
        if m:
            max_gpu_length = m.group(1) + "mm"

    
    max_cooler_height = extract_spec(
        soup,
        "Supported CPU cooler height",  
        "Max Cooler Height", "Maximum Cooler Height", "CPU Cooler Clearance",
        "CPU Cooler Height", "Max CPU Cooler Height", "Cooler Height",
    )
    if not max_cooler_height:
        m = re.search(
            r"(?:supported\s*cpu\s*cooler\s*height|(?:cpu\s*)?cooler)[^\n]{0,30}?(\d{2,3})\s*mm",
            soup.get_text(),
            re.IGNORECASE,
        )
        if m:
            max_cooler_height = m.group(1) + "mm"

    brand = producer or "Unknown"
    include_sursa = bool(psu_inc and re.search(r"yes|includ|bundled", (psu_inc or "").lower()))

    return {
        
        "part_number":              mpn or ean,
        "nume":                     name,
        "brand":                    brand,
        "tip_carcasa":              detect_tip_carcasa(name, soup),
        "formate_suportate":        parse_formate_suportate(soup),
        "include_sursa":            include_sursa,
        "pozitie_sursa":            psu_pos or "Jos Spate",
        "inaltime_mm":              parse_int(height) or 0,
        "lungime_mm":               parse_int(length) or 0,
        "latime_mm":                parse_int(width) or 0,
        "lungime_max_gpu_mm":       parse_int(max_gpu_length) or 0,    
        "inaltime_max_cooler_mm":   parse_int(max_cooler_height) or 0, 
        "suport_radiator_mm":       parse_radiator_support(soup), 
        "pret":                     None,
        "magazin":                  None,
        "url_produs":               None,
        "stoc":                     True,
        "regiune":                  "Romania",
    }
# ─────────────────────────── COOLER ──────────────────────────────────────────

# ─────────────────────────── COOLER ──────────────────────────────────────────

ALL_SOCKETS = [
    "AM5", "AM4", "AM3+", "AM3", "AM2+", "AM2",
    "LGA1851", "LGA1700", "LGA1200", "LGA1151", "LGA1150", "LGA1155",
    "LGA1156", "LGA2011-3", "LGA2011", "LGA2066",
    "TR4", "sTRX4", "sWRX8", "SP3",
]


def detect_tip_racire(name, soup):
    text = (name + " " + soup.get_text()[:400]).lower()
    if re.search(r"\b(360|280|240|120)\s*mm\b|\baio\b|\ball.in.one\b|\bliquid cool|\bwater cool", text):
        m = re.search(r"(360|280|240|120)\s*mm", text)
        size = m.group(1) if m else "240"
        return f"AIO {size}mm"
    return "Air"


def parse_socket_string(raw):
    """
    Parseaza string de forma "Intel LGA1851,1700,AM4,AM5"
    si returneaza ["LGA1851", "LGA1700", "AM4", "AM5"]
    """
    found = []
    tokens = re.split(r"[,\s]+", raw.strip())

    current_prefix = None
    for token in tokens:
        token = token.strip()
        if not token:
            continue

        # Token e prefix de brand
        if token.lower() in ("intel", "amd", "tr"):
            current_prefix = token.upper()
            continue

        # Token e socket complet cunoscut (AM4, AM5, LGA1700 etc.)
        normalized = token.upper()
        if normalized in [s.upper() for s in ALL_SOCKETS]:
            for s in ALL_SOCKETS:
                if s.upper() == normalized:
                    if s not in found:
                        found.append(s)
                    break
            current_prefix = None
            continue

        # Token e doar un numar dupa prefix Intel => LGA
        if re.match(r"^\d+(-\d+)?$", token) and current_prefix == "INTEL":
            socket_name = f"LGA{token}"
            if socket_name in ALL_SOCKETS and socket_name not in found:
                found.append(socket_name)
            continue

        # Fallback: potrivire partiala
        for s in ALL_SOCKETS:
            if token.upper() in s.upper() or s.upper() in token.upper():
                if s not in found:
                    found.append(s)
                break

    return found


def parse_sockets_cooler(soup):
    """
    Pe pc-kombo socketurile sunt pe o singura linie:
    <dt>Supported Sockets</dt>
    <dd>Intel LGA1851,1700,AM4,AM5</dd>
    """
    for dt in soup.find_all("dt"):
        if "supported socket" in dt.get_text(strip=True).lower():
            dd = dt.find_next_sibling("dd")
            if dd:
                return parse_socket_string(dd.get_text(strip=True))

    # Fallback: cautare in tot textul paginii
    text = soup.get_text()
    found = []
    for sock in ALL_SOCKETS:
        if re.search(rf"\b{re.escape(sock)}\b", text, re.IGNORECASE):
            if sock not in found:
                found.append(sock)
    return found


def scrape_cooler(session, url):
    resp = fetch(session, url)
    if not resp:
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    name = get_name(soup, url)
    ean  = get_ean(url, "cooler")

    mpn      = extract_spec(soup, "MPN", "Part Number")
    producer = extract_spec(soup, "Producer", "Brand", "Manufacturer")
    height   = extract_spec(soup, "Height", "Cooler Height", "Total Height", "CPU Cooler Height")
    rad      = extract_spec(soup, "Radiator Size", "Radiator Length", "Radiator")

    brand = producer or "Unknown"
    tip   = detect_tip_racire(name, soup)

    return {
        "part_number":         mpn or ean,
        "nume":                name,
        "brand":               brand,
        "tip_racire":          tip,
        "socket_suportate":    parse_sockets_cooler(soup),
        "inaltime_mm":         parse_int(height) if "Air" in tip else None,
        "lungime_radiator_mm": parse_int(rad)    if "AIO" in tip else None,
        "pret":                None,
        "magazin":             None,
        "url_produs":          None,
        "stoc":                True,
        "regiune":             "Romania",
    }
# ─────────────────────────── STORAGE ─────────────────────────────────────────

def detect_storage_tip(name, soup):
    text = (name + " " + soup.get_text()[:300]).lower()
    if re.search(r"\bnvme\b|m\.2.*pcie|pcie.*m\.2", text):
        return "NVME"
    if re.search(r"\bssd\b", text):
        return "SSD"
    return "HDD"


def detect_storage_format(name, soup):
    text = (name + " " + soup.get_text()[:300]).lower()
    if re.search(r"\bm\.2\b", text):
        return "M.2"
    if re.search(r'2\.5\s*["\']|2\.5\s*inch|2\.5"', text):
        return '2.5"'
    if re.search(r'3\.5\s*["\']|3\.5\s*inch|3\.5"', text):
        return '3.5"'
    return ""


def scrape_storage(session, url):
    resp = fetch(session, url)
    if not resp:
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    name = get_name(soup, url)

    m = re.search(r"/(hdd|ssd|nvme)/(\d+)_", url)
    ean = m.group(2) if m else get_ean(url, "ssd") or get_ean(url, "hdd")

    mpn       = extract_spec(soup, "MPN", "Part Number")
    producer  = extract_spec(soup, "Producer", "Brand", "Manufacturer")
    capacity  = extract_spec(soup, "Size", "Capacity", "Storage Capacity", "Total Capacity")
    interface = extract_spec(soup, "Protocol", "Interface", "Connection")
    read_spd  = extract_spec(soup, "Read Speed", "Sequential Read", "Max Read", "Read")
    write_spd = extract_spec(soup, "Write Speed", "Sequential Write", "Max Write", "Write")

    brand = producer or (
        "Samsung"  if "samsung" in name.lower() else
        "WD"       if re.search(r"\bwd\b|western digital", name.lower()) else
        "Seagate"  if "seagate" in name.lower() else
        "Crucial"  if "crucial" in name.lower() else
        "Kingston" if "kingston" in name.lower() else
        "Unknown"
    )

    cap_val = None
    if capacity:
        tb = re.search(r"([\d.]+)\s*TB", capacity, re.IGNORECASE)
        gb = re.search(r"([\d.]+)\s*GB", capacity, re.IGNORECASE)
        if tb:
            cap_val = int(float(tb.group(1)) * 1000)
        elif gb:
            cap_val = int(float(gb.group(1)))

    return {
        "part_number":         mpn or ean,
        "nume":                name,
        "brand":               brand,
        "tip":                 detect_storage_tip(name, soup),
        "capacitate_gb":       cap_val or 0,
        "interfata":           interface or "",
        "viteza_citire_mb_s":  parse_int(read_spd),
        "viteza_scriere_mb_s": parse_int(write_spd),
        "format":              detect_storage_format(name, soup),
        "pret":                None,
        "magazin":             None,
        "url_produs":          None,
        "stoc":                True,
        "regiune":             "Romania",
    }


# ─────────────────────────── IMPORTER GENERIC ────────────────────────────────

def run_import(stdout, session, model_class, list_path, product_keyword, scrape_fn):
    label = f"{model_class.__name__} ({list_path.split('/')[-1]})"
    stdout.write(f"\n{'='*60}")
    stdout.write(f"Importam: {label}")
    stdout.write("=" * 60)

    stdout.write(f"\n[1] Colectam URL-uri...")
    urls = get_urls(session, list_path, product_keyword)
    stdout.write(f"Total gasite: {len(urls)}\n")

    if not urls:
        stdout.write("Nu s-au gasit produse. Sarim.\n")
        return {"salvat": 0, "actualizat": 0, "sarit": 0, "eroare": 0}

    stdout.write("[2] Scrapam si salvam in DB...\n")
    stats = {"salvat": 0, "actualizat": 0, "sarit": 0, "eroare": 0}

    for i, url in enumerate(urls, 1):
        stdout.write(f"[{i:>4}/{len(urls)}] {url.split('/')[-1][:60]}")
        try:
            data = scrape_fn(session, url)

            if not data:
                stdout.write("         -> EROARE fetch")
                stats["eroare"] += 1
                continue

            part_number = data.pop("part_number", None)
            if not part_number:
                stdout.write("         -> SARIT (fara part_number/EAN)")
                stats["sarit"] += 1
                continue

            _, created = model_class.objects.update_or_create(
                part_number=part_number,
                defaults=data,
            )
            action = "NOU" if created else "ACTUALIZAT"
            stdout.write(f"         -> {action}: {data['nume']}")
            stats["salvat" if created else "actualizat"] += 1

        except Exception as e:
            stdout.write(f"         -> EXCEPTIE: {e}")
            stats["eroare"] += 1

        random_delay()

    return stats


# ─────────────────────────── COMMAND ─────────────────────────────────────────

class Command(BaseCommand):
    help = "Scrapeaza GPU/Motherboard/RAM/PSU/Case/Cooler/Storage de pe pc-kombo.com"

    COMPONENTS = [
        (GPU,         "/us/components/gpus",          "/us/product/gpu/",          scrape_gpu),
        (Motherboard, "/us/components/motherboards",  "/us/product/motherboard/",  scrape_motherboard),
        (RAM,         "/us/components/rams",          "/us/product/ram/",          scrape_ram),
        (PSU,         "/us/components/psus",          "/us/product/psu/",          scrape_psu),
        (Case,        "/us/components/cases",         "/us/product/case/",         scrape_case),
        (Cooler,      "/us/components/coolers",       "/us/product/cooler/",       scrape_cooler),
        (Storage,     "/us/components/hdds",          "/us/product/hdd/",          scrape_storage),
        (Storage,     "/us/components/ssds",          "/us/product/ssd/",          scrape_storage),
    ]

    def handle(self, *args, **options):
        session = get_session()
        all_stats = {}

        self.stdout.write("=" * 60)
        self.stdout.write("Scraper ALL - pc-kombo.com")
        self.stdout.write("=" * 60)

        for idx, (model_class, list_path, keyword, scrape_fn) in enumerate(self.COMPONENTS):
            if idx > 0:
                wait = random.randint(10, 18)
                self.stdout.write(f"\nPauza {wait}s intre componente...")
                time.sleep(wait)

            stats = run_import(
                self.stdout, session,
                model_class, list_path, keyword, scrape_fn,
            )
            key = f"{model_class.__name__} ({list_path.split('/')[-1]})"
            all_stats[key] = stats

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("RAPORT FINAL")
        self.stdout.write("=" * 60)
        for comp, s in all_stats.items():
            self.stdout.write(
                f"{comp:45s} | Noi: {s['salvat']:4d} | "
                f"Act: {s['actualizat']:4d} | "
                f"Sarite: {s['sarit']:4d} | "
                f"Erori: {s['eroare']:4d}"
            )
        self.stdout.write("=" * 60)
