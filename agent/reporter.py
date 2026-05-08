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

RESULTS_DIR = Path(__file__).parent.parent / "results"


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


def _save_result_local(result: dict, user_id: str) -> str:
    user_dir = RESULTS_DIR / user_id.replace("@", "_").replace(".", "_")
    user_dir.mkdir(parents=True, exist_ok=True)
    safe_name = (result.get("test_name", "test").replace(" ", "_").replace("/", "-").replace(":", "-"))
    filename = f"{safe_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    filepath = user_dir / filename
    safe_result = _make_json_safe(result)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(safe_result, f, ensure_ascii=False, indent=2)
    print(f"⚠️ Resultado guardado localmente: {filepath}")
    return str(filepath)


def _load_all_results_local(user_id: str) -> list[dict]:
    user_dir = RESULTS_DIR / user_id.replace("@", "_").replace(".", "_")
    if not user_dir.exists():
        return []
    results = []
    for filepath in user_dir.glob("*.json"):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                data["_file"] = filepath.name
                results.append(data)
        except (json.JSONDecodeError, IOError):
            pass
    results.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return results


def _clear_results_local(user_id: str) -> int:
    user_dir = RESULTS_DIR / user_id.replace("@", "_").replace(".", "_")
    if not user_dir.exists():
        return 0
    count = 0
    for filepath in user_dir.glob("*.json"):
        try:
            filepath.unlink()
            count += 1
        except Exception:
            pass
    return count


def save_result(result: dict, user_id: str = "default") -> str:
    result["timestamp"] = datetime.now().isoformat()
    result["created_at"] = datetime.now().isoformat()
    safe_result = _make_json_safe(result)

    # Si es invitado, no gastar cuota de Firestore, guardar solo local
    if user_id == "invitado@qa-agent.local":
        path = _save_result_local(result, user_id)
        # Limitar invitado a max 10 tests locales para no llenar el disco
        user_dir = RESULTS_DIR / "invitado_qa-agent_local"
        if user_dir.exists():
            files = sorted(user_dir.glob("*.json"), key=os.path.getmtime, reverse=True)
            for old_file in files[10:]:
                try: old_file.unlink()
                except Exception: pass
        return path

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

    return _save_result_local(result, user_id)


def load_all_results(user_id: str = "default") -> list[dict]:
    if user_id == "invitado@qa-agent.local":
        return _load_all_results_local(user_id)

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

    return _load_all_results_local(user_id)


def clear_results(user_id: str = "default") -> int:
    if user_id == "invitado@qa-agent.local":
        return _clear_results_local(user_id)

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

    return _clear_results_local(user_id)
