"""
Builder MCP Views — Gateway REST API.

Expune funcționalitățile MCP server-ului ca endpoint-uri HTTP REST,
accesibile din frontend-ul Vue (cu autentificare JWT unde e cazul).

Importă direct funcțiile Python din mcp_server.py — fără overhead de rețea.
"""

import json
import re
import hashlib
import logging

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status

from django.conf import settings
import google.genai as genai
from google.genai import types

# Importăm funcțiile din MCP server — le folosim ca funcții Python normale
from mcp_server import (
    search_components,
    get_bottleneck_score,
    check_compatibility,
    benchmark_build,
    create_build_from_preferences,
    get_fps_estimate,
    get_user_preferences,
    save_user_preferences,
    generate_build_image,
    get_component_alternatives,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
#  ENDPOINT PRINCIPAL: Chat AI cu Function Calling
# ═══════════════════════════════════════════════════════════════

# Declarații de funcții pentru Gemini — îi spunem ce tool-uri are la dispoziție
TOOL_DECLARATIONS = [
    {
        "name": "search_components",
        "description": "Caută componente PC din baza de date după tip și buget maxim.",
        "parameters": {
            "type": "object",
            "properties": {
                "component_type": {
                    "type": "string",
                    "description": "Tipul componentei: cpu, gpu, ram, storage, psu, motherboard, case, cooler",
                    "enum": ["cpu", "gpu", "ram", "storage", "psu", "motherboard", "case", "cooler"]
                },
                "budget": {
                    "type": "number",
                    "description": "Bugetul maxim în RON"
                },
                "in_stock": {
                    "type": "boolean",
                    "description": "Doar produse în stoc"
                }
            },
            "required": ["component_type", "budget"]
        }
    },
    {
        "name": "get_bottleneck_score",
        "description": "Calculează scorul de bottleneck între un CPU și un GPU specifice (după ID din DB).",
        "parameters": {
            "type": "object",
            "properties": {
                "cpu_id": {"type": "integer", "description": "ID-ul CPU-ului din baza de date"},
                "gpu_id": {"type": "integer", "description": "ID-ul GPU-ului din baza de date"}
            },
            "required": ["cpu_id", "gpu_id"]
        }
    },
    {
        "name": "check_compatibility",
        "description": "Verifică compatibilitatea componentelor unui build PC complet.",
        "parameters": {
            "type": "object",
            "properties": {
                "build": {
                    "type": "object",
                    "description": "Dicționar cu componentele build-ului (cpu, gpu, ram, motherboard, psu, case, cooler)"
                }
            },
            "required": ["build"]
        }
    },
    {
        "name": "benchmark_build",
        "description": "Rulează benchmark complet și returnează FPS estimat pentru jocurile preferate sau jocuri populare implicit.",
        "parameters": {
            "type": "object",
            "properties": {
                "cpu": {"type": "object", "description": "Datele CPU-ului (nume, nuclee, frecventa_ghz, consum_tdp)"},
                "gpu": {"type": "object", "description": "Datele GPU-ului (nume, vram_gb, consum_tdp)"},
                "ram": {"type": "object", "description": "Datele RAM-ului (capacitate_totala_gb, tip_memorie, frecventa_mhz)"},
                "rezolutie": {"type": "string", "description": "Rezoluția țintă: 1080p, 1440p, 4K", "enum": ["1080p", "1440p", "4K"]},
                "jocuri_preferate": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Lista de jocuri specifice pentru care vrei estimări FPS. Opțional."
                },
                "user_id": {"type": "integer", "description": "ID-ul utilizatorului (pentru a încărca jocurile preferate salvate în cont)."}
            },
            "required": ["cpu", "gpu", "ram"]
        }
    },
    {
        "name": "create_build_from_preferences",
        "description": "Construiește automat un build PC optim din baza de date, pe baza bugetului, jocurilor și rezoluției.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {"type": "integer", "description": "ID-ul utilizatorului (pentru a încărca preferințele salvate)"},
                "buget": {"type": "number", "description": "Bugetul total în RON"},
                "jocuri": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Lista de jocuri preferate"
                },
                "rezolutie": {"type": "string", "description": "Rezoluția dorită: 1080p, 1440p, 4K"},
                "tip_utilizare": {"type": "string", "description": "Tipul de utilizare: gaming, productivitate, mixt"}
            },
            "required": []
        }
    },
    {
        "name": "get_user_preferences",
        "description": "Returnează preferințele salvate ale utilizatorului (buget, jocuri, rezoluție). Folosește acest tool la începutul conversației.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {"type": "integer", "description": "ID-ul utilizatorului"}
            },
            "required": ["user_id"]
        }
    },
    {
        "name": "save_user_preferences",
        "description": "Salvează sau actualizează preferințele utilizatorului.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {"type": "integer", "description": "ID-ul utilizatorului"},
                "buget": {"type": "number", "description": "Bugetul în RON"},
                "jocuri": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Lista de jocuri"
                },
                "rezolutie": {"type": "string", "description": "Rezoluția dorită"},
                "tip_utilizare": {"type": "string", "description": "Tipul de utilizare"}
            },
            "required": ["user_id", "buget", "jocuri", "rezolutie"]
        }
    },
    {
        "name": "get_fps_estimate",
        "description": "Returnează FPS estimat din cache pentru o combinație CPU+GPU și un joc specific.",
        "parameters": {
            "type": "object",
            "properties": {
                "cpu_id": {"type": "integer", "description": "ID-ul CPU-ului"},
                "gpu_id": {"type": "integer", "description": "ID-ul GPU-ului"},
                "game": {"type": "string", "description": "Numele jocului"},
                "resolution": {"type": "string", "description": "Rezoluția: 1080p, 1440p, 4K"}
            },
            "required": ["cpu_id", "gpu_id", "game"]
        }
    },
    {
        "name": "generate_build_image",
        "description": "Generează o imagine render fotorealistă cu build-ul PC.",
        "parameters": {
            "type": "object",
            "properties": {
                "case_name": {"type": "string", "description": "Numele carcasei"},
                "gpu_name": {"type": "string", "description": "Numele plăcii video"},
                "cpu_name": {"type": "string", "description": "Numele procesorului"}
            },
            "required": ["case_name", "gpu_name", "cpu_name"]
        }
    },
    {
        "name": "get_component_alternatives",
        "description": "Găsește alternative pentru o componentă PC specificată.",
        "parameters": {
            "type": "object",
            "properties": {
                "component_type": {"type": "string", "description": "Tipul componentei (cpu, gpu, ram, etc.)"},
                "component_id": {"type": "integer", "description": "ID-ul componentei din DB"},
                "limit": {"type": "integer", "description": "Numărul maxim de alternative"}
            },
            "required": ["component_type", "component_id"]
        }
    }
]

# Mapping de la numele funcției la funcția Python reală
TOOL_MAP = {
    "search_components": search_components,
    "get_bottleneck_score": get_bottleneck_score,
    "check_compatibility": check_compatibility,
    "benchmark_build": benchmark_build,
    "create_build_from_preferences": create_build_from_preferences,
    "get_fps_estimate": get_fps_estimate,
    "get_user_preferences": get_user_preferences,
    "save_user_preferences": save_user_preferences,
    "generate_build_image": generate_build_image,
    "get_component_alternatives": get_component_alternatives,
}


def _execute_tool(name: str, args: dict) -> dict:
    """Execută un tool MCP și returnează rezultatul ca dict."""
    func = TOOL_MAP.get(name)
    if not func:
        return {"error": f"Tool necunoscut: {name}"}
    try:
        result = func(**args)
        return result
    except Exception as e:
        logger.error("Eroare la execuția tool-ului %s: %s", name, e)
        return {"error": f"Eroare la {name}: {str(e)}"}


def _convert_for_json(obj):
    """Converteste tipuri non-serializabile (Decimal, date, etc.) pentru JSON."""
    import decimal
    import datetime
    if isinstance(obj, decimal.Decimal):
        return float(obj)
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _convert_for_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_convert_for_json(item) for item in obj]
    return obj


class ChatView(APIView):
    """
    POST /api/builder/chat/
    
    Chat AI principal cu function calling — înlocuiește testing-agent/chat-architect.
    Necesită JWT. Trimite mesajul la Gemini cu toate tool-urile MCP disponibile.
    Gemini decide singur ce tool-uri să apeleze.
    """
    permission_classes = [IsAuthenticated]

    # Limita maximă de iterații function-calling (previne loop infinit)
    MAX_TOOL_ITERATIONS = 5

    def post(self, request):
        mesaj_nou = request.data.get("mesaj_nou", "").strip()
        istoric = request.data.get("istoric", [])

        if not mesaj_nou:
            return Response(
                {"error": "Mesajul nu poate fi gol."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = request.user
        user_id = user.id

        # Construim istoricul conversației pentru Gemini
        contents = []

        # System instruction cu contextul user-ului
        system_instruction = (
            f"Ești 'AI PC Architect', un expert în hardware PC. "
            f"Utilizatorul autentificat este '{user.username}' (ID: {user_id}). "
            f"La PRIMA interacțiune, apelează ÎNTOTDEAUNA tool-ul get_user_preferences "
            f"pentru a verifica dacă utilizatorul are preferințe salvate. "
            f"Dacă are, întreabă-l dacă vrea să le folosească sau altele noi. "
            f"Dacă nu are, întreabă-l de buget, jocuri și rezoluție. "
            f"Când ai toate datele, folosește create_build_from_preferences. "
            f"Când utilizatorul îți cere estimări de FPS (benchmark), întreabă-l mai întâi pentru ce jocuri dorește estimarea (dacă nu au fost deja stabilite sau salvate), apoi apelează benchmark_build trimițând 'jocuri_preferate' și 'user_id' = {user_id}. "
            f"Răspunde ÎNTOTDEAUNA în limba română. "
            f"Fii prietenos și profesionist."
        )

        # Adăugăm istoricul
        for msg in istoric:
            role = "user" if msg.get("role") == "user" else "model"
            text = msg.get("text", "")
            if text:
                contents.append(types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=text)]
                ))

        # Adăugăm mesajul nou
        contents.append(types.Content(
            role="user",
            parts=[types.Part.from_text(text=mesaj_nou)]
        ))

        try:
            client = genai.Client(api_key=settings.GEMINI_API_KEY)

            # Configurăm tool-urile pentru Gemini
            tools = types.Tool(function_declarations=[
                types.FunctionDeclaration(**decl)
                for decl in TOOL_DECLARATIONS
            ])

            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                tools=[tools],
                temperature=0.7,
            )

            # Loop de function calling — Gemini poate cere mai multe tool-uri în serie
            build_data = None
            all_tool_results = {}

            for iteration in range(self.MAX_TOOL_ITERATIONS):
                response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=contents,
                    config=config,
                )

                # Verificăm dacă Gemini cere apeluri de funcții
                candidate = response.candidates[0] if response.candidates else None
                if not candidate:
                    break

                has_function_calls = False
                function_call_parts = []
                function_response_parts = []

                for part in candidate.content.parts:
                    if part.function_call:
                        has_function_calls = True
                        fc = part.function_call
                        tool_name = fc.name
                        tool_args = dict(fc.args) if fc.args else {}

                        # Execută tool-ul
                        logger.info("Gemini apelează tool: %s(%s)", tool_name, tool_args)
                        result = _execute_tool(tool_name, tool_args)
                        result = _convert_for_json(result)

                        # Salvăm rezultatele relevante
                        all_tool_results[tool_name] = result

                        # Dacă e un build, îl salvăm
                        if tool_name == "create_build_from_preferences" and result.get("succes"):
                            build_data = result

                        function_call_parts.append(part)
                        function_response_parts.append(
                            types.Part.from_function_response(
                                name=tool_name,
                                response=result,
                            )
                        )

                if not has_function_calls:
                    # Gemini a terminat — avem răspunsul text final
                    break

                # Adăugăm apelul și răspunsul funcțiilor în conversație
                contents.append(candidate.content)
                contents.append(types.Content(
                    role="user",
                    parts=function_response_parts,
                ))

            # Extragem textul final al răspunsului
            mesaj_text = ""
            if response.candidates:
                for part in response.candidates[0].content.parts:
                    if part.text:
                        mesaj_text += part.text

            if not mesaj_text:
                mesaj_text = "Am procesat cererea ta, dar nu am putut genera un răspuns text."

            # Construim răspunsul
            response_data = {
                "mesaj_text": mesaj_text,
                "contine_build": build_data is not None,
                "build_data": build_data,
            }

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error("Eroare la chat AI: %s", e)
            return Response(
                {
                    "mesaj_text": "Scuze, am întâmpinat o eroare. Te rog să încerci din nou.",
                    "contine_build": False,
                    "build_data": None,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ═══════════════════════════════════════════════════════════════
#  ENDPOINT-URI DIRECTE (fără AI — apel direct la tool-urile MCP)
# ═══════════════════════════════════════════════════════════════

class SearchComponentsView(APIView):
    """POST /api/builder/search/ — Căutare componente din DB."""
    permission_classes = [AllowAny]

    def post(self, request):
        component_type = request.data.get("component_type", "")
        budget = request.data.get("budget", 0)
        in_stock = request.data.get("in_stock", True)

        if not component_type or not budget:
            return Response(
                {"error": "Parametrii component_type și budget sunt obligatorii."},
                status=status.HTTP_400_BAD_REQUEST
            )

        result = search_components(
            component_type=str(component_type),
            budget=float(budget),
            in_stock=bool(in_stock)
        )
        return Response(_convert_for_json(result))


class BottleneckView(APIView):
    """GET/POST /api/builder/bottleneck/ — Calcul bottleneck CPU/GPU."""
    permission_classes = [AllowAny]

    def get(self, request):
        cpu_id = request.query_params.get("cpu_id")
        gpu_id = request.query_params.get("gpu_id")

        if not cpu_id or not gpu_id:
            return Response(
                {"error": "Parametrii cpu_id și gpu_id sunt obligatorii."},
                status=status.HTTP_400_BAD_REQUEST
            )

        result = get_bottleneck_score(cpu_id=int(cpu_id), gpu_id=int(gpu_id))
        return Response(_convert_for_json(result))

    def post(self, request):
        cpu_id = request.data.get("cpu_id")
        gpu_id = request.data.get("gpu_id")

        if not cpu_id or not gpu_id:
            return Response(
                {"error": "Parametrii cpu_id și gpu_id sunt obligatorii."},
                status=status.HTTP_400_BAD_REQUEST
            )

        result = get_bottleneck_score(cpu_id=int(cpu_id), gpu_id=int(gpu_id))
        return Response(_convert_for_json(result))


class CompatibilityView(APIView):
    """POST /api/builder/compatibility/ — Verificare compatibilitate build."""
    permission_classes = [AllowAny]

    def post(self, request):
        build = request.data.get("build", {})
        if not build:
            return Response(
                {"error": "Parametrul build este obligatoriu."},
                status=status.HTTP_400_BAD_REQUEST
            )

        result = check_compatibility(build=build)
        return Response(_convert_for_json(result))


class BenchmarkView(APIView):
    """GET/POST /api/builder/benchmark/ — Estimare FPS via Gemini."""
    permission_classes = [AllowAny]

    def get(self, request):
        from components.models import BuildAnalysisCache
        import hashlib
        cpu_id = request.query_params.get("cpu_id")
        gpu_id = request.query_params.get("gpu_id")
        
        if not cpu_id or not gpu_id:
            return Response({"error": "cpu_id si gpu_id lipsesc"}, status=400)
            
        cache_key = hashlib.md5(f"{cpu_id}_{gpu_id}".encode()).hexdigest()
        try:
            cached = BuildAnalysisCache.objects.get(cache_key=cache_key)
            return Response({
                "cached": True,
                "fps_data": _convert_for_json(cached.fps_data),
                "analiza_text": cached.analiza_text
            })
        except BuildAnalysisCache.DoesNotExist:
            return Response({"cached": False})

    def post(self, request):
        from components.models import CPU, GPU, RAM
        from django.forms.models import model_to_dict

        cpu = request.data.get("cpu")
        gpu = request.data.get("gpu")
        ram = request.data.get("ram")

        cpu_id = request.data.get("cpu_id")
        gpu_id = request.data.get("gpu_id")
        ram_id = request.data.get("ram_id")

        if cpu_id and not cpu:
            try: cpu = model_to_dict(CPU.objects.get(id=cpu_id))
            except CPU.DoesNotExist: cpu = {}
            
        if gpu_id and not gpu:
            try: gpu = model_to_dict(GPU.objects.get(id=gpu_id))
            except GPU.DoesNotExist: gpu = {}
            
        if ram_id and not ram:
            try: ram = model_to_dict(RAM.objects.get(id=ram_id))
            except RAM.DoesNotExist: ram = {}

        if not cpu: cpu = {}
        if not gpu: gpu = {}
        if not ram: ram = {}

        rezolutie = request.data.get("rezolutie", "1080p")

        if not gpu:
            return Response(
                {"error": "Parametrul gpu (sau gpu_id) este obligatoriu."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user_id = request.user.id if hasattr(request.user, 'id') else None
        
        result = benchmark_build(
            cpu=cpu, gpu=gpu, ram=ram, rezolutie=str(rezolutie), user_id=user_id
        )
        return Response(_convert_for_json(result))


class AutoBuildView(APIView):
    """POST /api/builder/auto-build/ — Build automat optimizat."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user_id = request.user.id
        buget = request.data.get("buget")
        jocuri = request.data.get("jocuri")
        rezolutie = request.data.get("rezolutie", "1080p")
        tip_utilizare = request.data.get("tip_utilizare", "gaming")

        result = create_build_from_preferences(
            user_id=user_id,
            buget=float(buget) if buget else None,
            jocuri=jocuri,
            rezolutie=str(rezolutie),
            tip_utilizare=str(tip_utilizare),
        )
        return Response(_convert_for_json(result))


class PreferencesView(APIView):
    """
    GET  /api/builder/preferences/ — Citește preferințele user-ului
    POST /api/builder/preferences/ — Salvează preferințele user-ului
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        result = get_user_preferences(user_id=request.user.id)
        return Response(_convert_for_json(result))

    def post(self, request):
        buget = request.data.get("buget")
        jocuri = request.data.get("jocuri", [])
        rezolutie = request.data.get("rezolutie", "1080p")
        tip_utilizare = request.data.get("tip_utilizare", "gaming")

        if not buget:
            return Response(
                {"error": "Parametrul buget este obligatoriu."},
                status=status.HTTP_400_BAD_REQUEST
            )

        result = save_user_preferences(
            user_id=request.user.id,
            buget=float(buget),
            jocuri=list(jocuri),
            rezolutie=str(rezolutie),
            tip_utilizare=str(tip_utilizare),
        )
        return Response(_convert_for_json(result))


class GenerateImageView(APIView):
    """POST /api/builder/generate-image/ — Generează imagine render cu build-ul."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        case_name = request.data.get("case_name", "")
        gpu_name = request.data.get("gpu_name", "")
        cpu_name = request.data.get("cpu_name", "")

        if not case_name or not gpu_name or not cpu_name:
            return Response(
                {"error": "Parametrii case_name, gpu_name și cpu_name sunt obligatorii."},
                status=status.HTTP_400_BAD_REQUEST
            )

        result = generate_build_image(
            case_name=str(case_name),
            gpu_name=str(gpu_name),
            cpu_name=str(cpu_name),
        )
        if result.get("image_path"):
            import os
            from django.conf import settings
            filename = os.path.basename(result["image_path"])
            result["image_url"] = request.build_absolute_uri(settings.MEDIA_URL + 'builds/' + filename)
        
        return Response(_convert_for_json(result))

class AlternativesView(APIView):
    """POST /api/builder/alternatives/ — Caută alternative pentru componentă."""
    permission_classes = [AllowAny]

    def post(self, request):
        component_type = request.data.get("component_type", "")
        component_id = request.data.get("component_id", 0)
        limit = request.data.get("limit", 3)

        if not component_type or not component_id:
            return Response(
                {"error": "Parametrii component_type și component_id sunt obligatorii."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            result = get_component_alternatives(
                component_type=str(component_type),
                component_id=int(component_id),
                limit=int(limit)
            )
            return Response(_convert_for_json(result))
        except Exception as e:
            return Response({"error": str(e)}, status=500)
