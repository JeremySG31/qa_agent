"""
executor_desktop.py - Módulo de ejecución para desktop automation
PLACEHOLDER - Estructura lista para futuras implementaciones con PyAutoGUI, UIA, etc.
"""


def run_test(test_name: str, steps: list[dict], **kwargs) -> dict:
    """
    Ejecuta pasos de automatización desktop.
    [PLACEHOLDER] Actualmente retorna simulación.

    Args:
        test_name: Nombre descriptivo del test
        steps: Lista de pasos a ejecutar
        **kwargs: Argumentos adicionales

    Returns:
        {
            "test_name": str,
            "status": "PASS" | "FAIL",
            "steps": [...],
            "error": str
        }
    """
    print(f"⏳ Desktop automation aún no implementada: {test_name}")

    executed_steps = []
    for step in steps:
        executed_steps.append({
            "action": step.get("action", ""),
            "status": "skipped",
            "detail": "[PLACEHOLDER] Desktop automation no implementada",
            "selector": step.get("selector", ""),
            "value": step.get("value", ""),
        })

    return {
        "test_name": test_name,
        "status": "SKIPPED",
        "steps": executed_steps,
        "error": "Desktop automation is not yet implemented. Use --type web for web testing.",
    }
