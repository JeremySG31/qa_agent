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
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


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


def _plan_with_gemini(prompt: str, api_key: str) -> list[dict]:
    """
    Llama a Gemini para generar un plan de prueba estructurado.
    Devuelve una lista de pasos en formato dict.
    """
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-pro")

    system_instruction = (
        "Eres un experto en QA automatizado con Selenium. "
        "El usuario te dara un prompt describiendo que probar en una web. "
        "Responde UNICAMENTE con un JSON valido (sin markdown, sin explicaciones): "
        '[{"action": "open_url", "value": "<url>"}, '
        '{"action": "find_and_type", "selector": "<css_selector>", "value": "<texto>"}, '
        '{"action": "click", "selector": "<css_selector>"}, '
        '{"action": "validate_text", "selector": "<css_selector>", "value": "<texto esperado>"}] '
        "Acciones permitidas: open_url, find_and_type, click, validate_text. "
        "Usa selectores CSS reales. Si no conoces la URL exacta, usa una conocida de practica como "
        "https://practicetestautomation.com/practice-test-login/"
    )

    response = model.generate_content(system_instruction + "\nPrompt: " + prompt)
    raw = response.text.strip()

    # Limpiar posibles bloques markdown
    raw = re.sub(r"```(?:json)?", "", raw).strip().strip("`")
    steps = json.loads(raw)
    return steps


def generate_test_plan(prompt: str, api_key: str = None) -> list[dict]:
    """
    Punto de entrada principal del planner.
    1. Intenta usar Gemini si esta configurado.
    2. Si falla o no esta disponible, usa plan generico.
    """
    if api_key is None:
        api_key = os.getenv("GEMINI_API_KEY", "")

    if GEMINI_AVAILABLE and api_key:
        try:
            _safe_print("Usando Gemini para generar el plan de prueba...")
            return _plan_with_gemini(prompt, api_key)
        except Exception as e:
            _safe_print(f"Gemini fallo ({e}), propagando error.")
            raise Exception(f"Fallo en la API de Gemini: {e}")

    _safe_print("Generando plan basico (modo sin IA)...")
    return _fallback_plan(prompt)