import os
from dotenv import load_dotenv

load_dotenv()

PORT: int             = int(os.getenv("AGENT_PORT", "8003"))
GEMINI_API_KEY: str   = os.getenv("GEMINI_API_KEY", "")
PRAG_BOTTLENECK_PROCENT: float = 15.0
