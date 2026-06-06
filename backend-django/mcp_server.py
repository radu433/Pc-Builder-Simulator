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
    """Caută componente din DB după tip și buget."""
    
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
    """Calculează bottleneck între CPU și GPU"""
    try:
        cpu = CPU.objects.get(id=cpu_id)
        gpu = GPU.objects.get(id=gpu_id)
    except (CPU.DoesNotExist, GPU.DoesNotExist) as e:
        return {"error": str(e)}

    scor_cpu = cpu.nuclee * cpu.frecventa_ghz * 10
    if cpu.threaduri > cpu.nuclee:
        scor_cpu *= 1.15

    scor_gpu = gpu.vram_gb * 15 + gpu.consum_tdp * 0.8

    scor_max = max(scor_cpu, scor_gpu)
    procentaj = (abs(scor_cpu - scor_gpu) / scor_max) * 100

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
    """Returnează FPS estimat din cache pentru o combinație CPU+GPU și un joc specific."""
    from builder.models import BuildAnalysisCache

    try:
        cpu = CPU.objects.get(id=cpu_id)
        gpu = GPU.objects.get(id=gpu_id)
    except (CPU.DoesNotExist, GPU.DoesNotExist) as e:
        return {"error": str(e)}

    cache_key = hashlib.md5(f"{cpu_id}_{gpu_id}".encode()).hexdigest()

    try:
        cached = BuildAnalysisCache.objects.get(cache_key=cache_key)
        fps_data = cached.fps_data
        joc_data = next((j for j in fps_data.get("jocuri", []) if j["nume"] == game), None)
        if joc_data:
            return {
                "cpu": cpu.nume,
                "gpu": gpu.nume,
                "game": game,
                "resolution": resolution,
                "fps": joc_data.get(f"fps_{resolution.replace('p', '')}p", {}),
                "cached": True
            }
    except BuildAnalysisCache.DoesNotExist:
        pass

    return {
        "cpu": cpu.nume,
        "gpu": gpu.nume,
        "game": game,
        "cached": False,
        "nota": "Rulează benchmark_build pentru această combinație întâi."
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
def benchmark_build(cpu: dict, gpu: dict, ram: dict, rezolutie: str = "1080p") -> dict:
    """Rulează benchmark complet pentru un build și returnează FPS-uri estimate via Gemini."""
    
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
1. Exact 14 jocuri în ordinea asta: CS2, Valorant, Fortnite, Apex Legends, GTA V,
   The Witcher 3 (Next-Gen), Elden Ring, Red Dead Redemption 2, Cyberpunk 2077,
   Hogwarts Legacy, Alan Wake 2, Battlefield 2042, COD Warzone, Minecraft (BSL Shaders)
2. FPS: Low > Medium > High > Ultra pentru fiecare rezoluție
3. FPS: 1080p > 1440p > 4K pentru fiecare preset
4. Rating: S=144+fps, A=90-143fps, B=60-89fps, C=30-59fps, D=sub 30fps (High preset, rezoluția țintă)"""

    try:
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        text = response.text.strip()
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        return json.loads(text)
    except json.JSONDecodeError as e:
        return {"error": f"Gemini nu a returnat JSON valid: {e}"}
    except Exception as e:
        return {"error": f"Eroare la apelul Gemini: {e}"}


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
    from builder.models import BuildAnalysisCache

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
    cache_path = f"media/builds/{cache_key}.png"

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

    
if __name__ == "__main__":
    print("MCP Server pornit...")
    mcp.run()