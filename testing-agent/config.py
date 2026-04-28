import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
DJANGO_BASE_URL: str = os.getenv("DJANGO_BASE_URL", "http://localhost:8000/api")
PORT: int = int(os.getenv("AGENT_PORT", "8002"))

PRAG_BOTTLENECK_PROCENT: float = 15.0
MARJA_PSU: float = 1.25
MAX_SUGESTII: int = 3