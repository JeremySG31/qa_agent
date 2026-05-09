import json
import os
import sys
import io
import requests
from datetime import datetime
from pathlib import Path

# Forzar stdout a UTF-8 para evitar errores de codificacion en Windows
if sys.stdout and hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID", "qa-agent-web").strip()
FIREBASE_API_KEY = os.getenv("FIREBASE_API_KEY", "").strip()


def _make_json_safe(obj):
    if isinstance(obj, dict):
        return {k: _make_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_make_json_safe(v) for v in obj]
    if isinstance(obj, tuple):
        return tuple(_make_json_safe(v) for v in obj)
    try:
        from datetime import datetime
        if isinstance(obj, datetime):
            return obj.isoformat()
    except Exception:
        pass
    return obj




def save_result(result: dict, user_id: str = "default") -> str:
    from datetime import datetime, timezone, timedelta
    tz_local = timezone(timedelta(hours=-5))
    dt_now = datetime.now(tz_local)
    result["timestamp"] = dt_now.isoformat()
    result["created_at"] = dt_now.isoformat()
    safe_result = _make_json_safe(result)

    # Quitamos la restricción de invitado para que sus tests se guarden temporalmente 
    # y así funcionen las métricas y el límite de 10 pruebas por sesión.

    if FIREBASE_PROJECT_ID and FIREBASE_API_KEY:
        try:
            doc_id = user_id.replace("@", "_at_").replace(".", "_dot_")
            url = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents/users/{doc_id}/test_results?key={FIREBASE_API_KEY}"
            payload = {
                "fields": {
                    "created_at": {"stringValue": safe_result["created_at"]},
                    "data_json": {"stringValue": json.dumps(safe_result, ensure_ascii=False)}
                }
            }
            res = requests.post(url, json=payload, timeout=10)
            if res.ok:
                print(f"✅ Resultado guardado en Firestore REST")
                return res.json().get("name", "")
        except Exception as e:
            print(f"❌ Error guardando en Firestore REST: {e}")

    return "not_saved"


def load_all_results(user_id: str = "default") -> list[dict]:
    # Permitimos consultar los resultados del invitado actual
    if FIREBASE_PROJECT_ID and FIREBASE_API_KEY:
        try:
            doc_id = user_id.replace("@", "_at_").replace(".", "_dot_")
            url = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents/users/{doc_id}/test_results?key={FIREBASE_API_KEY}"
            res = requests.get(url, timeout=10)
            if res.ok:
                data = res.json()
                docs = data.get("documents", [])
                results = []
                for doc in docs:
                    fields = doc.get("fields", {})
                    data_str = fields.get("data_json", {}).get("stringValue", "")
                    if data_str:
                        try:
                            parsed = json.loads(data_str)
                            parsed["_id"] = doc.get("name")
                            results.append(parsed)
                        except:
                            pass
                results.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
                return results
        except Exception as e:
            print(f"❌ Error leyendo Firestore REST: {e}")
    return []


def clear_results(user_id: str = "default") -> int:
    # Permitimos limpiar historial de invitado
    if FIREBASE_PROJECT_ID and FIREBASE_API_KEY:
        try:
            doc_id = user_id.replace("@", "_at_").replace(".", "_dot_")
            url = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents/users/{doc_id}/test_results?key={FIREBASE_API_KEY}"
            res = requests.get(url, timeout=10)
            count = 0
            if res.ok:
                docs = res.json().get("documents", [])
                for doc in docs:
                    doc_url = f"https://firestore.googleapis.com/v1/{doc['name']}?key={FIREBASE_API_KEY}"
                    d_res = requests.delete(doc_url, timeout=5)
                    if d_res.ok:
                        count += 1
                return count
        except Exception as e:
            print(f"❌ Error limpiando Firestore REST: {e}")
    return 0
