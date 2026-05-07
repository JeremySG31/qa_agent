"""
main.py - Punto de entrada del agente QA
Acepta un prompt en lenguaje natural, genera el plan de prueba,
ejecuta la automatización y guarda los resultados.

Flujo:
    prompt (lenguaje natural) 
    → planner (IA / simulado) 
    → steps estructurados 
    → executor (Selenium/desktop/mobile)
    → resultado JSON 
    → dashboard (Streamlit)

Uso:
    python main.py "prueba el login de esta página"
    python main.py "busca algo en google" --type web --no-headless
    python main.py "abre notepad" --type desktop
    python main.py "toca el botón" --type mobile
"""

import sys
import argparse
from pathlib import Path
from agent.planner  import generate_test_plan
from agent.executor import run_test
from agent.reporter import save_result

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass


def parse_args():
    """Parsea argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(
        description="🤖 Agente QA con IA – Automatización de pruebas local",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python main.py "prueba el login"
  python main.py "busca en google" --type web --no-headless
  python main.py "abre notepad" --type desktop
  python main.py "pulsa el botón" --type mobile

Tipos de test disponibles:
  web      Automatización web con Selenium (predeterminado)
  desktop  Desktop automation (placeholder, próximamente)
  mobile   Mobile testing con Appium (placeholder, próximamente)
        """,
    )

    parser.add_argument(
        "prompt",
        nargs="?",
        default="prueba el login de esta página",
        help="Descripción en lenguaje natural de lo que se quiere probar",
    )

    parser.add_argument(
        "--type",
        choices=["web", "desktop", "mobile"],
        default="web",
        help="Tipo de prueba a ejecutar (default: web)",
    )

    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Muestra el navegador durante la ejecución (solo web, útil para debug)",
    )

    return parser.parse_args()


def main():
    """Función principal del agente QA."""
    args = parse_args()
    prompt = args.prompt
    test_type = args.type
    headless = not args.no_headless

    print("=" * 70)
    print("AGENTE QA - AUTOMATIZACION LOCAL CON IA")
    print("=" * 70)
    print(f"Prompt: {prompt}")
    print(f"Tipo: {test_type}")
    print(f"Modo: {'headless' if headless else 'visible'}")
    print("-" * 70)

    # 1️⃣  Generar plan de prueba desde el prompt
    print("\nGenerando plan de prueba...")
    steps = generate_test_plan(prompt)
    print(f"Plan generado ({len(steps)} pasos):")
    for i, step in enumerate(steps, 1):
        action = step.get("action", "")
        detail = step.get("value") or step.get("selector", "")
        print(f"   {i}. [{action}] {detail}")

    print("\n" + "-" * 70)

    # 2️⃣  Ejecutar la prueba con el executor apropiado
    test_name = f"Test: {prompt[:50]}"
    print(f"\nEjecutando {test_type} automation...")
    result = run_test(test_name, steps, test_type=test_type, headless=headless)

    print("\n" + "-" * 70)
    
    # Mostrar resultado
    status_icon = {
        "PASS": "PASS",
        "FAIL": "FAIL",
        "SKIPPED": "SKIPPED",
    }.get(result["status"], "UNKNOWN")

    print(f"\n{status_icon} - {result['test_name']}")
    if result["error"]:
        print(f"Error: {result['error']}")

    # 3️⃣  Guardar resultados
    filepath = save_result(result)

    print("\n" + "=" * 70)
    print(f"Resultado guardado: {filepath}")
    print("Ver dashboard: streamlit run dashboard/app.py")
    print("=" * 70)


if __name__ == "__main__":
    main()
