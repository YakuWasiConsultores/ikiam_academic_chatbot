# -*- coding: utf-8 -*-
import os
import sys
import time
import json
from flask import Flask, request, jsonify, send_from_directory, Response

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR = os.path.join(BASE_DIR, "documentos_oficiales")
PORT = int(os.environ.get("PORT", 8080))

from asesor_gemini_puro import responder_consulta

app = Flask(__name__, static_folder=None)

# Rate limiting ligero por IP (25 peticiones por minuto por IP)
IP_RATE_LIMITS = {}
MAX_REQUESTS_PER_MINUTE = 25

def is_rate_limited(ip):
    now = time.time()
    timestamps = IP_RATE_LIMITS.get(ip, [])
    timestamps = [t for t in timestamps if now - t < 60]
    if len(timestamps) >= MAX_REQUESTS_PER_MINUTE:
        IP_RATE_LIMITS[ip] = timestamps
        return True
    timestamps.append(now)
    IP_RATE_LIMITS[ip] = timestamps
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

    client_ip = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",")[0].strip()
    if is_rate_limited(client_ip):
        return jsonify({
            "reply": "Ha alcanzado el límite temporal de consultas por minuto. Por favor espere un momento antes de enviar otra consulta."
        }), 200

    data = request.get_json(silent=True) or {}
    msg = data.get("message", "").strip()
    session_id = data.get("sessionId", "web_default_session").strip()

    if not msg:
        return jsonify({"reply": "Por favor formule su pregunta sobre trámites académicos de Ikiam."}), 200

    try:
        reply = responder_consulta(session_id, msg)
        return jsonify({"reply": reply}), 200
    except Exception as e:
        app.logger.error(f"Error procesando chat: {e}")
        return jsonify({
            "reply": "Estimado/a estudiante, ocurrió un inconveniente temporal al conectar con el asesor. Por favor intente nuevamente en breves momentos."
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
