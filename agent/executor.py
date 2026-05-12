"""
executor.py - Módulo de ejecución web con Selenium
Toma los pasos generados por el planner y los ejecuta en el navegador.
Detecta el navegador predeterminado del sistema.
"""

import time
import platform
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


def _build_driver(headless: bool = True, incognito: bool = False):
    """
    Inicializa el driver. Prioriza undetected_chromedriver para evitar bloqueos.
    """
    is_linux = platform.system() == "Linux"
    
    # 1. Intentar Undetected Chrome (Modo Sigilo)
    _safe_print("   [1/3] Iniciando motor de sigilo...")
    try:
        import undetected_chromedriver as uc
        options = uc.ChromeOptions()
        if headless or is_linux:
            options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
        
        if incognito:
            options.add_argument("--incognito")
        
        # Iniciar driver (sin subprocesos para mayor estabilidad en Windows)
        driver = uc.Chrome(options=options)
        driver.set_page_load_timeout(25)
        _safe_print("   [OK] Navegador: Chrome (Safe Mode)")
        return driver
    except Exception as e:
        _safe_print(f"   [!] Modo sigilo no disponible. Cambiando a estándar...")

    # 2. Fallback a Selenium estándar (Más rápido)
    _safe_print("   [2/3] Iniciando motor estándar...")
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
                
                # Configuración de Headless y Anti-Bot
                if headless or is_linux: 
                    options.add_argument("--headless=new")
                    options.add_argument("--no-sandbox")
                    options.add_argument("--disable-dev-shm-usage")
                    options.add_argument("--disable-gpu")
                
                options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
                options.add_experimental_option("excludeSwitches", ["enable-automation"])
                options.add_experimental_option('useAutomationExtension', False)
                
                options.add_argument("--log-level=3")
                options.add_argument("--window-size=1920,1080")
                if incognito:
                    options.add_argument("--incognito")
                
                chromium_path = shutil.which("chromium") or shutil.which("chromium-browser")
                if chromium_path: options.binary_location = chromium_path

                chromedriver_path = shutil.which("chromedriver") or shutil.which("chromium-chromedriver")
                
                try:
                    if chromedriver_path:
                        service = ChromeService(executable_path=chromedriver_path)
                        driver = webdriver.Chrome(service=service, options=options)
                    else:
                        driver = webdriver.Chrome(options=options)
                    
                    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
                    })
                    _safe_print(f"Navegador: Google Chrome (Standard Stealth)")
                    return driver
                except Exception as e:
                    errors.append(f"Chrome: {e}")

            elif browser == "edge":
                options = EdgeOptions()
                if headless or is_linux: 
                    options.add_argument("--headless=new")
                options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0")
                
                try:
                    driver = webdriver.Edge(options=options)
                    return driver
                except Exception as e:
                    errors.append(f"Edge: {e}")
        except Exception as e:
            errors.append(f"{browser}: {e}")

    raise Exception(f"No se pudo iniciar navegador. Errores: {' | '.join(errors)}")


def _check_for_blocks(driver):
    """Verifica si la página actual es un CAPTCHA o bloqueo."""
    page_source = driver.page_source.lower()
    page_title = driver.title.lower()
    if "captcha" in page_source or "unusual traffic" in page_source or "not a robot" in page_source:
        return True, "🚫 BLOQUEO DETECTADO: Google ha solicitado resolver un CAPTCHA. Sugerencia: Usa DuckDuckGo para este test."
    if "blocked" in page_title or "access denied" in page_title:
        return True, f"🚫 ACCESO DENEGADO: El sitio ha bloqueado la conexión. (Título: {driver.title})"
    return False, ""


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

    result = {"action": action, "selector": selector, "value": value}

    try:
        # ── Acciones de Correo y Dominio ────────────────────────────────────
        if action == "generate_email":
            mgr = SecureEmailManager()
            email = mgr.create_account(prefix=value if value else None)
            context["email"] = email
            result["status"] = "ok"
            result["detail"] = f"Correo generado: {email}"
            result["email"] = email

        elif action == "wait_for_email":
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
        elif action == "open_url":
            if not value.startswith("http://") and not value.startswith("https://") and not value.startswith("data:"):
                value = "https://" + value
            driver.get(value)
            
            # Verificar si cargó un CAPTCHA o bloqueo tras abrir
            blocked, block_msg = _check_for_blocks(driver)
            if blocked:
                result["status"] = "error"
                result["detail"] = block_msg
                return result
                
            result["status"] = "ok"
            result["detail"] = f"Abrio: {value}"

        # ── Interacción con elementos ───────────────────────────────────────
        elif action in ("click", "find_and_type", "select_option"):
            # Soporte para selectores múltiples (ej: "link:Imágenes | link:Images")
            selectors_list = [s.strip() for s in selector.split("|")]
            element = None
            last_err = None
            
            # Diccionario de traducción automática para términos comunes de QA
            translation_map = {
                "imágenes": "images", "images": "imágenes",
                "videos": "videos", "noticias": "news", "news": "noticias",
                "mapas": "maps", "maps": "mapas",
                "configuración": "settings", "settings": "configuración",
                "buscar": "search", "search": "buscar",
                "entrar": "login", "login": "entrar", "iniciar sesión": "login"
            }
            
            for current_sel in selectors_list:
                # ... (lógica anterior de By)
                by_strategy = By.CSS_SELECTOR
                clean_selector = current_sel
                
                if current_sel.startswith("link:"):
                    by_strategy = By.PARTIAL_LINK_TEXT
                    clean_selector = current_sel[5:]
                elif current_sel.startswith("xpath:"):
                    by_strategy = By.XPATH
                    clean_selector = current_sel[6:]

                try:
                    element = wait.until(EC.element_to_be_clickable((by_strategy, clean_selector)))
                    # Si funciona, guardamos este selector como el exitoso
                    result["selector"] = current_sel
                    break
                except Exception as e:
                    last_err = e
                    # Si es un link y está en nuestro mapa, intentamos la traducción automáticamente
                    if by_strategy == By.PARTIAL_LINK_TEXT:
                        term = clean_selector.lower().strip()
                        if term in translation_map:
                            try:
                                translated = translation_map[term]
                                element = wait.until(EC.element_to_be_clickable((by_strategy, translated)))
                                result["selector"] = f"{current_sel} (via {translated})"
                                break
                            except: pass
                    
                    # Búsqueda de Último Recurso (Solo si es CSS y falló el normal)
                    if by_strategy == By.CSS_SELECTOR and len(clean_selector) < 50:
                        try:
                            smart_xpath = f"//*[text()='{clean_selector}' or contains(text(), '{clean_selector}') or @placeholder='{clean_selector}' or @aria-label='{clean_selector}']"
                            element = wait.until(EC.element_to_be_clickable((By.XPATH, smart_xpath)))
                            result["selector"] = f"{current_sel} (SmartSearch)"
                            break
                        except: continue
                    continue
            
            if not element:
                # ── FALLBACK DE EMERGENCIA AGRESIVO ────────────────────────
                is_ddg_images = "duckduckgo.com" in driver.current_url and ("images" in driver.current_url or "ia=" in driver.current_url)
                if is_ddg_images:
                    _safe_print("   [Emergency] Buscando cualquier resultado de imagen...")
                    # Buscar cualquier link que contenga una imagen o tenga clase de tile
                    for fallback in [".tile--img", "img.tile--img__img", "a[data-zci-link='images']", ".tile", "img"]:
                        try:
                            elements = driver.find_elements(By.CSS_SELECTOR, fallback)
                            for el in elements:
                                if el.is_displayed():
                                    element = el
                                    _safe_print(f"   [ContextFallback] Éxito con: {fallback}")
                                    break
                            if element: break
                        except: continue
                
                if not element:
                    err_type = type(last_err).__name__
                    err_msg = str(last_err).split('\n')[0] or "Sin detalle"
                    curr_url = driver.current_url
                    raise Exception(f"Falla total en {selectors_list} en URL: {curr_url}. Error: {err_type}: {err_msg}")
            
            if action == "click":
                try: driver.execute_script("arguments[0].scrollIntoView({block:'center'});", element)
                except: pass
                time.sleep(0.3)
                
                try:
                    element.click()
                except Exception:
                    # Forzar clic por JS si el normal falla
                    driver.execute_script("arguments[0].click();", element)
                
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
                try:
                    pixels = int(value) if value else 500
                except (ValueError, TypeError):
                    pixels = 500
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
    headless: bool = True,
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
        driver = _build_driver(headless=headless, incognito=incognito)
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
    headless: bool = True,
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
        driver = _build_driver(headless=headless, incognito=incognito)
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
