import requests
import random
import string
import time
from abc import ABC, abstractmethod
from typing import Optional, List, Dict

class DomainRegistrar(ABC):
    """Interfaz base para proveedores de registro de dominios."""
    @abstractmethod
    def check_availability(self, domain: str) -> bool:
        pass

    @abstractmethod
    def register_domain(self, domain: str) -> bool:
        pass

class CloudflareRegistrar(DomainRegistrar):
    """Implementación de Cloudflare para gestión de dominios y DNS."""
    def __init__(self, api_token: str, account_id: str):
        self.api_token = api_token
        self.account_id = account_id
        self.base_url = "https://api.cloudflare.com/client/v4"
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }

    def check_availability(self, domain: str) -> bool:
        # Nota: Cloudflare Registrar API requiere permisos específicos
        url = f"{self.base_url}/accounts/{self.account_id}/registrar/domains/search"
        params = {"query": domain}
        try:
            res = requests.get(url, headers=self.headers, params=params)
            data = res.json()
            return data.get("result", [{}])[0].get("available", False)
        except Exception:
            return False

    def register_domain(self, domain: str) -> bool:
        # Implementación simplificada (requiere datos de contacto reales en la vida real)
        url = f"{self.base_url}/accounts/{self.account_id}/registrar/domains/{domain}/register"
        try:
            res = requests.post(url, headers=self.headers)
            return res.status_code == 200
        except Exception:
            return False

class EmailService(ABC):
    """Interfaz base para servicios de correo electrónico."""
    @abstractmethod
    def get_emails(self, address: str) -> List[Dict]:
        pass

    @abstractmethod
    def generate_address(self) -> str:
        pass

class OneSecMail(EmailService):
    """Servicio de correos temporales '1secmail' (Gratuito y sin registro)."""
    def __init__(self):
        self.base_url = "https://www.1secmail.com/api/v1/"

    def generate_address(self) -> str:
        # Dominios disponibles en 1secmail
        domains = ["1secmail.com", "1secmail.org", "1secmail.net"]
        login = "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(10))
        domain = random.choice(domains)
        return f"{login}@{domain}"

    def get_emails(self, address: str) -> List[Dict]:
        login, domain = address.split("@")
        url = f"{self.base_url}?action=getMessages&login={login}&domain={domain}"
        try:
            res = requests.get(url)
            return res.json()
        except Exception:
            return []

    def get_message_content(self, address: str, msg_id: int) -> Dict:
        login, domain = address.split("@")
        url = f"{self.base_url}?action=readMessage&login={login}&domain={domain}&id={msg_id}"
        try:
            res = requests.get(url)
            return res.json()
        except Exception:
            return {}

class SecureEmailManager:
    """
    Gestor de alto nivel para crear correos 'seguros' (únicos y controlables).
    Combina la lógica de dominio y servicio de correo.
    """
    def __init__(self, domain: Optional[str] = None, registrar: Optional[DomainRegistrar] = None):
        self.domain = domain
        self.registrar = registrar
        self.temp_service = OneSecMail()

    def create_account(self, prefix: Optional[str] = None) -> str:
        """Crea una dirección de correo única."""
        if not self.domain:
            # Si no hay dominio propio, usamos un servicio temporal
            return self.temp_service.generate_address()
        
        # Si hay dominio, generamos un prefijo único
        if not prefix:
            prefix = "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(8))
        
        return f"{prefix}@{self.domain}"

    def wait_for_email(self, address: str, timeout: int = 60, interval: int = 5) -> Optional[Dict]:
        """Espera a que llegue un correo a la dirección especificada."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            emails = []
            if "@1secmail" in address:
                emails = self.temp_service.get_emails(address)
            
            if emails:
                # Retornamos el último mensaje recibido
                msg_id = emails[0].get("id")
                return self.temp_service.get_message_content(address, msg_id)
            
            time.sleep(interval)
        return None

# Ejemplo de uso
if __name__ == "__main__":
    manager = SecureEmailManager()
    email = manager.create_account()
    print(f"Correo creado: {email}")
    print("Esperando correos (60s)...")
    # msg = manager.wait_for_email(email)
    # print(f"Mensaje recibido: {msg.get('subject') if msg else 'Ninguno'}")
