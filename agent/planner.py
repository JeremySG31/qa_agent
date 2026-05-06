"""
planner.py - Módulo del agente LLM
Convierte prompts en lenguaje natural a pasos de prueba estructurados.
Intenta usar Gemini API; si no está disponible, usa respuestas simuladas.
"""

import os
import json
import re

# Intentar importar Google Generative AI (Gemini)
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


# ──────────────────────────────────────────────
# Plantillas de pasos simulados para demos rápidas
# ──────────────────────────────────────────────
BASE_URL = "https://reviewstar-web.vercel.app"

SIMULATED_PLANS = {
    # ── Página principal ──────────────────────────────────────────
    "inicio": [
        {"action": "open_url",     "value": f"{BASE_URL}/index.html"},
        {"action": "validate_text","selector": "h1",          "value": "ReviewStar"},
        {"action": "validate_text","selector": "body",         "value": "Iniciar sesión"},
        {"action": "validate_text","selector": "body",         "value": "Registrarse"},
    ],

    # ── Login con credenciales válidas ────────────────────────────
    "login": [
        {"action": "open_url",      "value": f"{BASE_URL}/login.html"},
        {"action": "validate_text", "selector": "h2",          "value": "Iniciar sesión"},
        {"action": "find_and_type", "selector": "input[type='email']",    "value": "test@reviewstar.com"},
        {"action": "find_and_type", "selector": "input[type='password']", "value": "Test1234!"},
        {"action": "click",         "selector": "button[type='submit']"},
        {"action": "validate_url",  "value": BASE_URL},
    ],

    # ── Login con credenciales inválidas (validar mensaje de error) ──
    "login invalido": [
        {"action": "open_url",      "value": f"{BASE_URL}/login.html"},
        {"action": "find_and_type", "selector": "input[type='email']",    "value": "noexiste@fake.com"},
        {"action": "find_and_type", "selector": "input[type='password']", "value": "clavemalísima"},
        {"action": "click",         "selector": "button[type='submit']"},
        {"action": "validate_exists","selector": ".error-message, .alert, [class*='error'], [class*='alert']"},
    ],

    # ── Registro de nuevo usuario ─────────────────────────────────
    "registro": [
        {"action": "open_url",      "value": f"{BASE_URL}/register.html"},
        {"action": "validate_text", "selector": "h2",                     "value": "Registrarse"},
        {"action": "find_and_type", "selector": "input[type='text'], input[placeholder*='suario'], input[placeholder*='sername']",
                                    "value": "TestUser123"},
        {"action": "find_and_type", "selector": "input[type='email']",    "value": "testuser123@mail.com"},
        {"action": "find_and_type", "selector": "input[type='password']", "value": "Secure123!"},
        {"action": "click",         "selector": "button[type='submit']"},
    ],

    # ── Navegación al feed ────────────────────────────────────────
    "feed": [
        {"action": "open_url",      "value": f"{BASE_URL}/feed.html"},
        {"action": "validate_text", "selector": "body",    "value": "ReviewStar"},
    ],

    # ── Verificar links de navegación desde el home ───────────────
    "navegacion": [
        {"action": "open_url",      "value": f"{BASE_URL}/index.html"},
        {"action": "validate_text", "selector": "body",     "value": "Iniciar sesión"},
        {"action": "click",         "selector": "a[href*='login']"},
        {"action": "validate_text", "selector": "h2",       "value": "Iniciar sesión"},
        {"action": "open_url",      "value": f"{BASE_URL}/index.html"},
        {"action": "click",         "selector": "a[href*='register']"},
        {"action": "validate_text", "selector": "h2",       "value": "Registrarse"},
    ],

    # ── Verificar que la página olvidé contraseña existe ─────────
    "forgot": [
        {"action": "open_url",      "value": f"{BASE_URL}/login.html"},
        {"action": "click",         "selector": "a[href*='forgot']"},
        {"action": "validate_text", "selector": "body",     "value": "contraseña"},
    ],

    # ── Default: verificar home carga correctamente ───────────────
    "default": [
        {"action": "open_url",      "value": f"{BASE_URL}/index.html"},
        {"action": "validate_text", "selector": "h1",       "value": "ReviewStar"},
        {"action": "validate_text", "selector": "body",     "value": "reseñas"},
    ],
}


def _keyword_match(prompt: str) -> list[dict]:
    """Selecciona un plan simulado según palabras clave en el prompt."""
    prompt_lower = prompt.lower()
    # Mapeo de palabras clave → clave del plan
    keyword_map = {
        "login invalido":  ["login inv", "credencial", "contraseña incorrecta", "usuario incorrecto"],
        "login":           ["login", "iniciar sesión", "inicia sesión", "sign in"],
        "registro":        ["registro", "registrar", "register", "sign up", "crear cuenta"],
        "feed":            ["feed", "explorar", "reseñas recientes"],
        "navegacion":      ["navegaci", "navegar", "links", "enlaces", "menú"],
        "forgot":          ["forgot", "olvidé", "olvidaste", "recuperar contraseña"],
        "inicio":          ["inicio", "home", "página principal", "index"],
    }
    for plan_key, keywords in keyword_map.items():
        if any(kw in prompt_lower for kw in keywords):
            return SIMULATED_PLANS[plan_key]
    return SIMULATED_PLANS["default"]


def _plan_with_gemini(prompt: str, api_key: str) -> list[dict]:
    """
    Llama a Gemini para generar un plan de prueba estructurado.
    Devuelve una lista de pasos en formato dict.
    """
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

    system_instruction = """
Eres un experto en QA automatizado con Selenium.
El usuario te dará un prompt describiendo qué probar en una web.
Responde ÚNICAMENTE con un JSON válido (sin markdown, sin explicaciones):
[
  {"action": "open_url",     "value": "<url>"},
  {"action": "find_and_type","selector": "<css_selector>", "value": "<texto>"},
  {"action": "click",        "selector": "<css_selector>"},
  {"action": "validate_text","selector": "<css_selector>", "value": "<texto esperado>"}
]
Acciones permitidas: open_url, find_and_type, click, validate_text.
Usa selectores CSS reales. Si no conoces la URL exacta, usa una conocida de práctica como
https://practicetestautomation.com/practice-test-login/
"""

    response = model.generate_content(system_instruction + "\nPrompt: " + prompt)
    raw = response.text.strip()

    # Limpiar posibles bloques markdown ```json ... ```
    raw = re.sub(r"```(?:json)?", "", raw).strip().strip("`")
    steps = json.loads(raw)
    return steps


def generate_test_plan(prompt: str) -> list[dict]:
    """
    Punto de entrada principal del planner.
    1. Intenta usar Gemini si está configurado.
    2. Si falla o no está disponible, usa plan simulado.
    """
    api_key = os.getenv("GEMINI_API_KEY", "")

    if GEMINI_AVAILABLE and api_key:
        try:
            print("🤖 Usando Gemini para generar el plan de prueba...")
            return _plan_with_gemini(prompt, api_key)
        except Exception as e:
            print(f"⚠️  Gemini falló ({e}), usando plan simulado.")

    print("🔧 Usando plan simulado (modo demo)...")
    return _keyword_match(prompt)