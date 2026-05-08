"""
reporter.py - Módulo de reporte de resultados
Guarda y carga los resultados de las pruebas en Firestore.
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

# Firebase/Firestore (Admin SDK - solo para servidor con credenciales)
try:
    import firebase_admin
    from firebase_admin import credentials, firestore

    _cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
    if _cred_path and os.path.exists(_cred_path):
        try:
            if not firebase_admin._apps:
                _cred = credentials.Certificate(_cred_path)
                firebase_admin.initialize_app(_cred)
            db = firestore.client()
            FIRESTORE_ENABLED = True
        except Exception as e:
            print(f"⚠️ Firestore no disponible: {e}")
            FIRESTORE_ENABLED = False
    else:
        # Sin credenciales de Admin SDK, usamos almacenamiento local
        FIRESTORE_ENABLED = False
except ImportError:
    FIRESTORE_ENABLED = False


# Directorio de fallback (solo si Firestore no está disponible)
RESULTS_DIR = Path(__file__).parent.parent / "results"


def _make_json_safe(obj):
    """Recursively convert non-serializable objects (eg. datetime) to strings.
    Returns a new object safe for json.dump.
    """
    if isinstance(obj, dict):
        return {k: _make_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_make_json_safe(v) for v in obj]
    if isinstance(obj, tuple):
        return tuple(_make_json_safe(v) for v in obj)
    # datetime -> ISO string
    try:
        from datetime import datetime
        if isinstance(obj, datetime):
            return obj.isoformat()
    except Exception:
        pass
    return obj


def save_result(result: dict, user_id: str = "default") -> str:
    """
    Guarda el resultado de una prueba.
    Intenta Firestore primero; si no está disponible, guarda localmente.
    Estructura Firestore: users/{user_id}/test_results/{test_id}
    Agrega timestamp al resultado.
    Retorna el ID del documento guardado.
    """
    result["timestamp"] = datetime.now().isoformat()
    result["created_at"] = datetime.now().isoformat()

    if FIRESTORE_ENABLED:
        try:
            doc_ref = db.collection("users").document(user_id).collection("test_results").add(result)
            doc_id = doc_ref[1].id
            print(f"✅ Resultado guardado en Firestore: {doc_id}")
            return doc_id
        except Exception as e:
            print(f"❌ Error guardando en Firestore: {e} — guardando localmente como fallback.")

    # Fallback: guardar en archivo local
    return _save_result_local(result)



def load_all_results(user_id: str = "default") -> list[dict]:
    """
    Lee todos los resultados de un usuario.
    Intenta Firestore primero; si no está disponible, lee archivos locales.
    Retorna lista de resultados ordenados por timestamp (más reciente primero).
    """
    if FIRESTORE_ENABLED:
        try:
            docs = (db.collection("users")
                   .document(user_id)
                   .collection("test_results")
                   .order_by("created_at", direction=firestore.Query.DESCENDING)
                   .stream())

            results = []
            for doc in docs:
                data = doc.to_dict()
                data["_id"] = doc.id
                results.append(data)

            print(f"✅ Cargados {len(results)} resultados desde Firestore")
            return results
        except Exception as e:
            print(f"❌ Error leyendo desde Firestore: {e} — leyendo archivos locales.")

    # Fallback: leer archivos locales
    return _load_all_results_local()



def clear_results(user_id: str = "default") -> int:
    """
    Elimina todos los resultados de un usuario.
    Intenta Firestore primero; si no está disponible, elimina archivos locales.
    Retorna el número de documentos eliminados.
    """
    if FIRESTORE_ENABLED:
        try:
            docs = (db.collection("users")
                   .document(user_id)
                   .collection("test_results")
                   .stream())

            count = 0
            for doc in docs:
                doc.reference.delete()
                count += 1

            print(f"✅ {count} resultados eliminados de Firestore")
            return count
        except Exception as e:
            print(f"❌ Error eliminando de Firestore: {e} — eliminando archivos locales.")

    # Fallback: eliminar archivos locales
    return _clear_results_local()



# ══════════════════════════════════════════════════════════════════════════════
# FUNCIONES DE FALLBACK (Archivos locales)
# ══════════════════════════════════════════════════════════════════════════════

def _save_result_local(result: dict) -> str:
    """Fallback: Guardar en archivo local si Firestore no está disponible."""
    RESULTS_DIR.mkdir(exist_ok=True)

    safe_name = (result.get("test_name", "test")
                 .replace(" ", "_")
                 .replace("/", "-")
                 .replace(":", "-")
                 .replace("*", "-")
                 .replace("?", "-")
                 .replace('"', "-")
                 .replace("<", "-")
                 .replace(">", "-")
                 .replace("|", "-"))
    filename = f"{safe_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    filepath = RESULTS_DIR / filename

    # Asegurar que todos los objetos son serializables
    safe_result = _make_json_safe(result)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(safe_result, f, ensure_ascii=False, indent=2)

    print(f"⚠️ Resultado guardado localmente: {filepath}")
    return str(filepath)


def _load_all_results_local() -> list[dict]:
    """Fallback: Leer archivos locales si Firestore no está disponible."""
    if not RESULTS_DIR.exists():
        return []

    results = []
    for filepath in RESULTS_DIR.glob("*.json"):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                data["_file"] = filepath.name
                results.append(data)
        except (json.JSONDecodeError, IOError):
            pass

    results.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return results


def _clear_results_local() -> int:
    """Fallback: Eliminar archivos locales si Firestore no está disponible."""
    if not RESULTS_DIR.exists():
        return 0

    count = 0
    for filepath in RESULTS_DIR.glob("*.json"):
        filepath.unlink()
        count += 1
    return count
