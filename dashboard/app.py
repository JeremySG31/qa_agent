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
  padding: 24px 20px;
  text-align: center;
  box-shadow: 0 10px 30px -5px rgba(56, 189, 248, 0.15), inset 0 1px 0 rgba(255,255,255,0.1);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}
.metric-box::before {
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 100%;
  background: radial-gradient(circle at top right, rgba(255,255,255,0.05), transparent 60%);
  pointer-events: none;
}
.metric-box:hover {
  transform: translateY(-5px);
  box-shadow: 0 20px 40px -5px rgba(56, 189, 248, 0.3), inset 0 1px 0 rgba(255,255,255,0.2);
  border-color: #38bdf8;
}
.metric-value { 
  font-family: 'Syne', sans-serif; 
  font-size: 3.5rem; 
  font-weight: 800; 
  line-height: 1.1; 
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
if "gemini_enabled" not in st.session_state:
    st.session_state.gemini_enabled = False
if "key_version" not in st.session_state:
    st.session_state.key_version = 0
if "gemini_api_key" not in st.session_state:
    st.session_state.gemini_api_key = os.getenv("GEMINI_API_KEY", "").strip()
if "firebase_id_token" not in st.session_state:
    st.session_state.firebase_id_token = ""

# ── Configuración de Firebase ──────────────────────────────────────────────────
# Se recomienda rotar esta clave en la consola de Firebase
FIREBASE_API_KEY = os.getenv("FIREBASE_API_KEY", "").strip()
FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID", "qa-agent-web").strip()
FIREBASE_REQUEST_URI = os.getenv("FIREBASE_REQUEST_URI", "http://localhost:8501").strip()
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "").strip()


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


def firebase_google_login(id_token):
    if not FIREBASE_API_KEY:
        return {"error": {"message": "INVALID_API_KEY"}}
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithIdp?key={FIREBASE_API_KEY}"
    payload = {
        "postBody": f"id_token={quote(id_token)}&providerId=google.com",
        "requestUri": FIREBASE_REQUEST_URI,
        "returnIdpCredential": True,
        "returnSecureToken": True
    }
    return firebase_request("POST", url, json=payload)


def firebase_save_settings(email, gemini_key):
    # Sanitizar email para el ID del documento
    doc_id = email.replace("@", "_at_").replace(".", "_dot_")
    url = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents/users/{doc_id}?updateMask.fieldPaths=gemini_api_key&key={FIREBASE_API_KEY}"
    payload = {
        "fields": {
            "gemini_api_key": {"stringValue": gemini_key}
        }
    }
    # Usar patch para crear o actualizar el documento
    return firebase_request("PATCH", url, json=payload, headers=firebase_headers())


def firebase_load_settings(email):
    doc_id = email.replace("@", "_at_").replace(".", "_dot_")
    url = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents/users/{doc_id}?key={FIREBASE_API_KEY}"
    data = firebase_request("GET", url, headers=firebase_headers())
    if "error" not in data:
        return data.get("fields", {}).get("gemini_api_key", {}).get("stringValue", "")
    return ""

# ── Manejo de Código OAuth (ELIMINADO) ─────────────────────────────────────────
# Se elimina por restricciones de Streamlit Cloud e iframe.

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
            l_email = st.text_input("Correo electrónico", key="l_email")
            l_pass = st.text_input("Contraseña", type="password", key="l_pass")
            if st.button("Ingresar", use_container_width=True, type="primary"):
                if l_email and l_pass:
                    with st.spinner("Autenticando..."):
                        res = firebase_login(l_email, l_pass)
                        if "idToken" in res:
                            st.session_state.user_logged_in = True
                            st.session_state.user_email = res.get("email")
                            st.session_state.firebase_id_token = res.get("idToken", "")
                            # CARGAR CONFIGURACIÓN DESDE FIRESTORE
                            st.session_state.gemini_api_key = firebase_load_settings(res.get("email"))
                            st.rerun()
                        else:
                            raw_error = res.get("error", {}).get("message", "Error desconocido")
                            st.error(firebase_error_message(raw_error))
                else:
                    st.warning("Completa los campos")
                
        with tab_register:
            r_email = st.text_input("Correo electrónico", key="r_email")
            r_pass = st.text_input("Contraseña", type="password", key="r_pass")
            r_pass2 = st.text_input("Repetir contraseña", type="password", key="r_pass2")
            if st.button("Crear cuenta", use_container_width=True):
                if r_email and r_pass and r_pass == r_pass2:
                    with st.spinner("Creando cuenta en Firebase..."):
                        res = firebase_register(r_email, r_pass)
                        if "idToken" in res:
                            st.session_state.user_logged_in = True
                            st.session_state.user_email = res.get("email")
                            st.session_state.firebase_id_token = res.get("idToken", "")
                            # CARGAR CONFIGURACIÓN DESDE FIRESTORE (estará vacío pero inicializa)
                            st.session_state.gemini_api_key = ""
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
            st.session_state.user_logged_in = True
            st.session_state.user_email = "invitado@qa-agent.local"
            st.session_state.is_guest = True
            st.session_state.gemini_api_key = "" # No tiene API Key guardada
            st.rerun()

        st.markdown("<div style='text-align:center; color:#64748b; font-size:0.85rem; letter-spacing:1px; margin-top:20px; margin-bottom:20px;'>PROTEGIDO POR FIREBASE</div>", unsafe_allow_html=True)
        st.caption("Usa tu correo y contraseña para acceder a tus reportes guardados en la nube.")
            
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
    if st.button("👤 Mi Perfil", use_container_width=True):
        show_profile()
    if st.button("🚪 Cerrar Sesión", use_container_width=True):
        st.session_state.user_logged_in = False
        st.session_state.user_email = ""
        st.session_state.firebase_id_token = ""
        st.rerun()
    st.markdown("---")

    # ── Configuración de IA ────────────────────────────────────────
    with st.expander("Configuracion de IA", expanded=False):
        st.toggle("Activar Inteligencia Artificial", value=False, key="gemini_enabled", help="Apágalo para no consumir la cuota de tu API.")

        input_key = f"temp_api_key_{st.session_state.key_version}"
        api_key_input = st.text_input(
            "Gemini API Key",
            value=st.session_state.gemini_api_key,
            type="password",
            help="Opcional. Sin key usa modo básico.",
            key=input_key
        )
        if st.button("💾 Guardar Configuración", use_container_width=True):
            st.session_state.gemini_api_key = api_key_input
            save_res = firebase_save_settings(st.session_state.user_email, api_key_input)
            msg_h = st.empty()
            if "error" in save_res:
                msg_h.error(firebase_error_message(save_res.get("error", {}).get("message", "Error desconocido")))
            else:
                msg_h.success("¡Configuración guardada!")
            import time
            time.sleep(2)
            msg_h.empty()
        
        if st.button("🗑️ Eliminar Key", use_container_width=True):
            st.session_state.gemini_api_key = ""
            st.session_state.key_version += 1 # Forzar a Streamlit a recrear el widget (limpiarlo)
            save_res = firebase_save_settings(st.session_state.user_email, "")
            st.warning("Key eliminada de la base de datos.")
            if "error" in save_res:
                st.error(firebase_error_message(save_res.get("error", {}).get("message", "Error desconocido")))
            import time
            time.sleep(1.5)
            st.rerun()
        if api_key_input != st.session_state.gemini_api_key:
            st.session_state.gemini_api_key = api_key_input
            st.rerun()
            
        if st.session_state.gemini_api_key and st.session_state.gemini_enabled:
            st.success("✅ IA Activada")
        elif not st.session_state.gemini_enabled:
            st.info("⏸️ IA Pausada (Modo básico)")

        st.caption("Obtén tu clave gratis en [ai.google.dev](https://ai.google.dev)")

    st.markdown("---")

    # ── Acciones rápidas ───────────────────────────────────────────
    st.markdown("### Panel")
    if st.button("Refrescar resultados", use_container_width=True):
        st.rerun()

    if st.button("Limpiar todos los resultados", use_container_width=True):
        n = clear_results()
        st.success(f"Eliminados {n} resultados.")
        st.rerun()

    st.markdown("---")
    st.markdown("**💡 Ejemplos de prompts:**")
    examples = [
        "prueba el login de esta página",
        "verifica que el formulario de registro funciona",
        "comprueba la página de inicio",
        "valida que el menú de navegación existe",
        "prueba login con credenciales inválidas",
    ]
    for ex in examples:
        if st.button(f"↗ {ex}", key=f"ex_{ex}", use_container_width=True):
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

# ── Métricas ───────────────────────────────────────────────────────────────────
results = load_all_results()
total   = len(results)
passed  = sum(1 for r in results if r.get("status") == "PASS")
failed  = total - passed
rate    = f"{int(passed/total*100)}%" if total > 0 else "–"

c1, c2, c3, c4 = st.columns(4)
for col, val, label, color in [
    (c1, total,  "Total Tests",    "#e2e8f0"),
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
# TAB 1 · EJECUTAR TEST CON IA
# ────────────────────────────────────────────────────────────────────────────
with tab_run:
    st.markdown('<div class="section-title">Describe que quieres probar</div>', unsafe_allow_html=True)

    col_left, col_right = st.columns([3, 2])

    with col_left:
        # Prompt preseleccionado desde sidebar
        default_prompt = st.session_state.pop("sidebar_prompt", "")
        
        is_ai_active = st.session_state.get("gemini_enabled", True) and st.session_state.get("gemini_api_key", "")

        test_url = st.text_input(
            "URL del sitio a probar" if is_ai_active else "URL a verificar (Modo Ping/Básico)",
            placeholder="https://mi-sitio.com (vacio para demo)",
            help="El agente usara esta URL como base para generar los pasos." if is_ai_active else "El agente solo abrirá esta URL para comprobar si está disponible."
        )

        if is_ai_active:
            prompt = st.text_area(
                "¿Qué quieres probar? (Lenguaje Natural con IA)",
                value=default_prompt,
                placeholder='Ej: "prueba el formulario de login"',
                height=120,
            )
        else:
            prompt = st.text_area(
                "Lenguaje natural desactivado (IA Apagada)",
                value=default_prompt,
                placeholder='La Inteligencia Artificial está pausada. Ve a la pestaña "Constructor Visual" para pasos manuales.',
                height=120,
                disabled=True,
                help="Sin IA, el sistema no puede interpretar lenguaje natural. Usa el Constructor Visual para pruebas complejas gratuitas."
            )
            st.info("💡 **Consejo:** Para crear un test paso a paso sin gastar cuota de IA, dirígete a la pestaña superior **Constructor Visual**.")

        test_name = st.text_input(
            "Nombre del test (opcional)",
            placeholder="Mi Test",
        )

    with col_right:
        st.markdown("**Opciones de ejecucion**")
        test_type = "web" # Simplificado a web por ahora


        headless = st.checkbox(
            "Modo headless (sin ventana)",
            value=True,
            help="Si desactivado, veras el navegador abrirse.",
        )

        preview_only = st.checkbox(
            "Solo previsualizar plan (sin ejecutar)",
            value=False,
            help="Genera el plan sin lanzar el navegador.",
        )

        st.markdown("")
        run_btn = st.button("Generar y Ejecutar Test", type="primary", use_container_width=True)

    st.markdown("---")

    # Ejecutar 
    if run_btn:
        if not prompt.strip() and not test_url.strip():
            st.warning("Escribe un prompt o indica una URL.")
        else:
            # Construir prompt con URL si se proporcionó
            full_prompt = prompt.strip() or "verifica disponibilidad"
            if test_url.strip():
                full_prompt = f"{full_prompt} en {test_url.strip()}"

            # 1. Generar plan
            spinner_msg = "Generando plan con IA..." if st.session_state.gemini_enabled and st.session_state.gemini_api_key else "Generando plan básico..."
            with st.spinner(spinner_msg):
                active_api_key = st.session_state.gemini_api_key if st.session_state.gemini_enabled else ""
                try:
                    steps = generate_test_plan(full_prompt, api_key=active_api_key)
                except Exception as e:
                    st.error(str(e))
                    st.stop()

            st.session_state.plan_preview = steps

            st.success(f"Plan generado: {len(steps)} pasos")
            st.markdown("**Vista previa del plan:**")
            render_plan_preview(steps)

            if not preview_only:

                from agent.executor import run_test
                from agent.reporter import save_result as _save

                final_name = test_name.strip() or f"Test: {full_prompt[:50]}"
                with st.spinner("Ejecutando automatizacion..."):
                    result = run_test(final_name, steps, test_type=test_type, headless=headless)

                _save(result)
                status = result.get("status")
                if status == "PASS":
                    st.success("Test completado: PASS")
                else:
                    st.error(f"Test fallo: {result.get('error','')}")
                
                with st.expander("Detalle de pasos"):
                    render_steps(result.get("steps", []))


    elif st.session_state.plan_preview:
        st.markdown("**Último plan generado:**")
        render_plan_preview(st.session_state.plan_preview)


# ────────────────────────────────────────────────────────────────────────────
# TAB 2 · CONSTRUCTOR VISUAL (sin código)
# ────────────────────────────────────────────────────────────────────────────
with tab_builder:
    st.markdown('<div class="section-title">Constructor visual de pasos</div>', unsafe_allow_html=True)
    st.caption("Crea un test paso a paso sin escribir código. Cada acción se añade a la lista.")

    col_b1, col_b2 = st.columns([2, 3])

    with col_b1:
        st.markdown("**1. Configurar Plataforma**")
        b_type = st.selectbox("Plataforma", ["web"], key="b_type") # Limitado a web por ahora

        st.markdown("**2. Añadir paso**")
        
        # Filtrar acciones según plataforma (Solo Web activa)
        actions = {
            "open_url":       "🌐 Abrir URL",
            "find_and_type":  "⌨️ Escribir en campo",
            "click":          "👆 Hacer clic",
            "validate_text":  "🔍 Validar texto",
            "validate_url":   "✅ Validar URL actual",
            "validate_exists":"👁️ Verificar que existe",
        }

        b_action = st.selectbox("Acción", list(actions.keys()), format_func=lambda x: actions[x])


        b_url = ""
        b_selector = ""
        b_value = ""

        # UI dinámica según la acción seleccionada
        if b_action in ("open_url", "open_app", "adb_open_app"):
            label = "URL" if b_action == "open_url" else ("Package Name" if b_action == "adb_open_app" else "Ruta/Nombre App")
            b_value = st.text_input(label, placeholder="https://... o notepad.exe", key="b_val_main")
        
        elif b_action in ("find_and_type", "type_text", "adb_type", "validate_text"):
            if b_action == "find_and_type":
                b_selector = st.text_input("Selector CSS", placeholder="input[type='email']", key="b_sel_web")
            b_value = st.text_input("Texto a escribir/validar", placeholder="Hola mundo", key="b_val_text")
        
        elif b_action in ("click", "adb_tap", "adb_swipe"):
            placeholder = "x,y (ej: 500,400)" if b_action != "adb_swipe" else "x1,y1,x2,y2"
            b_selector = st.text_input("Coordenadas" if b_type != "web" else "Selector CSS", placeholder=placeholder, key="b_sel_coord")
        
        elif b_action in ("press_key", "adb_keyevent", "wait", "validate_url"):
            label = "Tecla (ej: enter, esc)" if "key" in b_action else ("Segundos" if b_action == "wait" else "URL parcial")
            b_value = st.text_input(label, key="b_val_spec")

        if st.button("➕ Añadir paso", use_container_width=True):
            step = {"action": b_action}
            if b_selector: step["selector"] = b_selector
            if b_value:    step["value"]    = b_value
            st.session_state.custom_steps.append(step)
            st.rerun()

        st.markdown("---")
        st.markdown("**3. Añadir pasos con IA**")
        is_ai_active = st.session_state.get("gemini_enabled", True) and st.session_state.get("gemini_api_key", "")
        
        if is_ai_active:
            ai_step_prompt = st.text_area("¿Qué acción deseas añadir? (Lenguaje Natural)", placeholder="Ej: escribe 'admin' en el campo de usuario y dale al botón enviar", height=80, key="ai_step_prompt")
            if st.button("✨ Generar paso con IA", use_container_width=True):
                if ai_step_prompt.strip():
                    with st.spinner("Interpretando acción..."):
                        from agent.planner import generate_test_plan
                        try:
                            new_steps = generate_test_plan(ai_step_prompt, api_key=st.session_state.gemini_api_key)
                            if new_steps:
                                st.session_state.custom_steps.extend(new_steps)
                                st.rerun()
                        except Exception as e:
                            st.error(str(e))
                else:
                    st.warning("Escribe una instrucción primero.")
        else:
            st.text_area(
                "Lenguaje natural desactivado",
                placeholder="Activa la IA en el menú lateral para añadir pasos automáticamente.",
                height=80,
                disabled=True,
                key="ai_step_prompt_disabled",
                help="La Inteligencia Artificial está pausada."
            )

        st.markdown("---")
        b_test_name = st.text_input("🏷️ Nombre del test", placeholder="Mi Test Personalizado", key="b_name")
        b_run_type = b_type # Usar la plataforma seleccionada arriba
        b_headless  = st.checkbox("🫥 Headless (solo web)", value=True, key="b_headless")



        col_r1, col_r2 = st.columns(2)
        with col_r1:
            if st.button("🗑️ Limpiar pasos", use_container_width=True):
                st.session_state.custom_steps = []
                st.rerun()
        with col_r2:
            run_custom = st.button("▶ Ejecutar", type="primary", use_container_width=True)

    with col_b2:
        st.markdown("**Pasos del test**")
        custom_steps = st.session_state.custom_steps

        if not custom_steps:
            st.info("No hay pasos aún. Añade acciones desde el panel izquierdo.")
        else:
            for i, s in enumerate(custom_steps):
                c_del, c_info = st.columns([1, 8])
                with c_del:
                    if st.button("✕", key=f"del_{i}", help="Eliminar paso"):
                        st.session_state.custom_steps.pop(i)
                        st.rerun()
                with c_info:
                    action = s.get("action", "")
                    val    = s.get("value", "")
                    sel    = s.get("selector", "")
                    detail = val if val else sel
                    st.markdown(f"""
                    <div class="plan-step" style="border-bottom:none;padding:4px 0;">
                      <span class="plan-num">{i+1}.</span>
                      <span class="plan-act">[{action}]</span>
                      <span style="color:#94a3b8">{detail}</span>
                    </div>""", unsafe_allow_html=True)

            # Importar/exportar como JSON
            st.markdown("---")
            with st.expander("📤 Exportar / Importar pasos (JSON)"):
                st.code(json.dumps(custom_steps, indent=2, ensure_ascii=False), language="json")
                imported = st.text_area("Pega JSON aquí para importar", height=120, key="import_json")
                if st.button("📥 Importar pasos"):
                    try:
                        parsed = json.loads(imported)
                        if isinstance(parsed, list):
                            st.session_state.custom_steps = parsed
                            st.success(f"✅ {len(parsed)} pasos importados.")
                            st.rerun()
                        else:
                            st.error("El JSON debe ser una lista de pasos.")
                    except json.JSONDecodeError as e:
                        st.error(f"JSON inválido: {e}")

    # ── Ejecutar test personalizado ────────────────────────────────
    if run_custom:
        if not custom_steps:
            st.warning("Añade al menos un paso primero.")
        else:
            from agent.executor import run_test
            from agent.reporter import save_result as _save

            name = b_test_name.strip() or f"Test Personalizado {datetime.now().strftime('%H:%M:%S')}"
            with st.spinner(f"🚀 Ejecutando test {b_run_type}..."):
                result = run_test(name, custom_steps, test_type=b_run_type, headless=b_headless)


            _save(result)
            status = result.get("status")
            if status == "PASS":
                st.success(f"🎉 {name} — PASS")
            else:
                st.error(f"❌ {name} — FAIL: {result.get('error','')}")

            with st.expander("📋 Detalle de pasos"):
                render_steps(result.get("steps", []))


# ────────────────────────────────────────────────────────────────────────────
# TAB 3 · HISTORIAL DE RESULTADOS
# ────────────────────────────────────────────────────────────────────────────
with tab_results:
    st.markdown('<div class="section-title">📊 Historial de resultados</div>', unsafe_allow_html=True)

    results = load_all_results()

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
