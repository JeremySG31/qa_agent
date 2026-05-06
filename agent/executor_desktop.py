"""
executor_desktop.py - Módulo de ejecución para desktop automation usando PyAutoGUI
"""

import time
import subprocess
import os
import pyautogui

# Configuración de seguridad de PyAutoGUI
pyautogui.FAILSAFE = True  # Mueve el ratón a una esquina para abortar
pyautogui.PAUSE = 0.5      # Pausa entre comandos

def _execute_step(step: dict) -> dict:
    """
    Ejecuta un único paso de desktop automation.
    """
    action = step.get("action", "")
    value = step.get("value", "")
    selector = step.get("selector", "") # Puede ser coordenadas "x,y" o ruta de imagen

    result = {"action": action, "selector": selector, "value": value}

    try:
        if action == "open_app":
            # Intentar abrir la aplicación (funciona en Windows)
            subprocess.Popen(value, shell=True)
            result["status"] = "ok"
            result["detail"] = f"Iniciando aplicación: {value}"
            time.sleep(2) # Esperar a que cargue

        elif action == "type_text":
            pyautogui.write(value, interval=0.1)
            result["status"] = "ok"
            result["detail"] = f"Escribió: '{value}'"

        elif action == "press_key":
            pyautogui.press(value)
            result["status"] = "ok"
            result["detail"] = f"Presionó tecla: {value}"

        elif action == "click":
            if "," in selector:
                # Coordenadas x,y
                x, y = map(int, selector.split(","))
                pyautogui.click(x, y)
                result["status"] = "ok"
                result["detail"] = f"Hizo clic en coordenadas: {x}, {y}"
            else:
                # Intentar buscar imagen si se provee una ruta
                if os.path.exists(selector):
                    location = pyautogui.locateOnScreen(selector, confidence=0.8)
                    if location:
                        pyautogui.click(location)
                        result["status"] = "ok"
                        result["detail"] = f"Hizo clic en imagen: {selector}"
                    else:
                        result["status"] = "error"
                        result["detail"] = f"No se encontró la imagen en pantalla: {selector}"
                else:
                    # Clic simple donde esté el ratón si no hay selector
                    pyautogui.click()
                    result["status"] = "ok"
                    result["detail"] = "Hizo clic en posición actual"

        elif action == "wait":
            seconds = float(value) if value else 1.0
            time.sleep(seconds)
            result["status"] = "ok"
            result["detail"] = f"Esperó {seconds} segundos"

        else:
            result["status"] = "error"
            result["detail"] = f"Acción desconocida: '{action}'"

    except Exception as e:
        result["status"] = "error"
        result["detail"] = f"Error en paso: {str(e)}"

    return result

def run_test(test_name: str, steps: list[dict], **kwargs) -> dict:
    """
    Ejecuta todos los pasos de una prueba desktop.
    """
    executed_steps = []
    overall_status = "PASS"
    first_error = ""

    print(f"🚀 Ejecutando Desktop Test: {test_name}")
    
    # Dar tiempo al usuario para cambiar de ventana si es necesario
    print("⏳ Iniciando en 3 segundos... prepara tu escritorio.")
    time.sleep(3)

    for i, step in enumerate(steps, 1):
        print(f"   Paso {i}/{len(steps)}: {step.get('action')} ...")
        result = _execute_step(step)
        executed_steps.append(result)

        if result["status"] == "error":
            overall_status = "FAIL"
            if not first_error:
                first_error = result["detail"]
            print(f"   ❌ {result['detail']}")
        else:
            print(f"   ✅ {result['detail']}")

    return {
        "test_name": test_name,
        "status": overall_status,
        "steps": executed_steps,
        "error": first_error,
    }
