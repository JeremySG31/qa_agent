# 🤖 Agente QA con IA

Este proyecto es un **Agente de QA Automatizado** que utiliza Inteligencia Artificial (Gemini API) para convertir instrucciones en lenguaje natural en planes de prueba ejecutables. Puede automatizar flujos en entornos Web y Desktop, proporcionando un dashboard interactivo para visualizar los resultados.

## 🚀 Características

- **Comprensión de Lenguaje Natural**: Describe qué quieres probar (ej: "Prueba el login de mi página") y el agente generará los pasos necesarios.
- **Planificador con IA**: Utiliza Google Gemini para deducir selectores, acciones y validaciones lógicas.
- **Multi-plataforma**:
  - 🌐 **Web**: Automatización con Selenium.
  - 💻 **Desktop**: Integración con PyAutoGUI (Soporte inicial).
- **Sistema de Reportes Híbrido**: Almacena resultados en **Google Firestore** (nube) para usuarios registrados o de forma local (JSON) para invitados.
- **Dashboard Interactivo**: Visualiza los reportes de ejecución, capturas de pantalla y estados de los tests con Streamlit.
- **Acceso Rápido**: Incluye un **Modo Invitado** para probar la herramienta instantáneamente sin necesidad de registro.

---

## 🛠️ Requisitos Previos

Antes de comenzar, asegúrate de tener instalado:
- Python 3.9 o superior.
- Google Chrome (para pruebas web).
- Una **API Key de Gemini** (Consíguela en [Google AI Studio](https://aistudio.google.com/)).

---

## 📦 Instalación

1. **Clona el repositorio:**
   ```bash
   git clone https://github.com/JeremySG31/qa_agent.git
   cd qa_agent
   ```

2. **Crea un entorno virtual:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # En Windows: .venv\Scripts\activate
   ```

3. **Instala las dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configura las variables de entorno:**
   Crea un archivo `.env` en la raíz del proyecto con el siguiente contenido:
   ```env
   GEMINI_API_KEY=tu_api_key_aqui
   
   # Configuración de Firebase (para reportes en la nube)
   FIREBASE_API_KEY=tu_firebase_key
   FIREBASE_PROJECT_ID=tu_proyecto_id
   ```

---

## 💻 Uso

### Ejecutar un Test desde la CLI
```bash
python main.py "Prueba el login en https://example.com" --no-headless
```

### Ver el Dashboard
```bash
streamlit run dashboard/app.py
```

---

## 🏗️ Estructura del Proyecto

- `agent/`: Núcleo de la lógica del agente (Planner, Executor, Reporter).
- `dashboard/`: Interfaz de usuario con Streamlit y lógica de autenticación Firebase.
- `main.py`: Script de ejecución principal por línea de comandos.
- `results/`: Directorio local de reportes y screenshots.

---

**Desarrollado por [JeremySG31](https://github.com/JeremySG31)**
