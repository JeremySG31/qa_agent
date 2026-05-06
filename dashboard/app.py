"""
dashboard/app.py - Dashboard QA con interfaz completa sin código
Ejecutar con: streamlit run dashboard/app.py
"""

import sys, os, json, subprocess, re
from pathlib import Path
from datetime import datetime

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
  background:#111827; border:1px solid #1e293b;
  border-radius:10px; padding:20px; text-align:center;
}
.metric-value { font-family:'Syne',sans-serif; font-size:2.4rem; font-weight:800; line-height:1; }
.metric-label { font-size:.75rem; color:#64748b; text-transform:uppercase; letter-spacing:1px; margin-top:6px; }

.result-card {
  background:#111827; border:1px solid #1e293b;
  border-radius:10px; padding:20px 24px; margin-bottom:14px;
  transition:border-color .2s;
}
.result-card:hover { border-color:#334155; }
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
.stTextInput>div>div>input, .stTextArea>div>div>textarea {
  background:#111827 !important; border:1px solid #334155 !important;
  color:#e2e8f0 !important; border-radius:8px !important;
  font-family:'JetBrains Mono',monospace !important;
}
.stButton>button { border-radius:8px !important; font-family:'Syne',sans-serif !important; font-weight:700 !important; }
.stSelectbox>div>div { background:#111827 !important; border:1px solid #334155 !important; }
hr { border-color:#1e293b !important; }
.stExpander { border-color:#1e293b !important; }
.stTabs [data-baseweb="tab-list"] { background:#111827; border-radius:10px; padding:4px; gap:4px; }
.stTabs [data-baseweb="tab"] { border-radius:7px; color:#64748b; }
.stTabs [aria-selected="true"] { background:#1e293b; color:#22d3ee; }
.error-box { background:#1a0a0a; border:1px solid #7f1d1d; border-radius:8px; padding:12px 16px; font-family:'JetBrains Mono',monospace; font-size:.8rem; color:#fca5a5; margin-top:8px; }
</style>
""", unsafe_allow_html=True)


# ── Session state ──────────────────────────────────────────────────────────────
if "plan_preview" not in st.session_state:
    st.session_state.plan_preview = []
if "custom_steps" not in st.session_state:
    st.session_state.custom_steps = []
if "active_tab" not in st.session_state:
    st.session_state.active_tab = 0


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

    # ── Configuración de IA ────────────────────────────────────────
    with st.expander("Configuracion de IA", expanded=False):
        api_key_input = st.text_input(
            "Gemini API Key",
            value=os.getenv("GEMINI_API_KEY", ""),
            type="password",
            help="Opcional. Sin key usa modo demo inteligente.",
        )
        if api_key_input:
            os.environ["GEMINI_API_KEY"] = api_key_input
            st.success("✅ API Key configurada en sesión")

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
  <p>Automatiza pruebas web con IA sin tocar una linea de codigo</p>
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

        test_url = st.text_input(
            "URL del sitio a probar",
            placeholder="https://mi-sitio.com (vacio para demo)",
            help="El agente usara esta URL como base para generar los pasos."
        )

        prompt = st.text_area(
            "Que quieres probar? (lenguaje natural)",
            value=default_prompt,
            placeholder='Ej: "prueba el formulario de login"',
            height=120,
        )

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
        if not prompt.strip():
            st.warning("Escribe un prompt primero.")
        else:
            # Construir prompt con URL si se proporcionó
            full_prompt = prompt.strip()
            if test_url.strip():
                full_prompt = f"{full_prompt} en {test_url.strip()}"

            # 1. Generar plan
            with st.spinner("Generando plan con IA..."):
                steps = generate_test_plan(full_prompt)

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
