"""
planner.py - Módulo del agente LLM
Usa OpenRouter (modelo gratuito) como proveedor centralizado de IA.
La API key es del servidor; los usuarios no necesitan configurar nada.
"""

import os
import json
import re
import requests
from pathlib import Path
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()

# Modelo gratuito de OpenRouter (sin costo por token)
# Opciones probadas y funcionales:
#   openai/gpt-oss-120b:free              - Más completo, genera flujos detallados
#   openai/gpt-oss-20b:free              - Rápido pero planes simples
#   nvidia/nemotron-3-super-120b-a12b:free - Alternativa
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-oss-120b:free")
# Modelos de respaldo si el principal falla
FALLBACK_MODELS = [
    "openai/gpt-oss-120b:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "openai/gpt-oss-20b:free",
]

SYSTEM_INSTRUCTION = (
    "Eres un experto en QA automatizado con Selenium. "
    "Tu tarea es generar un plan de prueba COMPLETO que cubra TODOS los pasos necesarios para ejecutar la accion del usuario. "
    "Responde UNICAMENTE con un array JSON de objetos, sin texto adicional, sin markdown, sin explicaciones. "
    'Ejemplo para buscar algo: [{"action": "open_url", "value": "https://duckduckgo.com"}, {"action": "find_and_type", "selector": "[name=\'q\']", "value": "python"}, {"action": "press_key", "selector": "[name=\'q\']", "value": "enter"}, {"action": "wait", "value": "2"}, {"action": "validate_exists", "selector": "[data-testid=\'result\']"}] '
    "Acciones disponibles: open_url (value=URL), find_and_type (selector=CSS, value=texto), click (selector=CSS), "
    "hover (selector=CSS), press_key (selector=CSS opcional, value=tecla), select_option (selector=CSS, value=texto), "
    "scroll_to (selector=CSS), validate_text (selector=CSS, value=texto esperado), "
    "validate_url (value=URL parcial), validate_exists (selector=CSS), wait (value=segundos), screenshot. "
    "REGLA DE ORO: Google BLOQUEA este proyecto con CAPTCHAs. ESTÁ PROHIBIDO usar google.com a menos que el usuario escriba explícitamente la palabra 'Google'. Para cualquier búsqueda general o de imágenes, usa SIEMPRE duckduckgo.com. "
    "Puedes usar el prefijo 'link:' para hacer clic por texto (ej: 'link:Imágenes') o 'xpath:' para selectores complejos. "
    "Si el usuario pide buscar algo, incluye siempre un paso de 'wait' (2 seg) tras presionar enter para dar tiempo a la carga. "
    "Usa selectores CSS reales, genéricos y conocidos. "
    "Mantén el plan en maximo 8 pasos pero asegurate de que sea COMPLETO y funcional."
)


def _safe_print(*args, **kwargs):
    try:
        print(*args, **kwargs)
    except (UnicodeEncodeError, OSError):
        try:
            text = " ".join(str(a) for a in args)
            print(text.encode("ascii", errors="replace").decode("ascii"), **kwargs)
        except Exception:
            pass


def _extract_json_steps(raw: str) -> list[dict]:
    """Extrae de forma robusta una lista JSON desde el texto crudo del LLM."""
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

    raise ValueError(f"No se pudo parsear JSON de la IA: {raw[:300]}")


def _fallback_plan(prompt: str) -> list[dict]:
    """Plan genérico si OpenRouter no está disponible."""
    url_match = re.search(r'(https?://[^\s]+|[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:/[^\s]*)?)', prompt)
    extracted_url = url_match.group(0) if url_match else None

    if extracted_url:
        if not extracted_url.startswith("http"):
            extracted_url = "https://" + extracted_url
        return [
            {"action": "open_url", "value": extracted_url},
            {"action": "validate_text", "selector": "body", "value": ""}
        ]

    return [
        {"action": "open_url", "value": "data:text/html,%3Ch1%3EIA%20no%20disponible%3C%2Fh1%3E"},
        {"action": "validate_text", "selector": "h1", "value": ""}
    ]


def _call_model(model: str, prompt: str) -> str:
    """Llama a un modelo específico en OpenRouter y retorna el texto crudo."""
    response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://qa-agent-web.firebaseapp.com",
            "X-Title": "QA Agent No-Code",
        },
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_INSTRUCTION},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 1024,
        },
        timeout=30,
    )

    if not response.ok:
        raise ValueError(f"HTTP {response.status_code}: {response.text[:200]}")

    data = response.json()
    if "error" in data:
        raise ValueError(data["error"].get("message", "Error desconocido"))

    content = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
    if not content:
        raise ValueError("Respuesta vacía del modelo")

    _safe_print(f"[OpenRouter:{model}] Tokens usados: {data.get('usage', {})}")
    if not content:
        _safe_print(f"[planner] Error: El modelo retornó una respuesta vacía.")
    else:
        _safe_print(f"[planner] Respuesta cruda (primeros 100 carac): {content[:100]}...")
    return content


def _plan_with_openrouter(prompt: str) -> list[dict]:
    """Llama a OpenRouter con fallback automático entre modelos gratuitos."""
    global OPENROUTER_API_KEY
    if not OPENROUTER_API_KEY:
        OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()

    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY no configurada en el servidor.")

    models_to_try = [OPENROUTER_MODEL] + FALLBACK_MODELS
    last_error = None
    _safe_print(f"[planner] Intentando generar plan para: {prompt[:50]}...")

    for model in models_to_try:
        try:
            raw = _call_model(model, prompt)
            return _extract_json_steps(raw)
        except Exception as e:
            _safe_print(f"[planner] Modelo {model} falló: {e}")
            last_error = e
            continue

    raise ValueError(f"Todos los modelos fallaron. Último error: {last_error}")


def generate_test_plan(prompt: str, **kwargs) -> list[dict]:
    """
    Punto de entrada principal.
    Usa OpenRouter (server-side) con fallback local si falla por red/IA.
    Propaga errores de configuración (API Key).
    """
    try:
        return _plan_with_openrouter(prompt)
    except ValueError as ve:
        # Si es un error de configuración o parsing crítico, lo propagamos
        if "API_KEY" in str(ve) or "JSON" in str(ve):
            raise ve
        return _fallback_plan(prompt)
    except Exception:
        return _fallback_plan(prompt)

