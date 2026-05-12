import os

# Frase secreta para el cifrado (puedes cambiarla en Secrets si quieres)
SECRET_PHRASE = os.getenv("QA_AGENT_SECRET_KEY", "qa_agent_secure_v1_2024")

def xor_cipher(data: str) -> str:
    """Aplica un cifrado XOR simple pero efectivo para ocultar los datos."""
    key = SECRET_PHRASE
    return "".join(chr(ord(c) ^ ord(key[i % len(key)])) for i, c in enumerate(data))

def encrypt_data(data: str) -> str:
    """Convierte el texto plano en una cadena hexadecimal cifrada."""
    if not data: return ""
    try:
        ciphered = xor_cipher(data)
        # Lo pasamos a hexadecimal para que sea guardable sin problemas de caracteres
        return ciphered.encode('utf-8').hex()
    except Exception:
        return data

def decrypt_data(encrypted_data: str) -> str:
    """Recupera el texto original desde la cadena hexadecimal."""
    if not encrypted_data: return ""
    try:
        # Si es hexadecimal válido, lo desciframos
        decoded_hex = bytes.fromhex(encrypted_data).decode('utf-8')
        return xor_cipher(decoded_hex)
    except Exception:
        # Si falla (ej: dato viejo no cifrado), devolvemos el original
        return encrypted_data
