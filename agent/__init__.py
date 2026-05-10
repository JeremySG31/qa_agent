# 🤖 Paquete del agente QA local con IA
"""
Módulo principal del agente de automatización QA.

Submódulos:
  - planner: Generación de planes de prueba desde prompts (LLM)
  - executor: Ejecución de pasos web con Selenium
  - reporter: Guardado y carga de resultados JSON
"""

from .planner import generate_test_plan
from .executor import run_test
from .reporter import save_result, load_all_results, clear_results

__all__ = [
    "generate_test_plan",
    "run_test",
    "save_result",
    "load_all_results",
    "clear_results",
]

