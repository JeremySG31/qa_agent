from cryptography.fernet import Fernet
import os
import base64
import hashlib

def get_fernet():
    """Genera una llave de seguridad perfecta matemáticamente para evitar errores de formato."""
    # Usamos una frase secreta persistente para generar la llave real de 32 bytes
    secret_seed = os.getenv("QA_AGENT_SECRET_KEY", "qa_agent_universal_secret_seed_2024")
    
    # SHA256 siempre genera exactamente 32 bytes, que es lo que Fernet exige.
    key_32_bytes = hashlib.sha256(secret_seed.encode()).digest()
    key_base64 = base64.urlsafe_b64encode(key_32_bytes)
    
    return Fernet(key_base64)

def encrypt_data(data: str) -> str:
    """Cifra los datos. Si algo falla, devuelve el dato original para no romper la app."""
    if not data: return ""
    try:
        f = get_fernet()
        return f.encrypt(data.encode()).decode()
    except Exception:
        return data

def decrypt_data(encrypted_data: str) -> str:
    """Descifra los datos. Si algo falla, devuelve el original (útil para datos viejos)."""
    if not encrypted_data: return ""
    try:
        f = get_fernet()
        return f.decrypt(encrypted_data.encode()).decode()
    except Exception:
        return encrypted_data
