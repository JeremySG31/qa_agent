# 🤖 QA Agent – Automatización Local con IA

**MVP de un agente local de automatización QA impulsado por IA.**

Convierte prompts en lenguaje natural en pruebas automatizadas. Soporta automatización web (activa) y placeholders para desktop y mobile.

---

## 📋 Tabla de Contenidos

- [Características](#características)
- [Estructura del Proyecto](#estructura-del-proyecto)
- [Instalación](#instalación)
- [Uso](#uso)
- [API](#api)
- [Flujo](#flujo)
- [Troubleshooting](#troubleshooting)
- [Roadmap](#roadmap)

---

## ✨ Características

✅ **Agente Local**: Corre en Python, sin dependencias en la nube  
✅ **Lenguaje Natural**: Convierte prompts en pasos de automatización  
✅ **Automatización Web**: Selenium con Edge/Chrome  
✅ **Dashboard**: Streamlit para visualizar resultados  
✅ **Resultados JSON**: Guardado permanente de pruebas  
✅ **Estructura Extensible**: Placeholders para desktop y mobile  
✅ **Modo Mock/Simulado**: Funciona sin API key (Gemini opcional)  

---

## 📁 Estructura del Proyecto

```
qa_agent/
├── main.py                          ← Punto de entrada CLI
├── requirements.txt                 ← Dependencias
├── README.md                        ← Este archivo
├── .env.example                     ← Plantilla de variables de entorno
│
├── agent/                           ← Núcleo del agente
│   ├── __init__.py                  ← Exports públicas
│   ├── planner.py                   ← IA: prompt → pasos
│   ├── executor.py                  ← Dispatcher de ejecutores
│   ├── executor_web.py              ← Selenium (activo)
│   ├── executor_desktop.py          ← Desktop automation (placeholder)
│   ├── executor_mobile.py           ← Mobile testing (placeholder)
│   └── reporter.py                  ← Guardado/carga de resultados
│
├── dashboard/                       ← Interfaz visual
│   ├── __init__.py
│   └── app.py                       ← Streamlit (web UI)
│
├── data/                            ← Datos y configuraciones
│   └── .gitkeep
│
└── results/                         ← Resultados JSON de pruebas
    ├── Test_login_20240115_100000.json
    ├── Test_busqueda_20240115_110000.json
    └── ...
```

---

## ⚡ Instalación

### 1. Requisitos Previos

- **Python 3.10+**
- **Git** (para clonar el repo)
- **Navegador instalado**: Google Chrome o Microsoft Edge
- **Opcional**: API key de Google Gemini (en `.env`)

### 2. Clonar / Descargar

```bash
git clone <repo-url> qa_agent
cd qa_agent
```

### 3. Crear Entorno Virtual (Recomendado)

#### **Windows (PowerShell)**
```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

#### **macOS / Linux**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 4. Instalar Dependencias

```bash
pip install -r requirements.txt
```

**Nota**: Si `webdriver-manager` no se instala correctamente, prueba:
```bash
pip install --upgrade webdriver-manager
```

### 5. (Opcional) Configurar Gemini API

Si tienes API key de Gemini:

```bash
cp .env.example .env
# Edita .env y agrega: GEMINI_API_KEY=tu_clave_aqui
```

**Sin API key**: El agente funciona en modo simulado (planes predefinidos por palabras clave).

---

## 🚀 Uso

### CLI – Ejecutar Agente

#### **Prueba básica (web, headless)**
```bash
python main.py "prueba el login de esta página"
```

#### **Con opciones**
```bash
# Ver el navegador en vivo (debug)
python main.py "busca algo en google" --no-headless

# Especificar tipo de test
python main.py "prueba el formulario" --type web

# Todo junto
python main.py "navega a example.com" --type web --no-headless
```

#### **Tipos de test**

| Tipo | Descripción | Estado |
|------|---|---|
| `web` | Automatización web con Selenium | ✅ Activo |
| `desktop` | Desktop automation con PyAutoGUI | ✅ Activo |
| `mobile` | Mobile testing con ADB (Android) | ✅ Activo |


**Ejemplo**: `python main.py "abre notepad" --type desktop`

#### **Prompts que Disparan Planes Simulados** (cuando Gemini no está disponible)

| Palabras clave | Plan / Sitio |
|---|---|
| `login`, `iniciar sesión` | https://reviewstar-web.vercel.app/login.html |
| `registro`, `register` | https://reviewstar-web.vercel.app/register.html |
| `feed`, `explorar` | https://reviewstar-web.vercel.app/feed.html |
| `navegacion`, `navegar` | Links y menú |
| `forgot`, `olvidé contraseña` | Recuperación de cuenta |
| *cualquier otro* | Validación de home |

---

### Dashboard – Ver Resultados Visuales

```bash
streamlit run dashboard/app.py
```

Abre automáticamente: **http://localhost:8501**

#### Funcionalidades:

- 📊 **Métricas**: Total tests, PASS, FAIL, tasa de éxito
- 📋 **Lista de Resultados**: Cards expandibles con pasos
- 🔍 **Filtros**: Por nombre y estado (PASS/FAIL)
- ▶️ **Ejecutar Test**: Directamente desde el sidebar
- 🔄 **Refrescar**: Ver nuevos resultados
- 🗑️ **Limpiar**: Eliminar historial de pruebas

---

## 💻 API

### Uso Programático

```python
from agent import generate_test_plan, run_test, save_result

# 1. Generar plan
steps = generate_test_plan("prueba el login")
# → [{"action": "open_url", "value": "..."}, ...]

# 2. Ejecutar
result = run_test(
    test_name="Login Test",
    steps=steps,
    test_type="web",  # web, desktop, mobile
    headless=True     # False para ver el navegador
)
# → {"test_name": "...", "status": "PASS", "steps": [...], "error": ""}

# 3. Guardar
filepath = save_result(result)
# → "/path/to/results/Login_Test_20240115_100000.json"
```

### Funciones Principales

#### `generate_test_plan(prompt: str) -> list[dict]`
Convierte un prompt en pasos estructurados.

#### `run_test(test_name, steps, test_type="web", headless=True) -> dict`
Ejecuta los pasos y retorna el resultado.

#### `save_result(result: dict) -> str`
Guarda resultado en JSON y retorna ruta.

#### `load_all_results() -> list[dict]`
Lee todos los resultados guardados.

#### `clear_results() -> int`
Elimina todos los resultados, retorna cantidad borrada.

---

## 🔄 Flujo de Ejecución

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Usuario escribe prompt en lenguaje natural                │
│    "prueba el login de esta página"                         │
└──────────────────────────┬──────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. PLANNER (IA)                                             │
│    • Intenta usar Gemini API (si hay API key)              │
│    • Si falla, usa planes simulados con palabra clave      │
│    Salida: Lista de pasos estructurados                    │
└──────────────────────────┬──────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. EXECUTOR (según tipo)                                    │
│    • web: Selenium (Edge/Chrome)                           │
│    • desktop: PyAutoGUI / UIA (placeholder)                │
│    • mobile: Appium (placeholder)                          │
│    Ejecuta: open_url, find_and_type, click, validate_*    │
└──────────────────────────┬──────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. REPORTER                                                 │
│    Guarda resultado en: results/Test_*.json                │
│    Estructura:                                              │
│    {                                                        │
│      "test_name": "Test: prueba el login...",              │
│      "status": "PASS" | "FAIL" | "SKIPPED",               │
│      "steps": [{...}],                                     │
│      "error": "",                                          │
│      "timestamp": "2024-01-15T10:00:00"                   │
│    }                                                        │
└──────────────────────────┬──────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. DASHBOARD (Streamlit)                                    │
│    Muestra: Métricas, resultados, pasos, filtros           │
│    URL: http://localhost:8501                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 📄 Formato de Resultados

Cada prueba genera un JSON en `results/`:

```json
{
  "test_name": "Test: prueba el login de esta página",
  "status": "PASS",
  "timestamp": "2024-01-15T10:00:00.123456",
  "steps": [
    {
      "action": "open_url",
      "value": "https://reviewstar-web.vercel.app/login.html",
      "status": "ok",
      "detail": "Abrió: https://reviewstar-web.vercel.app/login.html",
      "selector": ""
    },
    {
      "action": "find_and_type",
      "selector": "input[type='email']",
      "value": "test@example.com",
      "status": "ok",
      "detail": "Escribió 'test@example.com' en 'input[type=\"email\"]'"
    },
    {
      "action": "click",
      "selector": "button[type='submit']",
      "status": "ok",
      "detail": "Hizo clic en 'button[type=\"submit\"]'",
      "value": ""
    }
  ],
  "error": ""
}
```

---

## 🔧 Solución de Problemas

### ❌ `ModuleNotFoundError: No module named 'selenium'`

```bash
pip install -r requirements.txt
# o específicamente:
pip install selenium webdriver-manager
```

### ❌ `Chrome/Edge no encontrado`

1. Instala Chrome desde https://www.google.com/chrome/ o Edge desde https://www.microsoft.com/edge/
2. Asegúrate de que esté en el PATH
3. Actualiza webdriver-manager:
```bash
pip install --upgrade webdriver-manager
```

### ❌ `Timeout: elemento no encontrado`

- El selector CSS es incorrecto → Inspeccciona el elemento en el navegador
- La página tardó más de 15s → Aumenta `WAIT_TIMEOUT` en `executor_web.py`
- Usa `--no-headless` para ver qué sucede:
```bash
python main.py "tu prompt" --no-headless
```

### ❌ Dashboard no carga en localhost:8501

```bash
# Reinicia el servidor
streamlit run dashboard/app.py

# Si sigue fallando, intenta otro puerto:
streamlit run dashboard/app.py --server.port 8502
```

### ❌ API key de Gemini no funciona

1. Verifica que `.env` existe y contiene `GEMINI_API_KEY=tu_clave`
2. Reinicia la terminal (variables de entorno)
3. Sin API key, el agente funciona igual en modo simulado

---

## 🛣️ Roadmap

**Fase 1 (MVP Actual - ✅ Completa)**
- [x] CLI con prompts en lenguaje natural
- [x] Integración Gemini (opcional)
- [x] Automatización web con Selenium
- [x] Dashboard con Streamlit
- [x] Almacenamiento JSON

**Fase 2 (Próxima)**
- [ ] Desktop automation (PyAutoGUI, UIA)
- [ ] Mobile testing (Appium)
- [ ] Captura de pantallas por paso
- [ ] Grabación de video
- [ ] Soporte Firefox/Safari

**Fase 3 (Futuro)**
- [ ] Pruebas en paralelo
- [ ] CI/CD integration (GitHub Actions)
- [ ] Exportar reportes HTML/PDF
- [ ] Base de datos de resultados
- [ ] UI avanzada (Vue.js)
- [ ] CLI mejorada (Rich TUI)

---

## 📝 Licencia

MIT (ver LICENSE)

---

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor, abre un issue o PR.

---

**Última actualización**: Mayo 2026  
**Versión**: 1.0 MVP

