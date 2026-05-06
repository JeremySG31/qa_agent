"""
dashboard/app.py - Dashboard de resultados con Streamlit
Muestra los resultados de las pruebas QA en una interfaz visual.

Ejecutar con:
    streamlit run dashboard/app.py
"""

import sys
import os
import json
import subprocess
from pathlib import Path
from datetime import datetime

import streamlit as st

# Asegurar que podemos importar módulos del proyecto desde cualquier directorio
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from agent.reporter import load_all_results, clear_results
from agent.planner  import generate_test_plan

# ──────────────────────────────────────────────
# Configuración de la página
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="QA Agent Dashboard",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────
# CSS personalizado – diseño oscuro tipo terminal
# ──────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Syne:wght@400;700;800&display=swap');

  html, body, [class*="css"] {
    font-family: 'Syne', sans-serif;
    background-color: #0d0f14;
    color: #e2e8f0;
  }

  /* Header principal */
  .qa-header {
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
    border: 1px solid #22d3ee33;
    border-radius: 12px;
    padding: 28px 36px;
    margin-bottom: 28px;
    position: relative;
    overflow: hidden;
  }
  .qa-header::before {
    content: '';
    position: absolute; top: 0; left: 0; right: 0; height: 3px;
    background: linear-gradient(90deg, #22d3ee, #818cf8, #f472b6);
  }
  .qa-header h1 {
    font-family: 'Syne', sans-serif;
    font-size: 2rem; font-weight: 800;
    color: #22d3ee; margin: 0 0 4px 0;
    letter-spacing: -0.5px;
  }
  .qa-header p { color: #94a3b8; margin: 0; font-size: 0.95rem; }

  /* Tarjeta de resultado */
  .result-card {
    background: #111827;
    border: 1px solid #1e293b;
    border-radius: 10px;
    padding: 20px 24px;
    margin-bottom: 16px;
    transition: border-color 0.2s;
  }
  .result-card:hover { border-color: #334155; }

  .result-card.pass { border-left: 4px solid #10b981; }
  .result-card.fail { border-left: 4px solid #ef4444; }

  .result-title {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.9rem; font-weight: 600;
    color: #e2e8f0; margin-bottom: 6px;
  }
  .result-meta {
    font-size: 0.75rem; color: #64748b;
    font-family: 'JetBrains Mono', monospace;
  }

  /* Badge de estado */
  .badge-pass {
    display: inline-block;
    background: #064e3b; color: #10b981;
    border: 1px solid #10b981;
    border-radius: 6px; padding: 2px 10px;
    font-size: 0.75rem; font-weight: 700;
    font-family: 'JetBrains Mono', monospace;
    letter-spacing: 1px;
  }
  .badge-fail {
    display: inline-block;
    background: #450a0a; color: #ef4444;
    border: 1px solid #ef4444;
    border-radius: 6px; padding: 2px 10px;
    font-size: 0.75rem; font-weight: 700;
    font-family: 'JetBrains Mono', monospace;
    letter-spacing: 1px;
  }

  /* Paso individual */
  .step-item {
    display: flex; align-items: flex-start; gap: 10px;
    padding: 8px 12px; border-radius: 6px;
    margin-bottom: 6px;
    background: #0f172a;
    border: 1px solid #1e293b;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.78rem;
  }
  .step-ok   { border-left: 3px solid #10b981; }
  .step-err  { border-left: 3px solid #ef4444; }
  .step-icon { font-size: 1rem; flex-shrink: 0; }
  .step-text { color: #cbd5e1; }
  .step-action {
    color: #22d3ee; font-weight: 600;
    margin-right: 6px;
  }

  /* Métricas */
  .metric-box {
    background: #111827;
    border: 1px solid #1e293b;
    border-radius: 10px;
    padding: 20px;
    text-align: center;
  }
  .metric-value {
    font-family: 'Syne', sans-serif;
    font-size: 2.4rem; font-weight: 800;
    line-height: 1;
  }
  .metric-label {
    font-size: 0.75rem; color: #64748b;
    text-transform: uppercase; letter-spacing: 1px;
    margin-top: 6px;
  }

  /* Error box */
  .error-box {
    background: #1a0a0a; border: 1px solid #7f1d1d;
    border-radius: 8px; padding: 12px 16px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem; color: #fca5a5;
    margin-top: 8px;
  }

  /* Inputs y botones de Streamlit */
  .stTextInput > div > div > input {
    background: #111827 !important;
    border: 1px solid #334155 !important;
    color: #e2e8f0 !important;
    border-radius: 8px !important;
    font-family: 'JetBrains Mono', monospace !important;
  }

  div[data-testid="stSidebar"] {
    background: #0a0c10 !important;
    border-right: 1px solid #1e293b;
  }

  .stButton > button {
    border-radius: 8px !important;
    font-family: 'Syne', sans-serif !important;
    font-weight: 700 !important;
    letter-spacing: 0.5px !important;
  }

  hr { border-color: #1e293b !important; }
  .stExpander { border-color: #1e293b !important; }
</style>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────
# Helper: renderizar pasos
# ──────────────────────────────────────────────
def render_steps(steps: list):
    for step in steps:
        status = step.get("status", "ok")
        icon   = "✅" if status == "ok" else "❌"
        css    = "step-ok" if status == "ok" else "step-err"
        action = step.get("action", "")
        detail = step.get("detail", "")
        sel    = step.get("selector", "")
        val    = step.get("value", "")

        if not detail:
            detail = f"{sel} → {val}" if sel else val

        st.markdown(f"""
        <div class="step-item {css}">
          <span class="step-icon">{icon}</span>
          <span class="step-text">
            <span class="step-action">[{action}]</span>
            {detail}
          </span>
        </div>
        """, unsafe_allow_html=True)


# ──────────────────────────────────────────────
# Helper: renderizar una tarjeta de resultado
# ──────────────────────────────────────────────
def render_result_card(result: dict, idx: int):
    status   = result.get("status", "UNKNOWN")
    name     = result.get("test_name", "Sin nombre")
    ts       = result.get("timestamp", "")
    error    = result.get("error", "")
    steps    = result.get("steps", [])
    css_cls  = "pass" if status == "PASS" else "fail"
    badge    = f'<span class="badge-pass">PASS</span>' if status == "PASS" else '<span class="badge-fail">FAIL</span>'

    # Formatear timestamp
    try:
        dt = datetime.fromisoformat(ts)
        ts_fmt = dt.strftime("%d/%m/%Y %H:%M:%S")
    except Exception:
        ts_fmt = ts

    st.markdown(f"""
    <div class="result-card {css_cls}">
      <div style="display:flex; justify-content:space-between; align-items:flex-start;">
        <div>
          <div class="result-title">#{idx:02d} — {name}</div>
          <div class="result-meta">🕐 {ts_fmt} &nbsp;|&nbsp; {len(steps)} pasos</div>
        </div>
        <div>{badge}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    if error:
        st.markdown(f'<div class="error-box">⚠️ {error}</div>', unsafe_allow_html=True)

    if steps:
        with st.expander(f"📋 Ver {len(steps)} pasos ejecutados"):
            render_steps(steps)

    st.markdown("")


# ──────────────────────────────────────────────
# SIDEBAR – Ejecutar nuevo test
# ──────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🤖 Nuevo Test")
    st.markdown("---")

    prompt = st.text_area(
        "Prompt en lenguaje natural",
        placeholder='Ej: "prueba el login de esta página"',
        height=100,
    )

    headless = st.checkbox("Modo headless (sin ventana)", value=True)

    if st.button("▶ Ejecutar Test", use_container_width=True, type="primary"):
        if prompt.strip():
            with st.spinner("🧠 Generando plan con IA..."):
                steps = generate_test_plan(prompt)

            st.success(f"✅ Plan listo: {len(steps)} pasos")

            with st.spinner("🚀 Ejecutando con Selenium..."):
                # Ejecutar en proceso separado para no bloquear Streamlit
                result = subprocess.run(
                    [
                        sys.executable, str(ROOT / "main.py"),
                        prompt,
                        *(["--no-headless"] if not headless else []),
                    ],
                    capture_output=True, text=True,
                    cwd=str(ROOT),
                )

            if result.returncode == 0:
                st.success("🎉 Test completado. Recarga para ver resultados.")
            else:
                st.error(f"Error al ejecutar:\n{result.stderr[:500]}")
        else:
            st.warning("Escribe un prompt primero.")

    st.markdown("---")

    if st.button("🗑️ Limpiar resultados", use_container_width=True):
        n = clear_results()
        st.success(f"Eliminados {n} resultados.")
        st.rerun()

    st.markdown("---")
    st.markdown("**Prompts de ejemplo:**")
    examples = [
        "prueba el login de esta página",
        "busca algo en Google",
        "prueba el formulario de contacto",
    ]
    for ex in examples:
        st.code(ex, language=None)


# ──────────────────────────────────────────────
# HEADER
# ──────────────────────────────────────────────
st.markdown("""
<div class="qa-header">
  <h1>🤖 QA Agent Dashboard</h1>
  <p>Automatización de pruebas web impulsada por IA · Selenium + LLM</p>
</div>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# Cargar resultados
# ──────────────────────────────────────────────
results = load_all_results()

# ──────────────────────────────────────────────
# MÉTRICAS
# ──────────────────────────────────────────────
total  = len(results)
passed = sum(1 for r in results if r.get("status") == "PASS")
failed = total - passed
rate   = f"{int(passed/total*100)}%" if total > 0 else "–"

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(f"""
    <div class="metric-box">
      <div class="metric-value" style="color:#e2e8f0">{total}</div>
      <div class="metric-label">Total Tests</div>
    </div>""", unsafe_allow_html=True)
with col2:
    st.markdown(f"""
    <div class="metric-box">
      <div class="metric-value" style="color:#10b981">{passed}</div>
      <div class="metric-label">Pasados</div>
    </div>""", unsafe_allow_html=True)
with col3:
    st.markdown(f"""
    <div class="metric-box">
      <div class="metric-value" style="color:#ef4444">{failed}</div>
      <div class="metric-label">Fallados</div>
    </div>""", unsafe_allow_html=True)
with col4:
    st.markdown(f"""
    <div class="metric-box">
      <div class="metric-value" style="color:#818cf8">{rate}</div>
      <div class="metric-label">Tasa de Éxito</div>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# Botón de refresco
col_r1, col_r2 = st.columns([8, 2])
with col_r2:
    if st.button("🔄 Refrescar", use_container_width=True):
        st.rerun()

# ──────────────────────────────────────────────
# LISTADO DE RESULTADOS
# ──────────────────────────────────────────────
st.markdown("### 📊 Resultados")

if not results:
    st.info("🔍 No hay resultados aún. Ejecuta tu primer test desde el panel lateral.")
else:
    # Filtros
    col_f1, col_f2 = st.columns([3, 1])
    with col_f1:
        search = st.text_input("🔍 Buscar test", placeholder="Filtrar por nombre...")
    with col_f2:
        filter_status = st.selectbox("Estado", ["Todos", "PASS", "FAIL"])

    # Aplicar filtros
    filtered = results
    if search:
        filtered = [r for r in filtered if search.lower() in r.get("test_name","").lower()]
    if filter_status != "Todos":
        filtered = [r for r in filtered if r.get("status") == filter_status]

    st.markdown(f"<p style='color:#64748b;font-size:0.85rem'>Mostrando {len(filtered)} de {total} resultados</p>", unsafe_allow_html=True)

    for i, result in enumerate(filtered, 1):
        render_result_card(result, i)

# ──────────────────────────────────────────────
# FOOTER
# ──────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<p style='text-align:center;color:#334155;font-size:0.75rem;font-family:JetBrains Mono,monospace'>"
    "QA Agent MVP · Selenium + LLM · Python · Streamlit"
    "</p>",
    unsafe_allow_html=True
)
