import sqlite3
import os
import sys
import django
import re

# ==========================================
# 1. CONECTARE LA DJANGO
# ==========================================
cale_curenta = os.path.dirname(os.path.abspath(__file__))
sys.path.append(cale_curenta)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings") 
django.setup()

from components.models import CPU, GPU, Motherboard, RAM, PSU, Case, Storage, Cooler

# ==========================================
# 2. CONECTARE LA BAZA TAMPON
# ==========================================
cale_tampon = os.path.join(cale_curenta, 'tampon.db')

if not os.path.exists(cale_tampon):
    print("❌ Nu găsesc tampon.db! Asigură-te că l-ai pus în folderul backend-django.")
    sys.exit()

conn = sqlite3.connect(cale_tampon)
cursor = conn.cursor()

# Funcții de protecție
def float_sigur(valoare):
    try: return float(valoare)
    except: return 0.0

def int_sigur(valoare):
    try: return int(valoare)
    except: return 0

def extrage_numar(text):
    if not text: return 0
    match = re.search(r"[\d.]+", str(text))
    return float(match.group()) if match else 0

# ==========================================
# 3. FUNCȚII DE DETECTIV (SMART PARSING)
# ==========================================
def deduce_cpu_avansat(nume):
    nume_upper = str(nume).upper()
    brand, serie = "Necunoscut", "Necunoscut"
    
    match_intel = re.search(r"(I[3579])-?(\d{1,2})\d{3}([A-Z]*)", nume_upper)
    if match_intel:
        brand = "Intel"
        serie = f"Core {match_intel.group(1).lower()} {match_intel.group(2)}th Gen"
        
    match_amd = re.search(r"RYZEN\s*([3579])\s*(\d)\d{3}([A-Z0-9]*)", nume_upper)
    if match_amd:
        brand = "AMD"
        serie = f"Ryzen {match_amd.group(1)} {match_amd.group(2)}000 Series"
        
    if brand == "Necunoscut":
        if "AMD" in nume_upper: brand = "AMD"
        elif "INTEL" in nume_upper: brand = "Intel"
    return brand, serie

def deduce_gpu_avansat(nume):
    match = re.search(r"(RTX|GTX|RX)\s*(\d{3,4})\s*(TI\s*SUPER|TI|SUPER|XTX|XT)?", nume, re.IGNORECASE)
    brand, serie, chipset = "Necunoscut", "Necunoscut", "Necunoscut"
    
    if match:
        prefix = match.group(1).upper()
        numar = match.group(2)
        sufix = match.group(3).upper() if match.group(3) else ""
        if sufix == "TI": sufix = "Ti"
        elif "TI SUPER" in sufix: sufix = "Ti SUPER"
        
        chipset = f"{prefix} {numar} {sufix}".strip()
        if prefix in ["RTX", "GTX"]:
            brand, serie = "NVIDIA", f"{prefix} {numar[:2]}00 Series"
        elif prefix == "RX":
            brand, serie = "AMD", f"Radeon RX {numar[:1]}000 Series"
    else:
        if "RADEON" in nume.upper(): brand = "AMD"
        elif "NVIDIA" in nume.upper() or "GEFORCE" in nume.upper(): brand = "NVIDIA"
    return brand, serie, chipset

def deduce_psu_avansat(nume, certificare_raw):
    text_combinat = f"{nume} {certificare_raw}".upper()
    if "TITANIUM" in text_combinat: return "80+ Titanium"
    if "PLATINUM" in text_combinat: return "80+ Platinum"
    if "GOLD" in text_combinat: return "80+ Gold"
    if "SILVER" in text_combinat: return "80+ Silver"
    if "BRONZE" in text_combinat: return "80+ Bronze"
    if "80+" in text_combinat or "80 PLUS" in text_combinat: return "80+ Standard"
    return "Neclasificat"

def deduce_mb_avansat(nume):
    nume_upper = str(nume).upper()
    chipset, tip_memorie = "Necunoscut", "DDR5"
    
    match_chipset = re.search(r"(A620|B650|X670|B550|A520|X570|H610|B660|B760|Z690|Z790|Z890|X870)", nume_upper)
    if match_chipset: chipset = match_chipset.group(1)
        
    if "DDR4" in nume_upper or " D4" in nume_upper: tip_memorie = "DDR4"
    elif "DDR5" in nume_upper or " D5" in nume_upper: tip_memorie = "DDR5"
    else:
        if chipset in ["B550", "X570", "A520", "H610"]: tip_memorie = "DDR4"
        elif chipset in ["X670", "B650", "A620", "Z890", "X870"]: tip_memorie = "DDR5"
    return chipset, tip_memorie

def deduce_storage_avansat(nume):
    nume_upper = str(nume).upper()
    tip, interfata = "SSD", "PCIe 3.0"
    
    if "HDD" in nume_upper or "HARD DRIVE" in nume_upper:
        tip, interfata = "HDD", "SATA III"
    elif "M.2" in nume_upper or "NVME" in nume_upper:
        tip = "NVME"
        if "GEN4" in nume_upper or "GEN 4" in nume_upper or "4.0" in nume_upper: interfata = "PCIe 4.0 x4"
        elif "GEN5" in nume_upper or "GEN 5" in nume_upper or "5.0" in nume_upper: interfata = "PCIe 5.0 x4"
    elif "SATA" in nume_upper:
        interfata = "SATA III"
    return tip, interfata

def deduce_cooler_avansat(nume):
    nume_upper = str(nume).upper()
    tip_racire, lungime_rad = "Aer", 0
    
    if "LIQUID" in nume_upper or "AIO" in nume_upper or "WATER" in nume_upper:
        tip_racire = "Lichid (AIO)"
        match_rad = re.search(r"(120|140|240|280|360|420)", nume_upper)
        if match_rad: lungime_rad = int(match_rad.group(1))
    return tip_racire, lungime_rad

def deduce_case_avansat(nume):
    nume_upper = str(nume).upper()
    if "MINI" in nume_upper or "ITX" in nume_upper or "SFF" in nume_upper: return "MINI"
    if "FULL" in nume_upper: return "FULL"
    return "MID"

# ==========================================
# 4. MĂCELĂRIA DE DATE (MIGRAREA TOTALĂ)
# ==========================================
print("\n🚀 Începem transferul TOTAL și INTELIGENT din tampon.db în Django...\n")

# --- CPU ---
print("⏳ Transferăm Procesoarele (CPU)...")
cursor.execute("SELECT name, core_count, core_clock, tdp, price FROM CPU")
for rand in cursor.fetchall():
    nume = rand[0]
    if not nume: continue
    brand_dedus, serie_dedusa = deduce_cpu_avansat(nume)
    pret_mock = float_sigur(rand[4])
    CPU.objects.update_or_create(nume=nume, defaults={
        'brand': brand_dedus, 'serie': serie_dedusa, 'pret': pret_mock, 'stoc': pret_mock > 0, 
        'magazin': 'Mock Data', 'url_produs': '#', 'socket': 'Necunoscut',
        'nuclee': int_sigur(rand[1]), 'frecventa_ghz': float_sigur(rand[2]), 'consum_tdp': int_sigur(rand[3])
    })

# --- GPU ---
print("⏳ Transferăm Plăcile Video (GPU)...")
cursor.execute("SELECT name, memory, length, price FROM GPU")
for rand in cursor.fetchall():
    nume = rand[0]
    if not nume: continue
    brand_dedus, serie_dedusa, chipset_curat = deduce_gpu_avansat(nume)
    pret_mock = float_sigur(rand[3])
    GPU.objects.update_or_create(nume=nume, defaults={
        'brand': brand_dedus, 'serie': serie_dedusa, 'model_chipset': chipset_curat,
        'pret': pret_mock, 'stoc': pret_mock > 0, 'magazin': 'Mock Data', 'url_produs': '#',
        'vram_gb': int_sigur(rand[1]), 'lungime_mm': int_sigur(rand[2]), 'latime_mm': 0, 'inaltime_mm': 0, 'consum_tdp': 0
    })

# --- MOTHERBOARD ---
print("⏳ Transferăm Plăcile de Bază (MB)...")
cursor.execute("SELECT name, socket, form_factor, memory_slots, price FROM MOTHERBOARD")
for rand in cursor.fetchall():
    nume = rand[0]
    if not nume: continue
    pret_mock = float_sigur(rand[4])
    chipset_dedus, tip_ram_dedus = deduce_mb_avansat(nume)
    Motherboard.objects.update_or_create(nume=nume, defaults={
        'brand': nume.split()[0], 'pret': pret_mock, 'stoc': pret_mock > 0, 'magazin': 'Mock Data', 'url_produs': '#',
        'socket': str(rand[1]), 'format': str(rand[2]), 'sloturi_ram': int_sigur(rand[3]) or 4,
        'chipset': chipset_dedus, 'tip_memorie': tip_ram_dedus
    })

# --- RAM ---
print("⏳ Transferăm Memoriile (RAM)...")
cursor.execute("SELECT name, speed, modules, cas_latency, price FROM RAM")
for rand in cursor.fetchall():
    nume = rand[0]
    if not nume: continue
    pret_mock = float_sigur(rand[4])
    mod_str = str(rand[2])
    nr_mod = int(extrage_numar(mod_str.split('x')[0])) if 'x' in mod_str else 1
    cap_mod = int(extrage_numar(mod_str.split('x')[-1])) if 'x' in mod_str else 8
    RAM.objects.update_or_create(nume=nume, defaults={
        'brand': nume.split()[0], 'pret': pret_mock, 'stoc': pret_mock > 0, 'magazin': 'Mock Data', 'url_produs': '#',
        'capacitate_totala_gb': nr_mod * cap_mod, 'numar_module': nr_mod,
        'frecventa_mhz': int(extrage_numar(rand[1])), 'latenta_cl': int_sigur(rand[3]), 'tip_memorie': 'DDR4'
    })

# --- PSU ---
print("⏳ Transferăm Sursele (PSU)...")
cursor.execute("SELECT name, wattage, efficiency, modular, price FROM PSU")
for rand in cursor.fetchall():
    nume = rand[0]
    if not nume: continue
    pret_mock = float_sigur(rand[4])
    PSU.objects.update_or_create(nume=nume, defaults={
        'brand': nume.split()[0], 'pret': pret_mock, 'stoc': pret_mock > 0, 'magazin': 'Mock Data', 'url_produs': '#',
        'putere_w': int_sigur(rand[1]), 'certificare': deduce_psu_avansat(nume, rand[2]),
        'este_modulara': 'full' in str(rand[3]).lower() or 'semi' in str(rand[3]).lower()
    })

# --- STORAGE ---
print("⏳ Transferăm Stocarea (SSD/HDD)...")
cursor.execute("SELECT name, capacity, type, interface, form_factor, price FROM STOCARE")
for rand in cursor.fetchall():
    nume = rand[0]
    if not nume: continue
    pret_mock = float_sigur(rand[5])
    tip_dedus, interfata_dedusa = deduce_storage_avansat(nume)
    Storage.objects.update_or_create(nume=nume, defaults={
        'brand': nume.split()[0], 'pret': pret_mock, 'stoc': pret_mock > 0, 'magazin': 'Mock Data', 'url_produs': '#',
        'capacitate_gb': int_sigur(rand[1]), 'tip': tip_dedus, 'interfata': interfata_dedusa, 'format': str(rand[4])
    })

# --- CARCASE ---
print("⏳ Transferăm Carcasele (Case)...")
cursor.execute("SELECT name, type, price FROM CARCASE")
for rand in cursor.fetchall():
    nume = rand[0]
    if not nume: continue
    pret_mock = float_sigur(rand[2])
    Case.objects.update_or_create(nume=nume, defaults={
        'brand': nume.split()[0], 'pret': pret_mock, 'stoc': pret_mock > 0, 'magazin': 'Mock Data', 'url_produs': '#',
        'tip_carcasa': deduce_case_avansat(nume), 'inaltime_mm': 400, 'lungime_mm': 400, 'latime_mm': 200
    })

# --- COOLERE ---
print("⏳ Transferăm Coolerele...")
cursor.execute("SELECT name, size, price FROM COOLERE")
for rand in cursor.fetchall():
    nume = rand[0]
    if not nume: continue
    pret_mock = float_sigur(rand[2])
    tip_racire_dedus, lungime_rad_dedus = deduce_cooler_avansat(nume)
    Cooler.objects.update_or_create(nume=nume, defaults={
        'brand': nume.split()[0], 'pret': pret_mock, 'stoc': pret_mock > 0, 'magazin': 'Mock Data', 'url_produs': '#',
        'tip_racire': tip_racire_dedus, 'lungime_radiator_mm': lungime_rad_dedus if lungime_rad_dedus > 0 else None,
        'inaltime_mm': int_sigur(rand[1])
    })

conn.close()
print("\n🎉 GATA! Toate datele tale au fost procesate, curățate și salvate în Django!")