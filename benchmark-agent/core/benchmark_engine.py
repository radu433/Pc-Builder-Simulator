"""
Motor de benchmark bazat pe Gemini AI.

Gemini primeste specificatiile complete ale build-ului si genereaza estimari
realiste de FPS pentru 14 jocuri populare la 3 rezolutii si 4 preset-uri grafice.
"""

import json
import re
import google.generativeai as genai

from core.schemas import (
    BenchmarkRequest, BenchmarkResponse,
    GameResult, FpsPreset, CpuImpact, GpuInfo,
)
from core.gpu_tier import detecteaza_tier, get_tier_name
from config import GEMINI_API_KEY, PRAG_BOTTLENECK_PROCENT

# ---------------------------------------------------------------------------
# Initializare model Gemini
# ---------------------------------------------------------------------------

genai.configure(api_key=GEMINI_API_KEY)
_model = genai.GenerativeModel("gemini-flash-latest")

# Jocurile pentru care Gemini va genera estimari
JOCURI_BENCHMARK = [
    "CS2",
    "Valorant",
    "Fortnite",
    "Apex Legends",
    "GTA V",
    "The Witcher 3 (Next-Gen)",
    "Elden Ring",
    "Red Dead Redemption 2",
    "Cyberpunk 2077",
    "Hogwarts Legacy",
    "Alan Wake 2",
    "Battlefield 2042",
    "COD Warzone",
    "Minecraft (BSL Shaders)",
]

# Metadata fixa per joc (categorie, icon, intensitate)
JOCURI_META = {
    "CS2":                        {"categorie": "FPS Competitiv",   "icon": "🎯", "intensitate": "Scazuta"},
    "Valorant":                   {"categorie": "FPS Competitiv",   "icon": "🔫", "intensitate": "Scazuta"},
    "Fortnite":                   {"categorie": "Battle Royale",    "icon": "🏆", "intensitate": "Medie"},
    "Apex Legends":               {"categorie": "Battle Royale",    "icon": "🦅", "intensitate": "Medie"},
    "GTA V":                      {"categorie": "Open World",       "icon": "🚗", "intensitate": "Medie"},
    "The Witcher 3 (Next-Gen)":   {"categorie": "RPG",              "icon": "⚔️", "intensitate": "Ridicata"},
    "Elden Ring":                 {"categorie": "RPG",              "icon": "🗡️", "intensitate": "Medie"},
    "Red Dead Redemption 2":      {"categorie": "Open World",       "icon": "🤠", "intensitate": "Foarte ridicata"},
    "Cyberpunk 2077":             {"categorie": "Open World",       "icon": "🌆", "intensitate": "Extrema"},
    "Hogwarts Legacy":            {"categorie": "RPG",              "icon": "🧙", "intensitate": "Ridicata"},
    "Alan Wake 2":                {"categorie": "Horror",           "icon": "🔦", "intensitate": "Extrema"},
    "Battlefield 2042":           {"categorie": "FPS Multiplayer",  "icon": "💣", "intensitate": "Ridicata"},
    "COD Warzone":                {"categorie": "Battle Royale",    "icon": "🪖", "intensitate": "Medie"},
    "Minecraft (BSL Shaders)":    {"categorie": "Sandbox",          "icon": "⛏️", "intensitate": "Medie"},
}


# ---------------------------------------------------------------------------
# Functia principala
# ---------------------------------------------------------------------------

def ruleaza_benchmark(req: BenchmarkRequest) -> BenchmarkResponse:
    gpu = req.gpu or {}
    cpu = req.cpu or {}

    # Detectam tier-ul GPU pentru context suplimentar trimis catre Gemini
    tier, scor_gpu = detecteaza_tier(gpu)
    scor_cpu = _scor_cpu(cpu)

    # Construim si trimitem prompt-ul catre Gemini
    prompt = _construieste_prompt(req, tier, scor_cpu, scor_gpu)
    date_gemini = _apeleaza_gemini(prompt)

    # Mapam raspunsul Gemini catre schema noastra
    return _construieste_raspuns(date_gemini, req, tier, scor_gpu, scor_cpu, gpu, cpu)


# ---------------------------------------------------------------------------
# Prompt Gemini
# ---------------------------------------------------------------------------

def _construieste_prompt(req: BenchmarkRequest, tier: int, scor_cpu: float, scor_gpu: float) -> str:
    gpu = req.gpu or {}
    cpu = req.cpu or {}
    ram = req.ram or {}

    # Construim descrierea build-ului
    specs = []
    if gpu:
        specs.append(
            f"- GPU: {gpu.get('nume', '?')} | {gpu.get('vram_gb', '?')}GB VRAM "
            f"| TDP {gpu.get('consum_tdp', '?')}W | Tier estimat: {tier}/8 ({get_tier_name(tier)})"
        )
    if cpu:
        specs.append(
            f"- CPU: {cpu.get('nume', '?')} | {cpu.get('nuclee', '?')} nuclee "
            f"@ {cpu.get('frecventa_ghz', '?')}GHz | TDP {cpu.get('consum_tdp', '?')}W"
        )
    if ram:
        specs.append(
            f"- RAM: {ram.get('capacitate_totala_gb', '?')}GB {ram.get('tip_memorie', '?')} "
            f"@ {ram.get('frecventa_mhz', '?')}MHz"
        )

    specs_str = "\n".join(specs) if specs else "Specificatii indisponibile"

    # Calculam daca exista bottleneck CPU
    bottleneck_info = ""
    if scor_cpu > 0 and scor_gpu > 0:
        scor_max = max(scor_cpu, scor_gpu)
        diff_pct = (abs(scor_cpu - scor_gpu) / scor_max) * 100
        if diff_pct >= PRAG_BOTTLENECK_PROCENT and scor_cpu < scor_gpu:
            bottleneck_info = (
                f"\nATENTIE: Exista un bottleneck CPU estimat de ~{diff_pct:.1f}%. "
                f"CPU-ul va limita GPU-ul. Ia in calcul o reducere a FPS-urilor fata de potentialul maxim al GPU-ului."
            )

    jocuri_str = "\n".join(f"- {j}" for j in JOCURI_BENCHMARK)
    rez_dorita = req.rezolutie_dorita or "1080p"

    return f"""Esti un expert in benchmarking hardware PC cu acces la date din surse precum Digital Foundry, TechPowerUp, GamersNexus si Hardware Unboxed.

CONFIGURATIA PC:
{specs_str}{bottleneck_info}

Rezolutie tinta utilizator: {rez_dorita}

SARCINA: Genereaza estimari REALISTE de FPS pentru urmatoarele {len(JOCURI_BENCHMARK)} jocuri:
{jocuri_str}

Bazeaza-te pe benchmark-uri reale si cunostintele tale despre performanta acestui GPU.
FPS-urile trebuie sa fie REALIST calibrate — nu exagera si nu subestima.

Returneaza EXCLUSIV un JSON valid cu urmatoarea structura (fara text suplimentar, fara markdown):

{{
  "gpu_tier": {tier},
  "gpu_tier_name": "{get_tier_name(tier)}",
  "rating_general": "<S|A|B|C|D bazat pe FPS mediu la {rez_dorita} preset High>",
  "recomandare_rezolutie": "<1080p|1440p|4K — rezolutia la care GPU-ul exceleaza>",
  "mesaj_general": "<2-3 propozitii in romana despre performanta gaming a acestui build>",
  "are_bottleneck_cpu": <true|false>,
  "procentaj_bottleneck": <0-100>,
  "mesaj_cpu": "<propozitie in romana despre echilibrul CPU/GPU>",
  "jocuri": [
    {{
      "nume": "<exact ca in lista de mai sus>",
      "fps_1080p": {{"low": <int>, "medium": <int>, "high": <int>, "ultra": <int>}},
      "fps_1440p": {{"low": <int>, "medium": <int>, "high": <int>, "ultra": <int>}},
      "fps_4k":    {{"low": <int>, "medium": <int>, "high": <int>, "ultra": <int>}},
      "preset_optim": "<Low|Medium|High|Ultra — preset recomandat la {rez_dorita}>",
      "rating_joc": "<S|A|B|C|D bazat pe FPS High la {rez_dorita}>"
    }}
  ]
}}

Reguli obligatorii:
1. Genereaza EXACT {len(JOCURI_BENCHMARK)} jocuri in ordinea din lista
2. FPS Low > Medium > High > Ultra pentru fiecare rezolutie
3. FPS 1080p > 1440p > 4K pentru fiecare preset
4. Rating: S=144+fps, A=90-143fps, B=60-89fps, C=30-59fps, D=sub30fps (la High preset, rezolutia tinta)
5. JSON valid, fara comentarii, fara cod markdown"""


# ---------------------------------------------------------------------------
# Apel Gemini + parsare JSON
# ---------------------------------------------------------------------------

def _apeleaza_gemini(prompt: str) -> dict:
    try:
        response = _model.generate_content(prompt)
        text = response.text.strip()

        # Stergem eventualele blocuri markdown ```json ... ```
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

        return json.loads(text)

    except json.JSONDecodeError as e:
        raise ValueError(f"Gemini nu a returnat JSON valid: {e}")
    except Exception as e:
        raise ValueError(f"Eroare la apelul Gemini: {e}")


# ---------------------------------------------------------------------------
# Mapare raspuns Gemini -> schema BenchmarkResponse
# ---------------------------------------------------------------------------

def _construieste_raspuns(
    date: dict,
    req: BenchmarkRequest,
    tier: int,
    scor_gpu: float,
    scor_cpu: float,
    gpu: dict,
    cpu: dict,
) -> BenchmarkResponse:

    # GpuInfo
    gpu_info = GpuInfo(
        nume_gpu  = gpu.get("nume", "GPU Necunoscut"),
        tier      = date.get("gpu_tier", tier),
        nume_tier = date.get("gpu_tier_name", get_tier_name(tier)),
        scor_gpu  = round(scor_gpu, 1),
        vram_gb   = int(gpu.get("vram_gb", 0)),
    )

    # CpuImpact
    reducere = 0.0
    are_bt   = date.get("are_bottleneck_cpu", False)
    diff_pct = float(date.get("procentaj_bottleneck", 0))
    if are_bt:
        reducere = min(diff_pct * 0.35, 35.0)

    cpu_impact = CpuImpact(
        are_bottleneck     = are_bt,
        procentaj_reducere = round(reducere, 1),
        scor_cpu           = round(scor_cpu, 1) if scor_cpu else None,
        scor_gpu           = round(scor_gpu, 1),
        mesaj              = date.get("mesaj_cpu", ""),
    )

    # GameResults
    rezultate: list[GameResult] = []
    rez_dorita = req.rezolutie_dorita or "1080p"

    for joc_raw in date.get("jocuri", []):
        nume = joc_raw.get("nume", "")
        meta = JOCURI_META.get(nume, {"categorie": "Altele", "icon": "🎮", "intensitate": "Medie"})

        fps_1080p = _parse_fps(joc_raw.get("fps_1080p", {}))
        fps_1440p = _parse_fps(joc_raw.get("fps_1440p", {}))
        fps_4k    = _parse_fps(joc_raw.get("fps_4k", {}))

        rezultate.append(GameResult(
            nume         = nume,
            categorie    = meta["categorie"],
            icon         = meta["icon"],
            intensitate  = meta["intensitate"],
            fps_1080p    = fps_1080p,
            fps_1440p    = fps_1440p,
            fps_4k       = fps_4k,
            preset_optim = joc_raw.get("preset_optim", "High"),
            rating_joc   = joc_raw.get("rating_joc", "B"),
        ))

    # Statistici agregate
    fps_mediu_1080p = _fps_mediu(rezultate, "1080p")
    fps_mediu_1440p = _fps_mediu(rezultate, "1440p")
    fps_mediu_4k    = _fps_mediu(rezultate, "4k")

    return BenchmarkResponse(
        gpu_info                 = gpu_info,
        cpu_impact               = cpu_impact,
        rezultate_jocuri         = rezultate,
        rating_general           = date.get("rating_general", "B"),
        rezolutie_dorita         = rez_dorita,
        fps_mediu_1080p          = fps_mediu_1080p,
        fps_mediu_1440p          = fps_mediu_1440p,
        fps_mediu_4k             = fps_mediu_4k,
        jocuri_peste_60fps_1080p = _jocuri_peste_60(rezultate, "1080p"),
        jocuri_peste_60fps_1440p = _jocuri_peste_60(rezultate, "1440p"),
        jocuri_peste_60fps_4k    = _jocuri_peste_60(rezultate, "4k"),
        recomandare_rezolutie    = date.get("recomandare_rezolutie", "1080p"),
        mesaj_general            = date.get("mesaj_general", ""),
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_fps(raw: dict) -> FpsPreset:
    return FpsPreset(
        low    = float(raw.get("low",    0)),
        medium = float(raw.get("medium", 0)),
        high   = float(raw.get("high",   0)),
        ultra  = float(raw.get("ultra",  0)),
    )


def _scor_cpu(cpu: dict) -> float:
    if not cpu:
        return 0.0
    try:
        nuclee    = int(cpu.get("nuclee", 4))
        threaduri = int(cpu.get("threaduri", nuclee))
        frecventa = float(cpu.get("frecventa_ghz", 3.0))
        scor = nuclee * frecventa * 10
        if threaduri > nuclee:
            scor *= 1.15
        return round(scor, 1)
    except (ValueError, TypeError):
        return 0.0


def _fps_mediu(rezultate: list[GameResult], rez: str) -> float:
    if not rezultate:
        return 0.0
    vals = []
    for r in rezultate:
        fps_obj = {"1080p": r.fps_1080p, "1440p": r.fps_1440p, "4k": r.fps_4k}.get(rez, r.fps_1080p)
        vals.append(fps_obj.high)
    return round(sum(vals) / len(vals), 1)


def _jocuri_peste_60(rezultate: list[GameResult], rez: str) -> int:
    count = 0
    for r in rezultate:
        fps_obj = {"1080p": r.fps_1080p, "1440p": r.fps_1440p, "4k": r.fps_4k}.get(rez, r.fps_1080p)
        if fps_obj.high >= 60:
            count += 1
    return count
