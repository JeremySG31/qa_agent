"""
planner.py - Modulo del agente LLM
Convierte prompts en lenguaje natural a pasos de prueba estructurados.
Intenta usar Gemini API; si no esta disponible, usa respuestas simuladas.
"""

import os
import json
import re


def _safe_print(*args, **kwargs):
    """Print seguro que nunca falla por encoding en Windows."""
    try:
        print(*args, **kwargs)
    except (UnicodeEncodeError, OSError):
        try:
            text = " ".join(str(a) for a in args)
            print(text.encode("ascii", errors="replace").decode("ascii"), **kwargs)
        except Exception:
            pass


# Intentar importar Google Generative AI (Gemini)
GEMINI_AVAILABLE = False
_GENAI_NEW = False  # True si usamos google.genai (nueva API)
try:
    import google.genai as genai  # nueva API (sin FutureWarning)
    GEMINI_AVAILABLE = True
    _GENAI_NEW = True
except ImportError:
    try:
        import warnings
        warnings.filterwarnings("ignore", category=FutureWarning)
        import google.generativeai as genai  # type: ignore  # fallback (deprecada)
        GEMINI_AVAILABLE = True
    except ImportError:
        pass

DEFAULT_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash").strip()


def _fallback_plan(prompt: str) -> list[dict]:
    """
    Genera un plan genérico básico si Gemini no está disponible o no hay API Key.
    Extrae la URL del prompt y genera un paso para abrirla.
    """
    url_match = re.search(r'(https?://[^\s]+|[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:/[^\s]*)?)', prompt)
    extracted_url = url_match.group(0) if url_match else None

    if extracted_url:
        if not extracted_url.startswith("http"):
            extracted_url = "https://" + extracted_url
        return [
            {"action": "open_url", "value": extracted_url},
            {"action": "validate_text", "selector": "body", "value": ""}
        ]

    # Si no hay URL en el prompt y no se usa Gemini, se requiere configurar la API Key
    return [
        {"action": "open_url", "value": "data:text/html,%3Ch1%3ESe%20requiere%20API%20Key%20de%20Gemini%20o%20especificar%20una%20URL%20en%20el%20prompt%3C%2Fh1%3E"},
        {"action": "validate_text", "selector": "h1", "value": "Esperando configuración"}
    ]


def _extract_json_steps(raw: str) -> list[dict]:
    """
    Extrae de forma robusta una lista JSON desde el texto crudo de Gemini.
    Estrategias:
      1. Strip de fences markdown y parse directo.
      2. Buscar el primer bloque [...] con regex.
      3. Lanzar error descriptivo si todo falla.
    """
    # Estrategia 1: limpiar fences y parsear
    cleaned = re.sub(r"```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
    cleaned = cleaned.strip().strip("`").strip()
    try:
        result = json.loads(cleaned)
        if isinstance(result, list):
            return result
        if isinstance(result, dict) and "steps" in result:
            return result["steps"]
    except json.JSONDecodeError:
        pass

    # Estrategia 2: encontrar el bloque [...] con regex
    match = re.search(r"(\[\s*\{.+?\}\s*\])", cleaned, re.DOTALL)
    if match:
        try:
            result = json.loads(match.group(1))
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass

    raise ValueError(
        f"No se pudo parsear la respuesta de Gemini como JSON.\n"
        f"Respuesta recibida (primeros 300 chars):\n{raw[:300]}"
    )


def _plan_with_gemini(prompt: str, api_key: str) -> list[dict]:
    """
    Llama a Gemini para generar un plan de prueba estructurado.
    Devuelve una lista de pasos en formato dict.
    Soporta tanto google.genai (nueva API) como google.generativeai (deprecada).
    """
    model_name = os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL).strip()

    system_instruction = (
        "Eres un experto en QA automatizado con Selenium. "
        "El usuario te dara un prompt describiendo que probar en una web. "
        "Responde UNICAMENTE con un JSON valido (sin markdown, sin explicaciones): "
        '[{"action": "open_url", "value": "<url>"}, '
        '{"action": "find_and_type", "selector": "<css_selector>", "value": "<texto>"}, '
        '{"action": "click", "selector": "<css_selector>"}, '
        '{"action": "validate_text", "selector": "<css_selector>", "value": "<texto esperado>"}] '
        "Acciones permitidas: open_url, find_and_type, click, validate_text, validate_url, validate_exists. "
        "Usa selectores CSS reales y concretos. Si no conoces la URL exacta, usa una conocida de practica como "
        "https://practicetestautomation.com/practice-test-login/"
    )
    full_prompt = system_instruction + "\nPrompt: " + prompt

    if _GENAI_NEW:
        # Nueva API: google.genai
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model_name,
            contents=full_prompt,
        )
        raw = response.text.strip()
    else:
        # API deprecada: google.generativeai (v1beta tiene problemas con gemini-1.5-flash)
        genai.configure(api_key=api_key)
        safe_model = "gemini-pro" if "1.5" in model_name else model_name
        model = genai.GenerativeModel(safe_model)
        response = model.generate_content(full_prompt)
        raw = response.text.strip()

    return _extract_json_steps(raw)


def generate_test_plan(prompt: str, api_key: str = None) -> list[dict]:
    """
    Punto de entrada principal del planner.
    1. Intenta usar Gemini si esta configurado.
    2. Si falla o no esta disponible, usa plan generico.
    """
    if api_key is None:
        api_key = os.getenv("GEMINI_API_KEY", "")
    api_key = api_key.strip()

    if api_key and not GEMINI_AVAILABLE:
        raise Exception(
            "Gemini esta configurado, pero falta instalar google-generativeai. "
            "Ejecuta: pip install -r requirements.txt"
        )

    if GEMINI_AVAILABLE and api_key:
        try:
            _safe_print("Usando Gemini para generar el plan de prueba...")
            return _plan_with_gemini(prompt, api_key)
        except Exception as e:
            _safe_print(f"Gemini fallo ({e}), propagando error.")
            raise Exception(f"Fallo en la API de Gemini: {e}")

    _safe_print("Generando plan basico (modo sin IA)...")
    return _fallback_plan(prompt)
