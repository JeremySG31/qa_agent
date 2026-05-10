"""

dashboard/app.py - Dashboard QA con interfaz completa sin código

Ejecutar con: streamlit run dashboard/app.py

"""



import sys, os, json, subprocess, re, importlib, uuid
from pathlib import Path
from datetime import datetime
from urllib.parse import quote
import streamlit as st
import streamlit.components.v1 as components
import platform

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import agent.planner
from agent.reporter import load_all_results, clear_results, save_result
from agent.planner  import generate_test_plan
from agent.crypto   import encrypt_data, decrypt_data
from streamlit_sortables import sort_items



@st.cache_data(ttl=300)

def get_cached_results(user_id):

    return load_all_results(user_id)



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

    initial_sidebar_state="collapsed",

)



# ── Verificación de Dominio (Google Search Console) ─────────────────────────────

st.markdown('<meta name="google-site-verification" content="1TyKKbQRLHJ9LvfxZnKzvgQUzSuz5EH_J4g5vjc3O-I" />', unsafe_allow_html=True)



# ── CSS ────────────────────────────────────────────────────────────────────────

st.markdown("""

<style>

@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Syne:wght@400;700;800&display=swap');



html, body, [data-testid="stAppViewContainer"] { 
    font-family:'Syne',sans-serif; 
    background:#0d0f14 !important; 
    color:#e2e8f0 !important; 
}



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
  font-size: 2.2rem; 
  font-weight: 800; 
  line-height: 1.1; 
  background: linear-gradient(135deg, #22d3ee, #818cf8, #f472b6);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  filter: drop-shadow(0px 4px 8px rgba(56,189,248,0.3));
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



/* Sidebar Styling */
[data-testid="stSidebar"] { 
    background: linear-gradient(180deg, #0f172a 0%, #0d0f14 100%) !important; 
    border-right: 1px solid #1e293b !important; 
}

/* El contenido interno de la barra lateral también necesita el fondo para evitar parches grises */
[data-testid="stSidebar"] > div {
    background: transparent !important;
}

[data-testid="stSidebar"] h2 {
    color: #22d3ee !important;
    font-weight: 800 !important;
    letter-spacing: -0.5px;
    margin-bottom: 20px !important;
    font-family: 'Syne', sans-serif !important;
}

[data-testid="stSidebar"] h3 {
    color: #94a3b8 !important;
    font-size: 1rem !important;
    font-weight: 700 !important;
    margin-top: 15px !important;
}

[data-testid="stSidebar"] .stButton button {
    background: rgba(30, 41, 59, 0.5) !important;
    border: 1px solid #334155 !important;
    color: #cbd5e1 !important;
    font-size: 0.85rem !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    text-align: left !important;
    padding: 10px 15px !important;
    border-radius: 10px !important;
    margin-bottom: 4px !important;
}

[data-testid="stSidebar"] .stButton button:hover {
    border-color: #22d3ee !important;
    color: #ffffff !important;
    background: rgba(34, 211, 238, 0.1) !important;
    transform: translateX(5px) !important;
    box-shadow: 0 4px 12px rgba(34, 211, 238, 0.15) !important;
}

[data-testid="stSidebar"] hr {
    margin: 1.5rem 0 !important;
    border-color: #1e293b !important;
    opacity: 0.5 !important;
}

/* Forzar modo oscuro en toda la app */
.stApp {
    background-color: #0d0f14 !important;
}

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

/* Responsive adjustments */
@media (max-width: 768px) {
  .qa-header { padding: 18px 20px !important; margin-bottom: 16px !important; }
  .qa-header h1 { font-size: 1.5rem !important; }
  .qa-header p { font-size: 0.85rem !important; }
  
  .metric-box { padding: 16px 8px !important; margin-bottom: 10px !important; }
  .metric-value { font-size: 1.8rem !important; }
  .metric-label { font-size: 0.7rem !important; letter-spacing: 1px !important; }
  
  .login-box { padding: 24px 20px !important; width: 95% !important; max-width: 380px !important; margin: 0 auto !important; }
  .login-logo { font-size: 2rem !important; }
  
  /* Sortable list adjustments */
  .sortable-item { font-size: 0.75rem !important; padding: 10px 12px !important; }
  
  /* Streamlit columns spacing */
  div[data-testid="column"] { margin-bottom: 1rem !important; }
}

/* Hide Streamlit's 'Missing Submit Button' flash during form hydration */
div[data-testid="stForm"] .stException,
div[data-testid="stForm"] .stAlert {
  display: none !important;
}
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
    st.session_state.ai_config = {"provider": "IA Incluida (OpenRouter)", "model": "openai/gpt-oss-120b:free"}

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
        "INVALID_EMAIL": "El correo electrónico no es válido.",

    }

    return error_map.get(raw_error, f"Error: {raw_error}")





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









def firebase_load_settings(email):
    # Ya no se cargan configuraciones de IA por usuario (usamos IA Incluida)
    return {"provider": "IA Incluida (OpenRouter)", "model": "openai/gpt-oss-120b:free"}



# ── Manejo de Código OAuth (ELIMINADO) ─────────────────────────────────────────

# Se elimina por restricciones de Streamlit Cloud e iframe.



# Se elimina la recarga de llaves personales ya que se usa IA centralizada
if st.session_state.pop("_needs_key_reload", False):
    pass



# ── Pantalla de Login ─────────────────────────────────────────────────────────

if not st.session_state.user_logged_in:

    # Nota: la persistencia del correo se hace solo via query params (sin redirección JS para evitar flashes)

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
                                st.session_state.custom_steps = []
                                st.session_state["_needs_scroll_to_top"] = True
                                st.session_state["_close_sidebar_mobile"] = True

                                st.query_params["user"] = st.session_state.user_email

                                if remember:

                                    st.query_params["saved_email"] = l_email
                                    st.session_state["_email_to_save"] = l_email

                                elif "saved_email" in st.query_params:

                                    del st.query_params["saved_email"]
                                    st.session_state["_email_to_remove"] = True

                                st.session_state.pop("_login_error", None)
                                st.rerun()

                            else:

                                st.session_state["_login_error"] = firebase_error_message(res.get("error", {}).get("message", "Error desconocido"))

                    else:

                        st.session_state["_login_error"] = "Completa los campos de correo y contraseña."

            # Mostrar error de login fuera del form (persistido en session state)
            _login_err = st.session_state.pop("_login_error", None)
            if _login_err:
                st.error(_login_err)


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

                                st.session_state.custom_steps = []
                                st.session_state["_needs_scroll_to_top"] = True

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

            st.session_state.custom_steps = []
            st.session_state["_needs_scroll_to_top"] = True
            st.session_state["_close_sidebar_mobile"] = True

            st.query_params["user"] = st.session_state.user_email

            st.rerun()



        

        

            

    st.stop()

    

# --- Forzar Scroll al Inicio (Solo tras login) ---
if st.session_state.get("_needs_scroll_to_top"):
    st.session_state.pop("_needs_scroll_to_top")
    components.html("""
        <script>
        window.parent.scrollTo(0, 0);
        </script>
    """, height=0)

# --- Cerrar Sidebar en Móvil tras login ---
if st.session_state.pop("_close_sidebar_mobile", False):
    components.html("""
        <script>
        (function() {
            if (window.innerWidth > 768) return;
            function tryClose() {
                var doc = window.parent.document;
                var selectors = [
                    '[data-testid="stSidebarCollapseButton"]',
                    'button[aria-label="Close sidebar"]',
                    '[data-testid="stSidebar"] button[kind="header"]'
                ];
                for (var i = 0; i < selectors.length; i++) {
                    var btn = doc.querySelector(selectors[i]);
                    if (btn) { btn.click(); return true; }
                }
                return false;
            }
            setTimeout(function(){ if(!tryClose()) setTimeout(tryClose, 600); }, 300);
        })();
        </script>
    """, height=0)

# --- Persistencia de Correo (Guardar en localStorage) ---
if st.session_state.get("_email_to_save"):
    email_to_save = st.session_state.pop("_email_to_save")
    components.html(f"""
        <script>
        localStorage.setItem('saved_qa_email', '{email_to_save}');
        </script>
    """, height=0)

if st.session_state.get("_email_to_remove"):
    st.session_state.pop("_email_to_remove")
    components.html("""
        <script>
        localStorage.removeItem('saved_qa_email');
        </script>
    """, height=0)

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



@st.dialog("⚠️ ¿Eliminar historial?")

def confirm_clear_history():

    st.warning("Esta acción eliminará permanentemente todos tus resultados de la base de datos. No se puede deshacer.")

    c1, c2 = st.columns(2)

    with c1:

        if st.button("Sí, eliminar todo", use_container_width=True, type="primary"):

            u_email = st.session_state.get("user_email", "invitado@qa-agent.local")

            from agent.reporter import clear_results

            n = clear_results(user_id=u_email)

            get_cached_results.clear() # Limpiar cache

            st.success(f"Historial borrado.")

            st.rerun()

    with c2:

        if st.button("Cancelar", use_container_width=True):

            st.rerun()



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



    error_html = f'<div class="error-box">⚠️ {error}</div>' if error else ""
    st.markdown(f"""
<div class="result-card {css_cls}">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;">
    <div>
      <div class="result-title">#{idx:02d} — {name}</div>
      <div class="result-meta">🕐 {ts_fmt} &nbsp;|&nbsp; {len(steps)} pasos</div>
    </div>
    <div>{badge}</div>
  </div>
  {error_html}
</div>""", unsafe_allow_html=True)

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





def run_test_subprocess(prompt, headless):

    """Ejecuta main.py en subproceso y retorna stdout/returncode."""

    cmd = [sys.executable, str(ROOT / "main.py"), prompt]

    if not headless:

        cmd.append("--no-headless")

    env = os.environ.copy()

    env["PYTHONIOENCODING"] = "utf-8"

    res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT), encoding="utf-8", env=env)

    return res.returncode, res.stdout, res.stderr





# ══════════════════════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## QA Agent")
    st.markdown("---")

    # Perfil de Usuario
    current_email = st.session_state.get("user_email", "")
    is_guest_mode = "invitado_" in current_email

    if is_guest_mode:
        if st.button("Salir del Modo Invitado", use_container_width=True):
            st.session_state.user_logged_in = False
            st.session_state.user_email = ""
            st.session_state.firebase_id_token = ""
            st.session_state.ai_config = {}
            st.session_state.is_guest = False
            st.session_state.custom_steps = []
            try:
                saved = st.query_params.get("saved_email", "")
                st.query_params.clear()
                if saved: st.query_params["saved_email"] = saved
            except Exception:
                pass
            st.rerun()
    else:
        if st.button("Mi Perfil", use_container_width=True):
            show_profile()
        if st.button("Cerrar Sesion", use_container_width=True):
            st.session_state.user_logged_in = False
            st.session_state.user_email = ""
            st.session_state.firebase_id_token = ""
            st.session_state.ai_config = {}
            st.session_state.is_guest = False
            st.session_state.custom_steps = []
            try:
                saved = st.query_params.get("saved_email", "")
                st.query_params.clear()
                if saved: st.query_params["saved_email"] = saved
            except Exception:
                pass
            st.rerun()
    st.markdown("---")

    # Info IA (server-side, sin configuracion de usuario)
    st.markdown("""
    <div style='background:rgba(15, 23, 42, 0.6); border:1px solid #22d3ee33; border-radius:12px; padding:12px 16px; margin-bottom:12px; font-size:.82rem; backdrop-filter:blur(5px);'>
        <span style='color:#22d3ee; font-weight:600; display:block; margin-bottom:4px;'>✨ IA Incluida</span>
        <span style='color:#94a3b8;'>Generador de pasos activo para todos los usuarios.</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # Panel
    st.markdown("### Panel")
    if st.button("Limpiar historial", use_container_width=True):
        confirm_clear_history()

    st.markdown("---")
    st.markdown("**Ejemplos de prompts:**")
    examples = [
        "prueba el login de esta pagina",
        "verifica que el formulario de registro funciona",
        "comprueba la pagina de inicio",
        "valida que el menu de navegacion existe",
        "prueba login con credenciales invalidas",
    ]
    for ex in examples:
        if st.button(f"{ex}", key=f"ex_{ex}", use_container_width=True):
            st.session_state["sidebar_prompt"] = ex
            st.rerun()

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
    st.warning("🕵️ Estás en **Modo Invitado**. Los resultados son temporales (máx 10 tests/24h) y las ejecuciones tienen un **límite de 7 pasos**. Inicia sesión para historial ilimitado y pruebas complejas.")



# ── Métricas ───────────────────────────────────────────────────────────────────

results = get_cached_results(user_id=user_email)

total   = len(results)

passed_tests = sum(1 for r in results if r.get("status") == "PASS")

failed_tests = total - passed_tests



# Calcular tasa de éxito basada en pasos individuales para ser más preciso

total_steps = 0

passed_steps = 0

for r in results:

    steps = r.get("steps", [])

    total_steps += len(steps)

    passed_steps += sum(1 for s in steps if s.get("status") == "ok")



rate = f"{int(passed_steps/total_steps*100)}%" if total_steps > 0 else "–"



total_label = "Tests (últimas 24h)" if "invitado_" in user_email else "Total Tests"

c1, c2, c3, c4 = st.columns(4)

for col, val, label, color in [

    (c1, f"{total}/10" if "invitado_" in user_email else total, total_label, "#e2e8f0"),

    (c2, passed_tests, "Tests OK",     "#10b981"),

    (c3, failed_tests, "Tests Fail",    "#ef4444"),

    (c4, rate,   "Tasa de Pasos",  "#818cf8"),

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

tab_builder, tab_results = st.tabs([

    "Constructor de Pruebas",

    "Historial de Resultados",

])





# ────────────────────────────────────────────────────────────────────────────

# TAB 2 - CONSTRUCTOR VISUAL

# ────────────────────────────────────────────────────────────────────────────

with tab_builder:

    st.markdown('<div class="section-title">1. Generador con IA ✨</div>', unsafe_allow_html=True)

    default_prompt = st.session_state.pop("sidebar_prompt", "")

    ai_full_prompt = st.text_area(

        "Describe qué quieres probar en lenguaje natural",

        value=default_prompt,

        placeholder='Ej: "Abre https://wikipedia.org y busca Python"',

        height=80
    )

    st.markdown("""
    <div style="background:rgba(34,211,238,0.05); border:1px solid rgba(34,211,238,0.2); border-radius:8px; padding:10px 14px; margin-bottom:15px;">
        <p style="margin:0; font-size:0.8rem; color:#22d3ee; font-weight:600;">💡 Tip para el éxito:</p>
        <p style="margin:0; font-size:0.75rem; color:#94a3b8;">Sé específico con los nombres de botones, incluye la URL y menciona si hay avisos de cookies.</p>
    </div>
    """, unsafe_allow_html=True)

    if "ai_generations_count" not in st.session_state:
        st.session_state.ai_generations_count = 0

    if st.button("✨ Generar todos los pasos con IA", use_container_width=True):
        is_guest = "invitado_" in st.session_state.get("user_email", "")
        max_generations = 3 if is_guest else 10
        
        if st.session_state.ai_generations_count >= max_generations:
            st.error(f"🛑 **Límite Alcanzado:** Has alcanzado el límite de {max_generations} generaciones con IA para esta sesión. Intenta crear los pasos manualmente para no gastar los tokens.")
        elif ai_full_prompt.strip():

            with st.spinner("Generando pasos con IA..."):

                try:
                    importlib.reload(agent.planner)
                    new_steps = agent.planner.generate_test_plan(ai_full_prompt)
                    
                    # Asegurar IDs únicos para drag and drop
                    for s in new_steps:
                        if "id" not in s: s["id"] = str(uuid.uuid4())[:8]
                        
                    st.session_state.custom_steps = new_steps
                    st.session_state.ai_generations_count += 1
                    st.session_state["_scroll_to_steps"] = True
                    st.success(f"¡Pasos generados! (Uso: {st.session_state.ai_generations_count}/{max_generations})")
                    st.rerun()

                except Exception as e:

                    st.error(str(e))

        else:

            st.warning("Escribe una instrucción primero.")



    st.markdown("---")

    st.markdown('<div class="section-title">2. Constructor Visual</div>', unsafe_allow_html=True)

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
            b_val_wait = st.select_slider("Segundos a esperar", options=[0.5, 1.0, 1.5, 2.0, 3.0, 5.0], value=1.0, key="bv_wt")
            b_value = str(b_val_wait)

        elif b_action == "screenshot":
            b_value = ""

        elif b_action == "generate_email":
            b_value = st.text_input("Prefijo opcional", placeholder="Aleatorio si queda vacio", key="bv_ge")

        elif b_action == "wait_for_email":
            b_value = st.text_input("Correo a monitorear", placeholder="Último generado si vacío", key="bv_we")

        REQUIRES_SEL = {"find_and_type","click","hover","scroll_to","select_option","validate_text","validate_exists"}
        REQUIRES_VAL = {"open_url","find_and_type","select_option","validate_text","validate_url","wait"}

        if st.button("Añadir paso", use_container_width=True):
            err = None
            if b_action in REQUIRES_SEL and not b_selector and b_action != "scroll_to":
                err = "Selector CSS requerido para esta acción."
            elif b_action in REQUIRES_VAL and not b_value and b_action not in ("scroll_to",):
                err = "Valor requerido para esta acción."
            
            if err: st.error(err)
            else:
                st.session_state.custom_steps.append({"action": b_action, "id": str(uuid.uuid4())[:8], "selector": b_selector, "value": b_value})
                st.success(f"Paso '{b_action}' agregado.")
                st.rerun()

        st.markdown("---")
        
    with col_b2:
        st.markdown('<div id="steps-section"></div>', unsafe_allow_html=True)
        st.markdown("**Pasos del test**")
        
        if st.session_state.get("_scroll_to_steps"):
            st.session_state.pop("_scroll_to_steps")
            components.html("""
                <script>
                window.parent.document.getElementById('steps-section').scrollIntoView({behavior: 'smooth'});
                </script>
            """, height=0)
        
        @st.fragment
        def render_sortable_steps():
            custom_steps = st.session_state.custom_steps
            if not custom_steps:
                st.markdown(
                    '<div style="background:#0f172a;border:1px dashed #334155;border-radius:10px;'
                    'padding:30px;text-align:center;color:#475569;">'
                    '<div style="font-size:2rem;margin-bottom:8px">+</div>'
                    '<div>No hay pasos aún. Añade acciones o genéralas con IA.</div>'
                    '</div>',
                    unsafe_allow_html=True)
                return

            display_to_step = {}
            display_list = []
            for i, s in enumerate(custom_steps):
                if "id" not in s: s["id"] = str(uuid.uuid4())[:8]
                act, val, sel = s.get("action",""), s.get("value",""), s.get("selector","")
                detail = val if val else sel
                display_text = f"⠿ {i+1}. [{act.upper()}] {detail}"
                key = f"{display_text}" + (" " * 50) + f"\u200b{s['id']}"
                display_list.append(key)
                display_to_step[key] = s

            custom_style = """
            .sortable-container { background-color: #0d0f14 !important; border: 1px solid #1e293b !important; border-radius: 12px !important; margin-bottom: 20px !important; }
            .sortable-container-header { background-color: #1e293b !important; color: #22d3ee !important; font-weight: 800 !important; text-transform: uppercase !important; letter-spacing: 1px !important; font-size: 0.85rem !important; padding: 10px !important; border-bottom: 1px solid #334155 !important; }
            .sortable-container-body { background-color: #0d0f14 !important; max-height: 380px !important; overflow-y: auto !important; padding: 10px !important; }
            .sortable-item { background: linear-gradient(90deg, #1e293b, #0f172a) !important; border: 1px solid #38bdf844 !important; border-radius: 8px !important; color: #e2e8f0 !important; padding: 12px 16px !important; margin-bottom: 8px !important; font-family: 'JetBrains Mono', monospace !important; font-size: 0.82rem !important; box-shadow: 0 4px 6px rgba(0,0,0,0.2) !important; white-space: nowrap !important; overflow: hidden !important; text-overflow: ellipsis !important; }
            .sortable-item:hover { border-color: #22d3ee !important; background: #1e293b !important; }
            @media (max-width: 768px) {
                .sortable-container-header { font-size: 0.75rem !important; padding: 8px !important; }
                .sortable-item { font-size: 0.75rem !important; padding: 8px 10px !important; }
            }
            """
            st.caption("🖱️ Arrastra para reordenar o a la Papelera para borrar.")
            columns = [{"header": "📋 ORDEN DE EJECUCIÓN", "items": display_list}, {"header": "🗑️ PAPELERA", "items": []}]
            results = sort_items(columns, direction="vertical", multi_containers=True, custom_style=custom_style)
            
            new_display_list = results[0].get("items", [])
            trash_list = results[1].get("items", [])
            new_steps = [display_to_step[k] for k in new_display_list if k in display_to_step]
            
            if len(new_steps) != len(custom_steps) or new_display_list != display_list:
                st.session_state.custom_steps = new_steps
                if trash_list: st.toast(f"🗑️ Eliminado(s) {len(trash_list)} paso(s)")
                st.rerun(scope="fragment")

        render_sortable_steps()

        with st.expander("Exportar / Importar pasos (JSON)"):
            st.code(json.dumps(st.session_state.custom_steps, indent=2, ensure_ascii=False), language="json")
            imported = st.text_area("Pega JSON aqui para importar", height=120, key="import_json")
            if st.button("Importar pasos"):
                try:
                    parsed = json.loads(imported)
                    if isinstance(parsed, list):
                        st.session_state.custom_steps = parsed
                        st.success(f"{len(parsed)} pasos importados.")
                        st.rerun()
                    else: st.error("Debe ser una lista.")
                except Exception as e: st.error(f"Error: {e}")






    # Controles de Ejecución Globales

    st.markdown("---")

    col_c1, col_c2, col_c3 = st.columns([1.5, 1.5, 1])

    with col_c1:

        b_test_name = st.text_input("Nombre de la prueba (Opcional)", placeholder="Ej: Comprar un producto", key="b_name")
        
        is_cloud = platform.system() == "Linux"
        b_visible = False
        if not is_cloud:
            b_visible = st.toggle(
                "Ver navegador", 
                value=False, 
                help="Muestra la ventana del navegador durante el test (solo disponible localmente)"
            )

    with col_c2:

        b_timeout = st.select_slider("Tiempo límite (seg)", options=[5,10,15,20,30], value=15, key="b_timeout")

        b_delay   = st.select_slider("Pausa (seg)", options=[0.0,0.5,1.0,2.0], value=0.5, key="b_delay")

    with col_c3:

        st.markdown("<br>", unsafe_allow_html=True)

        run_custom = st.button("🚀 Ejecutar Prueba", type="primary", use_container_width=True)
        if "invitado_" in st.session_state.get("user_email", ""):
            st.caption("⚠️ Máximo 7 pasos en modo invitado")

        

        def clear_custom_steps():

            st.session_state.custom_steps = []

            st.session_state.pop("last_result", None)

            

        st.button("Limpiar pasos", use_container_width=True, on_click=clear_custom_steps)



    # Ejecucion con streaming

    if st.session_state.get("last_result"):

        lr = st.session_state.last_result

        st.markdown(f"### Última ejecución: {lr['name']}")

        ok = lr['status'] == 'PASS'

        if ok:

            st.success("✅ Completado con éxito")

        else:

            st.error("❌ Falló el test")

            

        with st.expander("Ver detalle de los pasos", expanded=not ok):

            for idx, s in enumerate(lr['steps'], 1):

                s_ok = s.get("status") == "ok"

                icon = "✅" if s_ok else "❌"

                st.write(f"**Paso {idx}:** {icon} [{s.get('action')}] - {s.get('detail', 'OK')}")

                if "screenshot" in s:

                    import base64

                    try:

                        decoded = base64.b64decode(s["screenshot"])

                        st.image(decoded, caption="Captura de pantalla", use_container_width=True)

                    except Exception:

                        pass



    if run_custom:

        st.session_state.pop("last_result", None)

        if "invitado_" in st.session_state.get("user_email", "") and len(get_cached_results(st.session_state.get("user_email", ""))) >= 10:

            st.error("🛑 **Límite Diario Alcanzado:** Has llegado al límite de 10 pruebas gratuitas en las últimas 24 horas. ¡Espera un poco o regístrate para continuar usando QA Agent sin límites!")

            st.stop()

        if not st.session_state.custom_steps:

            st.warning("Anade al menos un paso primero.")

        else:

            import importlib

            from agent import executor

            importlib.reload(executor)

            from agent.reporter import save_result as _save

            from datetime import timezone, timedelta

            tz_local = timezone(timedelta(hours=-5))

            dt_now = datetime.now(tz_local)

            default_name = f"Test del {dt_now.strftime('%d/%m a las %H:%M')}"

            name = b_test_name.strip() or default_name

            result_holder = {}

            

            user_email_check = st.session_state.get("user_email", "invitado@qa-agent.local")

            if "invitado_" in user_email_check and len(st.session_state.custom_steps) > 7:
                st.error("🛑 **Límite de Invitado:** Tu test tiene demasiados pasos. Los invitados solo pueden ejecutar hasta 7 pasos por prueba. Por favor, elimina pasos o inicia sesión para pruebas ilimitadas.")
                st.stop()

            with st.status("Ejecutando: " + name, expanded=True) as live_status:
                for event in executor.run_test_streaming(
                    name, st.session_state.custom_steps, 
                    headless=not b_visible,
                    timeout=b_timeout,
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

                umail = st.session_state.get("user_email", "invitado@qa-agent.local")

                

                # Limpiar Base64 antes de guardar para no exceder límite de 1MB de Firestore

                clean_steps = []

                for s in result_holder.get("steps", []):

                    clean_s = s.copy()

                    if "screenshot" in clean_s:

                        del clean_s["screenshot"]

                    clean_steps.append(clean_s)



                _save({

                    "test_name": name,

                    "status":    result_holder.get("status","FAIL"),

                    "steps":     clean_steps,

                    "error":     result_holder.get("error",""),

                }, user_id=umail)

                

                # Insertar cache clear

                get_cached_results.clear()

                

                st.session_state.last_result = {

                    "name": name,

                    "status": result_holder.get("status", "FAIL"),

                    "steps": result_holder.get("steps", [])

                }

                st.rerun()

# ────────────────────────────────────────────────────────────────────────────

# TAB 3 · HISTORIAL DE RESULTADOS

# ────────────────────────────────────────────────────────────────────────────

with tab_results:

    st.markdown('<div class="section-title">📊 Historial de resultados</div>', unsafe_allow_html=True)



    user_email = st.session_state.get("user_email", "invitado_default@qa-agent.local")

    results = get_cached_results(user_id=user_email)

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

    "QA Agent No-Code · Selenium + IA · Python · Streamlit"

    "</p>",

    unsafe_allow_html=True,

)

