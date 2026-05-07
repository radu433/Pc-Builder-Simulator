"""
Mapare GPU real -> Tier (1-8) prin keyword matching pe numele GPU.

Tier 1 — Entry Level  : GT 1030, RX 550, Arc A380
Tier 2 — Budget       : GTX 1650, RX 6500 XT, Arc A580
Tier 3 — Mid-Low      : GTX 1660 Super, RX 6600, RTX 3060
Tier 4 — Mid          : RTX 3060 Ti, RX 6700 XT, RTX 4060
Tier 5 — Mid-High     : RTX 3070, RX 6800 XT, RTX 4060 Ti, RTX 4070
Tier 6 — High         : RTX 3080, RX 6900 XT, RTX 4070 Ti, RTX 4070 Super
Tier 7 — Ultra        : RTX 3090, RTX 4080, RX 7900 XTX, RTX 4070 Ti Super
Tier 8 — Flagship     : RTX 4090
"""

from typing import Tuple


# ---------------------------------------------------------------------------
# Definitia tier-urilor GPU
# ---------------------------------------------------------------------------

TIER_NAMES = {
    1: "Entry Level",
    2: "Budget",
    3: "Mid-Low",
    4: "Mid",
    5: "Mid-High",
    6: "High",
    7: "Ultra",
    8: "Flagship",
}

# Scorul GPU de baza per tier (folosit si pentru calculul bottleneck)
# Reflecta puterea relativa de procesare grafica
TIER_SCORE = {
    1: 80.0,
    2: 150.0,
    3: 250.0,
    4: 380.0,
    5: 530.0,
    6: 700.0,
    7: 900.0,
    8: 1200.0,
}

# ---------------------------------------------------------------------------
# Reguli de detectie — ordonate de la mai specific la mai general
# Fiecare regula e un tuplu: (keyword_list, tier)
# Se evalueaza in ordine; prima regula care se potriveste castiga.
# ---------------------------------------------------------------------------

_RULES: list[Tuple[list[str], int]] = [

    # ── Tier 8: Flagship ────────────────────────────────────────────────────
    (["rtx 4090"],                          8),

    # ── Tier 7: Ultra ───────────────────────────────────────────────────────
    (["rtx 4080 super"],                    7),
    (["rtx 4080"],                          7),
    (["rtx 4070 ti super"],                 7),
    (["rtx 3090 ti"],                       7),
    (["rtx 3090"],                          7),
    (["rx 7900 xtx"],                       7),
    (["rx 7900 xt"],                        7),

    # ── Tier 6: High ────────────────────────────────────────────────────────
    (["rtx 4070 super"],                    6),
    (["rtx 4070 ti"],                       6),
    (["rtx 3080 ti"],                       6),
    (["rtx 3080 12gb"],                     6),
    (["rtx 3080"],                          6),
    (["rx 6900 xt"],                        6),
    (["rx 7800 xt"],                        6),
    (["rx 6950 xt"],                        6),
    (["rx 7900 gre"],                       6),

    # ── Tier 5: Mid-High ────────────────────────────────────────────────────
    (["rtx 4070"],                          5),
    (["rtx 4060 ti 16gb"],                  5),
    (["rtx 4060 ti"],                       5),
    (["rtx 3070 ti"],                       5),
    (["rtx 3070"],                          5),
    (["rx 6800 xt"],                        5),
    (["rx 6800"],                           5),
    (["rx 7700 xt"],                        5),
    (["arc a770"],                          5),

    # ── Tier 4: Mid ─────────────────────────────────────────────────────────
    (["rtx 4060"],                          4),
    (["rtx 3060 ti"],                       4),
    (["rx 6700 xt"],                        4),
    (["rx 6700"],                           4),
    (["rx 7600"],                           4),
    (["arc a750"],                          4),
    (["rtx 2070 super"],                    4),
    (["rtx 2080"],                          4),

    # ── Tier 3: Mid-Low ─────────────────────────────────────────────────────
    (["rtx 3060"],                          3),
    (["rtx 2060 super"],                    3),
    (["rtx 2070"],                          3),
    (["rx 6600 xt"],                        3),
    (["rx 6600"],                           3),
    (["rx 5700 xt"],                        3),
    (["rx 5700"],                           3),
    (["gtx 1660 super"],                    3),
    (["gtx 1660 ti"],                       3),
    (["gtx 1660"],                          3),
    (["arc a580"],                          3),

    # ── Tier 2: Budget ──────────────────────────────────────────────────────
    (["rtx 2060"],                          2),
    (["rtx 3050"],                          2),
    (["rtx 4050"],                          2),
    (["rx 6500 xt"],                        2),
    (["rx 5500 xt"],                        2),
    (["rx 580"],                            2),
    (["rx 570"],                            2),
    (["gtx 1650 super"],                    2),
    (["gtx 1650"],                          2),
    (["gtx 1060"],                          2),
    (["arc a380"],                          2),

    # ── Tier 1: Entry Level ─────────────────────────────────────────────────
    (["gt 1030"],                           1),
    (["rx 550"],                            1),
    (["rx 560"],                            1),
    (["gtx 1050 ti"],                       1),
    (["gtx 1050"],                          1),
    (["arc a310"],                          1),
]


# ---------------------------------------------------------------------------
# Functia principala de detectie
# ---------------------------------------------------------------------------

def detecteaza_tier(gpu: dict) -> Tuple[int, float]:
    """
    Primeste dict-ul unui GPU din Django si returneaza (tier, scor_gpu).
    Daca GPU-ul nu poate fi detectat, returneaza (3, 250.0) — tier Mid-Low
    ca valoare sigura de fallback.
    """
    if not gpu:
        return 3, TIER_SCORE[3]

    # Construim un string de cautare combinand toate campurile relevante
    camp_cautare = " ".join([
        str(gpu.get("nume", "")),
        str(gpu.get("serie", "")),
        str(gpu.get("model_chipset", "")),
        str(gpu.get("brand", "")),
    ]).lower()

    for keywords, tier in _RULES:
        if all(kw in camp_cautare for kw in keywords):
            return tier, TIER_SCORE[tier]

    # Fallback: incercam sa estimam din VRAM si TDP
    tier = _estimeaza_din_specs(gpu)
    return tier, TIER_SCORE[tier]


def get_tier_name(tier: int) -> str:
    """Returneaza numele unui tier."""
    return TIER_NAMES.get(tier, "Unknown")


# ---------------------------------------------------------------------------
# Helper: estimare tier din specificatii tehnice (fallback)
# ---------------------------------------------------------------------------

def _estimeaza_din_specs(gpu: dict) -> int:
    """
    Estimare bruta a tier-ului din VRAM si TDP cand nu putem identifica modelul.
    """
    try:
        vram = int(gpu.get("vram_gb", 4))
        tdp  = int(gpu.get("consum_tdp", 100))
    except (ValueError, TypeError):
        return 3

    scor = vram * 15 + tdp * 0.8

    if scor >= 1000:  return 8
    if scor >= 750:   return 7
    if scor >= 580:   return 6
    if scor >= 440:   return 5
    if scor >= 310:   return 4
    if scor >= 200:   return 3
    if scor >= 130:   return 2
    return 1
