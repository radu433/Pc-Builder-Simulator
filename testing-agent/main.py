"""
PC Builder — Testing Agent  |  port 8002
Include: Analiză Build (vechi) + Chat Architect cu acces la DB (nou)
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import httpx
import google.generativeai as genai
import json
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

from config import GEMINI_API_KEY, DJANGO_BASE_URL
from core.schemas import BuildRequest, AgentResponse
from core.compatibility import verifica_compatibilitate
from core.bottleneck import calculeaza_bottleneck
from core.suggestions import obtine_sugestii

# Configurare Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-flash-latest")

app = FastAPI(
    title="PC Builder — Testing Agent",
    description="Analiză build și Arhitect AI cu selecție din DB",
    version="1.1.0",
)

# Configurare CORS pentru Frontend (Vue) și Backend (Django)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:8000", "http://127.0.0.1:5173", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- SCHEME PENTRU NOUL CHAT AI ---
class ChatMessage(BaseModel):
    role: str
    text: str

class ChatRequest(BaseModel):
    mesaj_nou: str
    istoric: List[ChatMessage]

class ChatResponse(BaseModel):
    mesaj_text: str
    contine_build: bool
    build_data: Optional[Dict[str, Any]] = None

# --- RUTE EXISTENTE ---

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

# --- RUTĂ NOUĂ: CHAT ARCHITECT ---

@app.post("/chat-architect", response_model=ChatResponse)
async def chat_architect(req: ChatRequest):
    """
    Endpoint care folosește Gemini pentru a înțelege utilizatorul și a genera build-uri din DB.
    """
    istoric_text = "\n".join([f"{m.role}: {m.text}" for m in req.istoric])
    
    # Promptul forțează Gemini să răspundă doar în format JSON pentru ca Python să poată procesa datele
    prompt = f"""Ești 'AI PC Architect', un expert în hardware. 
    Scopul tău este să ajuți utilizatorul să decidă un buget (în RON) și să înțelegi ce nevoi are.
    
    ISTORIC CONVERSAȚIE:
    {istoric_text}
    
    MESAJ NOU UTILIZATOR:
    {req.mesaj_nou}
    
    Instrucțiune: Dacă utilizatorul a menționat un buget (sau se deduce din context), extrage suma.
    RĂSPUNDE EXCLUSIV CU UN JSON VALID (fără alt text adițional):
    {{
        "mesaj_catre_utilizator": "răspunsul tău prietenos în română...",
        "buget_detectat_ron": 5000, 
        "are_destule_date": true 
    }}
    Note: 'are_destule_date' devine true DOAR când ai un buget clar peste 1500 RON."""

    try:
        response = model.generate_content(prompt)
        text_raspuns = response.text.strip()
        
        # Curățare formatare markdown dacă Gemini o include
        if "```json" in text_raspuns:
            text_raspuns = text_raspuns.split("```json")[1].split("```")[0].strip()
        elif "```" in text_raspuns:
            text_raspuns = text_raspuns.split("```")[1].split("```")[0].strip()
            
        ai_data = json.loads(text_raspuns)
    except Exception as e:
        print(f"Eroare AI: {e}")
        return ChatResponse(mesaj_text="Sistemul de inteligență întâmpină dificultăți. Te rog revino imediat.", contine_build=False)

    buget = ai_data.get("buget_detectat_ron")
    are_date = ai_data.get("are_destule_date")
    mesaj_ai = ai_data.get("mesaj_catre_utilizator", "Înțeles!")

    # Dacă avem buget, interogăm baza de date Django
    if are_date and buget and isinstance(buget, (int, float)):
        build_propus = await _genereaza_build_din_db(float(buget))
        return ChatResponse(
            mesaj_text=mesaj_ai + f"\n\nAm configurat un sistem optim pentru ~{buget} RON folosind piese din stocul nostru:",
            contine_build=True,
            build_data=build_propus
        )
    
    return ChatResponse(mesaj_text=mesaj_ai, contine_build=False)

async def _genereaza_build_din_db(buget: float) -> dict:
    """
    Caută componente reale în Django și asamblează cel mai bun build în limita bugetului.
    """
    # Adăugăm follow_redirects=True în caz că Django ne redirecționează
    async with httpx.AsyncClient(follow_redirects=True) as http:
        try:
            # Ne asigurăm că URL-ul de bază nu are slash la final ca să nu se dubleze
            base_url = DJANGO_BASE_URL.rstrip('/')
            urls = {
                "cpus": f"{base_url}/cpus/",
                "gpus": f"{base_url}/gpus/",
                "motherboards": f"{base_url}/motherboards/",
                "rams": f"{base_url}/rams/"
            }
            
            piese_db = {}
            for key, url in urls.items():
                res = await http.get(url)
                if res.status_code != 200:
                    print(f"Eroare API Django pt {key}: status {res.status_code}")
                    piese_db[key] = []
                    continue
                data = res.json()
                piese_db[key] = data.get("results", data) if isinstance(data, dict) else data

            # Algoritm simplu de distribuție a bugetului
            gpu_ales = _alege_piesa_optima(piese_db["gpus"], buget * 0.40)
            cpu_ales = _alege_piesa_optima(piese_db["cpus"], buget * 0.25)
            
            # Filtrare Placă de bază (PROTEJATĂ la erori)
            cpu_socket = cpu_ales.get("socket") if cpu_ales else None
            mobos_compatibile = [m for m in piese_db["motherboards"] if m.get("socket") == cpu_socket] if cpu_socket else piese_db["motherboards"]
            mobo_aleasa = _alege_piesa_optima(mobos_compatibile, buget * 0.15)
            
            # Filtrare RAM (PROTEJATĂ la erori)
            mobo_tip = mobo_aleasa.get("tip_memorie") if mobo_aleasa else None
            rams_compatibile = [r for r in piese_db["rams"] if r.get("tip") == mobo_tip] if mobo_tip else piese_db["rams"]
            ram_ales = _alege_piesa_optima(rams_compatibile, buget * 0.10)
            
            total = sum([float(p.get("pret", 0)) for p in [cpu_ales, gpu_ales, mobo_aleasa, ram_ales] if p])
            
            return {
                "cpu": cpu_ales,
                "gpu": gpu_ales,
                "motherboard": mobo_aleasa,
                "ram": ram_ales,
                "totalPrice": round(total, 2)
            }
        except Exception as e:
            # Acum, dacă dă eroare, o va printa clar în terminal ca să știm de ce!
            import traceback
            traceback.print_exc()
            print(f"Eroare severă la conectarea cu DB: {e}")
            return {}

def _alege_piesa_optima(lista_piese, buget_max):
    # Găsește piesa cea mai scumpă (cea mai performantă) care se încadrează în bugetul alocat
    valabile = [p for p in lista_piese if float(p.get("pret", 0)) <= buget_max]
    if not valabile:
        # Dacă bugetul e prea mic, o ia pe cea mai ieftină din listă
        lista_piese.sort(key=lambda x: float(x.get("pret", 0)))
        return lista_piese[0] if lista_piese else None
    
    valabile.sort(key=lambda x: float(x.get("pret", 0)), reverse=True)
    return valabile[0]

# --- HELPERS GENERARE ANALIZĂ ---

def _genereaza_analiza(build, probleme, bottleneck, sugestii) -> str:
    prompt = _construieste_prompt(build, probleme, bottleneck, sugestii)
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Analiza AI indisponibila momentan: {e}"

def _construieste_prompt(build, probleme, bottleneck, sugestii) -> str:
    # (Păstrat neschimbat din versiunea ta anterioară)
    comp = []
    # ... (logica de construcție a listei de componente) ...
    # [Codul tău de prompt engineering de mai sus]
    return f"Esti un expert hardware... [Restul promptului tau]"

def _severitate(probleme: list, bottleneck: dict) -> str:
    if probleme: return "error"
    if bottleneck.get("are_bottleneck") and bottleneck.get("procentaj_bottleneck", 0) > 20:
        return "warning"
    return "ok"