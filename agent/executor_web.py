"""
executor_web.py - Modulo de ejecucion web con Selenium
Toma los pasos generados por el planner y los ejecuta en el navegador.
Detecta el navegador predeterminado del sistema.

Acciones soportadas:
  open_url, find_and_type, click, validate_text, validate_url, validate_exists,
  wait, scroll_to, hover, press_key, select_option, screenshot,
  generate_email, wait_for_email
"""

import time
import platform
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, WebDriverException
)
from .domain_manager import SecureEmailManager

try:
    from selenium.webdriver.edge.service import Service as EdgeService
    from webdriver_manager.microsoft import EdgeChromiumDriverManager
    EDGE_MANAGER_AVAILABLE = True
except ImportError:
    EDGE_MANAGER_AVAILABLE = False

try:
    from selenium.webdriver.chrome.service import Service as ChromeService
    from webdriver_manager.chrome import ChromeDriverManager
    from webdriver_manager.core.os_manager import ChromeType
    CHROME_MANAGER_AVAILABLE = True
except ImportError:
    CHROME_MANAGER_AVAILABLE = False


WAIT_TIMEOUT = 15

KEY_MAP = {
    "enter": Keys.ENTER, "tab": Keys.TAB, "escape": Keys.ESCAPE,
    "esc": Keys.ESCAPE, "space": Keys.SPACE, "backspace": Keys.BACKSPACE,
    "delete": Keys.DELETE, "up": Keys.ARROW_UP, "down": Keys.ARROW_DOWN,
    "left": Keys.ARROW_LEFT, "right": Keys.ARROW_RIGHT, "home": Keys.HOME,
    "end": Keys.END, "pageup": Keys.PAGE_UP, "pagedown": Keys.PAGE_DOWN,
}


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


def _build_driver(incognito: bool = False):
    """
    Inicializa el driver (Chrome o Edge).
    El modo headless ahora es automático (solo en Linux).
    Si incognito=True, inicia el navegador en modo privado.
    """
    default = _get_default_browser()
    browsers_to_try = [default]
    for b in ["chrome", "edge"]:
        if b not in browsers_to_try:
            browsers_to_try.append(b)

    errors = []
    for browser in browsers_to_try:
        try:
            if browser == "chrome":
                import shutil
                options = ChromeOptions()
                is_linux = platform.system() == "Linux"
                
                # En Linux (Streamlit Cloud), forzamos headless para evitar crashes
                if is_linux: 
                    options.add_argument("--headless=new")
                    options.add_argument("--no-sandbox")
                    options.add_argument("--disable-dev-shm-usage")
                    options.add_argument("--disable-gpu")
                options.add_argument("--log-level=3")
                options.add_argument("--window-size=1920,1080")
                if incognito:
                    options.add_argument("--incognito")
                
                # Intentar detectar Chromium en Linux/Streamlit Cloud
                chromium_path = shutil.which("chromium") or shutil.which("chromium-browser")
                if chromium_path:
                    options.binary_location = chromium_path

                chromedriver_path = shutil.which("chromedriver") or shutil.which("chromium-chromedriver")
                
                try:
                    # 1. Intentar usar el driver del sistema si se encontró (ideal para Streamlit Cloud)
                    if chromedriver_path:
                        service = ChromeService(executable_path=chromedriver_path)
                        driver = webdriver.Chrome(service=service, options=options)
                        _safe_print("Navegador: Google Chrome / Chromium (System Driver)")
                        return driver
                    
                    # 2. Intentar Selenium Manager nativo (Selenium >= 4.6)
                    try:
                        driver = webdriver.Chrome(options=options)
                        _safe_print("Navegador: Google Chrome (Selenium Manager)")
                        return driver
                    except Exception as inner_e:
                        # 3. Fallback a webdriver-manager si falla lo anterior
                        if CHROME_MANAGER_AVAILABLE:
                            service = ChromeService(ChromeDriverManager().install())
                            driver = webdriver.Chrome(service=service, options=options)
                            _safe_print("Navegador: Google Chrome (Webdriver Manager)")
                            return driver
                        raise inner_e
                except Exception as e:
                    _safe_print(f"Fallo Chrome: {e}")
                    errors.append(f"Chrome: {e}")

            elif browser == "edge":
                options = EdgeOptions()
                is_linux = platform.system() == "Linux"
                
                if is_linux: 
                    options.add_argument("--headless=new")
                    options.add_argument("--no-sandbox")
                    options.add_argument("--disable-dev-shm-usage")
                    options.add_argument("--disable-gpu")
                options.add_argument("--log-level=3")
                options.add_argument("--window-size=1920,1080")
                if incognito:
                    options.add_argument("-inPrivate")
                
                try:
                    # 1. Intentar Selenium Manager nativo primero (evita errores de red de webdriver-manager)
                    try:
                        driver = webdriver.Edge(options=options)
                        _safe_print("Navegador: Microsoft Edge (Selenium Manager)")
                        return driver
                    except Exception as inner_e:
                        # 2. Fallback a webdriver-manager
                        if EDGE_MANAGER_AVAILABLE:
                            service = EdgeService(EdgeChromiumDriverManager().install())
                            driver = webdriver.Edge(service=service, options=options)
                            _safe_print("Navegador: Microsoft Edge (Webdriver Manager)")
                            return driver
                        raise inner_e
                except Exception as e:
                    _safe_print(f"Fallo Edge: {e}")
                    errors.append(f"Edge: {e}")
        except Exception as e:
            _safe_print(f"No se pudo iniciar {browser}: {e}")
            errors.append(f"{browser}: {e}")

    raise Exception(f"No se pudo iniciar navegador. Errores: {' | '.join(errors)}")


def _execute_step(driver, step: dict, wait, context: dict, screenshot_on_fail: bool = False) -> dict:
    """Ejecuta un unico paso y devuelve un dict con el resultado."""
    action   = step.get("action", "")
    value    = step.get("value", "") or ""
    selector = step.get("selector", "") or ""

    # Reemplazar placeholders en el valor (ej: {{email}})
    if isinstance(value, str) and "{{" in value:
        for k, v in context.items():
            value = value.replace(f"{{{{{k}}}}}", str(v))

    result = {"action": action, "selector": selector, "value": value}

    try:
        # ── Acciones de Correo y Dominio ────────────────────────────────────
        if action == "generate_email":
            if not SecureEmailManager:
                raise Exception("Librería domain_manager no encontrada.")
            mgr = SecureEmailManager()
            email = mgr.create_account(prefix=value if value else None)
            context["email"] = email
            result["status"] = "ok"
            result["detail"] = f"Correo generado: {email}"
            result["email"] = email

        elif action == "wait_for_email":
            if not SecureEmailManager:
                raise Exception("Librería domain_manager no encontrada.")
            email_addr = value or context.get("email")
            if not email_addr:
                raise Exception("No se especificó dirección de correo ni hay una generada.")
            
            mgr = SecureEmailManager()
            msg = mgr.wait_for_email(email_addr, timeout=30)
            if msg:
                context["last_email_subject"] = msg.get("subject")
                context["last_email_body"] = msg.get("text")
                result["status"] = "ok"
                result["detail"] = f"Correo recibido: {msg.get('subject')}"
                result["message"] = msg
            else:
                result["status"] = "error"
                result["detail"] = "Timeout esperando correo."

        # ── Acciones de navegación ──────────────────────────────────────────
        if action == "open_url":
            if not value.startswith("http://") and not value.startswith("https://"):
                value = "https://" + value
            driver.get(value)
            result["status"] = "ok"
            result["detail"] = f"Abrio: {value}"

        # ── Interacción con elementos ───────────────────────────────────────
        elif action in ("click", "find_and_type", "select_option"):
            element = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
            
            if action == "click":
                element.click()
                result["detail"] = f"Hizo clic en '{selector}'"
            elif action == "find_and_type":
                element.clear()
                element.send_keys(value)
                result["detail"] = f"Escribio '{value}' en '{selector}'"
            elif action == "select_option":
                sel_obj = Select(element)
                try:
                    sel_obj.select_by_visible_text(value)
                except Exception:
                    sel_obj.select_by_value(value)
                result["detail"] = f"Seleccionado '{value}' en '{selector}'"
            result["status"] = "ok"

        elif action == "hover":
            element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
            ActionChains(driver).move_to_element(element).perform()
            time.sleep(0.3)
            result["status"] = "ok"
            result["detail"] = f"Hover sobre '{selector}'"

        elif action == "press_key":
            key = KEY_MAP.get(value.lower().strip(), value)
            if selector:
                element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                element.send_keys(key)
            else:
                ActionChains(driver).send_keys(key).perform()
            result["status"] = "ok"
            result["detail"] = f"Tecla '{value}' presionada" + (f" en '{selector}'" if selector else "")

        # ── Scroll ──────────────────────────────────────────────────────────
        elif action == "scroll_to":
            if selector:
                element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                driver.execute_script("arguments[0].scrollIntoView({behavior:'smooth',block:'center'});", element)
            else:
                pixels = int(value) if value else 500
                driver.execute_script(f"window.scrollBy(0, {pixels});")
            time.sleep(0.4)
            result["status"] = "ok"
            result["detail"] = f"Scroll hasta '{selector or value}'"

        # ── Espera ──────────────────────────────────────────────────────────
        elif action == "wait":
            secs = float(value) if value else 1.0
            time.sleep(secs)
            result["status"] = "ok"
            result["detail"] = f"Esperó {secs}s"

        # ── Validaciones ────────────────────────────────────────────────────
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
            time.sleep(1.0)
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

        # ── Captura ─────────────────────────────────────────────────────────
        elif action == "screenshot":
            base64_img = driver.get_screenshot_as_base64()
            result["status"] = "ok"
            result["detail"] = "Captura realizada"
            result["screenshot"] = base64_img

        else:
            result["status"] = "error"
            result["detail"] = f"Accion desconocida: '{action}'"

    except TimeoutException:
        result["status"] = "error"
        result["detail"] = f"Timeout: elemento '{selector}' no encontrado"
    except NoSuchElementException:
        result["status"] = "error"
        result["detail"] = f"Elemento no encontrado: '{selector}'"
    except WebDriverException as e:
        msg = str(e).split('\n')[0]
        result["status"] = "error"
        result["detail"] = f"WebDriver error: {msg}"
    except Exception as e:
        result["status"] = "error"
        result["detail"] = f"Error inesperado: {str(e)[:120]}"

    # Captura automática en fallo desactivada para evitar carpetas locales

    return result


# ══════════════════════════════════════════════════════════════════════════════
# EJECUCIÓN CLÁSICA (bloqueante)
# ══════════════════════════════════════════════════════════════════════════════

def run_test(
    test_name: str,
    steps: list[dict],
    incognito: bool = False,
    highlight: bool = False,
    timeout: int = 15,
    step_delay: float = 0.5,
    screenshot_on_fail: bool = False,
) -> dict:
    """
    Ejecuta todos los pasos de una prueba de forma síncrona.
    """
    driver = None
    executed_steps = []
    overall_status = "PASS"
    first_error = ""

    global WAIT_TIMEOUT
    WAIT_TIMEOUT = timeout

    try:
        driver = _build_driver(incognito=incognito)
        wait   = WebDriverWait(driver, timeout)
        _safe_print(f"Ejecutando: {test_name} ({len(steps)} pasos)")

        test_context = {}
        for i, step in enumerate(steps, 1):
            _safe_print(f"   Paso {i}/{len(steps)}: {step.get('action')} ...")
            result = _execute_step(driver, step, wait, test_context, screenshot_on_fail=screenshot_on_fail)
            executed_steps.append(result)
            if result["status"] == "error":
                overall_status = "FAIL"
                if not first_error:
                    first_error = result["detail"]
                _safe_print(f"   Error: {result['detail']}")
            else:
                _safe_print(f"   OK: {result['detail']}")
            if step_delay > 0:
                time.sleep(step_delay)

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


# ══════════════════════════════════════════════════════════════════════════════
# EJECUCIÓN STREAMING (genera eventos en tiempo real para la UI)
# ══════════════════════════════════════════════════════════════════════════════

def run_test_streaming(
    test_name: str,
    steps: list[dict],
    incognito: bool = False,
    highlight: bool = False,
    timeout: int = 15,
    step_delay: float = 0.5,
    screenshot_on_fail: bool = False,
):
    """
    Versión generadora para iterar y mostrar resultados en tiempo real en la UI.
    """
    driver = None
    executed_steps = []
    overall_status = "PASS"
    first_error = ""

    global WAIT_TIMEOUT
    WAIT_TIMEOUT = timeout

    yield {"type": "start", "total": len(steps)}

    try:
        driver = _build_driver(incognito=incognito)
        wait   = WebDriverWait(driver, timeout)

        yield {"type": "start", "test_name": test_name, "total": len(steps)}

        test_context = {}
        for i, step in enumerate(steps, 1):
            yield {"type": "step_start", "index": i, "total": len(steps), "step": step}

            result = _execute_step(driver, step, wait, test_context, screenshot_on_fail=screenshot_on_fail)
            executed_steps.append(result)

            if result["status"] == "error":
                overall_status = "FAIL"
                if not first_error:
                    first_error = result["detail"]

            yield {"type": "step_done", "index": i, "total": len(steps), "result": result}

            if step_delay > 0:
                time.sleep(step_delay)

    except Exception as e:
        overall_status = "FAIL"
        first_error = f"Error al iniciar driver: {str(e)}"
        yield {"type": "driver_error", "message": first_error}
    finally:
        if driver:
            driver.quit()

    yield {
        "type": "complete",
        "test_name": test_name,
        "status":    overall_status,
        "steps":     executed_steps,
        "error":     first_error,
    }
