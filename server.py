# -*- coding: utf-8 -*-
import os
import sys
import time
import json
from flask import Flask, request, jsonify, send_from_directory, Response

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR = os.path.join(BASE_DIR, "documentos_oficiales")
PORT = int(os.environ.get("PORT", 8080))

import threading

from asesor_gemini_puro import es_comando_reinicio, responder_consulta
from whatsapp_adapter import register_whatsapp_routes

app = Flask(__name__, static_folder=None)
register_whatsapp_routes(app)

# Rate limiting segmentado por sesión + IP (permite redes NAT/campus compartidas sin bloquear estudiantes)
SESSION_RATE_LIMITS = {}
IP_RATE_LIMITS = {}
RATE_LOCK = threading.Lock()
MAX_SESSION_REQUESTS_PER_MINUTE = 30
MAX_IP_REQUESTS_PER_MINUTE = 120


def is_rate_limited(ip, session_id):
    now = time.time()
    with RATE_LOCK:
        s_key = f"{ip}:{session_id}"
        s_ts = [t for t in SESSION_RATE_LIMITS.get(s_key, []) if now - t < 60]
        ip_ts = [t for t in IP_RATE_LIMITS.get(ip, []) if now - t < 60]
        if len(s_ts) >= MAX_SESSION_REQUESTS_PER_MINUTE or len(ip_ts) >= MAX_IP_REQUESTS_PER_MINUTE:
            SESSION_RATE_LIMITS[s_key] = s_ts
            IP_RATE_LIMITS[ip] = ip_ts
            return True
        s_ts.append(now)
        ip_ts.append(now)
        SESSION_RATE_LIMITS[s_key] = s_ts
        IP_RATE_LIMITS[ip] = ip_ts
        return False

@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
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
        "version": "2.0-render"
    }), 200

@app.route("/api/chat", methods=["POST", "OPTIONS"])
def chat():
    if request.method == "OPTIONS":
        return Response("", status=200)

    data = request.get_json(silent=True) or {}
    msg = str(data.get("message", "")).strip()
    session_id = str(data.get("sessionId", "web_default_session")).strip()
    scope_raw = str(data.get("scope", "academico")).strip().lower()
    scope = "admisiones" if scope_raw in ("admisiones", "admision") else "academico"

    client_ip = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",")[0].strip()
    if is_rate_limited(client_ip, session_id):
        return jsonify({
            "reply": "Ha alcanzado el límite temporal de consultas por minuto. Por favor espere un momento antes de enviar otra consulta.",
            "reset": False,
        }), 200

    if not msg:
        prompt_vacio = "Por favor formule su consulta sobre el proceso de admisión a Ikiam." if scope == "admisiones" else "Por favor formule su pregunta sobre trámites académicos de Ikiam."
        return jsonify({"reply": prompt_vacio, "reset": False}), 200

    try:
        fue_reset = es_comando_reinicio(msg)
        reply = responder_consulta(session_id, msg, scope=scope)
        return jsonify({"reply": reply, "reset": fue_reset, "scope": scope}), 200
    except Exception as e:
        app.logger.error(f"Error procesando chat ({scope}): {e}")
        return jsonify({
            "reply": "Estimado/a estudiante, ocurrió un inconveniente temporal al conectar con el asesor. Por favor intente nuevamente en breves momentos.",
            "reset": False,
        }), 200

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
