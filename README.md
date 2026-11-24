# Asesor Inteligente - Dirección Académica Ikiam

Plataforma oficial del chatbot institucional de la **Dirección Académica de la Universidad Regional Amazónica Ikiam**.

## 🚀 Arquitectura y Tecnologías
* **Backend:** Python + Flask con servidor WSGI Gunicorn para producción.
* **Base de Conocimiento:** SQLite FTS (`ikiam_knowledge.db`) con reglamentos, instructivos y calendario académico.
* **Inteligencia Artificial:** Google Gemini AI con memoria cognitiva persistente por sesión de estudiante.
* **Frontend:** Portal institucional integrado de Ikiam con widget conversacional interactivo.
* **Despliegue Cloud:** Compatible con Render.com (Plan Free) mediante Blueprint `render.yaml`.

## 📦 Despliegue en Render.com
1. Conecta este repositorio en tu cuenta de Render.
2. Selecciona **New +** -> **Blueprint** o **Web Service**.
3. Configura la variable de entorno:
   * `GEMINI_API_KEY`: Tu API Key de Google Gemini.
4. Render ejecutará automáticamente:
   * Build: `pip install -r requirements.txt`
   * Start: `gunicorn wsgi:app --bind 0.0.0.0:$PORT`
