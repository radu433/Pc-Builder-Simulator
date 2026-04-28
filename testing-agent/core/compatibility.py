"""
Verificare compatibilitate hardware — reguli pur logice, fara AI.

Reguli implementate:
  1. CPU <-> Motherboard : socket match
  2. RAM <-> Motherboard : tip memorie (DDR4 / DDR5)
  3. RAM <-> Motherboard : capacitate totala <= capacitate_max_ram_gb
  4. GPU <-> Case        : lungimea GPU incape in carcasa
  5. Cooler <-> CPU      : socket CPU in lista socket_suportate cooler
  6. Cooler <-> Case     : inaltimea cooler <= inaltimea maxima carcasa
  7. PSU                 : putere suficienta pentru TDP total estimat
"""

from typing import List
from core.schemas import BuildRequest
from config import MARJA_PSU


def verifica_compatibilitate(build: BuildRequest) -> List[str]:
    """Returneaza lista de mesaje de eroare. Lista goala = build compatibil."""
    probleme = []
    probleme += _socket_cpu_mb(build)
    probleme += _ram_tip(build)
    probleme += _ram_capacitate(build)
    probleme += _gpu_case(build)
    probleme += _cooler_socket(build)
    probleme += _cooler_inaltime(build)
    probleme += _psu(build)
    return probleme


# ---------------------------------------------------------------------------
# Reguli individuale
# ---------------------------------------------------------------------------

def _socket_cpu_mb(build: BuildRequest) -> List[str]:
    if not build.cpu or not build.motherboard:
        return []
    socket_cpu = str(build.cpu.get("socket") or "").strip().upper()
    socket_mb  = str(build.motherboard.get("socket") or "").strip().upper()
    if socket_cpu and socket_mb and socket_cpu != socket_mb:
        return [f"Incompatibilitate socket: CPU foloseste {socket_cpu}, "
                f"placa de baza are {socket_mb}."]
    return []


def _ram_tip(build: BuildRequest) -> List[str]:
    if not build.ram or not build.motherboard:
        return []
    tip_ram = str(build.ram.get("tip_memorie") or "").strip().upper()
    tip_mb  = str(build.motherboard.get("tip_memorie") or "").strip().upper()
    if tip_ram and tip_mb and tip_ram != tip_mb:
        return [f"Incompatibilitate RAM: modulele sunt {tip_ram}, "
                f"placa de baza suporta {tip_mb}."]
    return []


def _ram_capacitate(build: BuildRequest) -> List[str]:
    if not build.ram or not build.motherboard:
        return []
    try:
        cap_ram = int(build.ram.get("capacitate_totala_gb") or 0)
        cap_max = int(build.motherboard.get("capacitate_max_ram_gb") or 0)
    except (ValueError, TypeError):
        return []
    if cap_ram and cap_max and cap_ram > cap_max:
        return [f"RAM depaseste limita placii de baza: ai {cap_ram}GB, "
                f"maxim suportat {cap_max}GB."]
    return []


def _gpu_case(build: BuildRequest) -> List[str]:
    if not build.gpu or not build.case:
        return []
    try:
        lungime_gpu = int(build.gpu.get("lungime_mm") or 0)
        lungime_max = int(build.case.get("lungime_max_gpu_mm") or 0)
    except (ValueError, TypeError):
        return []
    if lungime_gpu and lungime_max and lungime_gpu > lungime_max:
        return [f"GPU-ul nu incape in carcasa: GPU {lungime_gpu}mm, "
                f"carcasa permite maxim {lungime_max}mm."]
    return []


def _cooler_socket(build: BuildRequest) -> List[str]:
    if not build.cooler or not build.cpu:
        return []
    socket_cpu = str(build.cpu.get("socket") or "").strip().upper()
    suportate  = [str(s).strip().upper() for s in (build.cooler.get("socket_suportate") or [])]
    if socket_cpu and suportate and socket_cpu not in suportate:
        return [f"Cooler-ul nu suporta socket-ul {socket_cpu}. "
                f"Compatibil cu: {', '.join(suportate)}."]
    return []


def _cooler_inaltime(build: BuildRequest) -> List[str]:
    if not build.cooler or not build.case:
        return []
    tip = str(build.cooler.get("tip_racire") or "").lower()
    if "aio" in tip or "lichid" in tip:
        return []
    try:
        inaltime_cooler = int(build.cooler.get("inaltime_mm") or 0)
        inaltime_max    = int(build.case.get("inaltime_max_cooler_mm") or 0)
    except (ValueError, TypeError):
        return []
    if inaltime_cooler and inaltime_max and inaltime_cooler > inaltime_max:
        return [f"Cooler-ul nu incape in carcasa: cooler {inaltime_cooler}mm, "
                f"carcasa permite maxim {inaltime_max}mm."]
    return []


def _psu(build: BuildRequest) -> List[str]:
    if not build.psu:
        return []
    tdp_total = _tdp_total(build)
    if not tdp_total:
        return []
    try:
        putere_psu = int(build.psu.get("putere_w") or 0)
    except (ValueError, TypeError):
        return []
    recomandat = int(tdp_total * MARJA_PSU)
    if putere_psu and putere_psu < recomandat:
        return [f"PSU posibil insuficient: TDP estimat ~{tdp_total}W, "
                f"recomandam minim {recomandat}W. PSU selectat: {putere_psu}W."]
    return []


def _tdp_total(build: BuildRequest) -> int:
    total = 0
    try:
        if build.cpu and build.cpu.get("consum_tdp"):
            total += int(build.cpu["consum_tdp"])
        if build.gpu and build.gpu.get("consum_tdp"):
            total += int(build.gpu["consum_tdp"])
    except (ValueError, TypeError):
        pass
    return total + 50 if total else 0   # +50W pentru MB, RAM, storage, fans