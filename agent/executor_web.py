"""
executor_web.py - Modulo de ejecucion web con Selenium
Toma los pasos generados por el planner y los ejecuta en el navegador.
Detecta el navegador predeterminado del sistema.
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


WAIT_TIMEOUT = 15


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


def _get_default_browser():
    """Intenta detectar el navegador predeterminado en Windows."""
    try:
        import winreg
        path = r"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\https\UserChoice"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path) as key:
            prog_id, _ = winreg.QueryValueEx(key, "ProgId")
            if "Chrome" in prog_id: return "chrome"
            if "MSEdge" in prog_id: return "edge"
            if "Firefox" in prog_id: return "firefox"
    except Exception:
        pass
    return "chrome"


def _build_driver(headless: bool = True):
    """Intenta iniciar el navegador predeterminado del sistema."""
    default = _get_default_browser()

    browsers_to_try = [default]
    for b in ["chrome", "edge"]:
        if b not in browsers_to_try:
            browsers_to_try.append(b)

    for browser in browsers_to_try:
        try:
            if browser == "chrome":
                options = ChromeOptions()
                if headless: options.add_argument("--headless=new")
                options.add_argument("--log-level=3")
                if CHROME_MANAGER_AVAILABLE:
                    service = ChromeService(ChromeDriverManager().install())
                    driver = webdriver.Chrome(service=service, options=options)
                else:
                    driver = webdriver.Chrome(options=options)
                _safe_print(f"Navegador: Google Chrome")
                return driver

            elif browser == "edge":
                options = EdgeOptions()
                if headless: options.add_argument("--headless=new")
                options.add_argument("--log-level=3")
                if EDGE_MANAGER_AVAILABLE:
                    service = EdgeService(EdgeChromiumDriverManager().install())
                    driver = webdriver.Edge(service=service, options=options)
                else:
                    driver = webdriver.Edge(options=options)
                _safe_print(f"Navegador: Microsoft Edge")
                return driver
        except Exception as e:
            _safe_print(f"No se pudo iniciar {browser}: {e}")

    raise Exception("No se pudo iniciar ningun navegador compatible (Chrome/Edge).")


def _execute_step(driver, step: dict, wait) -> dict:
    """Ejecuta un unico paso y devuelve un dict con el resultado."""
    action   = step.get("action", "")
    value    = step.get("value", "")
    selector = step.get("selector", "")

    result = {"action": action, "selector": selector, "value": value}

    try:
        if action == "open_url":
            if not value.startswith("http://") and not value.startswith("https://"):
                value = "https://" + value
            driver.get(value)
            result["status"] = "ok"
            result["detail"] = f"Abrio: {value}"

        elif action == "find_and_type":
            element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
            element.clear()
            element.send_keys(value)
            result["status"] = "ok"
            result["detail"] = f"Escribio '{value}' en '{selector}'"

        elif action == "click":
            element = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
            element.click()
            result["status"] = "ok"
            result["detail"] = f"Hizo clic en '{selector}'"

        elif action == "validate_text":
            element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
            actual_text = element.text
            if not value or value.lower() in actual_text.lower():
                result["status"] = "ok"
                result["detail"] = f"Validacion OK: '{value}' encontrado en '{selector}'"
            else:
                result["status"] = "error"
                result["detail"] = f"Esperado: '{value}' | Encontrado: '{actual_text[:100]}'"

        elif action == "validate_url":
            time.sleep(1.5)
            current_url = driver.current_url
            if value.lower() in current_url.lower():
                result["status"] = "ok"
                result["detail"] = f"URL OK: '{current_url}' contiene '{value}'"
            else:
                result["status"] = "error"
                result["detail"] = f"URL inesperada: '{current_url}' (esperaba '{value}')"

        elif action == "validate_exists":
            selectors = [s.strip() for s in selector.split(",")]
            found = False
            for sel in selectors:
                try:
                    driver.find_element(By.CSS_SELECTOR, sel)
                    found = True
                    selector = sel
                    break
                except NoSuchElementException:
                    continue
            if found:
                result["status"] = "ok"
                result["detail"] = f"Elemento encontrado: '{selector}'"
            else:
                result["status"] = "error"
                result["detail"] = f"Ningun selector encontrado: '{selector}'"

        else:
            result["status"] = "error"
            result["detail"] = f"Accion desconocida: '{action}'"

    except TimeoutException:
        result["status"] = "error"
        result["detail"] = f"Timeout: elemento '{selector}' no encontrado en {WAIT_TIMEOUT}s"
    except NoSuchElementException:
        result["status"] = "error"
        result["detail"] = f"Elemento no encontrado: '{selector}'"
    except WebDriverException as e:
        msg = str(e).split('\n')[0]
        result["status"] = "error"
        result["detail"] = f"WebDriver error: {msg}"

    time.sleep(0.5)
    return result


def run_test(test_name: str, steps: list[dict], headless: bool = True) -> dict:
    """Ejecuta todos los pasos de una prueba web y devuelve el reporte."""
    driver = None
    executed_steps = []
    overall_status = "PASS"
    first_error = ""

    try:
        driver = _build_driver(headless=headless)
        wait   = WebDriverWait(driver, WAIT_TIMEOUT)

        _safe_print(f"Ejecutando: {test_name} ({len(steps)} pasos)")

        for i, step in enumerate(steps, 1):
            _safe_print(f"   Paso {i}/{len(steps)}: {step.get('action')} ...")
            result = _execute_step(driver, step, wait)
            executed_steps.append(result)

            if result["status"] == "error":
                overall_status = "FAIL"
                if not first_error:
                    first_error = result["detail"]
                _safe_print(f"   Error: {result['detail']}")
            else:
                _safe_print(f"   OK: {result['detail']}")

    except Exception as e:
        overall_status = "FAIL"
        first_error = f"Error al iniciar driver: {str(e)}"
        _safe_print(f"Error fatal: {first_error}")

    finally:
        if driver:
            driver.quit()

    return {
        "test_name": test_name,
        "status":    overall_status,
        "steps":     executed_steps,
        "error":     first_error,
    }
