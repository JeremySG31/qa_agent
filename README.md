# 🤖 QA Agent No-Code: Automatización con IA

Este proyecto es un **Agente de QA de Próxima Generación** que combina la potencia de los Modelos de Lenguaje (IA) con una interfaz visual intuitiva. Permite a cualquier persona crear, organizar y ejecutar pruebas de software sin escribir una sola línea de código.

![QA Agent Dashboard](https://raw.githubusercontent.com/JeremySG31/qa_agent/main/results/preview.png)

## 🚀 Características Premium

- **IA Incluida y Gratuita**: Acceso centralizado a modelos avanzados (vía OpenRouter) para generar planes de prueba instantáneos. ¡No necesitas configurar tu propia API Key para empezar!
- **Constructor Visual (Drag & Drop)**: Reordena pasos, edita acciones y limpia tu flujo de trabajo arrastrando elementos a la papelera con una interfaz fluida y sin parpadeos.
- **Comprensión de Lenguaje Natural**: Simplemente describe qué quieres probar y la IA deducirá los selectores CSS y las acciones lógicas necesarias.
- **Dashboard de Alto Rendimiento**: Interfaz oscura profesional (Slate & Cyan) optimizada para escritorio y dispositivos móviles.
- **Sistema de Reportes en la Nube**: Integración con **Firebase** para persistencia de resultados, historial ilimitado y capturas de pantalla para usuarios registrados.
- **Modo Invitado Seguro**: Prueba todas las funcionalidades de inmediato con almacenamiento temporal y límites de seguridad automáticos.

---

## 🛠️ Requisitos Previos

- **Python 3.10+**
- **Google Chrome** instalado (el agente usa Selenium para las ejecuciones reales).

---

## 📦 Instalación Rápida

1. **Clona el repositorio:**
   ```bash
   git clone https://github.com/JeremySG31/qa_agent.git
   cd qa_agent
   ```

2. **Prepara el entorno:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # En Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Variables de Entorno (Opcional para local):**
   Crea un archivo `.env` si deseas usar tus propias claves:
   ```env
   OPENROUTER_API_KEY=tu_clave_opcional
   FIREBASE_API_KEY=tu_clave_firebase
   ```

---

## 💻 Uso

### Iniciar el Dashboard Profesional
La mejor forma de interactuar con el agente es a través de su interfaz visual:
```bash
streamlit run dashboard/app.py
```

### Ejecución Directa (CLI)
Si prefieres la línea de comandos:
```bash
python main.py "Verifica el carrito de compras en https://tienda.com" --no-headless
```

---

## 🏗️ Arquitectura del Sistema

- **`dashboard/app.py`**: Interfaz premium con gestión de estados mediante fragmentos de Streamlit para una UX fluida.
- **`agent/planner.py`**: Motor de IA que traduce intenciones humanas en acciones de Selenium.
- **`agent/executor.py`**: El "brazo robótico" que ejecuta las acciones en el navegador real.
- **`agent/reporter.py`**: Generador de evidencias (JSON, Capturas) y sincronización con Firebase Firestore.

---

## 📱 Diseño Responsivo
El dashboard ha sido diseñado bajo principios de *Mobile-First*, asegurando que puedas monitorear el estado de tus tests desde cualquier lugar, con una barra lateral inteligente y métricas adaptables.

---

**Desarrollado con ❤️ por [JeremySG31](https://github.com/JeremySG31)**
