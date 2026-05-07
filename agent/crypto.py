from cryptography.fernet import Fernet
import os

# La clave debe ser una cadena base64 persistente en el .env de 32 bytes
# Esta es una llave válida generada para el proyecto
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "uN_K0vG7jZ3v8_WqX9Z_LpQ6m2N5vR8tY1uI4oP7sA0=")

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
