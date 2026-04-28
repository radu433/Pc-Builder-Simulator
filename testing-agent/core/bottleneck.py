"""
Calcul bottleneck CPU/GPU bazat pe scoruri de performanta aproximative.

scor_cpu = nuclee * frecventa_ghz * 10  (* 1.15 daca are SMT)
scor_gpu = vram_gb * 15 + consum_tdp * 0.8

Daca diferenta dintre cele doua scoruri depaseste PRAG_BOTTLENECK_PROCENT,
componenta mai slaba e declarata "limitatoare".
"""

from typing import Dict, Any
from core.schemas import BuildRequest
from config import PRAG_BOTTLENECK_PROCENT, MARJA_PSU


def calculeaza_bottleneck(build: BuildRequest) -> Dict[str, Any]:
    rez: Dict[str, Any] = {
        "are_bottleneck":        False,
        "procentaj_bottleneck":  0.0,
        "componenta_limitatoare": None,
        "componenta_limitata":    None,
        "tdp_total_w":           None,
        "psu_suficient":         None,
        "scor_cpu":              None,
        "scor_gpu":              None,
    }

    if not build.cpu or not build.gpu:
        return rez

    scor_cpu = _scor_cpu(build.cpu)
    scor_gpu = _scor_gpu(build.gpu)
    rez["scor_cpu"] = round(scor_cpu, 1)
    rez["scor_gpu"] = round(scor_gpu, 1)

    scor_max = max(scor_cpu, scor_gpu)
    if scor_max == 0:
        return rez

    procentaj = (abs(scor_cpu - scor_gpu) / scor_max) * 100
    rez["procentaj_bottleneck"] = round(procentaj, 1)

    if procentaj >= PRAG_BOTTLENECK_PROCENT:
        rez["are_bottleneck"] = True
        if scor_cpu < scor_gpu:
            rez["componenta_limitatoare"] = "CPU"
            rez["componenta_limitata"]    = "GPU"
        else:
            rez["componenta_limitatoare"] = "GPU"
            rez["componenta_limitata"]    = "CPU"

    # TDP total + verificare PSU
    tdp = _tdp_total(build)
    rez["tdp_total_w"] = tdp
    if build.psu and build.psu.get("putere_w") and tdp:
        rez["psu_suficient"] = int(build.psu["putere_w"]) >= tdp * MARJA_PSU

    return rez


# ---------------------------------------------------------------------------
# Scoruri aproximative
# ---------------------------------------------------------------------------

def _scor_cpu(cpu: Dict[str, Any]) -> float:
    nuclee    = _int(cpu.get("nuclee"), 4)
    threaduri = _int(cpu.get("threaduri"), nuclee)
    frecventa = _float(cpu.get("frecventa_ghz"), 3.0)
    scor = nuclee * frecventa * 10
    if threaduri > nuclee:
        scor *= 1.15      # bonus SMT / Hyper-Threading
    return scor


def _scor_gpu(gpu: Dict[str, Any]) -> float:
    vram = _int(gpu.get("vram_gb"), 4)
    tdp  = _int(gpu.get("consum_tdp"), 100)
    return vram * 15 + tdp * 0.8


def _tdp_total(build: BuildRequest) -> int:
    total = 0
    if build.cpu and build.cpu.get("consum_tdp"):
        total += _int(build.cpu["consum_tdp"])
    if build.gpu and build.gpu.get("consum_tdp"):
        total += _int(build.gpu["consum_tdp"])
    return total + 50 if total else 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _int(val: Any, default: int = 0) -> int:
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def _float(val: Any, default: float = 0.0) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return default