"""
Módulo de autenticación con Google OAuth 2.0 para Streamlit
Flujo de cliente para usuarios finales sin Firebase Admin SDK
"""

import os
import json
import streamlit as st
from urllib.parse import urlencode, parse_qs, urlparse
from typing import Dict, Optional, Tuple
import requests
from pathlib import Path
from datetime import datetime, timedelta

# Configuración de Google OAuth 2.0
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "").strip()
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8501").strip()

# Endpoints de Google
GOOGLE_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_ENDPOINT = "https://www.googleapis.com/oauth2/v1/userinfo"


def init_auth_session():
    """
    Inicializa el session_state para autenticación.
    Se ejecuta una sola vez al cargar la aplicación.
    """
    if "auth" not in st.session_state:
        st.session_state.auth = {
            "authenticated": False,
            "user_info": None,
            "access_token": None,
            "id_token": None,
            "token_expires_at": None,
            "login_timestamp": None,
        }
    
    if "auth_code" not in st.session_state:
        st.session_state.auth_code = None


def get_google_auth_url() -> str:
    """
    Genera la URL de autorización de Google.
    El usuario será redireccionado a esta URL para login.
    """
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",  # OpenID es necesario para el id_token
        "access_type": "offline",
        "prompt": "select_account",  # Cambiado de consent a select_account
    }
    return f"{GOOGLE_AUTH_ENDPOINT}?{urlencode(params)}"


def exchange_code_for_tokens(auth_code: str) -> Optional[Dict]:
    """
    Canjea el código de autorización por tokens (access_token, id_token).
    Se ejecuta en el servidor Streamlit.
    """
    try:
        payload = {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "code": auth_code,
            "grant_type": "authorization_code",
            "redirect_uri": REDIRECT_URI,
        }
        
        response = requests.post(GOOGLE_TOKEN_ENDPOINT, data=payload, timeout=10)
        response.raise_for_status()
        
        token_data = response.json()
        return {
            "access_token": token_data.get("access_token"),
            "id_token": token_data.get("id_token"),
            "expires_in": token_data.get("expires_in", 3600),
            "refresh_token": token_data.get("refresh_token"),
        }
    except Exception as e:
        st.error(f"❌ Error al obtener tokens: {str(e)}")
        return None


def get_user_info(access_token: str) -> Optional[Dict]:
    """
    Obtiene información del usuario autenticado usando el access_token.
    """
    try:
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(
            f"{GOOGLE_USERINFO_ENDPOINT}?alt=json",
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"❌ Error al obtener información del usuario: {str(e)}")
        return None


def handle_login(auth_code: str) -> bool:
    """
    Maneja el flujo de login:
    1. Canjea el código por tokens
    2. Obtiene información del usuario
    3. Guarda en session_state
    """
    init_auth_session()
    
    # Canjear código por tokens
    token_data = exchange_code_for_tokens(auth_code)
    if not token_data:
        return False
    
    # Obtener información del usuario
    user_info = get_user_info(token_data["access_token"])
    if not user_info:
        return False
    
    # Guardar en session_state (persistente durante la sesión)
    st.session_state.auth = {
        "authenticated": True,
        "user_info": user_info,
        "access_token": token_data["access_token"],
        "id_token": token_data.get("id_token"),
        "refresh_token": token_data.get("refresh_token"),
        "token_expires_at": datetime.now() + timedelta(seconds=token_data["expires_in"]),
        "login_timestamp": datetime.now().isoformat(),
    }
    
    return True


def handle_logout():
    """
    Limpia la sesión de autenticación.
    """
    st.session_state.auth = {
        "authenticated": False,
        "user_info": None,
        "access_token": None,
        "id_token": None,
        "token_expires_at": None,
        "login_timestamp": None,
    }
    st.session_state.auth_code = None


def is_authenticated() -> bool:
    """Verifica si el usuario está autenticado."""
    init_auth_session()
    return st.session_state.auth.get("authenticated", False)


def get_current_user() -> Optional[Dict]:
    """Obtiene la información del usuario actual."""
    if is_authenticated():
        return st.session_state.auth.get("user_info")
    return None


def is_token_expired() -> bool:
    """Verifica si el access_token ha expirado."""
    if not is_authenticated():
        return True
    
    expires_at = st.session_state.auth.get("token_expires_at")
    if not expires_at:
        return True
    
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    
    return datetime.now() >= expires_at


def extract_auth_code_from_query_params() -> Optional[str]:
    """
    Extrae el código de autorización de los query parameters.
    Streamlit lo proporciona en la URL cuando Google redirige.
    """
    query_params = st.query_params
    return query_params.get("code")


def check_and_process_oauth_callback():
    """
    Verifica si hay un callback de OAuth y procesa el login automáticamente.
    Se debe llamar al inicio del app Streamlit.
    """
    init_auth_session()
    
    # Intentar extraer código de la URL
    auth_code = extract_auth_code_from_query_params()
    
    if auth_code and not is_authenticated():
        # Procesar login silenciosamente
        if handle_login(auth_code):
            # Limpiar query params para que no quede en la URL
            st.query_params.clear()
            st.rerun()
