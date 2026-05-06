"""
executor_web.py - Módulo de ejecución web con Selenium
Toma los pasos generados por el planner y los ejecuta en el navegador.
Soporta Edge (predeterminado) y Chrome como fallback automático.
"""

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, WebDriverException
)

# Intentar importar webdriver-manager para Edge y Chrome
try:
    from selenium.webdriver.edge.service import Service as EdgeService
    from webdriver_manager.microsoft import EdgeChromiumDriverManager
    EDGE_MANAGER_AVAILABLE = True
except ImportError:
    EDGE_MANAGER_AVAILABLE = False

try:
    from selenium.webdriver.chrome.service import Service as ChromeService
    from webdriver_manager.chrome import ChromeDriverManager
    CHROME_MANAGER_AVAILABLE = True
except ImportError:
    CHROME_MANAGER_AVAILABLE = False


# Tiempo máximo de espera para encontrar elementos (segundos)
WAIT_TIMEOUT = 15


def _build_driver(headless: bool = True):
    """
    Intenta iniciar Edge primero (ya instalado en Windows).
    Si falla, intenta Chrome como fallback.
    headless=True → sin ventana visible.
    headless=False → muestra el navegador (útil para ver qué hace el agente).
    """
    # ── Intentar Edge ──────────────────────────────────────────────
    try:
        options = EdgeOptions()
        if headless:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1280,800")
        options.add_argument("--log-level=3")
        # Deshabilitar notificaciones y popups que interfieren con las pruebas
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-popup-blocking")

        if EDGE_MANAGER_AVAILABLE:
            service = EdgeService(EdgeChromiumDriverManager().install())
            driver = webdriver.Edge(service=service, options=options)
        else:
            driver = webdriver.Edge(options=options)

        print("🌐 Navegador: Microsoft Edge")
        return driver

    except Exception as edge_err:
        print(f"⚠️  Edge no disponible ({edge_err}), intentando Chrome...")

    # ── Fallback: Chrome ───────────────────────────────────────────
    options = ChromeOptions()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280,800")
    options.add_argument("--log-level=3")
    options.add_argument("--disable-notifications")

    if CHROME_MANAGER_AVAILABLE:
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
    else:
        driver = webdriver.Chrome(options=options)

    print("🌐 Navegador: Google Chrome")
    return driver


def _execute_step(driver: webdriver.Chrome, step: dict, wait: WebDriverWait) -> dict:
    """
    Ejecuta un único paso y devuelve un dict con el resultado.
    Estructura de retorno: {"action": ..., "status": "ok"/"error", "detail": ...}
    """
    action  = step.get("action", "")
    value   = step.get("value", "")
    selector= step.get("selector", "")

    result = {"action": action, "selector": selector, "value": value}

    try:
        if action == "open_url":
            driver.get(value)
            result["status"] = "ok"
            result["detail"] = f"Abrió: {value}"

        elif action == "find_and_type":
            element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
            element.clear()
            element.send_keys(value)
            result["status"] = "ok"
            result["detail"] = f"Escribió '{value}' en '{selector}'"

        elif action == "click":
            element = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
            element.click()
            result["status"] = "ok"
            result["detail"] = f"Hizo clic en '{selector}'"

        elif action == "validate_text":
            element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
            actual_text = element.text
            if value.lower() in actual_text.lower():
                result["status"] = "ok"
                result["detail"] = f"Validación OK: '{value}' encontrado en '{selector}'"
            else:
                result["status"] = "error"
                result["detail"] = f"Esperado: '{value}' | Encontrado: '{actual_text}'"

        elif action == "validate_url":
            # Espera hasta que la URL contenga el valor esperado (útil tras un redirect)
            time.sleep(1.5)
            current_url = driver.current_url
            if value.lower() in current_url.lower():
                result["status"] = "ok"
                result["detail"] = f"URL OK: '{current_url}' contiene '{value}'"
            else:
                result["status"] = "error"
                result["detail"] = f"URL inesperada: '{current_url}' (esperaba '{value}')"

        elif action == "validate_exists":
            # Verifica que al menos uno de los selectores separados por coma exista
            selectors = [s.strip() for s in selector.split(",")]
            found = False
            for sel in selectors:
                try:
                    driver.find_element(By.CSS_SELECTOR, sel)
                    found = True
                    selector = sel  # guardar cuál se encontró
                    break
                except NoSuchElementException:
                    continue
            if found:
                result["status"] = "ok"
                result["detail"] = f"Elemento encontrado: '{selector}'"
            else:
                result["status"] = "error"
                result["detail"] = f"Ningún selector encontrado: '{selector}'"

        else:
            result["status"] = "error"
            result["detail"] = f"Acción desconocida: '{action}'"

    except TimeoutException:
        result["status"] = "error"
        result["detail"] = f"Timeout: elemento '{selector}' no encontrado en {WAIT_TIMEOUT}s"
    except NoSuchElementException:
        result["status"] = "error"
        result["detail"] = f"Elemento no encontrado: '{selector}'"
    except WebDriverException as e:
        result["status"] = "error"
        result["detail"] = f"WebDriver error: {str(e)[:200]}"

    # Pequeña pausa entre pasos para estabilidad
    time.sleep(0.5)
    return result


def run_test(test_name: str, steps: list[dict], headless: bool = True) -> dict:
    """
    Ejecuta todos los pasos de una prueba web y devuelve el reporte completo.

    Args:
        test_name: Nombre descriptivo del test
        steps: Lista de pasos a ejecutar (generados por planner)
        headless: Si True, ejecuta sin ventana visible

    Returns:
        {
            "test_name": str,
            "status": "PASS" | "FAIL",
            "steps": [...],
            "error": str
        }
    """
    driver = None
    executed_steps = []
    overall_status = "PASS"
    first_error = ""

    try:
        driver = _build_driver(headless=headless)
        wait   = WebDriverWait(driver, WAIT_TIMEOUT)

        print(f"🚀 Ejecutando: {test_name} ({len(steps)} pasos)")

        for i, step in enumerate(steps, 1):
            print(f"   Paso {i}/{len(steps)}: {step.get('action')} ...")
            result = _execute_step(driver, step, wait)
            executed_steps.append(result)

            if result["status"] == "error":
                overall_status = "FAIL"
                if not first_error:
                    first_error = result["detail"]
                print(f"   ❌ {result['detail']}")
            else:
                print(f"   ✅ {result['detail']}")

    except Exception as e:
        overall_status = "FAIL"
        first_error = f"Error al iniciar driver: {str(e)}"
        print(f"💥 {first_error}")

    finally:
        if driver:
            driver.quit()

    return {
        "test_name": test_name,
        "status":    overall_status,
        "steps":     executed_steps,
        "error":     first_error,
    }
