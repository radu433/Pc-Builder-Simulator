"""
Scheme Pydantic pentru request/response-urile Testing Agent-ului.
Structura componentelor reflecta modelele Django din backend.
"""

from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class BuildRequest(BaseModel):
    """
    Configuratia curenta a utilizatorului.
    Toate campurile sunt Optional — build-ul poate fi partial.
    """
    cpu:         Optional[Dict[str, Any]] = None
    gpu:         Optional[Dict[str, Any]] = None
    motherboard: Optional[Dict[str, Any]] = None
    ram:         Optional[Dict[str, Any]] = None
    psu:         Optional[Dict[str, Any]] = None
    case:        Optional[Dict[str, Any]] = None
    cooler:      Optional[Dict[str, Any]] = None
    storage:     Optional[Dict[str, Any]] = None

    # Preferintele utilizatorului (din UserProfile Django)
    buget_max:        Optional[float] = None
    rezolutie_dorita: Optional[str] = None        # '1080p', '1440p', '4K'
    jocuri_preferate: Optional[List[str]] = []
    locatie:          Optional[str] = "Romania"


class AgentResponse(BaseModel):
    compatibil:  bool
    severitate:  str                                   # 'ok' | 'warning' | 'error'
    probleme:    List[str]                             # mesaje de eroare compatibilitate
    bottleneck:  Dict[str, Any]                        # rezultatul calculului bottleneck
    sugestii:    Dict[str, List[Dict[str, Any]]]       # {'cpu': [...], 'gpu': [...], ...}
    analiza_ai:  str                                   # textul generat de Claude