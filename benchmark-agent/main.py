"""
Benchmark Agent — port 8003
POST /benchmark  →  returneaza FPS-uri estimate pentru 14 jocuri populare
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from core.schemas import BenchmarkRequest, BenchmarkResponse
from core.benchmark_engine import ruleaza_benchmark

app = FastAPI(
    title="PC Builder — Benchmark Agent",
    description="Estimeaza FPS-uri pentru jocuri populare pe baza configuratiei PC selectate.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "service": "benchmark-agent", "port": 8003}


@app.post("/benchmark", response_model=BenchmarkResponse)
def benchmark(build: BenchmarkRequest):
    """
    Primeste configuratia PC-ului si returneaza benchmark-ul estimat.

    Cel putin campul `gpu` trebuie sa fie prezent.
    Daca `cpu` lipseste, impactul CPU nu este calculat.
    """
    if not build.gpu:
        raise HTTPException(
            status_code=422,
            detail="Campul 'gpu' este obligatoriu pentru a rula benchmark-ul.",
        )
    try:
        return ruleaza_benchmark(build)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Eroare neasteptata: {type(e).__name__}: {e}")
