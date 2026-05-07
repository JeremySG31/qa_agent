# 🤖 Agente QA con IA

Este proyecto es un **Agente de QA Automatizado** que utiliza Inteligencia Artificial (Gemini API) para convertir instrucciones en lenguaje natural en planes de prueba ejecutables. Puede automatizar flujos en entornos Web, Desktop y Mobile, proporcionando un dashboard interactivo para visualizar los resultados.

## 🚀 Características

- **Comprensión de Lenguaje Natural**: Describe qué quieres probar (ej: "Prueba el login de mi página") y el agente generará los pasos necesarios.
- **Planificador con IA**: Utiliza Google Gemini para deducir selectores, acciones y validaciones lógicas.
- **Multi-plataforma**:
  - 🌐 **Web**: Automatización con Selenium.
  - 💻 **Desktop**: Integración con PyAutoGUI (Soporte inicial).
  - 📱 **Mobile**: Soporte para pruebas móviles (Próximamente).
- **Sistema de Reportes Híbrido**: Almacena resultados en **Google Firestore** (nube) o de forma local (JSON) como respaldo.
- **Dashboard Interactivo**: Visualiza los reportes de ejecución, capturas de pantalla y estados de los tests con Streamlit.
- **Seguridad**: Integración opcional con **Google Auth** para proteger el acceso al dashboard y separar resultados por usuario.

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
   GEMINI_MODEL=gemini-1.5-flash
   
   # Opcional: Configuración de Firebase (para reportes en la nube)
   GOOGLE_APPLICATION_CREDENTIALS=ruta/a/tu/archivo-firebase-adminsdk.json
   ```

> [!NOTE]
> Si no configuras Firebase, el agente guardará los resultados automáticamente en la carpeta `results/` local.

---

## 💻 Uso

### Ejecutar un Test desde la CLI

El punto de entrada principal es `main.py`. Solo necesitas pasarle un "prompt" con lo que deseas probar.

**Ejemplo básico (Web):**
```bash
python main.py "Prueba el login en https://practicetestautomation.com/practice-test-login/ usando student/Password123" --no-headless
```

**Opciones disponibles:**
- `--type [web|desktop|mobile]`: Define el entorno de ejecución (default: `web`).
- `--no-headless`: Abre el navegador para que puedas ver la ejecución (solo web).

### Ver el Dashboard

Para visualizar los resultados de las pruebas ejecutadas de forma gráfica:

```bash
streamlit run dashboard/app.py
```

---

## 🏗️ Estructura del Proyecto

- `agent/`: Núcleo de la lógica del agente.
  - `planner.py`: Genera el plan de pasos usando la IA.
  - `executor.py`: Orquestador de la ejecución.
  - `executor_web.py`: Lógica específica de Selenium.
  - `reporter.py`: Gestión de guardado de resultados y capturas.
- `auth/`: Módulo de autenticación (Google Auth).
- `dashboard/`: Interfaz de usuario con Streamlit.
- `main.py`: Script de ejecución principal.
- `results/`: Directorio donde se guardan los reportes JSON y screenshots (generado automáticamente).

---

## 🛠️ Tecnologías Utilizadas

- **Lenguaje**: Python 🐍
- **IA**: Google Gemini API 🤖
- **Automatización**: Selenium, PyAutoGUI.
- **Interfaz**: Streamlit.
- **Configuración**: Python-dotenv.

---

## 📝 Notas de Desarrollo

- El módulo `desktop` y `mobile` están en fases iniciales de desarrollo.
- Si no se proporciona una API Key de Gemini, el agente intentará ejecutar un plan básico de respaldo si detecta una URL en el prompt.

---

**Desarrollado por [JeremySG31](https://github.com/JeremySG31)**
