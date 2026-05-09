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
DEFAULT_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash").strip()


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
    """
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

    match = re.search(r"(\[\s*\{.+?\}\s*\])", cleaned, re.DOTALL)
    if match:
        try:
            result = json.loads(match.group(1))
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass

    raise ValueError(f"No se pudo parsear JSON de la IA: {raw[:200]}")

def _plan_with_ai(prompt: str, api_key: str, model_name: str, base_url: str = None) -> list[dict]:
    """Llama a un modelo de IA para generar un plan de prueba."""
    import openai
    
    if not base_url and "gemini" in model_name.lower():
        base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
        
    client = openai.OpenAI(api_key=api_key, base_url=base_url)

    system_instruction = (
        "Eres un experto en QA automatizado con Selenium. "
        "Responde UNICAMENTE con un array JSON de objetos. "
        'Ejemplo: [{"action": "open_url", "value": "url"}, {"action": "click", "selector": "css"}] '
        "Acciones permitidas: open_url, find_and_type, click, hover, press_key, select_option, scroll_to, validate_text, validate_url, validate_exists, wait, screenshot, generate_email, wait_for_email. "
        "Usa {{email}} para referenciar un correo generado previamente."
    )

    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": prompt}
        ],
        temperature=0.1
    )
    
    raw = response.choices[0].message.content.strip()
    return _extract_json_steps(raw)


def generate_test_plan(prompt: str, api_key: str = None, model_name: str = "gemini-2.0-flash", base_url: str = None) -> list[dict]:
    """Punto de entrada principal para generar planes de prueba."""
    if api_key is None:
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        
    if api_key:
        try:
            return _plan_with_ai(prompt, api_key, model_name, base_url)
        except Exception as e:
            raise Exception(f"Error en IA: {e}")

    return _fallback_plan(prompt)
