"""
Scheme Pydantic pentru request/response-urile Benchmark Agent-ului.
"""

from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class BenchmarkRequest(BaseModel):
    """
    Configuratia PC-ului trimisa de frontend.
    Campurile sunt Optional — benchmark-ul se calculeaza cu ce exista.
    Cel putin gpu trebuie sa fie prezent pentru a obtine rezultate.
    """
    cpu:         Optional[Dict[str, Any]] = None
    gpu:         Optional[Dict[str, Any]] = None
    ram:         Optional[Dict[str, Any]] = None
    motherboard: Optional[Dict[str, Any]] = None
    psu:         Optional[Dict[str, Any]] = None
    case:        Optional[Dict[str, Any]] = None
    cooler:      Optional[Dict[str, Any]] = None
    storage:     Optional[Dict[str, Any]] = None

    # Preferintele utilizatorului
    rezolutie_dorita:  Optional[str] = "1080p"   # '1080p', '1440p', '4K'
    jocuri_preferate:  Optional[List[str]] = []
    buget_max:         Optional[float] = None
    locatie:           Optional[str] = "Romania"


class FpsPreset(BaseModel):
    """FPS-urile pentru un joc la o rezolutie data, pe toate preset-urile."""
    low:   float
    medium: float
    high:  float
    ultra: float


class GameResult(BaseModel):
    """Rezultatul benchmark-ului pentru un singur joc."""
    nume:          str          # ex: "Cyberpunk 2077"
    categorie:     str          # ex: "Open World", "FPS Competitiv"
    icon:          str          # emoji reprezentativ
    intensitate:   str          # "Scazuta", "Medie", "Ridicata", "Extrema"
    fps_1080p:     FpsPreset
    fps_1440p:     FpsPreset
    fps_4k:        FpsPreset
    preset_optim:  str          # preset-ul recomandat la rezolutia dorita
    rating_joc:    str          # 'S', 'A', 'B', 'C', 'D' la rezolutia dorita


class CpuImpact(BaseModel):
    """Informatii despre impactul CPU-ului asupra benchmark-ului."""
    are_bottleneck:       bool
    procentaj_reducere:   float   # % cu care FPS-urile sunt reduse
    scor_cpu:             Optional[float] = None
    scor_gpu:             Optional[float] = None
    mesaj:                str


class GpuInfo(BaseModel):
    """Informatii despre GPU-ul detectat."""
    nume_gpu:     str
    tier:         int            # 1-8
    nume_tier:    str            # ex: "Mid-High"
    scor_gpu:     float
    vram_gb:      int


class BenchmarkResponse(BaseModel):
    """Raspunsul complet al agentului de benchmark."""
    gpu_info:          GpuInfo
    cpu_impact:        CpuImpact
    rezultate_jocuri:  List[GameResult]
    rating_general:    str          # 'S', 'A', 'B', 'C', 'D'
    rezolutie_dorita:  str
    fps_mediu_1080p:   float        # media FPS la High preset
    fps_mediu_1440p:   float
    fps_mediu_4k:      float
    jocuri_peste_60fps_1080p: int   # numar jocuri playable la 1080p High
    jocuri_peste_60fps_1440p: int
    jocuri_peste_60fps_4k:    int
    recomandare_rezolutie:    str   # rezolutia recomandata pt acest build
    mesaj_general:            str   # mesaj sumar despre performanta
