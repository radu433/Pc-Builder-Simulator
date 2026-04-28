"""
Obtine sugestii alternative din baza de date Django.

Logica per caz:
  - CPU bottleneck  -> CPU-uri cu mai multe nuclee, acelasi socket
  - GPU bottleneck  -> GPU-uri cu mai mult VRAM, incape in carcasa
  - Socket gresit   -> Placi de baza cu socketul CPU-ului
  - RAM tip gresit  -> RAM de tipul suportat de MB
  - PSU insuficient -> PSU-uri cu putere suficienta
  - GPU nu incape   -> Carcase cu spatiu suficient
"""

import httpx
from typing import Dict, List, Any
from core.schemas import BuildRequest
from config import MAX_SUGESTII


async def obtine_sugestii(
    build: BuildRequest,
    probleme: List[str],
    bottleneck: Dict[str, Any],
    http: httpx.AsyncClient,
    django_url: str,
) -> Dict[str, List[Dict[str, Any]]]:

    sugestii: Dict[str, List[Dict[str, Any]]] = {}

    # CPU bottleneck
    if bottleneck.get("are_bottleneck") and bottleneck.get("componenta_limitatoare") == "CPU":
        cpus = await _fetch(http, f"{django_url}/cpus/")
        if cpus and build.cpu:
            nuclee_min = int(build.cpu.get("nuclee", 0)) + 1
            socket     = str(build.cpu.get("socket", "")).upper()
            candidati  = [
                c for c in cpus
                if int(c.get("nuclee", 0)) >= nuclee_min
                and str(c.get("socket", "")).upper() == socket
                and _in_buget(c, build.buget_max, build.cpu.get("pret"))
            ]
            sugestii["cpu"] = sorted(candidati, key=lambda c: float(c.get("pret") or 9999))[:MAX_SUGESTII]

    # GPU bottleneck
    if bottleneck.get("are_bottleneck") and bottleneck.get("componenta_limitatoare") == "GPU":
        gpus = await _fetch(http, f"{django_url}/gpus/")
        if gpus and build.gpu:
            vram_min  = int(build.gpu.get("vram_gb", 0)) + 1
            candidati = [
                g for g in gpus
                if int(g.get("vram_gb", 0)) >= vram_min
                and _gpu_incape(g, build)
                and _in_buget(g, build.buget_max, build.gpu.get("pret"))
            ]
            sugestii["gpu"] = sorted(candidati, key=lambda g: float(g.get("pret") or 9999))[:MAX_SUGESTII]

    # Socket incompatibil -> sugeram placi de baza
    if _are_problema(probleme, "socket") and build.cpu:
        mbs = await _fetch(http, f"{django_url}/motherboards/")
        if mbs:
            socket    = str(build.cpu.get("socket", "")).upper()
            candidati = [
                m for m in mbs
                if str(m.get("socket", "")).upper() == socket
                and _in_buget(m, build.buget_max, build.motherboard.get("pret") if build.motherboard else None)
            ]
            sugestii["motherboard"] = sorted(candidati, key=lambda m: float(m.get("pret") or 9999))[:MAX_SUGESTII]

    # RAM tip incompatibil -> sugeram RAM corect
    if _are_problema(probleme, "RAM") and build.motherboard:
        rams = await _fetch(http, f"{django_url}/rams/")
        if rams:
            tip       = str(build.motherboard.get("tip_memorie", "")).upper()
            candidati = [
                r for r in rams
                if str(r.get("tip_memorie", "")).upper() == tip
                and _in_buget(r, build.buget_max, build.ram.get("pret") if build.ram else None)
            ]
            sugestii["ram"] = sorted(candidati, key=lambda r: float(r.get("pret") or 9999))[:MAX_SUGESTII]

    # PSU insuficient -> sugeram PSU mai puternic
    if _are_problema(probleme, "PSU") and build.psu:
        putere_min = (bottleneck.get("tdp_total_w") or 0) * 1.25
        psus       = await _fetch(http, f"{django_url}/psus/")
        if psus:
            candidati = [
                p for p in psus
                if int(p.get("putere_w") or 0) >= putere_min
                and _in_buget(p, build.buget_max, build.psu.get("pret"))
            ]
            sugestii["psu"] = sorted(candidati, key=lambda p: float(p.get("pret") or 9999))[:MAX_SUGESTII]

    # GPU nu incape -> sugeram carcase mai mari
    if _are_problema(probleme, "incape") and build.gpu:
        lungime_gpu = int(build.gpu.get("lungime_mm") or 0)
        cases       = await _fetch(http, f"{django_url}/cases/")
        if cases:
            candidati = [
                c for c in cases
                if int(c.get("lungime_max_gpu_mm") or 0) >= lungime_gpu
                and _in_buget(c, build.buget_max, build.case.get("pret") if build.case else None)
            ]
            sugestii["case"] = sorted(candidati, key=lambda c: float(c.get("pret") or 9999))[:MAX_SUGESTII]

    return sugestii


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _fetch(http: httpx.AsyncClient, url: str) -> List[Dict[str, Any]]:
    try:
        r = await http.get(url, timeout=5.0)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "results" in data:
            return data["results"]
        return []
    except Exception:
        return []


def _in_buget(comp: Dict, buget_max: float | None, pret_curent: float | None) -> bool:
    pret = comp.get("pret")
    if pret is None:
        return True
    pret = float(pret)
    if buget_max and pret <= buget_max:
        return True
    if pret_curent and pret <= float(pret_curent) * 1.3:
        return True
    return False


def _are_problema(probleme: List[str], cuvant: str) -> bool:
    return any(cuvant.lower() in p.lower() for p in probleme)


def _gpu_incape(gpu: Dict, build: BuildRequest) -> bool:
    if not build.case or not build.case.get("lungime_max_gpu_mm"):
        return True
    return int(gpu.get("lungime_mm") or 0) <= int(build.case["lungime_max_gpu_mm"])