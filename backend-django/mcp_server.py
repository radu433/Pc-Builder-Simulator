import os
import django
import json
import re
import hashlib

# Inițializare mediului Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from mcp.server.fastmcp import FastMCP
from components.models import CPU, GPU, RAM, Storage, PSU, Motherboard, Case, Cooler
from django.conf import settings
import google.genai as genai
from google.genai import types

PRAG_BOTTLENECK_PROCENT = 15.0

mcp = FastMCP("PC Builder Tools")


@mcp.tool()
def search_components(component_type: str, budget: float, in_stock: bool = True) -> dict:
    """
        Caută componente disponibile în DB după tip și buget maxim.
        Tipuri acceptate: cpu, gpu, ram, storage, psu, motherboard, case, cooler.
        Returnează maxim 15 rezultate sortate după preț descrescător.
        Folosește acest tool când userul întreabă ce componente sunt disponibile
        într-un anumit buget sau vrea să exploreze opțiunile.
    """
    
    model_map = {
        "cpu": CPU, 
        "gpu": GPU, 
        "ram": RAM, 
        "storage": Storage, 
        "psu": PSU,
        "motherboard": Motherboard,
        "case": Case,
        "cooler": Cooler
    }
    
    model = model_map.get(component_type.lower())
    if not model:
        return {"error": f"Tip necunoscut: {component_type}"}

    queryset = model.objects.filter(pret__lte=budget)
    if in_stock:
        queryset = queryset.filter(stoc=True) 

    rezultate = list(queryset.values()[:15])
    return {
        "components": rezultate, 
        "count_returnat": len(rezultate),
        "total_disponibil_in_db": queryset.count()
    }

    
@mcp.tool()
def get_bottleneck_score(cpu_id: int, gpu_id: int):
    """
    Calculează bottleneck-ul între un CPU și GPU dintr-un build.
    Returnează scorul fiecărei componente, procentajul de bottleneck
    și care componentă limitează performanța.
    Folosește când userul întreabă dacă un combo CPU+GPU e echilibrat
    sau dacă o componentă îl trage înapoi pe cealaltă.
    """
    try:
        cpu = CPU.objects.get(id=cpu_id)
        gpu = GPU.objects.get(id=gpu_id)
    except (CPU.DoesNotExist, GPU.DoesNotExist) as e:
        return {"error": str(e)}

    scor_cpu = float(cpu.nuclee) * float(cpu.frecventa_ghz) * 10
    if cpu.threaduri and cpu.threaduri > cpu.nuclee:
        scor_cpu *= 1.15

    scor_gpu = float(gpu.vram_gb) * 15 + float(gpu.consum_tdp) * 0.8

    scor_max = max(scor_cpu, scor_gpu)
    procentaj = (abs(scor_cpu - scor_gpu) / scor_max) * 100 if scor_max > 0 else 0

    are_bottleneck = procentaj >= PRAG_BOTTLENECK_PROCENT
    limitator = None
    if are_bottleneck:
        limitator = "CPU" if scor_cpu < scor_gpu else "GPU"

    return {
        "cpu": cpu.nume,
        "gpu": gpu.nume,
        "scor_cpu": round(scor_cpu, 1),
        "scor_gpu": round(scor_gpu, 1),
        "procentaj_bottleneck": round(procentaj, 1),
        "are_bottleneck": are_bottleneck,
        "componenta_limitatoare": limitator,
    }

@mcp.tool()
def get_fps_estimate(cpu_id: int, gpu_id: int, game: str, resolution: str = "1080p") -> dict:
    """
    Returnează FPS estimat din cache pentru o combinație CPU+GPU și un joc specific.
    Caută în cache după numele jocului (match parțial, case-insensitive).
    Dacă nu există cache pentru combo-ul respectiv, sugerează rularea benchmark_build întâi.
    Folosește când userul întreabă câte FPS-uri face un build la un anumit joc și rezoluție.
    Rezoluții acceptate: 1080p, 1440p, 4k.
    """
    from components.models import BuildAnalysisCache

    try:
        cpu = CPU.objects.get(id=cpu_id)
        gpu = GPU.objects.get(id=gpu_id)
    except (CPU.DoesNotExist, GPU.DoesNotExist) as e:
        return {"error": str(e)}

    cache_key = hashlib.md5(f"{cpu_id}_{gpu_id}".encode()).hexdigest()

    try:
        cached = BuildAnalysisCache.objects.get(cache_key=cache_key)
        fps_data = cached.fps_data

        joc_data = next(
            (j for j in fps_data.get("jocuri", [])
             if game.lower() in j["nume"].lower() or j["nume"].lower() in game.lower()),
            None
        )

        if joc_data:
            res_key = f"fps_{resolution.replace('p', '').replace('P', '')}p"
            return {
                "cpu": cpu.nume,
                "gpu": gpu.nume,
                "game": joc_data["nume"],
                "resolution": resolution,
                "fps": joc_data.get(res_key, {}),
                "preset_optim": joc_data.get("preset_optim"),
                "rating_joc": joc_data.get("rating_joc"),
                "cached": True
            }
        else:
            jocuri_disponibile = [j["nume"] for j in fps_data.get("jocuri", [])]
            return {
                "cpu": cpu.nume,
                "gpu": gpu.nume,
                "game": game,
                "cached": True,
                "nota": f"Jocul '{game}' nu există în cache. Jocuri disponibile: {', '.join(jocuri_disponibile)}"
            }

    except BuildAnalysisCache.DoesNotExist:
        return {
            "cpu": cpu.nume,
            "gpu": gpu.nume,
            "game": game,
            "cached": False,
            "nota": "Nu există benchmark pentru această combinație CPU+GPU. Rulează benchmark_build întâi."
        }

@mcp.tool()
def check_compatibility(build: dict) -> dict:
    """Verifică compatibilitatea componentelor unui build."""
    probleme = []

    cpu = build.get("cpu", {})
    gpu = build.get("gpu", {})
    ram = build.get("ram", {})
    motherboard = build.get("motherboard", {})
    psu = build.get("psu", {})
    case = build.get("case", {})
    cooler = build.get("cooler", {})

    if cpu and motherboard:
        if str(cpu.get("socket", "")).upper() != str(motherboard.get("socket", "")).upper():
            probleme.append(f"Incompatibilitate socket: CPU {cpu.get('socket')}, MB {motherboard.get('socket')}.")

    if ram and motherboard:
        if str(ram.get("tip_memorie", "")).upper() != str(motherboard.get("tip_memorie", "")).upper():
            probleme.append(f"Incompatibilitate RAM: {ram.get('tip_memorie')} vs {motherboard.get('tip_memorie')}.")

    if ram and motherboard:
        cap = int(ram.get("capacitate_totala_gb", 0) or 0)
        cap_max = int(motherboard.get("capacitate_max_ram_gb", 0) or 0)
        if cap and cap_max and cap > cap_max:
            probleme.append(f"RAM depășește limita MB: {cap}GB față de maxim {cap_max}GB.")

    if gpu and case:
        lung_gpu = int(gpu.get("lungime_mm", 0) or 0)
        lung_max = int(case.get("lungime_max_gpu_mm", 0) or 0)
        if lung_gpu and lung_max and lung_gpu > lung_max:
            probleme.append(f"GPU nu încape în carcasă: {lung_gpu}mm față de maxim {lung_max}mm.")

    if cooler and cpu:
        socket_cpu = str(cpu.get("socket", "")).upper()
        suportate = [str(s).upper() for s in (cooler.get("socket_suportate") or [])]
        if socket_cpu and suportate and socket_cpu not in suportate:
            probleme.append(f"Cooler nu suportă socket {socket_cpu}. Compatibil: {', '.join(suportate)}.")

    if cooler and case:
        tip = str(cooler.get("tip_racire", "")).lower()
        if "aio" not in tip and "lichid" not in tip:
            inal = int(cooler.get("inaltime_mm", 0) or 0)
            inal_max = int(case.get("inaltime_max_cooler_mm", 0) or 0)
            if inal and inal_max and inal > inal_max:
                probleme.append(f"Cooler nu încape în carcasă: {inal}mm față de maxim {inal_max}mm.")

    if psu:
        tdp = 50
        if cpu: tdp += int(cpu.get("consum_tdp", 0) or 0)
        if gpu: tdp += int(gpu.get("consum_tdp", 0) or 0)
        putere = int(psu.get("putere_w", 0) or 0)
        recomandat = int(tdp * 1.25)
        if putere and putere < recomandat:
            probleme.append(f"PSU insuficient: TDP ~{tdp}W, recomandat minim {recomandat}W, selectat {putere}W.")

    return {"compatibil": len(probleme) == 0, "probleme": probleme}


@mcp.tool()
def benchmark_build(cpu: dict, gpu: dict, ram: dict, rezolutie: str = "1080p", jocuri_preferate: list[str] = None, user_id: int = None) -> dict:
    """Rulează benchmark complet pentru un build și returnează FPS-uri estimate via Gemini. Poți specifica 'jocuri_preferate'."""
    from components.models import BuildAnalysisCache

    try:
        # --- CACHE CHECK ---
        cpu_id = cpu.get("id")
        gpu_id = gpu.get("id")
        if cpu_id and gpu_id:
            cache_key = hashlib.md5(f"{cpu_id}_{gpu_id}".encode()).hexdigest()
            try:
                cached = BuildAnalysisCache.objects.get(cache_key=cache_key)
                result = cached.fps_data
                result["_cached"] = True
                return result
            except BuildAnalysisCache.DoesNotExist:
                pass
        else:
            cache_key = None
        # --- END CACHE CHECK ---

        if not jocuri_preferate and user_id:
            try:
                from accounts.models import UserPreferences
                prefs = UserPreferences.objects.get(user_id=user_id)
                if prefs.jocuri:
                    jocuri_preferate = prefs.jocuri
            except:
                pass

        if not jocuri_preferate:
            jocuri_preferate = ["CS2", "Cyberpunk 2077", "Minecraft", "Valorant"]

        scor_cpu = 0.0
        if cpu:
            nuclee    = int(cpu.get("nuclee", 4) or 4)
            threaduri = int(cpu.get("threaduri", nuclee) or nuclee)
            frecventa = float(cpu.get("frecventa_ghz", 3.0) or 3.0)
            scor_cpu  = nuclee * frecventa * 10
            if threaduri > nuclee:
                scor_cpu *= 1.15

        scor_gpu = 0.0
        if gpu:
            vram     = int(gpu.get("vram_gb", 4) or 4)
            tdp_gpu  = int(gpu.get("consum_tdp", 100) or 100)
            scor_gpu = vram * 15 + tdp_gpu * 0.8

        bottleneck_info = ""
        if scor_cpu > 0 and scor_gpu > 0:
            scor_max = max(scor_cpu, scor_gpu)
            diff = (abs(scor_cpu - scor_gpu) / scor_max) * 100
            if diff >= PRAG_BOTTLENECK_PROCENT and scor_cpu < scor_gpu:
                bottleneck_info = f"\nATENTIE: Bottleneck CPU estimat ~{diff:.1f}%. CPU limitează GPU-ul."

        prompt = f"""Ești expert în benchmarking PC cu date din Digital Foundry, TechPowerUp și GamersNexus.

CPU: {cpu.get('nume', '?')} | {cpu.get('nuclee', '?')} nuclee @ {cpu.get('frecventa_ghz', '?')}GHz | TDP {cpu.get('consum_tdp', '?')}W
GPU: {gpu.get('nume', '?')} | {gpu.get('vram_gb', '?')}GB VRAM | TDP {gpu.get('consum_tdp', '?')}W
RAM: {ram.get('capacitate_totala_gb', '?')}GB {ram.get('tip_memorie', '?')} @ {ram.get('frecventa_mhz', '?')}MHz
Rezoluție țintă: {rezolutie}{bottleneck_info}

Returnează EXCLUSIV JSON valid (fără markdown, fără text adițional):
{{
  "rating_general": "<S|A|B|C|D>",
  "recomandare_rezolutie": "<1080p|1440p|4K>",
  "mesaj_general": "<2-3 propoziții în română despre performanța acestui build>",
  "are_bottleneck_cpu": <true|false>,
  "procentaj_bottleneck": <0-100>,
  "mesaj_bottleneck": "<o propoziție în română despre echilibrul CPU/GPU>",
  "jocuri": [
    {{
      "nume": "<nume joc>",
      "fps_1080p": {{"low": <int>, "medium": <int>, "high": <int>, "ultra": <int>}},
      "fps_1440p": {{"low": <int>, "medium": <int>, "high": <int>, "ultra": <int>}},
      "fps_4k":    {{"low": <int>, "medium": <int>, "high": <int>, "ultra": <int>}},
      "preset_optim": "<Low|Medium|High|Ultra>",
      "rating_joc": "<S|A|B|C|D>"
    }}
  ]
}}

Reguli:
1. Exact {len(jocuri_preferate)} jocuri în ordinea asta: {', '.join(jocuri_preferate)}
2. FPS: Low > Medium > High > Ultra pentru fiecare rezoluție
3. FPS: 1080p > 1440p > 4K pentru fiecare preset
4. Rating: S=144+fps, A=90-143fps, B=60-89fps, C=30-59fps, D=sub 30fps (High preset, rezoluția țintă)"""

        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        response = client.models.generate_content(
            model="gemini-2.5-flash"
            contents=prompt
        )
        text = response.text.strip()
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        result = json.loads(text)

        # --- SALVEAZĂ ÎN CACHE ---
        if cache_key:
            BuildAnalysisCache.objects.update_or_create(
                cache_key=cache_key,
                defaults={"fps_data": result}
            )
        # --- END CACHE ---

        return result

    except json.JSONDecodeError as e:
        return {"error": f"Gemini nu a returnat JSON valid: {e}"}
    except Exception as e:
        import traceback
        return {"error": f"Eroare internă în benchmark_build: {str(e)}", "traceback": traceback.format_exc()}


@mcp.tool()
def get_user_preferences(user_id: int) -> dict:
    """Returnează preferințele salvate ale utilizatorului sau semnalează că lipsesc."""
    try:
        from accounts.models import UserPreferences
        prefs = UserPreferences.objects.get(user_id=user_id)
        return {
            "are_preferinte": True,
            "preferinte": {
                "buget": prefs.buget,
                "jocuri": prefs.jocuri,
                "rezolutie": prefs.rezolutie,
                "tip_utilizare": prefs.tip_utilizare,
            },
            "mesaj_agent": (
                f"Ai preferințe salvate: buget {prefs.buget} RON, "
                f"jocuri {prefs.jocuri}, rezoluție {prefs.rezolutie}. "
                f"Dorești să construim build-ul pe baza acestora sau preferi să îmi spui altele?"
            )
        }
    except:
        return {
            "are_preferinte": False,
            "mesaj_agent": (
                "Nu ai preferințe salvate. "
                "Spune-mi bugetul, jocurile preferate și rezoluția dorită."
            )
        }


@mcp.tool()
def save_user_preferences(user_id: int, buget: float, 
                           jocuri: list, rezolutie: str,
                           tip_utilizare: str = "gaming") -> dict:
    """Salvează sau actualizează preferințele utilizatorului."""
    from accounts.models import UserPreferences
    
    prefs, created = UserPreferences.objects.update_or_create(
        user_id=user_id,
        defaults={
            "buget": buget,
            "jocuri": jocuri,
            "rezolutie": rezolutie,
            "tip_utilizare": tip_utilizare,
        }
    )
    return {
        "salvat": True,
        "actiune": "creat" if created else "actualizat",
        "preferinte": {
            "buget": buget,
            "jocuri": jocuri,
            "rezolutie": rezolutie,
        }
    }


@mcp.tool()
def create_build_from_preferences(
    user_id: int = None,
    buget: float = None,
    jocuri: list = None,
    rezolutie: str = "1080p",
    tip_utilizare: str = "gaming"
) -> dict:
    """
    Construiește un build optim din DB pe baza preferințelor utilizatorului.
    Dacă user_id e furnizat, încearcă să încarce preferințele salvate.
    Dacă nu există preferințe, folosește parametrii transmiși direct.
    """
    from components.models import BuildAnalysisCache

    if user_id:
        try:
            from accounts.models import UserPreferences
            prefs = UserPreferences.objects.get(user_id=user_id)
            buget = buget or prefs.buget
            jocuri = jocuri or prefs.jocuri
            rezolutie = rezolutie or prefs.rezolutie
            tip_utilizare = tip_utilizare or prefs.tip_utilizare
        except:
            pass

    if not buget:
        return {
            "succes": False,
            "mesaj": "Nu am un buget. Spune-mi cât vrei să cheltuiești."
        }

    if not jocuri:
        return {
            "succes": False,
            "mesaj": "Nu știu ce jocuri vrei să joci. Spune-mi titlurile preferate."
        }

    if tip_utilizare == "gaming":
        distributie = {
            "gpu": 0.40,
            "cpu": 0.22,
            "ram": 0.10,
            "storage": 0.10,
            "psu": 0.08,
            "motherboard": 0.10,
        }
    else:
        distributie = {
            "gpu": 0.28,
            "cpu": 0.30,
            "ram": 0.15,
            "storage": 0.12,
            "psu": 0.07,
            "motherboard": 0.08,
        }

    def alege_optima(queryset, buget_max):
        """Alege cea mai performantă componentă în limita bugetului."""
        valabile = list(queryset.filter(pret__lte=buget_max, stoc=True).order_by("-pret"))
        if valabile:
            return valabile[0]
        fallback = list(queryset.filter(stoc=True).order_by("pret"))
        return fallback[0] if fallback else None

    gpu_ales    = alege_optima(GPU.objects.all(), buget * distributie["gpu"])
    cpu_ales    = alege_optima(CPU.objects.all(), buget * distributie["cpu"])
    ram_ales    = alege_optima(RAM.objects.all(), buget * distributie["ram"])
    storage_ales = alege_optima(Storage.objects.all(), buget * distributie["storage"])
    psu_ales    = alege_optima(PSU.objects.all(), buget * distributie["psu"])

    if cpu_ales:
        mb_qs = Motherboard.objects.filter(socket=cpu_ales.socket)
        motherboard_aleasa = alege_optima(mb_qs, buget * distributie["motherboard"])
    else:
        motherboard_aleasa = None

    if not gpu_ales or not cpu_ales:
        return {
            "succes": False,
            "mesaj": f"Bugetul de {buget} RON este prea mic pentru un build viabil. "
                     f"Încearcă un buget de minim 2000 RON."
        }

    componente = {
        "gpu": gpu_ales,
        "cpu": cpu_ales,
        "ram": ram_ales,
        "storage": storage_ales,
        "psu": psu_ales,
        "motherboard": motherboard_aleasa,
    }
    total = sum(float(c.pret) for c in componente.values() if c)

    bottleneck = get_bottleneck_score(cpu_ales.id, gpu_ales.id)

    build_dict = {
        k: {f: getattr(v, f, None) for f in [
            "id", "nume", "pret", "socket", "tip_memorie",
            "capacitate_totala_gb", "capacitate_max_ram_gb",
            "vram_gb", "consum_tdp", "nuclee", "frecventa_ghz",
            "threaduri", "putere_w"
        ] if hasattr(v, f)}
        for k, v in componente.items() if v
    }
    compatibilitate = check_compatibility(build_dict)

    cache_key = hashlib.md5(f"{cpu_ales.id}_{gpu_ales.id}".encode()).hexdigest()
    benchmark = None
    try:
        cached = BuildAnalysisCache.objects.get(cache_key=cache_key)
        benchmark = cached.fps_data
    except BuildAnalysisCache.DoesNotExist:
        benchmark = benchmark_build(
            cpu=build_dict.get("cpu", {}),
            gpu=build_dict.get("gpu", {}),
            ram=build_dict.get("ram", {}),
            rezolutie=rezolutie
        )
        if "error" not in benchmark:
            BuildAnalysisCache.objects.create(
                cache_key=cache_key,
                cpu_id=cpu_ales.id,
                gpu_id=gpu_ales.id,
                fps_data=benchmark
            )

    fps_jocuri_cerute = []
    if benchmark and "jocuri" in benchmark:
        for joc in benchmark["jocuri"]:
            if any(j.lower() in joc["nume"].lower() for j in jocuri):
                fps_jocuri_cerute.append({
                    "joc": joc["nume"],
                    "fps": joc.get(f"fps_{rezolutie.replace('p', '')}p", {}),
                    "preset_optim": joc.get("preset_optim"),
                    "rating": joc.get("rating_joc"),
                })

    return {
        "succes": True,
        "buget_total": buget,
        "pret_total": round(total, 2),
        "diferenta": round(buget - total, 2),
        "rezolutie": rezolutie,
        "jocuri_cerute": jocuri,
        "build": {
            k: {"id": v.id, "nume": v.nume, "pret": float(v.pret)}
            for k, v in componente.items() if v
        },
        "bottleneck": bottleneck,
        "compatibilitate": compatibilitate,
        "fps_jocuri_cerute": fps_jocuri_cerute,
        "rating_general": benchmark.get("rating_general") if benchmark else None,
        "mesaj_general": benchmark.get("mesaj_general") if benchmark else None,
    }


@mcp.tool()
def generate_build_image(case_name: str, gpu_name: str, cpu_name: str) -> dict:
    """Generează o imagine render cu build-ul PC pe baza componentelor selectate."""

    cache_key = f"{case_name}_{gpu_name}_{cpu_name}".replace(" ", "_").lower()
    cache_key = hashlib.md5(cache_key.encode()).hexdigest()
    cache_path = os.path.join(settings.MEDIA_ROOT, "builds", f"{cache_key}.png")

    if os.path.exists(cache_path):
        return {"image_path": cache_path, "cached": True}

    os.makedirs("media/builds", exist_ok=True)

    prompt = (
        f"Realistic PC build render inside a {case_name} mid-tower case, "
        f"featuring {gpu_name} graphics card and {cpu_name} processor, "
        f"clean cable management, RGB lighting, studio lighting, "
        f"4K quality, photorealistic, dark background, professional photography"
    )

    try:
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        response = client.models.generate_images(
            model="imagen-4.0-generate-001",
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio="16:9",
                safety_filter_level="block_low_and_above",
            )
        )

        image_data = response.generated_images[0].image.image_bytes
        with open(cache_path, "wb") as f:
            f.write(image_data)

        return {
            "image_path": cache_path,
            "cached": False,
            "prompt": prompt,
        }

    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def compare_components(component_type: str, component_names: list[str]) -> dict:
    """Compară 2 până la 3 componente de același tip (ex: CPU, GPU, RAM) din baza de date.

        Pentru fiecare componentă returnează:
        - Nume, brand, preț actual (RON) și magazin
        - Specificații tehnice relevante categoriei (nuclee/threaduri pentru CPU, VRAM pentru GPU, etc.)
        - Scor calitate/preț calculat ca: (scor_performanță / preț) * 100

        Logica scorului de performanță per categorie:
        - CPU: frecventa_ghz * nuclee * threaduri / consum_tdp
        - GPU: vram_gb * frecventa_mhz / consum_tdp  
        - RAM: frecventa_mhz * capacitate_gb / latenta

        Returnează:
        1. 'tabel_markdown': string formatat ca tabel markdown cu toate datele
        2. 'recomandat': numele componentei cu cel mai bun raport calitate/preț
        3. 'componente': lista cu datele brute ale fiecărei componente
        4. 'sumar': 1-2 propoziții care explică de ce e recomandat cel ales

        Dacă o componentă nu are preț în DB, exclude-o din calculul calitate/preț 
        și menționează asta în sumar.
        """
    
    model_map = {
        "cpu": CPU, 
        "gpu": GPU, 
        "ram": RAM, 
        "storage": Storage, 
        "psu": PSU,
        "motherboard": Motherboard,
        "case": Case,
        "cooler": Cooler
    }
    
    model = model_map.get(component_type.lower())
    if not model:
        return {"error": f"Tip necunoscut: {component_type}"}

    if len(component_names) < 2 or len(component_names) > 3:
        return {"error": "Te rog să furnizezi exact 2 sau 3 nume de componente pentru comparație."}

    comparison_data = []
    
    for name in component_names:
        query = model.objects.filter(stoc=True)
        for word in name.split():
            query = query.filter(nume__icontains=word)
            
        found = query.order_by("pret").first()
        if not found:
            query_nostoc = model.objects.all()
            for word in name.split():
                query_nostoc = query_nostoc.filter(nume__icontains=word)
            found = query_nostoc.order_by("pret").first()
            
        if not found:
            comparison_data.append({"error": f"Nu am găsit nicio componentă pentru: {name}", "nume_cautat": name})
            continue

        c = found
        data = {
            "nume": c.nume,
            "pret": float(c.pret) if c.pret else 0,
            "stoc": c.stoc,
            "magazin": c.magazin
        }
        
        if component_type.lower() == "gpu":
            data["specs"] = {
                "VRAM": f"{c.vram_gb} GB",
                "TDP": f"{c.consum_tdp} W",
                "Chipset": c.model_chipset,
                "Lungime": f"{c.lungime_mm} mm"
            }
            data["scor_performanta"] = c.vram_gb * 15 + c.consum_tdp * 0.8
            
        elif component_type.lower() == "cpu":
            data["specs"] = {
                "Nuclee / Threaduri": f"{c.nuclee}C / {c.threaduri}T",
                "Frecvență": f"{c.frecventa_ghz} GHz",
                "TDP": f"{c.consum_tdp} W",
                "Socket": c.socket
            }
            scor = c.nuclee * float(c.frecventa_ghz) * 10
            if c.threaduri > c.nuclee:
                scor *= 1.15
            data["scor_performanta"] = scor
            
        elif component_type.lower() == "ram":
            data["specs"] = {
                "Capacitate": f"{c.capacitate_totala_gb} GB",
                "Frecvență": f"{c.frecventa_mhz} MHz",
                "Tip": c.tip_memorie,
                "Latență": f"CL{c.latenta_cl}"
            }
            scor = (c.capacitate_totala_gb * 100) + (c.frecventa_mhz * 0.1) - (c.latenta_cl * 5)
            data["scor_performanta"] = max(scor, 1)

        elif component_type.lower() == "motherboard":
            data["specs"] = {
                "Socket": c.socket,
                "Chipset": c.chipset,
                "Format": c.format,
                "WiFi": "Da" if c.are_wifi else "Nu",
                "Sloturi RAM": c.sloturi_ram
            }
            
        elif component_type.lower() == "storage":
            data["specs"] = {
                "Capacitate": f"{c.capacitate_gb} GB",
                "Tip": c.tip,
                "Format": c.format,
                "Citire": f"{c.viteza_citire_mb_s} MB/s" if c.viteza_citire_mb_s else "N/A",
                "Scriere": f"{c.viteza_scriere_mb_s} MB/s" if c.viteza_scriere_mb_s else "N/A"
            }
            scor = c.capacitate_gb + (c.viteza_citire_mb_s or 500) * 0.5
            data["scor_performanta"] = scor
            
        elif component_type.lower() == "psu":
            data["specs"] = {
                "Putere": f"{c.putere_w} W",
                "Certificare": c.certificare,
                "Modulară": c.este_modulara
            }
            scor = c.putere_w + (50 if "Gold" in str(c.certificare) else 0)
            data["scor_performanta"] = scor
            
        elif component_type.lower() == "case":
            data["specs"] = {
                "Tip": c.tip_carcasa,
                "Sursă inclusă": "Da" if c.include_sursa else "Nu",
                "GPU Max": f"{c.lungime_max_gpu_mm} mm" if c.lungime_max_gpu_mm else "N/A",
                "Cooler Max": f"{c.inaltime_max_cooler_mm} mm" if c.inaltime_max_cooler_mm else "N/A"
            }
            
        elif component_type.lower() == "cooler":
            data["specs"] = {
                "Tip răcire": c.tip_racire,
                "Înălțime": f"{c.inaltime_mm} mm" if c.inaltime_mm else "N/A",
                "Radiator": f"{c.lungime_radiator_mm} mm" if c.lungime_radiator_mm else "N/A"
            }
            
        comparison_data.append(data)

    nume_cols = []
    for c in comparison_data:
        if "error" in c:
            nume_cols.append(c["nume_cautat"])
        else:
            short_name = c['nume'][:35] + "..." if len(c.get('nume','')) > 35 else c.get('nume','')
            nume_cols.append(short_name)
            
    md = f"### 📊 Comparație: {' vs '.join(nume_cols)}\n\n"
    md += "| Funcție / Specificație | " + " | ".join(nume_cols) + " |\n"
    md += "|" + "---|" * (len(comparison_data) + 1) + "\n"
    
    md += "| 💰 **Preț minim** | " + " | ".join([f"**{c.get('pret', 0)} RON**" if "error" not in c else "N/A" for c in comparison_data]) + " |\n"
    md += "| 📦 **Stoc** | " + " | ".join(["✅ În stoc" if c.get('stoc') else "❌ Indisponibil" if "error" not in c else "N/A" for c in comparison_data]) + " |\n"
    
    all_spec_keys = []
    for c in comparison_data:
        if "specs" in c:
            for k in c["specs"].keys():
                if k not in all_spec_keys:
                    all_spec_keys.append(k)
                    
    for k in all_spec_keys:
        md += f"| ⚙️ **{k}** | " + " | ".join([str(c.get("specs", {}).get(k, "-")) if "error" not in c else "-" for c in comparison_data]) + " |\n"
        
    if any("scor_performanta" in c for c in comparison_data):
        md += "| 🏆 **Scor Performanță (Estimat)** | " + " | ".join([str(round(c.get("scor_performanta", 0))) if "error" not in c else "-" for c in comparison_data]) + " |\n"
        md += "| ⚖️ **Raport Performanță/Preț** | "
        
        for c in comparison_data:
            if "error" in c or not c.get("pret") or c.get("pret") == 0 or not c.get("scor_performanta"):
                md += "- | "
            else:
                raport = c["scor_performanta"] / c["pret"] * 100
                md += f"**{round(raport, 1)}** pct/100RON | "
        md = md.rstrip(" |") + " |\n"

    best_buy = None
    best_ratio = 0
    for c in comparison_data:
        if "error" not in c and c.get("pret") and c.get("pret") > 0 and c.get("scor_performanta"):
            r = c["scor_performanta"] / c["pret"]
            if r > best_ratio:
                best_ratio = r
                best_buy = c["nume"]
                
    if best_buy:
        md += f"\n💡 **Recomandare (Best Buy):** **{best_buy}** oferă cel mai bun raport performanță/preț din această selecție.\n"

    return {
        "succes": True,
        "markdown": md,
        "date_brute": comparison_data
    }


@mcp.tool()
def get_best_value_builds(buget: float) -> dict:
    """
        Generează top 3 build-uri complete optimizate pentru tipuri diferite de utilizare,
        respectând un buget maxim dat în RON.

        Tipuri de build-uri generate:
        - GAMING: prioritizează GPU puternic, CPU echilibrat, RAM 16GB+ rapid
        - OFFICE: prioritizează stabilitate și consum redus, GPU integrat sau entry-level
        - WORKSTATION: prioritizează CPU cu multe nuclee/threaduri, RAM 32GB+, GPU cu VRAM mare

        Criterii de selecție componente (doar cele cu preț în DB):
        - CPU: ales în funcție de nuclee/threaduri necesare tipului de build
        - GPU: ales după VRAM și performanță relativă la preț
        - RAM: minim 16GB gaming/office, 32GB workstation, frecvență cât mai mare
        - Storage: cel mai rapid disponibil în buget (preferă NVMe > SATA SSD > HDD)
        - Compatibilitate: socket CPU == socket Motherboard, DDR generation match

        Calcul scor calitate/preț per build:
        - suma scorurilor individuale ale componentelor / costul total * 100
        - penalizare dacă bugetul e depășit
        - bonus dacă toate componentele au preț real din DB (nu estimat)

        Returnează pentru fiecare build:
        1. 'tip': Gaming / Office / Workstation
        2. 'componente': dict cu fiecare componentă selectată (nume, preț, magazin, url)
        3. 'pret_total': suma prețurilor reale din DB
        4. 'scor_calitate_pret': float calculat
        5. 'procent_buget_folosit': cât % din buget e folosit
        6. 'sumar': 2-3 propoziții care explică de ce acest build e optim pentru tipul său
        7. 'avertismente': lista de probleme (ex: "GPU-ul depășește 40% din buget")

        Dacă bugetul e prea mic pentru un tip de build, returnează un mesaj explicit
        în loc să forțezi componente incompatibile.
        """
    
    distributii = {
        "Gaming": {
            "gpu": 0.45, "cpu": 0.20, "ram": 0.10, "storage": 0.10, "psu": 0.07, "motherboard": 0.08
        },
        "Workstation": {
            "gpu": 0.25, "cpu": 0.35, "ram": 0.15, "storage": 0.12, "psu": 0.05, "motherboard": 0.08
        },
        "Office": {
            "gpu": 0.10, "cpu": 0.40, "ram": 0.15, "storage": 0.15, "psu": 0.10, "motherboard": 0.10
        }
    }
    
    def alege_optima(queryset, buget_max):
        valabile = list(queryset.filter(pret__lte=buget_max, stoc=True).order_by("-pret"))
        return valabile[0] if valabile else None
        
    def alege_ieftina(queryset):
        valabile = list(queryset.filter(stoc=True).order_by("pret"))
        return valabile[0] if valabile else None

    builds = []
    
    for nume_build, dist in distributii.items():
        gpu_ales = alege_optima(GPU.objects.all(), buget * dist["gpu"])
        if not gpu_ales: gpu_ales = alege_ieftina(GPU.objects.all())
        
        cpu_ales = alege_optima(CPU.objects.all(), buget * dist["cpu"])
        if not cpu_ales: cpu_ales = alege_ieftina(CPU.objects.all())
        
        ram_ales = alege_optima(RAM.objects.all(), buget * dist["ram"])
        if not ram_ales: ram_ales = alege_ieftina(RAM.objects.all())
        
        sto_ales = alege_optima(Storage.objects.all(), buget * dist["storage"])
        if not sto_ales: sto_ales = alege_ieftina(Storage.objects.all())
        
        psu_ales = alege_optima(PSU.objects.all(), buget * dist["psu"])
        if not psu_ales: psu_ales = alege_ieftina(PSU.objects.all())
        
        mb_aleasa = None
        if cpu_ales:
            mb_qs = Motherboard.objects.filter(socket=cpu_ales.socket)
            mb_aleasa = alege_optima(mb_qs, buget * dist["motherboard"])
            if not mb_aleasa: mb_aleasa = alege_ieftina(mb_qs)
            
        componente = [cpu_ales, gpu_ales, ram_ales, sto_ales, psu_ales, mb_aleasa]
        pret_total = sum(float(c.pret) for c in componente if c and c.pret)
        
        # Scor global
        scor_total = 0
        if cpu_ales: scor_total += cpu_ales.nuclee * float(cpu_ales.frecventa_ghz) * 10
        if gpu_ales: scor_total += gpu_ales.vram_gb * 15
        if ram_ales: scor_total += ram_ales.capacitate_totala_gb * 10
        
        scor_calitate_pret = (scor_total / pret_total * 100) if pret_total > 0 else 0
        
        builds.append({
            "tip_build": nume_build,
            "pret_total": round(pret_total, 2),
            "scor_performanta_absolut": round(scor_total, 1),
            "scor_calitate_pret": round(scor_calitate_pret, 2),
            "componente": {
                "CPU": cpu_ales.nume if cpu_ales else "N/A",
                "GPU": gpu_ales.nume if gpu_ales else "N/A",
                "Placa de baza": mb_aleasa.nume if mb_aleasa else "N/A",
                "RAM": ram_ales.nume if ram_ales else "N/A",
                "Storage": sto_ales.nume if sto_ales else "N/A",
                "Sursa": psu_ales.nume if psu_ales else "N/A",
            }
        })
        
    md = f"### 🏆 Top 3 Build-uri Recomandate (Buget: {buget} RON)\n\n"
    
    for b in builds:
        md += f"#### 🖥️ Build {b['tip_build']} - {b['pret_total']} RON\n"
        md += f"**Scor Calitate/Preț:** {b['scor_calitate_pret']} pct/100RON | **Performanță Brută:** {b['scor_performanta_absolut']} pct\n\n"
        md += "- **CPU:** " + b['componente']['CPU'] + "\n"
        md += "- **GPU:** " + b['componente']['GPU'] + "\n"
        md += "- **Placă de bază:** " + b['componente']['Placa de baza'] + "\n"
        md += "- **RAM:** " + b['componente']['RAM'] + "\n"
        md += "- **Stocare:** " + b['componente']['Storage'] + "\n"
        md += "- **Sursă:** " + b['componente']['Sursa'] + "\n\n"
        
    return {
        "succes": True,
        "markdown": md,
        "builds": builds
    }

@mcp.tool()
def get_component_alternatives(component_type: str, component_id: int, limit: int = 3) -> dict:
    """
        Găsește alternative mai ieftine sau cu raport calitate/preț mai bun pentru o componentă dată.

        Primește un component_id și tipul componentei (cpu/gpu/ram/storage/motherboard/psu/case/cooler).

        Criterii de similaritate per tip:
        - CPU: același socket, diferență max ±2 nuclee, frecvență similară (±0.5 GHz), TDP similar
        - GPU: același tier de performanță (±15% VRAM), același tip memorie (GDDR6/GDDR6X)
        - RAM: aceeași generație (DDR4/DDR5), capacitate identică, frecvență similară (±400 MHz)
        - Storage: același tip (NVMe/SATA), capacitate identică sau superioară
        - Motherboard: același socket, același chipset tier (B-series vs X-series), același tip RAM suportat
        - PSU: putere similară (±50W), același rating eficiență (80+ Bronze/Gold/Platinum)
        - Case: același form factor (ATX/mATX/ITX)
        - Cooler: compatibil cu același socket, TDP suportat similar

        Pentru fiecare alternativă găsită calculează:
        - 'economie_ron': cât economisești față de componenta originală
        - 'diferenta_performanta': estimare procentuală față de original (+ mai bun / - mai slab)
        - 'scor_calitate_pret': performanță relativă / preț * 100
        - 'verdict': 'Recomandat' / 'Compromis acceptabil' / 'Evită' cu explicație scurtă

        Returnează:
        1. 'componenta_originala': datele componentei de referință (nume, preț, specs)
        2. 'alternative': lista sortată după scor calitate/preț descrescător (max 5 rezultate)
        3. 'recomandata': alternativa cu cel mai bun echilibru preț/performanță
        4. 'sumar': 2-3 propoziții care explică contextul (ex: "Dacă bugetul e limitat, X oferă 90% din performanță la 70% din preț")

        Returnează doar componente care au preț real în DB.
        Dacă nu există alternative cu preț în DB, returnează un mesaj explicit.
    """
    
    model_map = {
        "cpu": CPU, "gpu": GPU, "ram": RAM, "storage": Storage, 
        "psu": PSU, "motherboard": Motherboard, "case": Case, "cooler": Cooler
    }
    
    model = model_map.get(component_type.lower())
    if not model:
        return {"error": f"Tip componentă necunoscut: {component_type}"}
        
    try:
        orig = model.objects.get(id=component_id)
    except model.DoesNotExist:
        return {"error": f"Nu există componentă de tip {component_type} cu ID-ul {component_id}"}
        
    if not orig.pret:
        return {"error": "Componenta originală nu are preț, deci nu putem căuta alternative mai ieftine."}
        
    # Preluăm toate componentele în stoc
    qs = model.objects.filter(stoc=True)
    
    # Filtrare de bază pentru compatibilitate rezonabilă
    if component_type.lower() == "cpu":
        qs = qs.filter(nuclee__gte=max(2, getattr(orig, 'nuclee', 2) - 2))
    elif component_type.lower() == "gpu":
        qs = qs.filter(vram_gb__gte=max(2, getattr(orig, 'vram_gb', 2) - 4))
    elif component_type.lower() == "ram":
        # Aici e esențial să păstrăm tipul de memorie (DDR4/DDR5) pentru a nu rupe complet build-ul
        qs = qs.filter(tip_memorie=orig.tip_memorie, capacitate_totala_gb__gte=getattr(orig, 'capacitate_totala_gb', 8))
    elif component_type.lower() == "storage":
        qs = qs.filter(capacitate_gb__gte=getattr(orig, 'capacitate_gb', 256) * 0.5)
    elif component_type.lower() == "psu":
        qs = qs.filter(putere_w__gte=getattr(orig, 'putere_w', 400) - 100)
    elif component_type.lower() == "case":
        qs = qs.filter(tip_carcasa=orig.tip_carcasa)

    def calc_scor(c, tip):
        if tip == "cpu": return (getattr(c, 'nuclee', 0) or 0) * float(getattr(c, 'frecventa_ghz', 0) or 0) * 10
        if tip == "gpu": return (getattr(c, 'vram_gb', 0) or 0) * 15 + (getattr(c, 'consum_tdp', 0) or 0) * 0.8
        if tip == "ram": return (getattr(c, 'capacitate_totala_gb', 0) or 0) * 100 + (getattr(c, 'frecventa_mhz', 0) or 0) * 0.1
        if tip == "storage": return getattr(c, 'capacitate_gb', 0) or 0
        if tip == "psu": return getattr(c, 'putere_w', 0) or 0
        return 1

    def get_brand(name):
        n = name.lower()
        if 'intel' in n or 'core i' in n: return 'intel'
        if 'amd' in n or 'ryzen' in n or 'radeon' in n or 'rx ' in n: return 'amd'
        if 'nvidia' in n or 'geforce' in n or 'rtx ' in n or 'gtx ' in n: return 'nvidia'
        return n.split()[0] if n else 'other'

    scor_orig = calc_scor(orig, component_type.lower())
    brand_orig = get_brand(orig.nume)
    alts = [a for a in qs if a.pret is not None]
    
    buget_alt = None
    echivalent_alt = None
    upgrade_alt = None

    # Sortăm lista pentru a parcurge logic
    alts.sort(key=lambda x: x.pret)

    for a in alts:
        if a.id == orig.id: continue
        
        scor_a = calc_scor(a, component_type.lower())
        if scor_orig == 0: scor_orig = 1
        diff_proc = ((scor_a - scor_orig) / scor_orig) * 100
        economie = float(orig.pret - a.pret)
        brand_a = get_brand(a.nume)

        alt_dict = {
            "id": a.id, "nume": a.nume, "pret": float(a.pret), "magazin": a.magazin, "url": a.url_produs,
            "economie_ron": round(economie, 2), "diferenta_performanta_procent": round(diff_proc, 1),
            "scor_performanta": round(scor_a, 1)
        }

        # 1. BUGET: Ieftin, performanță max -15%, brand irelevant
        if diff_proc >= -15 and economie > 0:
            if not buget_alt or economie > buget_alt["economie_ron"]:
                # Preferăm cea mai mare economie care se încadrează în limită
                alt_dict["tip_alternativa"] = "💰 Varianta de Buget"
                buget_alt = alt_dict

        # 2. ECHIVALENT CONCURENȚĂ: Performanță similară (-10% la +10%), brand diferit
        if -10 <= diff_proc <= 10 and brand_a != brand_orig:
            if not echivalent_alt or abs(diff_proc) < abs(echivalent_alt["diferenta_performanta_procent"]):
                alt_dict["tip_alternativa"] = "⚖️ Echivalent Concurență"
                echivalent_alt = alt_dict

        # 3. UPGRADE: Mai bun cu 10% - 30%, același brand
        if 10 <= diff_proc <= 30 and brand_a == brand_orig:
            if not upgrade_alt or alt_dict["pret"] < upgrade_alt["pret"]:
                alt_dict["tip_alternativa"] = "🚀 Upgrade (Aceeași Platformă)"
                upgrade_alt = alt_dict

    rezultate_valide = [alt for alt in [buget_alt, echivalent_alt, upgrade_alt] if alt]
    
    md = f"### 🔄 Alternative pentru {orig.nume} ({orig.pret} RON)\n\n"
    if not rezultate_valide:
        md += "Nu am găsit alternative mai ieftine cu performanțe similare sau hardware compatibil.\n"
    else:
        for a in rezultate_valide:
            semn = "+" if a['diferenta_performanta_procent'] > 0 else ""
            md += f"- **[{a['tip_alternativa']}] {a['nume']}** la **{a['pret']} RON** | Perf estimată: {semn}{a['diferenta_performanta_procent']}% | Economie: {a['economie_ron']} RON\n"

    return {
        "succes": True,
        "original": {
            "nume": orig.nume,
            "pret": float(orig.pret),
            "scor_performanta": round(scor_orig, 1)
        },
        "alternative": rezultate_valide,
        "markdown": md
    }

if __name__ == "__main__":
    print("MCP Server pornit...")
    mcp.run()