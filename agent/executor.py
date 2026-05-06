"""
executor.py - Dispatcher de módulos de ejecución
Enruta los pasos de prueba al ejecutor correcto según el tipo de test.
Soporta: web (Selenium), desktop (placeholder), mobile (placeholder)
"""

from . import executor_web, executor_desktop, executor_mobile


def run_test(
    test_name: str,
    steps: list[dict],
    test_type: str = "web",
    headless: bool = True,
    **kwargs
) -> dict:
    """
    Ejecuta un test usando el ejecutor apropiado según el tipo.

    Args:
        test_name: Nombre descriptivo del test
        steps: Lista de pasos a ejecutar (generados por planner)
        test_type: Tipo de test ("web", "desktop", "mobile")
        headless: Si True, ejecuta sin ventana visible (aplica a web)
        **kwargs: Argumentos adicionales para el ejecutor específico

    Returns:
        {
            "test_name": str,
            "status": "PASS" | "FAIL" | "SKIPPED",
            "steps": [...],
            "error": str
        }
    """
    test_type = test_type.lower().strip()

    if test_type == "web":
        return executor_web.run_test(test_name, steps, headless=headless, **kwargs)
    elif test_type == "desktop":
        return executor_desktop.run_test(test_name, steps, **kwargs)
    elif test_type == "mobile":
        return executor_mobile.run_test(test_name, steps, **kwargs)
    else:
        return {
            "test_name": test_name,
            "status": "FAIL",
            "steps": [],
            "error": f"Tipo de test desconocido: '{test_type}'. Use 'web', 'desktop' o 'mobile'.",
        }
