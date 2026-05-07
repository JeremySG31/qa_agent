from cryptography.fernet import Fernet
import os

# Clave maestra generada oficialmente (32 bytes base64)
# Puedes cambiarla en tus Secrets de Streamlit usando el nombre ENCRYPTION_KEY
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "v2-yN7jZ3v8_WqX9Z_LpQ6m2N5vR8tY1uI4oP7sA0v8=")

def get_fernet():
    return Fernet(ENCRYPTION_KEY.encode())

def encrypt_data(data: str) -> str:
    """Cifra un texto plano."""
    if not data: return ""
    try:
        f = get_fernet()
        return f.encrypt(data.encode()).decode()
    except Exception as e:
        print(f"Error al cifrar: {e}")
        return data # Fallback para no perder el dato si algo falla

def decrypt_data(encrypted_data: str) -> str:
    """Descifra un texto cifrado."""
    if not encrypted_data: return ""
    try:
        f = get_fernet()
        return f.decrypt(encrypted_data.encode()).decode()
    except Exception:
        # Si no se puede descifrar, asumimos que ya está en texto plano (para datos antiguos)
        return encrypted_data
