"""
dashboard/app.py - Dashboard QA con interfaz completa sin código
Ejecutar con: streamlit run dashboard/app.py
"""

import sys, os, json, subprocess, re
from pathlib import Path
from datetime import datetime
from urllib.parse import quote

import streamlit as st

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from agent.reporter import load_all_results, clear_results, save_result
from agent.planner  import generate_test_plan
from agent.crypto   import encrypt_data, decrypt_data

# ── Cargar .env ────────────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

# ── Config página ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="QA Agent No-Code",
    page_icon="robot",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Verificación de Dominio (Google Search Console) ─────────────────────────────
st.markdown('<meta name="google-site-verification" content="1TyKKbQRLHJ9LvfxZnKzvgQUzSuz5EH_J4g5vjc3O-I" />', unsafe_allow_html=True)

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Syne:wght@400;700;800&display=swap');

html, body, [class*="css"] { font-family:'Syne',sans-serif; background:#0d0f14; color:#e2e8f0; }

.qa-header {
  background:linear-gradient(135deg,#0f172a,#1e293b);
  border:1px solid #22d3ee33; border-radius:14px;
  padding:28px 36px; margin-bottom:24px; position:relative; overflow:hidden;
}
.qa-header::before {
  content:''; position:absolute; top:0; left:0; right:0; height:3px;
  background:linear-gradient(90deg,#22d3ee,#818cf8,#f472b6);
}
.qa-header h1 { font-size:2rem; font-weight:800; color:#22d3ee; margin:0 0 4px; }
.qa-header p  { color:#94a3b8; margin:0; font-size:.95rem; }

.metric-box {
  background: linear-gradient(145deg, #1e293b, #0a0c10);
  border: 1px solid #38bdf840;
  border-top: 1px solid #38bdf880;
  border-radius: 16px;
  padding: 24px 10px;
  text-align: center;
  box-shadow: 0 10px 30px -5px rgba(56, 189, 248, 0.15), inset 0 1px 0 rgba(255,255,255,0.1);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: visible;
}
.metric-box::before {
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 100%;
  background: radial-gradient(circle at top right, rgba(255,255,255,0.05), transparent 60%);
  pointer-events: none;
  border-radius: 16px;
}
.metric-box:hover {
  transform: translateY(-5px);
  box-shadow: 0 20px 40px -5px rgba(56, 189, 248, 0.3), inset 0 1px 0 rgba(255,255,255,0.2);
  border-color: #38bdf8;
}
.metric-value { 
  font-family: 'Syne', sans-serif; 
  font-size: clamp(1.8rem, 3vw, 2.8rem); 
  font-weight: 800; 
  line-height: 1.1; 
  white-space: nowrap;
  background: linear-gradient(135deg, #22d3ee, #818cf8, #f472b6);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  filter: drop-shadow(0px 4px 10px rgba(56,189,248,0.4));
}
.metric-label { font-size:.85rem; color:#94a3b8; text-transform:uppercase; letter-spacing:1.5px; margin-top:10px; font-weight:700; }

.result-card {
  background: linear-gradient(180deg, #111827 0%, #0f172a 100%);
  border: 1px solid #1e293b;
  border-radius: 12px; padding: 20px 24px; margin-bottom: 16px;
  transition: all .25s ease;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
}
.result-card:hover { border-color:#334155; transform:translateY(-2px); box-shadow:0 10px 15px -3px rgba(0,0,0,0.3); }
.result-card.pass  { border-left:4px solid #10b981; }
.result-card.fail  { border-left:4px solid #ef4444; }
.result-title { font-family:'JetBrains Mono',monospace; font-size:.9rem; font-weight:600; color:#e2e8f0; margin-bottom:6px; }
.result-meta  { font-size:.75rem; color:#64748b; font-family:'JetBrains Mono',monospace; }

.badge-pass { display:inline-block; background:#064e3b; color:#10b981; border:1px solid #10b981; border-radius:6px; padding:2px 10px; font-size:.75rem; font-weight:700; font-family:'JetBrains Mono',monospace; }
.badge-fail { display:inline-block; background:#450a0a; color:#ef4444; border:1px solid #ef4444; border-radius:6px; padding:2px 10px; font-size:.75rem; font-weight:700; font-family:'JetBrains Mono',monospace; }

.step-item {
  display:flex; align-items:flex-start; gap:10px;
  padding:8px 12px; border-radius:6px; margin-bottom:6px;
  background:#0f172a; border:1px solid #1e293b;
  font-family:'JetBrains Mono',monospace; font-size:.78rem;
}
.step-ok  { border-left:3px solid #10b981; }
.step-err { border-left:3px solid #ef4444; }
.step-icon { font-size:1rem; flex-shrink:0; }
.step-text { color:#cbd5e1; }
.step-action { color:#22d3ee; font-weight:600; margin-right:6px; }

.plan-preview {
  background:#0f172a; border:1px solid #22d3ee33;
  border-radius:10px; padding:16px; margin:12px 0;
}
.plan-step {
  display:flex; gap:10px; align-items:flex-start;
  padding:6px 0; border-bottom:1px solid #1e293b;
  font-family:'JetBrains Mono',monospace; font-size:.8rem; color:#94a3b8;
}
.plan-step:last-child { border-bottom:none; }
.plan-num  { color:#818cf8; font-weight:700; min-width:24px; }
.plan-act  { color:#22d3ee; font-weight:600; min-width:130px; }

.section-title {
  font-size:1.15rem; font-weight:700; color:#e2e8f0;
  margin:20px 0 12px; padding-bottom:8px;
  border-bottom:1px solid #1e293b;
}

div[data-testid="stSidebar"] { background:#0a0c10 !important; border-right:1px solid #1e293b; }
.stTextInput [data-baseweb="input"], .stTextArea [data-baseweb="textarea"] {
  background-color: #111827 !important;
  border: 1px solid #334155 !important;
  border-radius: 8px !important;
}
.stTextInput input, .stTextArea textarea {
  color: #e2e8f0 !important;
  font-family: 'JetBrains Mono', monospace !important;
  background: transparent !important;
}
/* Ocultar el ojo nativo de contraseñas del navegador (Edge) para evitar duplicados con Streamlit */
input::-ms-reveal, input::-ms-clear {
  display: none;
}
.stButton>button { border-radius:8px !important; font-family:'Syne',sans-serif !important; font-weight:700 !important; }
.stSelectbox>div>div { background:#111827 !important; border:1px solid #334155 !important; }
hr { border-color:#1e293b !important; }
.stExpander { border-color:#1e293b !important; }
.stTabs [data-baseweb="tab-list"] { background:#111827; border-radius:10px; padding:4px; gap:4px; }
.stTabs [data-baseweb="tab"] { border-radius:7px; color:#64748b; }
.stTabs [aria-selected="true"] { background:#1e293b; color:#22d3ee; }
.error-box { background:#1a0a0a; border:1px solid #7f1d1d; border-radius:8px; padding:12px 16px; font-family:'JetBrains Mono',monospace; font-size:.8rem; color:#fca5a5; margin-top:8px; }

/* Login Page CSS */
.login-container {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  height: 80vh; text-align: center;
}
.login-box {
  background: linear-gradient(145deg, #1e293b, #0a0c10);
  border: 1px solid #38bdf840; border-top: 1px solid #38bdf880;
  border-radius: 20px; padding: 40px 50px;
  box-shadow: 0 10px 40px -10px rgba(56, 189, 248, 0.2), inset 0 1px 0 rgba(255,255,255,0.1);
  max-width: 450px; width: 100%;
}
.login-logo {
  font-family: 'Syne', sans-serif; font-size: 2.5rem; font-weight: 800;
  background: linear-gradient(135deg, #22d3ee, #818cf8, #f472b6);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  filter: drop-shadow(0px 4px 10px rgba(56,189,248,0.3)); margin-bottom: 10px;
}
.login-subtitle { color: #94a3b8; font-size: 1rem; margin-bottom: 30px; }
.google-btn {
  display: flex; align-items: center; justify-content: center; gap: 12px;
  background: #ffffff; color: #1e293b !important; text-decoration: none;
  font-weight: 700; font-size: 1.05rem; padding: 12px 24px; border-radius: 10px;
  transition: all 0.3s ease; border: none; cursor: pointer; width: 100%;
}
.google-btn:hover {
  transform: translateY(-2px); box-shadow: 0 8px 20px rgba(255,255,255,0.2);
}
.google-icon { width: 24px; height: 24px; }
</style>
""", unsafe_allow_html=True)


# ── Session state ──────────────────────────────────────────────────────────────
if "plan_preview" not in st.session_state:
    st.session_state.plan_preview = []
if "custom_steps" not in st.session_state:
    st.session_state.custom_steps = []
if "active_tab" not in st.session_state:
    st.session_state.active_tab = 0
if "user_logged_in" not in st.session_state:
    st.session_state.user_logged_in = False
if "ai_enabled" not in st.session_state:
    st.session_state.ai_enabled = False
if "key_version" not in st.session_state:
    st.session_state.key_version = 0
if "ai_config" not in st.session_state:
    st.session_state.ai_config = {"provider": "Google Gemini", "api_key": os.getenv("GEMINI_API_KEY", "").strip(), "model": "gemini-2.0-flash", "base_url": ""}
if "firebase_id_token" not in st.session_state:
    st.session_state.firebase_id_token = ""

# Persistir usuario en query params para mantener sesión tras recarga
try:
    _params = st.query_params
    _user_from_url = _params.get("user", "")
except Exception:
    _user_from_url = ""

if _user_from_url and not st.session_state.get("user_logged_in"):
    st.session_state.user_logged_in = True
    st.session_state.user_email = _user_from_url
    # La Gemini API key se recarga en el bloque posterior (tras definir firebase_load_settings)
    st.session_state["_needs_key_reload"] = True


# ── Configuración de Firebase ──────────────────────────────────────────────────
# Se recomienda rotar esta clave en la consola de Firebase
FIREBASE_API_KEY = os.getenv("FIREBASE_API_KEY", "").strip()
FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID", "qa-agent-web").strip()


def firebase_headers():
    token = st.session_state.get("firebase_id_token", "")
    return {"Authorization": f"Bearer {token}"} if token else {}


def firebase_error_message(raw_error):
    error_map = {
        "API key not valid. Please pass a valid API key.": "La API key de Firebase no es valida. Revisa FIREBASE_API_KEY en .env.",
        "EMAIL_EXISTS": "Este correo ya esta registrado.",
        "EMAIL_NOT_FOUND": "El correo electronico no esta registrado.",
        "INVALID_API_KEY": "FIREBASE_API_KEY no es valida o esta vacia.",
        "INVALID_IDP_RESPONSE": "Google no entrego una credencial valida. Revisa el Google Client ID y los origenes autorizados.",
        "INVALID_LOGIN_CREDENTIALS": "Credenciales incorrectas. Revisa tu correo y contrasena.",
        "INVALID_PASSWORD": "La contrasena es incorrecta.",
        "MISSING_PASSWORD": "Ingresa una contrasena.",
        "OPERATION_NOT_ALLOWED": "Este proveedor no esta habilitado en Firebase Authentication.",
        "TOO_MANY_ATTEMPTS_TRY_LATER": "Demasiados intentos. Intenta mas tarde.",
        "USER_DISABLED": "Esta cuenta ha sido deshabilitada.",
    }
    return error_map.get(raw_error, f"Error de autenticacion: {raw_error}")


def firebase_request(method, url, **kwargs):
    import requests
    try:
        res = requests.request(method, url, timeout=20, **kwargs)
        data = res.json() if res.content else {}
    except requests.RequestException as exc:
        return {"error": {"message": f"NETWORK_ERROR: {exc}"}}
    except ValueError:
        return {"error": {"message": "Respuesta no JSON de Firebase"}}

    if res.ok:
        return data
    if "error" not in data:
        data["error"] = {"message": f"HTTP_{res.status_code}"}
    return data



def firebase_reset_password(email):
    if not FIREBASE_API_KEY:
        return {"error": {"message": "INVALID_API_KEY"}}
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key={FIREBASE_API_KEY}"
    return firebase_request("POST", url, json={"requestType": "PASSWORD_RESET", "email": email})

def firebase_login(email, password):

    if not FIREBASE_API_KEY:
        return {"error": {"message": "INVALID_API_KEY"}}
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"
    return firebase_request("POST", url, json={"email": email, "password": password, "returnSecureToken": True})


def firebase_register(email, password):
    if not FIREBASE_API_KEY:
        return {"error": {"message": "INVALID_API_KEY"}}
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={FIREBASE_API_KEY}"
    return firebase_request("POST", url, json={"email": email, "password": password, "returnSecureToken": True})


def firebase_save_settings(email, ai_config):
    """Cifra la configuracion de IA (dict) y la guarda como JSON en Firestore."""
    import json
    doc_id = email.replace("@", "_at_").replace(".", "_dot_")
    url = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents/users/{doc_id}?updateMask.fieldPaths=ai_config&key={FIREBASE_API_KEY}"
    
    config_json = json.dumps(ai_config)
    encrypted_config = encrypt_data(config_json)
    
    payload = {
        "fields": {
            "ai_config": {"stringValue": encrypted_config}
        }
    }
    return firebase_request("PATCH", url, json=payload, headers=firebase_headers())

def firebase_load_settings(email):
    """Carga la configuracion de IA y la descifra para su uso en la sesion."""
    import json
    try:
        doc_id = email.replace("@", "_at_").replace(".", "_dot_")
        url = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents/users/{doc_id}?key={FIREBASE_API_KEY}"
        data = firebase_request("GET", url, headers=firebase_headers())
        if "error" not in data and "fields" in data:
            # Intentar cargar la nueva ai_config
            if "ai_config" in data.get("fields", {}):
                encrypted_config = data["fields"]["ai_config"].get("stringValue", "")
                decrypted = decrypt_data(encrypted_config)
                return json.loads(decrypted)
                
            # Retrocompatibilidad con la antigua gemini_api_key
            if "gemini_api_key" in data.get("fields", {}):
                encrypted_key = data["fields"]["gemini_api_key"].get("stringValue", "")
                decrypted_key = decrypt_data(encrypted_key)
                return {
                    "provider": "Google Gemini",
                    "api_key": decrypted_key,
                    "model": "gemini-2.0-flash",
                    "base_url": ""
                }
    except Exception as e:
        print(f"⚠️ Error cargando configuracion: {e}")
    return {}

# ── Manejo de Código OAuth (ELIMINADO) ─────────────────────────────────────────
# Se elimina por restricciones de Streamlit Cloud e iframe.

# ── Recargar Gemini Key tras restauración de sesión desde URL ──────────────────
if st.session_state.pop("_needs_key_reload", False):
    _email_to_restore = st.session_state.get("user_email", "")
    if _email_to_restore and not st.session_state.get("ai_config", {}).get("api_key"):
        st.session_state.ai_config = firebase_load_settings(_email_to_restore)

# ── Pantalla de Login ─────────────────────────────────────────────────────────
if not st.session_state.user_logged_in:
    st.markdown("<br><br>", unsafe_allow_html=True)
    _, col_login, _ = st.columns([1, 1.2, 1])
    
    with col_login:
        st.markdown("""
        <div style="text-align: center; margin-bottom: 2rem;">
            <div class="login-logo" style="font-size: 3.5rem;">QA Agent</div>
            <div class="login-subtitle">Acceso a la plataforma No-Code</div>
        </div>
        """, unsafe_allow_html=True)
        
        tab_login, tab_register = st.tabs(["🔑 Iniciar Sesión", "📝 Registrarse"])
        
        with tab_login:
            saved_email = st.query_params.get("saved_email", "")
            with st.form("login_form"):
                l_email = st.text_input("Correo electrónico", value=saved_email, key="l_email")
                l_pass = st.text_input("Contraseña", type="password", key="l_pass")
                c1, c2 = st.columns([1, 1])
                with c1:
                    remember = st.checkbox("Recordar correo", value=bool(saved_email))
                with c2:
                    st.markdown("<div style='text-align:right;'><a href='#' style='color:#38bdf8; font-size:0.85rem; text-decoration:none;'></a></div>", unsafe_allow_html=True)
                
                submitted = st.form_submit_button("Ingresar", use_container_width=True, type="primary")
                
                if submitted:
                    if l_email and l_pass:
                        with st.spinner("Autenticando..."):
                            res = firebase_login(l_email, l_pass)
                            if "idToken" in res:
                                st.session_state.user_logged_in = True
                                st.session_state.user_email = res.get("email")
                                st.session_state.firebase_id_token = res.get("idToken", "")
                                st.session_state.gemini_api_key = firebase_load_settings(res.get("email"))
                                st.query_params["user"] = st.session_state.user_email
                                if remember:
                                    st.query_params["saved_email"] = l_email
                                elif "saved_email" in st.query_params:
                                    del st.query_params["saved_email"]
                                st.rerun()
                            else:
                                st.error(firebase_error_message(res.get("error", {}).get("message", "Error desconocido")))
                    else:
                        st.warning("Completa los campos")

            with st.expander("¿Olvidaste tu contraseña?"):
                reset_email = st.text_input("Ingresa tu correo para recuperar", value=l_email, key="reset_email")
                if st.button("Enviar enlace de recuperación", use_container_width=True):
                    if reset_email:
                        with st.spinner("Enviando correo..."):
                            reset_res = firebase_reset_password(reset_email)
                            if "error" not in reset_res:
                                st.success("¡Enlace enviado! Revisa tu bandeja de entrada o spam.")
                            else:
                                st.error(firebase_error_message(reset_res.get("error", {}).get("message", "")))
                    else:
                        st.warning("Ingresa tu correo electrónico primero.")
                
        with tab_register:
            r_email = st.text_input("Correo electrónico", key="r_email")
            r_pass = st.text_input("Contraseña", type="password", key="r_pass")
            r_pass2 = st.text_input("Repetir contraseña", type="password", key="r_pass2")
            if st.button("Crear cuenta", use_container_width=True):
                import re
                
                def is_valid_email(email_str):
                    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
                    if not re.match(pattern, email_str):
                        return False, "El formato del correo es inválido."
                    
                    blocked_words = ["admin", "root", "put", "mierda", "caca", "pene", "test", "fuck", "bitch", "shit", "ass", "cochinada"]
                    email_lower = email_str.lower()
                    for word in blocked_words:
                        if word in email_lower:
                            return False, f"El correo contiene términos no permitidos o reservados."
                    return True, ""
                
                if r_email and r_pass and r_pass == r_pass2:
                    is_valid, error_msg = is_valid_email(r_email)
                    if not is_valid:
                        st.error(error_msg)
                    else:
                        with st.spinner("Creando cuenta en Firebase..."):
                            res = firebase_register(r_email, r_pass)
                            if "idToken" in res:
                                st.session_state.user_logged_in = True
                                st.session_state.user_email = res.get("email")
                                st.session_state.firebase_id_token = res.get("idToken", "")
                                # CARGAR CONFIGURACIÓN DESDE FIRESTORE (estará vacío pero inicializa)
                                st.session_state.ai_config = {}
                                st.query_params["user"] = st.session_state.user_email
                                st.rerun()
                            else:
                                raw_error = res.get("error", {}).get("message", "Error desconocido")
                                st.error(firebase_error_message(raw_error))
                elif r_pass != r_pass2:
                    st.warning("Las contraseñas no coinciden.")
                else:
                    st.warning("Completa todos los campos.")
                
        # ── Botón de Invitado (Acceso Rápido) ──────────────────────────────────
        st.markdown("<div style='margin-top:20px; margin-bottom:10px; border-top:1px solid #1e293b; padding-top:20px;'></div>", unsafe_allow_html=True)
        if st.button("🚀 Probar como Invitado (Sin registro)", use_container_width=True):
            import uuid
            st.session_state.user_logged_in = True
            st.session_state.user_email = f"invitado_{str(uuid.uuid4())[:8]}@qa-agent.local"
            st.session_state.is_guest = True
            st.session_state.ai_config = {} # No tiene API Key guardada
            st.query_params["user"] = st.session_state.user_email
            st.rerun()

        
        
            
    st.stop()
    
# ── Perfil de Usuario (Modal) ──────────────────────────────────────────────────
@st.dialog("👤 Mi Perfil")
def show_profile():
    st.markdown("### Datos de la cuenta")
    user_email = st.session_state.get("user_email", "Usuario de Google")
    
    st.markdown(f"""
    <div style="background:#0f172a; padding:15px; border-radius:10px; border:1px solid #1e293b; margin-bottom:15px;">
        <div style="color:#94a3b8; font-size:0.8rem; text-transform:uppercase; margin-bottom:5px;">Correo electrónico</div>
        <div style="color:#e2e8f0; font-weight:bold; font-size:1.1rem;">{user_email}</div>
    </div>
    <div style="background:#0f172a; padding:15px; border-radius:10px; border:1px solid #1e293b; margin-bottom:20px;">
        <div style="color:#94a3b8; font-size:0.8rem; text-transform:uppercase; margin-bottom:5px;">Tipo de Plan</div>
        <div style="color:#10b981; font-weight:bold; font-size:1.1rem;">⭐ Premium (Gratuito)</div>
    </div>
    """, unsafe_allow_html=True)

# ── Helpers ────────────────────────────────────────────────────────────────────
def render_steps(steps):
    for step in steps:
        status = step.get("status", "ok")
        icon   = "✅" if status == "ok" else "❌"
        css    = "step-ok" if status == "ok" else "step-err"
        action = step.get("action", "")
        detail = step.get("detail", "") or f"{step.get('selector','')} → {step.get('value','')}"
        st.markdown(f"""
        <div class="step-item {css}">
          <span class="step-icon">{icon}</span>
          <span class="step-text"><span class="step-action">[{action}]</span>{detail}</span>
        </div>""", unsafe_allow_html=True)


def render_result_card(result, idx):
    status  = result.get("status", "UNKNOWN")
    name    = result.get("test_name", "Sin nombre")
    ts      = result.get("timestamp", "")
    error   = result.get("error", "")
    steps   = result.get("steps", [])
    css_cls = "pass" if status == "PASS" else "fail"
    badge   = '<span class="badge-pass">PASS</span>' if status == "PASS" else '<span class="badge-fail">FAIL</span>'
    try:
        ts_fmt = datetime.fromisoformat(ts).strftime("%d/%m/%Y %H:%M:%S")
    except Exception:
        ts_fmt = ts

    st.markdown(f"""
    <div class="result-card {css_cls}">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;">
        <div>
          <div class="result-title">#{idx:02d} — {name}</div>
          <div class="result-meta">🕐 {ts_fmt} &nbsp;|&nbsp; {len(steps)} pasos</div>
        </div>
        <div>{badge}</div>
      </div>
    </div>""", unsafe_allow_html=True)

    if error:
        st.markdown(f'<div class="error-box">⚠️ {error}</div>', unsafe_allow_html=True)
    if steps:
        with st.expander(f"📋 Ver {len(steps)} pasos ejecutados"):
            render_steps(steps)
    st.markdown("")


def render_plan_preview(steps):
    if not steps:
        return
    st.markdown('<div class="plan-preview">', unsafe_allow_html=True)
    for i, s in enumerate(steps, 1):
        action = s.get("action", "")
        val    = s.get("value", "")
        sel    = s.get("selector", "")
        detail = val if val else sel
        st.markdown(f"""
        <div class="plan-step">
          <span class="plan-num">{i}.</span>
          <span class="plan-act">[{action}]</span>
          <span>{detail}</span>
        </div>""", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


def run_test_subprocess(prompt, headless, test_type="web"):
    """Ejecuta main.py en subproceso y retorna stdout/returncode."""
    cmd = [sys.executable, str(ROOT / "main.py"), prompt, "--type", test_type]
    if not headless:
        cmd.append("--no-headless")
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT), encoding="utf-8", env=env)
    return res.returncode, res.stdout, res.stderr


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## QA Agent")
    st.markdown("---")

    # ── Perfil de Usuario ──────────────────────────────────────────
    if st.button("Mi Perfil", use_container_width=True):
        show_profile()
    if st.button("Cerrar Sesión", use_container_width=True):
        st.session_state.user_logged_in = False
        st.session_state.user_email = ""
        st.session_state.firebase_id_token = ""
        st.session_state.ai_config = {}
        st.session_state.is_guest = False
        try:
            st.query_params.clear()
        except Exception:
            pass
        st.rerun()
    st.markdown("---")

    # ── Configuración de IA ────────────────────────────────────────
    with st.expander("Configuracion de IA", expanded=False):
        st.toggle("Activar Inteligencia Artificial", value=False, key="ai_enabled", help="Apágalo para no consumir la cuota de tu API.")

        config = st.session_state.get("ai_config", {})
        provider = st.selectbox("Proveedor de IA", ["Google Gemini", "OpenAI", "Groq", "DeepSeek", "Custom OpenAI"], index=["Google Gemini", "OpenAI", "Groq", "DeepSeek", "Custom OpenAI"].index(config.get("provider", "Google Gemini")))
        
        provider_models = {
            "Google Gemini": ["gemini-2.0-flash", "gemini-2.0-pro", "gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.5-flash", "Otro (Manual)"],
            "OpenAI": ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo", "o1-mini", "o3-mini", "Otro (Manual)"],
            "Groq": ["llama3-8b-8192", "llama3-70b-8192", "mixtral-8x7b-32768", "gemma2-9b-it", "Otro (Manual)"],
            "DeepSeek": ["deepseek-chat", "deepseek-reasoner", "Otro (Manual)"],
            "Custom OpenAI": ["Otro (Manual)"]
        }
        
        available_models = provider_models.get(provider, ["Otro (Manual)"])
        current_model = config.get("model", "")
        
        if current_model and current_model not in available_models:
            sel_index = available_models.index("Otro (Manual)")
            manual_val = current_model
        else:
            try:
                sel_index = available_models.index(current_model)
                manual_val = ""
            except ValueError:
                sel_index = 0
                manual_val = ""
                
        selected_model_dropdown = st.selectbox("Modelo", available_models, index=sel_index)
        
        if selected_model_dropdown == "Otro (Manual)":
            model = st.text_input("Escribe el nombre del modelo", value=manual_val or "")
        else:
            model = selected_model_dropdown
        
        base_url = ""
        if provider == "Custom OpenAI" or provider == "DeepSeek" or provider == "Groq":
            base_url = st.text_input("Base URL", value=config.get("base_url", ""))
            
        if provider == "DeepSeek" and not base_url:
            base_url = "https://api.deepseek.com"
        elif provider == "Groq" and not base_url:
            base_url = "https://api.groq.com/openai/v1"
            
        input_key = f"temp_api_key_{st.session_state.key_version}"
        api_key_input = st.text_input(
            "API Key",
            value=config.get("api_key", ""),
            type="password",
            help="Requerido para usar IA.",
            key=input_key
        )
        
        if st.button("Guardar Configuración", use_container_width=True):
            new_config = {
                "provider": provider,
                "model": model,
                "api_key": api_key_input,
                "base_url": base_url
            }
            st.session_state.ai_config = new_config
            save_res = firebase_save_settings(st.session_state.user_email, new_config)
            msg_h = st.empty()
            if "error" in save_res:
                msg_h.error(firebase_error_message(save_res.get("error", {}).get("message", "Error desconocido")))
            else:
                msg_h.success("Configuración guardada")
            import time
            time.sleep(2)
            msg_h.empty()
            st.rerun()
        
        if st.button("Eliminar Key", use_container_width=True):
            st.session_state.ai_config = {}
            st.session_state.key_version += 1 # Forzar a Streamlit a recrear el widget
            save_res = firebase_save_settings(st.session_state.user_email, {})
            st.warning("Configuración eliminada.")
            import time
            time.sleep(1.5)
            st.rerun()
            
        if st.session_state.get("ai_config", {}).get("api_key") and st.session_state.get("ai_enabled"):
            st.success("IA Activada")
        elif not st.session_state.get("ai_enabled"):
            st.info("IA Pausada")

            st.session_state.ai_config = {}

    st.markdown("---")

    # ── Acciones rápidas ───────────────────────────────────────────
    st.markdown("### Panel")
    if st.button("Refrescar resultados", use_container_width=True):
        st.rerun()

    if st.button("Limpiar todos los resultados", use_container_width=True):
        u_email = st.session_state.get("user_email", "invitado@qa-agent.local")
        n = clear_results(user_id=u_email)
        st.success(f"Eliminados {n} resultados.")
        st.rerun()

    st.markdown("---")
    st.markdown("**Ejemplos de prompts:**")
    examples = [
        "prueba el login de esta página",
        "verifica que el formulario de registro funciona",
        "comprueba la página de inicio",
        "valida que el menú de navegación existe",
        "prueba login con credenciales inválidas",
    ]
    for ex in examples:
        if st.button(f"{ex}", key=f"ex_{ex}", use_container_width=True):
            st.session_state["sidebar_prompt"] = ex
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="qa-header">
  <h1>QA Agent No-Code</h1>
  <p>Crea pruebas repetibles, ejecutalas en navegador real y guarda reportes. Gemini es opcional: el constructor visual no consume tokens.</p>
</div>
""", unsafe_allow_html=True)

user_email = st.session_state.get("user_email", "invitado_default@qa-agent.local")

if "invitado_" in user_email:
    st.warning("🕵️ Estás en **Modo Invitado**. Los resultados solo se guardan de forma temporal (máx 10 tests) y se perderán. Para guardar en la nube y tener un historial ilimitado, por favor inicia sesión.")

# ── Métricas ───────────────────────────────────────────────────────────────────
results = load_all_results(user_id=user_email)
total   = len(results)
passed  = sum(1 for r in results if r.get("status") == "PASS")
failed  = total - passed
rate    = f"{int(passed/total*100)}%" if total > 0 else "–"

total_label = "Tests (Máx 10)" if "invitado_" in user_email else "Total Tests"
c1, c2, c3, c4 = st.columns(4)
for col, val, label, color in [
    (c1, f"{total}/10" if "invitado_" in user_email else total, total_label, "#e2e8f0"),
    (c2, passed, "Pasados",     "#10b981"),
    (c3, failed, "Fallados",    "#ef4444"),
    (c4, rate,   "Tasa de Exito",  "#818cf8"),
]:
    with col:
        st.markdown(f"""
        <div class="metric-box">
          <div class="metric-value" style="color:{color}">{val}</div>
          <div class="metric-label">{label}</div>
        </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TABS PRINCIPALES
# ══════════════════════════════════════════════════════════════════════════════
tab_run, tab_builder, tab_results = st.tabs([
    "Ejecutar Test",
    "Constructor Visual",
    "Historial de Resultados",
])


# ────────────────────────────────────────────────────────────────────────────
# TAB 1 - EJECUTAR TEST CON IA
# ────────────────────────────────────────────────────────────────────────────
with tab_run:
    st.markdown('<div class="section-title">Describe que quieres probar</div>', unsafe_allow_html=True)

    col_left, col_right = st.columns([3, 2])
    with col_left:
        default_prompt = st.session_state.pop("sidebar_prompt", "")
        is_ai_active = bool(st.session_state.get("ai_enabled") and st.session_state.get("ai_config", {}).get("api_key"))

        test_url = st.text_input(
            "URL del sitio a probar" if is_ai_active else "URL a verificar (Modo Basico)",
            placeholder="https://mi-sitio.com",
        )

        if is_ai_active:
            prompt = st.text_area(
                "Que quieres probar? (Lenguaje Natural con IA)",
                value=default_prompt,
                placeholder='Ej: "prueba el formulario de login con usuario admin y clave test123"',
                height=120,
            )
        else:
            prompt = ""
            st.text_area(
                "Generador de pruebas con IA",
                placeholder='La IA está desactivada.\n\n👉 Para usar lenguaje natural: Ve al menú izquierdo y activa la IA con tu propia API Key.\n\n👉 Para usuarios invitados: Recomendamos crear una cuenta gratuita para poder guardar tu configuración de IA de forma permanente.',
                height=120,
                disabled=True
            )
            st.info("💡 **Tip:** Puedes crear pruebas manualmente sin IA usando la pestaña **Constructor Visual**.")


        test_name = st.text_input("Nombre del test (opcional)", placeholder="Mi Test")

    with col_right:
        st.info("🤖 **¿Qué hace esta herramienta?**\nNuestro robot leerá tu instrucción, abrirá el sitio web y realizará todas las acciones automáticamente paso a paso.")
        st.markdown("**Ajustes (Opcional)**")
        step_timeout = st.select_slider("Tiempo de espera para cargar (seg)", options=[5, 10, 15, 20, 30], value=15, help="Aumenta esto si la página que vas a probar es muy lenta.")
        step_delay   = st.select_slider("Pausa entre clics (seg)", options=[0.0, 0.5, 1.0, 2.0], value=0.5, help="Si es muy rápido, aumentalo para ver con claridad lo que hace el robot.")
        st.markdown("")
        run_btn = st.button("🚀 Iniciar Prueba Automática", type="primary", use_container_width=True)

    st.markdown("---")

    if run_btn:
        if user_email == "invitado@qa-agent.local" and total >= 10:
            st.error("🛑 **Límite Alcanzado:** Has llegado al límite de 10 pruebas gratuitas como invitado. ¡Por favor regístrate para continuar usando QA Agent sin límites!")
            st.stop()
        if not prompt.strip() and not test_url.strip():
            st.warning("Escribe un prompt o indica una URL.")
        else:
            full_prompt = prompt.strip() or "verifica disponibilidad"
            if test_url.strip():
                full_prompt = full_prompt + " en " + test_url.strip()

            with st.spinner("Generando plan con IA..." if is_ai_active else "Generando plan basico..."):
                active_config = st.session_state.ai_config if st.session_state.ai_enabled else {}
                try:
                    steps = generate_test_plan(full_prompt, api_key=active_config.get("api_key"), model_name=active_config.get("model", "gemini-2.0-flash"), base_url=active_config.get("base_url"))
                except Exception as e:
                    st.error(str(e))
                    st.stop()

            st.session_state.plan_preview = steps
            n = len(steps)
            st.markdown(
                f'<div class="plan-preview"><div style="color:#22d3ee;font-weight:700;margin-bottom:8px;font-size:.9rem">Plan generado - {n} pasos</div>',
                unsafe_allow_html=True)
            render_plan_preview(steps)
            st.markdown("</div>", unsafe_allow_html=True)

            if True:
                import importlib
                from agent import executor_web
                importlib.reload(executor_web)
                from agent.reporter import save_result as _save
                final_name    = test_name.strip() or ("Test: " + full_prompt[:50])
                result_holder = {}
                
                user_email_check = st.session_state.get("user_email", "invitado@qa-agent.local")
                if "invitado_" in user_email_check and len(steps) > 7:
                    st.error("🛑 **Límite de Invitado:** Tu test tiene demasiados pasos. Los invitados solo pueden ejecutar hasta 7 pasos por prueba para prevenir abusos. Por favor, acorta tu prueba o inicia sesión.")
                    st.stop()

                with st.status("Ejecutando: " + final_name, expanded=True) as live_status:
                    for event in executor_web.run_test_streaming(
                        final_name, steps, timeout=step_timeout,
                        step_delay=step_delay, screenshot_on_fail=False,
                    ):
                        et = event.get("type")
                        if et == "start":
                            total = event["total"]
                            st.markdown(
                                f'<span style="color:#64748b;font-family:JetBrains Mono,monospace;font-size:.8rem">Iniciando Test - {total} pasos</span>',
                                unsafe_allow_html=True)
                        elif et == "step_start":
                            idx = event["index"]
                            tot = event["total"]
                            act = event["step"].get("action", "")
                            st.markdown(
                                f'<span style="color:#818cf8;font-family:JetBrains Mono,monospace;font-size:.78rem">Paso [{idx}/{tot}] {act}...</span>',
                                unsafe_allow_html=True)
                        elif et == "step_done":
                            r   = event["result"]
                            ok  = r["status"] == "ok"
                            css = "step-ok" if ok else "step-err"
                            act = r.get("action","")
                            det = r.get("detail","")
                            st.markdown(
                                f'<div class="step-item {css}"><span class="step-icon">{"ok" if ok else "x"}</span>'
                                f'<span class="step-text"><span class="step-action">[{act}]</span>{det}</span></div>',
                                unsafe_allow_html=True)
                            
                            if "screenshot" in r:
                                import base64
                                try:
                                    st.image(base64.b64decode(r["screenshot"]))
                                except Exception:
                                    pass

                        elif et == "driver_error":
                            st.error(event["message"])
                        elif et == "complete":
                            result_holder.update(event)

                    if result_holder.get("status") == "PASS":
                        live_status.update(label="PASS - " + final_name, state="complete", expanded=False)
                    else:
                        err = result_holder.get("error", "")
                        live_status.update(label="FAIL - " + err, state="error", expanded=True)

                if result_holder:
                    umail = st.session_state.get("user_email", "invitado@qa-agent.local")
                    
                    # Limpiar Base64 antes de guardar para no exceder límite de 1MB de Firestore
                    clean_steps = []
                    for s in result_holder.get("steps", []):
                        clean_s = s.copy()
                        if "screenshot" in clean_s:
                            del clean_s["screenshot"]
                        clean_steps.append(clean_s)

                    _save({
                        "test_name": final_name,
                        "status":    result_holder.get("status", "FAIL"),
                        "steps":     clean_steps,
                        "error":     result_holder.get("error", ""),
                    }, user_id=umail)

    elif st.session_state.plan_preview:
        st.markdown("**Ultimo plan generado:**")
        render_plan_preview(st.session_state.plan_preview)

# ────────────────────────────────────────────────────────────────────────────
# TAB 2 - CONSTRUCTOR VISUAL
# ────────────────────────────────────────────────────────────────────────────
with tab_builder:
    st.markdown('<div class="section-title">Constructor visual de pasos</div>', unsafe_allow_html=True)
    st.caption("Crea un test paso a paso sin codigo. Incluye acciones avanzadas: hover, scroll, teclas, capturas y mas.")

    col_b1, col_b2 = st.columns([2, 3])

    with col_b1:
        st.markdown("**1. Anadir paso**")
        ACTIONS = {
            "open_url":       "Abrir URL",
            "find_and_type":  "Escribir en campo",
            "click":          "Hacer clic",
            "hover":          "Hover sobre elemento",
            "press_key":      "Presionar tecla",
            "scroll_to":      "Scroll hasta elemento",
            "select_option":  "Seleccionar opcion (dropdown)",
            "validate_text":  "Validar texto",
            "validate_url":   "Validar URL actual",
            "validate_exists":"Verificar que existe",
            "wait":           "Esperar N segundos",
            "screenshot":     "Captura de pantalla",
            "generate_email": "Generar correo seguro",
            "wait_for_email": "Esperar correo",
        }

        b_action = st.selectbox("Accion", list(ACTIONS.keys()), format_func=lambda x: ACTIONS[x])

        b_selector = ""
        b_value    = ""

        if b_action == "open_url":
            b_value = st.text_input("URL", placeholder="https://mi-sitio.com", key="bv_url")

        elif b_action == "find_and_type":
            b_selector = st.text_input("Selector CSS del campo", placeholder="input[name='user'], #email", key="bs_ft")
            b_value    = st.text_input("Texto a escribir", placeholder="admin", key="bv_ft")

        elif b_action == "click":
            b_selector = st.text_input("Selector CSS", placeholder="button[type='submit'], .btn-login", key="bs_cl")

        elif b_action == "hover":
            b_selector = st.text_input("Selector CSS", placeholder=".menu-item, nav a", key="bs_hv")

        elif b_action == "press_key":
            b_selector = st.text_input("Selector CSS (opcional, para enfocar)", placeholder="Dejar vacio para teclado global", key="bs_pk")
            b_value    = st.selectbox("Tecla", ["enter","tab","escape","space","backspace","delete","up","down","left","right","home","end","pageup","pagedown"], key="bv_pk")

        elif b_action == "scroll_to":
            b_selector = st.text_input("Selector CSS del elemento destino", placeholder="#footer, .section-2", key="bs_sc")
            if not b_selector:
                b_value = st.text_input("O pixels a bajar (si no hay selector)", placeholder="500", key="bv_sc")

        elif b_action == "select_option":
            b_selector = st.text_input("Selector CSS del select", placeholder="select#pais, .dropdown", key="bs_so")
            b_value    = st.text_input("Texto visible de la opcion", placeholder="Colombia", key="bv_so")

        elif b_action == "validate_text":
            b_selector = st.text_input("Selector CSS", placeholder="h1, .alert, #mensaje", key="bs_vt")
            b_value    = st.text_input("Texto esperado (parcial)", placeholder="Bienvenido", key="bv_vt")

        elif b_action == "validate_url":
            b_value = st.text_input("URL parcial esperada", placeholder="dashboard, /home", key="bv_vu")

        elif b_action == "validate_exists":
            b_selector = st.text_input("Selector CSS a verificar", placeholder=".navbar, #logo, button", key="bs_ve")

        elif b_action == "wait":
            b_value = st.select_slider("Segundos a esperar", options=[0.5, 1.0, 1.5, 2.0, 3.0, 5.0], value=1.0, key="bv_wt")
            b_value = str(b_value)

        elif b_action == "screenshot":
            b_value = ""  # Sin parametros adicionales

        elif b_action == "generate_email":
            b_value = st.text_input("Prefijo opcional (ej: user_test)", placeholder="Aleatorio si queda vacio", key="bv_ge")

        elif b_action == "wait_for_email":
            b_value = st.text_input("Correo a monitorear (opcional)", placeholder="Usa el último generado si queda vacio", key="bv_we")

        # Validacion y boton agregar
        REQUIRES_SEL = {"find_and_type","click","hover","scroll_to","select_option","validate_text","validate_exists"}
        REQUIRES_VAL = {"open_url","find_and_type","select_option","validate_text","validate_url","wait"}

        if st.button("Anadir paso", use_container_width=True):
            err = None
            if b_action in REQUIRES_SEL and not b_selector and b_action != "scroll_to":
                err = "Selector CSS requerido para esta accion."
            elif b_action in REQUIRES_VAL and not b_value and b_action not in ("scroll_to",):
                err = "Valor/texto requerido para esta accion."
            if err:
                st.error(err)
            else:
                step = {"action": b_action}
                if b_selector: step["selector"] = b_selector
                if b_value:    step["value"]    = b_value
                st.session_state.custom_steps.append(step)
                st.success("Paso '" + b_action + "' agregado (" + str(len(st.session_state.custom_steps)) + " pasos)")
                st.rerun()

        st.markdown("---")
        st.markdown("**2. Anadir pasos con IA**")
        is_ai = bool(st.session_state.get("ai_enabled") and st.session_state.get("ai_config", {}).get("api_key"))
        if is_ai:
            ai_p = st.text_area("Describe la accion en lenguaje natural", placeholder="Ej: escribe 'admin' en el campo usuario y pulsa Enter", height=80, key="ai_step_prompt")
            if st.button("Generar paso con IA", use_container_width=True):
                if ai_p.strip():
                    with st.spinner("Interpretando accion..."):
                        try:
                            cfg = st.session_state.get("ai_config", {}); new_steps = generate_test_plan(ai_p, api_key=cfg.get("api_key"), model_name=cfg.get("model", "gemini-2.0-flash"), base_url=cfg.get("base_url"))
                            if new_steps:
                                st.session_state.custom_steps.extend(new_steps)
                                st.rerun()
                        except Exception as e:
                            st.error(str(e))
                else:
                    st.warning("Escribe una instruccion primero.")
        else:
            st.text_area("IA desactivada", placeholder="Activa tu API Key de IA en el panel lateral.", height=60, disabled=True, key="ai_step_disabled")

        st.markdown("---")
        b_test_name = st.text_input("Nombre de la prueba", placeholder="Ej: Comprar un producto", key="b_name")
        st.markdown("**Ajustes de velocidad**")
        b_timeout  = st.select_slider("Tiempo límite de carga (seg)", options=[5,10,15,20,30], value=15, key="b_timeout")
        b_delay    = st.select_slider("Pausa entre cada paso (seg)", options=[0.0,0.5,1.0,2.0], value=0.5, key="b_delay")

        cr1, cr2 = st.columns(2)
        with cr1:
            if st.button("Limpiar pasos", use_container_width=True):
                st.session_state.custom_steps = []
                st.rerun()
        with cr2:
            run_custom = st.button("Ejecutar", type="primary", use_container_width=True)

    with col_b2:
        st.markdown("**Pasos del test**")
        custom_steps = st.session_state.custom_steps

        if not custom_steps:
            st.markdown(
                '<div style="background:#0f172a;border:1px dashed #334155;border-radius:10px;'
                'padding:30px;text-align:center;color:#475569;">'
                '<div style="font-size:2rem;margin-bottom:8px">+</div>'
                '<div>No hay pasos aun. Anade acciones desde el panel izquierdo.</div>'
                '</div>',
                unsafe_allow_html=True)

        else:
            for i, s in enumerate(custom_steps):
                act    = s.get("action","")
                val    = s.get("value","")
                sel    = s.get("selector","")
                detail = val if val else sel
                c_num, c_info, c_up, c_dn, c_del = st.columns([0.5, 5.5, 0.8, 0.8, 0.8])
                with c_num:
                    st.markdown(f"<div style='color:#818cf8;font-family:JetBrains Mono,monospace;font-size:.85rem;padding-top:8px;'>{i+1}</div>", unsafe_allow_html=True)
                with c_info:
                    st.markdown(
                        f'<div class="plan-step" style="border-bottom:none;padding:4px 0;">'
                        f'<span class="plan-act">[{act}]</span>'
                        f'<span style="color:#94a3b8">{detail}</span></div>',
                        unsafe_allow_html=True)
                with c_up:
                    if i > 0 and st.button("↑", key=f"up_{i}", help="Subir", use_container_width=True):
                        custom_steps[i-1], custom_steps[i] = custom_steps[i], custom_steps[i-1]
                        st.rerun()
                with c_dn:
                    if i < len(custom_steps)-1 and st.button("↓", key=f"dn_{i}", help="Bajar", use_container_width=True):
                        custom_steps[i], custom_steps[i+1] = custom_steps[i+1], custom_steps[i]
                        st.rerun()
                with c_del:
                    if st.button("×", key=f"del_{i}", help="Eliminar", use_container_width=True):
                        st.session_state.custom_steps.pop(i)
                        st.rerun()

            st.markdown("---")
            with st.expander("Exportar / Importar pasos (JSON)"):
                st.code(json.dumps(custom_steps, indent=2, ensure_ascii=False), language="json")
                imported = st.text_area("Pega JSON aqui para importar", height=120, key="import_json")
                if st.button("Importar pasos"):
                    try:
                        parsed = json.loads(imported)
                        if isinstance(parsed, list):
                            st.session_state.custom_steps = parsed
                            st.success(str(len(parsed)) + " pasos importados.")
                            st.rerun()
                        else:
                            st.error("El JSON debe ser una lista de pasos.")
                    except json.JSONDecodeError as e:
                        st.error("JSON invalido: " + str(e))

    # Ejecucion con streaming
    if run_custom:
        if "invitado_" in st.session_state.get("user_email", "") and len(load_all_results(st.session_state.get("user_email", ""))) >= 10:
            st.error("🛑 **Límite Alcanzado:** Has llegado al límite de 10 pruebas gratuitas como invitado. ¡Por favor regístrate para continuar usando QA Agent sin límites!")
            st.stop()
        if not custom_steps:
            st.warning("Anade al menos un paso primero.")
        else:
            import importlib
            from agent import executor_web
            importlib.reload(executor_web)
            from agent.reporter import save_result as _save
            name = b_test_name.strip() or ("Test Personalizado " + datetime.now().strftime("%H:%M:%S"))
            result_holder = {}
            
            user_email_check = st.session_state.get("user_email", "invitado@qa-agent.local")
            if "invitado_" in user_email_check and len(custom_steps) > 7:
                st.error("🛑 **Límite de Invitado:** Tu test tiene demasiados pasos. Los invitados solo pueden ejecutar hasta 7 pasos por prueba. Por favor, elimina pasos o inicia sesión para pruebas ilimitadas.")
                st.stop()

            with st.status("Ejecutando: " + name, expanded=True) as live_status:
                for event in executor_web.run_test_streaming(
                    name, custom_steps, timeout=b_timeout,
                    step_delay=b_delay, screenshot_on_fail=False,
                ):
                    et = event.get("type")
                    if et == "start":
                        st.markdown(f'<span style="color:#64748b;font-family:JetBrains Mono,monospace;font-size:.8rem">Iniciando Test - {event["total"]} pasos</span>', unsafe_allow_html=True)
                    elif et == "step_start":
                        idx = event["index"]
                        tot = event["total"]
                        act = event["step"].get("action","")
                        st.markdown(f'<span style="color:#818cf8;font-family:JetBrains Mono,monospace;font-size:.78rem">Paso [{idx}/{tot}] {act}...</span>', unsafe_allow_html=True)
                    elif et == "step_done":
                        r   = event["result"]
                        ok  = r["status"] == "ok"
                        css = "step-ok" if ok else "step-err"
                        act = r.get("action","")
                        det = r.get("detail","")
                        st.markdown(
                            f'<div class="step-item {css}"><span class="step-icon">{"ok" if ok else "x"}</span>'
                            f'<span class="step-text"><span class="step-action">[{act}]</span>{det}</span></div>',
                            unsafe_allow_html=True)
                        
                        if "screenshot" in r:
                            import base64
                            try:
                                st.image(base64.b64decode(r["screenshot"]))
                            except Exception:
                                pass

                    elif et == "driver_error":
                        st.error(event["message"])
                    elif et == "complete":
                        result_holder.update(event)

                if result_holder.get("status") == "PASS":
                    live_status.update(label="PASS - " + name, state="complete", expanded=False)
                else:
                    err = result_holder.get("error","")
                    live_status.update(label="FAIL - " + err, state="error", expanded=True)

            if result_holder:
                umail = st.session_state.get("user_email","invitado@qa-agent.local")
                _save({
                    "test_name": name,
                    "status":    result_holder.get("status","FAIL"),
                    "steps":     result_holder.get("steps",[]),
                    "error":     result_holder.get("error",""),
                }, user_id=umail)

# ────────────────────────────────────────────────────────────────────────────
# TAB 3 · HISTORIAL DE RESULTADOS
# ────────────────────────────────────────────────────────────────────────────
with tab_results:
    st.markdown('<div class="section-title">📊 Historial de resultados</div>', unsafe_allow_html=True)

    user_email = st.session_state.get("user_email", "invitado_default@qa-agent.local")
    results = load_all_results(user_id=user_email)
    total = len(results)  # Calcular total ANTES de usarlo

    if not results:
        st.info("🔍 No hay resultados aún. Ejecuta tu primer test en la pestaña **Ejecutar Test**.")
    else:
        col_f1, col_f2, col_f3 = st.columns([3, 1, 1])
        with col_f1:
            search = st.text_input("🔍 Buscar test", placeholder="Filtrar por nombre...", key="search")
        with col_f2:
            filter_status = st.selectbox("Estado", ["Todos", "PASS", "FAIL"], key="fstatus")
        with col_f3:
            sort_order = st.selectbox("Orden", ["Más reciente", "Más antiguo"], key="fsort")

        filtered = results
        if search:
            filtered = [r for r in filtered if search.lower() in r.get("test_name", "").lower()]
        if filter_status != "Todos":
            filtered = [r for r in filtered if r.get("status") == filter_status]
        if sort_order == "Más antiguo":
            filtered = list(reversed(filtered))

        st.markdown(
            f"<p style='color:#64748b;font-size:.85rem'>Mostrando {len(filtered)} de {total} resultados</p>",
            unsafe_allow_html=True,
        )

        for i, result in enumerate(filtered, 1):
            render_result_card(result, i)

# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<p style='text-align:center;color:#334155;font-size:.75rem;font-family:JetBrains Mono,monospace'>"
    "QA Agent No-Code · Selenium + Gemini · Python · Streamlit"
    "</p>",
    unsafe_allow_html=True,
)
