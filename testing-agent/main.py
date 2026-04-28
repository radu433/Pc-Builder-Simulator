"""
PC Builder — Testing Agent  |  port 8002
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import httpx
import google.generativeai as genai

from config import GEMINI_API_KEY, DJANGO_BASE_URL
from core.schemas import BuildRequest, AgentResponse
from core.compatibility import verifica_compatibilitate
from core.bottleneck import calculeaza_bottleneck
from core.suggestions import obtine_sugestii

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-flash-latest")

app = FastAPI(
    title="PC Builder — Testing Agent",
    description="Compatibilitate, bottleneck si sugestii componente",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "service": "testing-agent", "port": 8002}


@app.post("/analizeaza-build", response_model=AgentResponse)
async def analizeaza_build(build: BuildRequest):
    probleme   = verifica_compatibilitate(build)
    bottleneck = calculeaza_bottleneck(build)

    sugestii = {}
    if probleme or bottleneck.get("are_bottleneck"):
        async with httpx.AsyncClient() as http:
            sugestii = await obtine_sugestii(build, probleme, bottleneck, http, DJANGO_BASE_URL)

    analiza_ai = _genereaza_analiza(build, probleme, bottleneck, sugestii)
    severitate = _severitate(probleme, bottleneck)

    return AgentResponse(
        compatibil=len(probleme) == 0,
        severitate=severitate,
        probleme=probleme,
        bottleneck=bottleneck,
        sugestii=sugestii,
        analiza_ai=analiza_ai,
    )


def _genereaza_analiza(build, probleme, bottleneck, sugestii) -> str:
    prompt = _construieste_prompt(build, probleme, bottleneck, sugestii)
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Analiza AI indisponibila momentan: {e}"


def _construieste_prompt(build, probleme, bottleneck, sugestii) -> str:
    comp = []
    if build.cpu:
        comp.append(f"- CPU: {build.cpu.get('nume','?')} | socket {build.cpu.get('socket','?')} | "
                    f"{build.cpu.get('nuclee','?')} nuclee @ {build.cpu.get('frecventa_ghz','?')}GHz | "
                    f"TDP {build.cpu.get('consum_tdp','?')}W")
    if build.gpu:
        comp.append(f"- GPU: {build.gpu.get('nume','?')} | {build.gpu.get('vram_gb','?')}GB VRAM | "
                    f"TDP {build.gpu.get('consum_tdp','?')}W | lungime {build.gpu.get('lungime_mm','?')}mm")
    if build.motherboard:
        comp.append(f"- Motherboard: {build.motherboard.get('nume','?')} | "
                    f"socket {build.motherboard.get('socket','?')} | {build.motherboard.get('tip_memorie','?')}")
    if build.ram:
        comp.append(f"- RAM: {build.ram.get('nume','?')} | "
                    f"{build.ram.get('capacitate_totala_gb','?')}GB {build.ram.get('tip_memorie','?')} "
                    f"@ {build.ram.get('frecventa_mhz','?')}MHz")
    if build.psu:
        comp.append(f"- PSU: {build.psu.get('nume','?')} | {build.psu.get('putere_w','?')}W")
    if build.case:
        comp.append(f"- Carcasa: {build.case.get('nume','?')} | max GPU {build.case.get('lungime_max_gpu_mm','?')}mm")
    if build.cooler:
        comp.append(f"- Cooler: {build.cooler.get('nume','?')} | {build.cooler.get('tip_racire','?')}")
    if build.storage:
        comp.append(f"- Storage: {build.storage.get('nume','?')} | "
                    f"{build.storage.get('capacitate_gb','?')}GB {build.storage.get('tip','?')}")

    prob_str = "\n".join(f"- {p}" for p in probleme) if probleme else "Nicio problema."

    if bottleneck.get("are_bottleneck"):
        bt_str = (f"DA — {bottleneck['componenta_limitatoare']} limiteaza "
                  f"{bottleneck['componenta_limitata']} cu {bottleneck['procentaj_bottleneck']}%")
    else:
        bt_str = f"Nu (diferenta: {bottleneck.get('procentaj_bottleneck', 0)}%)"

    sug_str = "Nu sunt necesare." if not sugestii else "\n".join(
        f"- {tip.upper()}: " + ", ".join(
            f"{p.get('nume','?')} ({p.get('pret','?')} RON)" for p in lista[:3]
        )
        for tip, lista in sugestii.items() if lista
    )

    return f"""Esti un expert in hardware PC. Analizeaza configuratia si ofera feedback CONCIS in romana.

COMPONENTE SELECTATE:
{chr(10).join(comp) if comp else 'Build gol.'}

PROBLEME COMPATIBILITATE:
{prob_str}

BOTTLENECK:
{bt_str}

SUGESTII ALTERNATIVE:
{sug_str}

PREFERINTE UTILIZATOR:
- Buget: {build.buget_max or 'nespecificat'} RON
- Rezolutie: {build.rezolutie_dorita or 'nespecificata'}
- Jocuri: {', '.join(build.jocuri_preferate) if build.jocuri_preferate else 'nespecificate'}

Raspunde in maximum 4-5 randuri. Fii direct si prietenos. Fara markdown."""


def _severitate(probleme: list, bottleneck: dict) -> str:
    if probleme:
        return "error"
    if bottleneck.get("are_bottleneck") and bottleneck.get("procentaj_bottleneck", 0) > 20:
        return "warning"
    return "ok"