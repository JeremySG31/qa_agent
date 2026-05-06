"""
executor_mobile.py - Módulo de ejecución para mobile testing usando ADB (Android)
"""

import time
import subprocess

def _run_adb(command: str):
    """Ejecuta un comando ADB y devuelve la salida."""
    full_cmd = f"adb {command}"
    res = subprocess.run(full_cmd, shell=True, capture_output=True, text=True)
    if res.returncode != 0:
        raise Exception(f"Error ADB: {res.stderr.strip()}")
    return res.stdout.strip()

def _execute_step(step: dict) -> dict:
    """
    Ejecuta un único paso de mobile automation vía ADB.
    """
    action = step.get("action", "")
    value = step.get("value", "")
    selector = step.get("selector", "") # Coordenadas "x,y"

    result = {"action": action, "selector": selector, "value": value}

    try:
        if action == "adb_open_app":
            # value debe ser el package name, ej: com.android.chrome
            _run_adb(f"shell monkey -p {value} 1")
            result["status"] = "ok"
            result["detail"] = f"Abrió app: {value}"
            time.sleep(3)

        elif action == "adb_tap":
            if "," in selector:
                x, y = map(int, selector.split(","))
                _run_adb(f"shell input tap {x} {y}")
                result["status"] = "ok"
                result["detail"] = f"Tap en: {x}, {y}"
            else:
                result["status"] = "error"
                result["detail"] = "Selector debe ser coordenadas x,y"

        elif action == "adb_type":
            # ADB no soporta espacios fácilmente, los reemplazamos por %s
            safe_text = value.replace(" ", "%s")
            _run_adb(f"shell input text {safe_text}")
            result["status"] = "ok"
            result["detail"] = f"Escribió: '{value}'"

        elif action == "adb_keyevent":
            # value debe ser el código numérico o nombre de la tecla (HOME, BACK)
            _run_adb(f"shell input keyevent {value}")
            result["status"] = "ok"
            result["detail"] = f"Presionó tecla: {value}"

        elif action == "adb_swipe":
            # selector: "x1,y1,x2,y2"
            coords = list(map(int, selector.split(",")))
            if len(coords) == 4:
                _run_adb(f"shell input swipe {coords[0]} {coords[1]} {coords[2]} {coords[3]}")
                result["status"] = "ok"
                result["detail"] = f"Swipe de ({coords[0]},{coords[1]}) a ({coords[2]},{coords[3]})"
            else:
                result["status"] = "error"
                result["detail"] = "Selector debe ser x1,y1,x2,y2"

        elif action == "wait":
            time.sleep(float(value or 1))
            result["status"] = "ok"
            result["detail"] = f"Esperó {value}s"

        else:
            result["status"] = "error"
            result["detail"] = f"Acción desconocida: '{action}'"

    except Exception as e:
        result["status"] = "error"
        result["detail"] = str(e)

    return result

def run_test(test_name: str, steps: list[dict], **kwargs) -> dict:
    """
    Ejecuta todos los pasos de una prueba mobile.
    """
    executed_steps = []
    overall_status = "PASS"
    first_error = ""

    print(f"📱 Ejecutando Mobile Test: {test_name}")
    
    try:
        # Verificar si hay dispositivos conectados
        devices = _run_adb("devices")
        if "device" not in devices.split("\n", 1)[1]:
            raise Exception("No hay dispositivos Android conectados vía ADB.")
    except Exception as e:
        return {
            "test_name": test_name,
            "status": "FAIL",
            "steps": [],
            "error": f"Error de conexión: {str(e)}",
        }

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
