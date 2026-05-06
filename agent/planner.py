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


# Plantillas de pasos simulados para demos rapidas
BASE_URL = "https://reviewstar-web.vercel.app"

SIMULATED_PLANS = {
    "inicio": [
        {"action": "open_url",     "value": f"{BASE_URL}/index.html"},
        {"action": "validate_text","selector": "h1",          "value": "ReviewStar"},
        {"action": "validate_text","selector": "body",         "value": "Iniciar"},
        {"action": "validate_text","selector": "body",         "value": "Registrarse"},
    ],
    "login": [
        {"action": "open_url",      "value": f"{BASE_URL}/login.html"},
        {"action": "validate_text", "selector": "h2",          "value": "Iniciar"},
        {"action": "find_and_type", "selector": "input[type='email']",    "value": "test@reviewstar.com"},
        {"action": "find_and_type", "selector": "input[type='password']", "value": "Test1234!"},
        {"action": "click",         "selector": "button[type='submit']"},
        {"action": "validate_url",  "value": BASE_URL},
    ],
    "login invalido": [
        {"action": "open_url",      "value": f"{BASE_URL}/login.html"},
        {"action": "find_and_type", "selector": "input[type='email']",    "value": "noexiste@fake.com"},
        {"action": "find_and_type", "selector": "input[type='password']", "value": "clavemal"},
        {"action": "click",         "selector": "button[type='submit']"},
        {"action": "validate_exists","selector": ".error-message, .alert, [class*='error'], [class*='alert']"},
    ],
    "registro": [
        {"action": "open_url",      "value": f"{BASE_URL}/register.html"},
        {"action": "validate_text", "selector": "h2",                     "value": "Registrarse"},
        {"action": "find_and_type", "selector": "input[type='text'], input[placeholder*='suario'], input[placeholder*='sername']",
                                    "value": "TestUser123"},
        {"action": "find_and_type", "selector": "input[type='email']",    "value": "testuser123@mail.com"},
        {"action": "find_and_type", "selector": "input[type='password']", "value": "Secure123!"},
        {"action": "click",         "selector": "button[type='submit']"},
    ],
    "feed": [
        {"action": "open_url",      "value": f"{BASE_URL}/feed.html"},
        {"action": "validate_text", "selector": "body",    "value": "ReviewStar"},
    ],
    "navegacion": [
        {"action": "open_url",      "value": f"{BASE_URL}/index.html"},
        {"action": "validate_text", "selector": "body",     "value": "Iniciar"},
        {"action": "click",         "selector": "a[href*='login']"},
        {"action": "validate_text", "selector": "h2",       "value": "Iniciar"},
        {"action": "open_url",      "value": f"{BASE_URL}/index.html"},
        {"action": "click",         "selector": "a[href*='register']"},
        {"action": "validate_text", "selector": "h2",       "value": "Registrarse"},
    ],
    "forgot": [
        {"action": "open_url",      "value": f"{BASE_URL}/login.html"},
        {"action": "click",         "selector": "a[href*='forgot']"},
        {"action": "validate_text", "selector": "body",     "value": "contrase"},
    ],
    "default": [
        {"action": "open_url",      "value": f"{BASE_URL}/index.html"},
        {"action": "validate_text", "selector": "h1",       "value": "ReviewStar"},
        {"action": "validate_text", "selector": "body",     "value": "review"},
    ],
}


def _keyword_match(prompt: str) -> list[dict]:
    """Selecciona un plan simulado segun palabras clave en el prompt."""
    prompt_lower = prompt.lower()

    # Intentar extraer una URL del prompt
    url_match = re.search(r'(https?://[^\s]+|[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:/[^\s]*)?)', prompt)
    extracted_url = url_match.group(0) if url_match else None

    keyword_map = {
        "login invalido":  ["login inv", "credencial"],
        "login":           ["login", "iniciar ses", "sign in"],
        "registro":        ["registro", "registrar", "register", "sign up", "crear cuenta"],
        "feed":            ["feed", "explorar"],
        "navegacion":      ["navegaci", "navegar", "links", "enlaces"],
        "forgot":          ["forgot", "olvid", "recuperar contrase"],
        "inicio":          ["inicio", "home", "index"],
    }

    plan = None
    for plan_key, keywords in keyword_map.items():
        if any(kw in prompt_lower for kw in keywords):
            plan = [dict(s) for s in SIMULATED_PLANS[plan_key]]
            break

    if not plan:
        plan = [dict(s) for s in SIMULATED_PLANS["default"]]

    # Si encontramos una URL en el prompt, reemplazamos la URL base del plan
    if extracted_url:
        if not extracted_url.startswith("http"):
            extracted_url = "https://" + extracted_url

        is_reviewstar = "reviewstar" in extracted_url.lower()

        if is_reviewstar:
            if plan and plan[0]["action"] == "open_url":
                plan[0]["value"] = extracted_url
        else:
            # For non-reviewstar URLs, ONLY use the generic plan, because specific selectors will fail
            plan = [
                {"action": "open_url", "value": extracted_url},
                {"action": "validate_text", "selector": "body", "value": ""},
            ]

    return plan


def _plan_with_gemini(prompt: str, api_key: str) -> list[dict]:
    """
    Llama a Gemini para generar un plan de prueba estructurado.
    Devuelve una lista de pasos en formato dict.
    """
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

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


def generate_test_plan(prompt: str) -> list[dict]:
    """
    Punto de entrada principal del planner.
    1. Intenta usar Gemini si esta configurado.
    2. Si falla o no esta disponible, usa plan simulado.
    """
    api_key = os.getenv("GEMINI_API_KEY", "")

    if GEMINI_AVAILABLE and api_key:
        try:
            _safe_print("Usando Gemini para generar el plan de prueba...")
            return _plan_with_gemini(prompt, api_key)
        except Exception as e:
            _safe_print(f"Gemini fallo ({e}), usando plan simulado.")

    _safe_print("Usando plan simulado (modo demo)...")
    return _keyword_match(prompt)