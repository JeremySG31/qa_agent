"""
reporter.py - Módulo de reporte de resultados
Guarda y carga los resultados de las pruebas en formato JSON.
"""

import json
import os
import sys
import io
from datetime import datetime
from pathlib import Path

# Forzar stdout a UTF-8 para evitar errores de codificacion en Windows
if sys.stdout and hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


# Directorio donde se guardan los reportes
RESULTS_DIR = Path(__file__).parent.parent / "results"


def save_result(result: dict) -> str:
    """
    Guarda el resultado de una prueba en un archivo JSON.
    Agrega timestamp al resultado.
    Retorna la ruta del archivo guardado.
    """
    RESULTS_DIR.mkdir(exist_ok=True)

    # Agregar timestamp al resultado
    result["timestamp"] = datetime.now().isoformat()

    # Nombre de archivo seguro basado en el nombre del test
    # Reemplazar caracteres problemáticos en Windows/Unix
    safe_name = (result["test_name"]
                 .replace(" ", "_")
                 .replace("/", "-")
                 .replace(":", "-")
                 .replace("*", "-")
                 .replace("?", "-")
                 .replace('"', "-")
                 .replace("<", "-")
                 .replace(">", "-")
                 .replace("|", "-"))
    filename  = f"{safe_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    filepath  = RESULTS_DIR / filename

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"Resultado guardado: {filepath}")
    return str(filepath)


def load_all_results() -> list[dict]:
    """
    Lee todos los archivos JSON del directorio results/.
    Retorna lista de resultados ordenados por timestamp (más reciente primero).
    """
    if not RESULTS_DIR.exists():
        return []

    results = []
    for filepath in RESULTS_DIR.glob("*.json"):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                data["_file"] = filepath.name   # guardar nombre de archivo para referencia
                results.append(data)
        except (json.JSONDecodeError, IOError):
            pass    # ignorar archivos corruptos

    # Ordenar: más reciente primero
    results.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return results


def clear_results() -> int:
    """
    Elimina todos los archivos de resultados.
    Retorna el número de archivos eliminados.
    """
    if not RESULTS_DIR.exists():
        return 0

    count = 0
    for filepath in RESULTS_DIR.glob("*.json"):
        filepath.unlink()
        count += 1
    return count
