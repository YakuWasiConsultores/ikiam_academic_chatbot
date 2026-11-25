# -*- coding: utf-8 -*-
import os
import sys
import time
import json
import threading
from flask import Flask, request, jsonify, send_from_directory, Response, redirect, make_response

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR = os.path.join(BASE_DIR, "documentos_oficiales")
PORT = int(os.environ.get("PORT", 8080))
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "ikiam_admin_sec_2027")

from asesor_gemini_puro import es_comando_reinicio, responder_consulta
from whatsapp_adapter import register_whatsapp_routes
from auditoria_consultas import (
    registrar_consulta,
    exportar_csv_consultas,
    exportar_json_consultas,
    actualizar_feedback_humano,
)
from seguridad_ikiam import (
    validar_tamano_consulta,
    escapar_para_tabla,
    MENSAJE_BLOQUEO_SEGURIDAD,
)

app = Flask(__name__, static_folder=None)
register_whatsapp_routes(app)

# Rate limiting segmentado por sesión + IP (permite redes NAT/campus compartidas sin bloquear estudiantes)
SESSION_RATE_LIMITS = {}
IP_RATE_LIMITS = {}
RATE_LOCK = threading.Lock()
MAX_SESSION_REQUESTS_PER_MINUTE = 30
MAX_IP_REQUESTS_PER_MINUTE = 120
WINDOW_SECONDS = 60

def is_rate_limited(client_ip: str, session_id: str) -> bool:
    now = time.time()
    with RATE_LOCK:
        # 1. Comprobar sesión individual
        s_times = SESSION_RATE_LIMITS.setdefault(session_id, [])
        s_times[:] = [t for t in s_times if now - t < WINDOW_SECONDS]
        if len(s_times) >= MAX_SESSION_REQUESTS_PER_MINUTE:
            return True

        # 2. Comprobar IP global (NAT campus)
        ip_times = IP_RATE_LIMITS.setdefault(client_ip, [])
        ip_times[:] = [t for t in ip_times if now - t < WINDOW_SECONDS]
        if len(ip_times) >= MAX_IP_REQUESTS_PER_MINUTE:
            return True

        s_times.append(now)
        ip_times.append(now)
        return False

def verificar_admin_auth(req) -> bool:
    """Verifica si la petición cuenta con el token de administración válido."""
    token = (
        req.headers.get("X-Admin-Token")
        or req.headers.get("Authorization", "").replace("Bearer ", "").strip()
        or req.args.get("token")
        or req.cookies.get("ikiam_admin_token")
    )
    return bool(token and token == ADMIN_TOKEN)

@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With, X-Admin-Token"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response

@app.route("/", methods=["GET"])
@app.route("/portal", methods=["GET"])
def home():
    index_path = os.path.join(BASE_DIR, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            html = f.read()
        return Response(html, mimetype="text/html; charset=utf-8")
    return Response("<h1>Portal Académico Ikiam</h1>", mimetype="text/html; charset=utf-8")

@app.route("/admisiones", methods=["GET"])
@app.route("/admisiones/", methods=["GET"])
def home_admisiones():
    adm_path = os.path.join(BASE_DIR, "admisiones.html")
    if os.path.exists(adm_path):
        with open(adm_path, "r", encoding="utf-8") as f:
            html = f.read()
        return Response(html, mimetype="text/html; charset=utf-8")
    return Response("<h1>Portal Admisiones Ikiam</h1>", mimetype="text/html; charset=utf-8")

@app.route("/healthz", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "service": "ikiam-academic-chatbot",
        "version": "2.1-security-hardened"
    }), 200

@app.route("/api/chat", methods=["POST", "OPTIONS"])
def chat():
    if request.method == "OPTIONS":
        return Response("", status=200)

    data = request.get_json(silent=True) or {}
    msg = str(data.get("message", "")).strip()
    session_id_raw = str(data.get("sessionId", "web_default_session")).strip()
    # Sanitizar session_id para evitar caracteres de control o inyecciones de ruta
    session_id = "".join(c for c in session_id_raw if c.isalnum() or c in "-_")[:64] or "web_default_session"
    scope_raw = str(data.get("scope", "academico")).strip().lower()
    scope = "admisiones" if scope_raw in ("admisiones", "admision") else "academico"

    client_ip = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",")[0].strip()
    if is_rate_limited(client_ip, session_id):
        return jsonify({
            "reply": "Ha alcanzado el límite temporal de consultas por minuto. Por favor espere un momento antes de enviar otra consulta.",
            "reset": False,
        }), 200

    if not msg:
        prompt_vacio = "¡Hola! Escribe tu consulta sobre el proceso de admisión o elige una de las opciones." if scope == "admisiones" else "¡Hola! Escribe tu consulta sobre trámites académicos de Ikiam o elige una opción."
        return jsonify({"reply": prompt_vacio, "reset": False}), 200

    # Validación de seguridad: longitud y caracteres de control
    valido, err_msg = validar_tamano_consulta(msg)
    if not valido:
        return jsonify({"reply": err_msg, "reset": False}), 200

    try:
        fue_reset = es_comando_reinicio(msg)
        reply = responder_consulta(session_id, msg, scope=scope)

        # Registro persistente de auditoría y aprendizaje
        try:
            registrar_consulta(scope, session_id, client_ip, msg, reply, fue_reinicio=fue_reset)
        except Exception as log_err:
            app.logger.warning(f"Error registrando auditoría: {log_err}")

        return jsonify({"reply": reply, "reset": fue_reset, "scope": scope}), 200
    except Exception as e:
        app.logger.error(f"Error procesando chat ({scope}): {e}")
        return jsonify({
            "reply": "Estimado/a estudiante, ocurrió un inconveniente temporal al conectar con el asesor. Por favor intente nuevamente en breves momentos.",
            "reset": False,
        }), 200

@app.route("/api/consultas/exportar", methods=["GET"])
def exportar_consultas_route():
    """Descarga de consultas en formato CSV (para Excel) o JSON. Requiere token administrativo."""
    if not verificar_admin_auth(request):
        return jsonify({"error": "No autorizado. Token de administración requerido."}), 401

    scope = request.args.get("scope")
    formato = request.args.get("formato", "csv").lower()
    limite = int(request.args.get("limite", 5000))

    if formato == "json":
        return jsonify(exportar_json_consultas(scope=scope, limite=limite))

    csv_data = exportar_csv_consultas(scope=scope, limite=limite)
    return Response(
        csv_data,
        mimetype="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": "attachment; filename=consultas_estudiantes_ikiam.csv",
            "Cache-Control": "no-cache, no-store, must-revalidate",
        }
    )

@app.route("/api/consultas/feedback", methods=["POST"])
def feedback_consulta_route():
    """Permite calificar y alimentar la respuesta real esperada a una consulta. Requiere token administrativo."""
    if not verificar_admin_auth(request):
        return jsonify({"error": "No autorizado. Token de administración requerido."}), 401

    data = request.get_json(silent=True) or {}
    c_id = data.get("id")
    resp_esperada = str(data.get("respuesta_esperada", "")).strip()
    estado = str(data.get("estado", "revisado")).strip()
    notas = str(data.get("notas", "")).strip()

    if not c_id or not resp_esperada:
        return jsonify({"error": "Parámetros 'id' y 'respuesta_esperada' requeridos"}), 400

    actualizar_feedback_humano(int(c_id), resp_esperada, estado=estado, notas=notas)
    return jsonify({"status": "ok", "id": c_id}), 200

LOGIN_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Acceso Administrativo — Ikiam</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background:#f8fafc; display:flex; align-items:center; justify-content:center; min-height:100vh; margin:0; }
        .card { background:#ffffff; border:1px solid #e2e8f0; border-top:4px solid #0d5f3a; border-radius:8px; padding:28px 24px; width:100%; max-width:380px; box-shadow:0 4px 6px -1px rgba(0,0,0,0.05); }
        h1 { margin:0 0 8px; font-size:16px; color:#0d5f3a; }
        p { margin:0 0 18px; font-size:12px; color:#64748b; line-height:1.4; }
        label { display:block; font-size:11.5px; font-weight:600; color:#334155; margin-bottom:6px; }
        input[type="password"] { width:100%; box-sizing:border-box; padding:8px 10px; font-size:13px; border:1px solid #cbd5e1; border-radius:5px; margin-bottom:14px; }
        input[type="password"]:focus { outline:none; border-color:#0d5f3a; }
        button { width:100%; background:#0d5f3a; color:#ffffff; border:none; padding:9px; border-radius:5px; font-size:12.5px; font-weight:600; cursor:pointer; }
        button:hover { background:#09472b; }
        .err { background:#fef2f2; border:1px solid #fecaca; color:#991b1b; padding:8px 10px; border-radius:5px; font-size:11.5px; margin-bottom:14px; }
    </style>
</head>
<body>
    <div class="card">
        <h1>Panel de Auditoría Institucional</h1>
        <p>Universidad Regional Amazónica Ikiam. Ingrese el token de seguridad administrativa para acceder a los registros de consultas.</p>
        __ERROR_MSG__
        <form method="POST" action="/admin/consultas">
            <label for="token">Token de Administración</label>
            <input type="password" id="token" name="token" placeholder="Ingrese el token administrativo" required autofocus />
            <button type="submit">Ingresar al Panel</button>
        </form>
    </div>
</body>
</html>"""

@app.route("/admin/consultas", methods=["GET", "POST"])
def panel_auditoria_html():
    """Panel visual y formal para revisar consultas en vivo y descargar el dataset."""
    if request.method == "POST":
        token_ingresado = request.form.get("token", "").strip()
        if token_ingresado == ADMIN_TOKEN:
            resp = redirect("/admin/consultas")
            resp.set_cookie("ikiam_admin_token", token_ingresado, max_age=86400 * 7, httponly=True, samesite="Lax")
            return resp
        else:
            err_html = '<div class="err">Token administrativo incorrecto. Acceso denegado.</div>'
            return Response(LOGIN_HTML_TEMPLATE.replace("__ERROR_MSG__", err_html), mimetype="text/html; charset=utf-8"), 401

    if not verificar_admin_auth(request):
        return Response(LOGIN_HTML_TEMPLATE.replace("__ERROR_MSG__", ""), mimetype="text/html; charset=utf-8"), 401

    consultas = exportar_json_consultas(limite=200)
    filas_html = ""
    for c in consultas:
        c_id = int(c.get("id"))
        ts = escapar_para_tabla(c.get("timestamp", ""))
        sc = escapar_para_tabla(c.get("scope", ""))
        preg = escapar_para_tabla(c.get("pregunta_usuario", ""))
        resp_cruda = str(c.get("respuesta_sistema", "") or "")
        resp = escapar_para_tabla(resp_cruda[:200])
        esperada = escapar_para_tabla(c.get("respuesta_esperada") or "")
        badge_scope = "<span style=\"background:#ecfdf5; color:#065f46; padding:2px 7px; border-radius:10px; font-weight:600; font-size:10px;\">" + sc + "</span>" if sc == "admisiones" else "<span style=\"background:#eff6ff; color:#1e40af; padding:2px 7px; border-radius:10px; font-weight:600; font-size:10px;\">" + sc + "</span>"
        
        filas_html += f"""
        <tr id="row-{c_id}" style="border-bottom:1px solid #e2e8f0; font-size:11.5px;">
            <td style="padding:8px 10px; font-weight:600;">#{c_id}</td>
            <td style="padding:8px 10px; white-space:nowrap; color:#64748b;">{ts}</td>
            <td style="padding:8px 10px;">{badge_scope}</td>
            <td style="padding:8px 10px; max-width:280px; word-break:break-word; font-weight:600; color:#0f172a;">{preg}</td>
            <td style="padding:8px 10px; max-width:320px; word-break:break-word; color:#334155;">{resp}...</td>
            <td style="padding:8px 10px;">
                <input type="text" id="resp-esp-{c_id}" value="{esperada}" placeholder="Escribir respuesta correcta..." style="width:100%; min-width:180px; padding:4px 7px; font-size:11px; border:1px solid #cbd5e1; border-radius:4px;" />
            </td>
            <td style="padding:8px 10px;">
                <button onclick="guardarFeedback({c_id})" style="background:#0d5f3a; color:#ffffff; border:none; padding:4px 9px; border-radius:4px; font-size:11px; font-weight:600; cursor:pointer;">Guardar</button>
            </td>
        </tr>
        """

    plantilla = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Panel de Auditoría y Curaduría de Consultas — Ikiam</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin:0; padding:20px; background:#f8fafc; color:#1e293b; }
        .header { display:flex; justify-content:space-between; align-items:center; background:#ffffff; padding:16px 22px; border-radius:8px; border:1px solid #e2e8f0; margin-bottom:16px; border-left:4px solid #0d5f3a; }
        h1 { margin:0; font-size:17px; color:#0d5f3a; }
        p { margin:3px 0 0; font-size:12px; color:#64748b; }
        .btn-export { background:#0d5f3a; color:#ffffff; text-decoration:none; padding:8px 14px; border-radius:6px; font-size:12px; font-weight:600; display:inline-flex; align-items:center; gap:6px; }
        .btn-export:hover { background:#09472b; }
        .btn-logout { background:#f1f5f9; color:#475569; text-decoration:none; padding:8px 14px; border-radius:6px; font-size:12px; font-weight:600; border:1px solid #cbd5e1; }
        .btn-logout:hover { background:#e2e8f0; }
        table { width:100%; border-collapse:collapse; background:#ffffff; border-radius:8px; overflow:hidden; border:1px solid #e2e8f0; }
        th { background:#f1f5f9; padding:9px 10px; text-align:left; font-size:11.5px; font-weight:700; color:#475569; border-bottom:2px solid #cbd5e1; }
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>Auditoría y Curaduría de Consultas — Ikiam</h1>
            <p>Registro continuo de preguntas formuladas por estudiantes y aspirantes para retroalimentación y mejora de respuestas.</p>
        </div>
        <div style="display:flex; gap:10px; align-items:center;">
            <a href="/api/consultas/exportar?formato=csv" class="btn-export">Descargar CSV para Excel</a>
            <a href="/admin/logout" class="btn-logout">Cerrar Sesión</a>
        </div>
    </div>

    <table>
        <thead>
            <tr>
                <th>ID</th>
                <th>Fecha y Hora</th>
                <th>Módulo</th>
                <th>Pregunta del Estudiante</th>
                <th>Respuesta Emitida</th>
                <th>Respuesta Real Esperada (Curaduría Humana)</th>
                <th>Acción</th>
            </tr>
        </thead>
        <tbody>
            __FILAS__
        </tbody>
    </table>

    <script>
        async function guardarFeedback(id) {
            var input = document.getElementById('resp-esp-' + id);
            var val = input.value.trim();
            if (!val) { alert('Por favor escriba la respuesta esperada antes de guardar.'); return; }
            try {
                var res = await fetch('/api/consultas/feedback', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ id: id, respuesta_esperada: val, estado: 'revisado' })
                });
                var data = await res.json();
                if (data.status === 'ok') {
                    input.style.borderColor = '#16a34a';
                    input.style.backgroundColor = '#f0fdf4';
                    setTimeout(function() { input.style.backgroundColor = '#ffffff'; }, 1500);
                } else {
                    alert('Error: ' + (data.error || 'No autorizado'));
                }
            } catch(e) {
                alert('Error al guardar feedback: ' + e);
            }
        }
    </script>
</body>
</html>"""
    filas_finales = filas_html or '<tr><td colspan="7" style="text-align:center; padding:24px; color:#94a3b8; font-size:12px;">No hay consultas registradas aún. Formule preguntas en el chat para visualizarlas aquí.</td></tr>'
    html = plantilla.replace("__FILAS__", filas_finales)
    return Response(html, mimetype="text/html; charset=utf-8")

@app.route("/admin/logout", methods=["GET"])
def admin_logout():
    resp = redirect("/admin/consultas")
    resp.set_cookie("ikiam_admin_token", "", expires=0)
    return resp

@app.route("/documentos/<path:filename>", methods=["GET"])
def download_documento(filename):
    safe_name = os.path.basename(filename)
    file_path = os.path.join(DOCS_DIR, safe_name)
    if os.path.exists(file_path):
        return send_from_directory(DOCS_DIR, safe_name, as_attachment=True)
    return Response("Documento no encontrado en el repositorio oficial.", status=404, mimetype="text/plain; charset=utf-8")

if __name__ == "__main__":
    print(f"Servidor Ikiam Academic Chatbot activo en http://0.0.0.0:{PORT}")
    app.run(host="0.0.0.0", port=PORT)
