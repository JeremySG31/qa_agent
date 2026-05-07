from cryptography.fernet import Fernet
import os

# La clave debe ser una cadena base64 persistente en el .env
# Si no existe, usamos una por defecto (aunque se recomienda generar una única)
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "7-uE_r3_r0b0t_v3ry_s3cr3t_k3y_for_qa_agent_123=")

def get_fernet():
    return Fernet(ENCRYPTION_KEY.encode())

def encrypt_data(data: str) -> str:
    """Cifra un texto plano."""
    if not data: return ""
    f = get_fernet()
    return f.encrypt(data.encode()).decode()

def decrypt_data(encrypted_data: str) -> str:
    """Descifra un texto cifrado."""
    if not encrypted_data: return ""
    try:
        f = get_fernet()
        return f.decrypt(encrypted_data.encode()).decode()
    except Exception:
        return "ERROR_DE_DESCIFRADO"
