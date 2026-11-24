# -*- coding: utf-8 -*-
"""
Adaptador seguro de WhatsApp Cloud API para Ikiam Academic Chatbot.
Provee:
- Verificación de webhook (GET /webhook) y validación HMAC X-Hub-Signature-256 (POST /webhook).
- Deduplicación idempotente por message_id (wamid) frente a reintentos de Meta.
- Procesamiento asíncrono en segundo plano para responder 200 OK inmediato a Meta.
- Conversión de flujos guiados a Mensajes Interactivos (Lista) de WhatsApp con fallback numérico.
- División automática de textos > 3800 caracteres para respetar el límite de 4096 de Meta.
"""

from collections import OrderedDict
import hashlib
import hmac
import logging
import os
import re
import threading
import time
from typing import Any, Dict, List, Optional

from flask import Flask, Response, jsonify, request
import requests

from asesor_gemini_puro import DEFAULT_PUBLIC_URL, responder_consulta_estructurada

logger = logging.getLogger("ikiam_whatsapp")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

GRAPH_API_VERSION = "v22.0"
WA_MAX_TEXT_LEN = 3800
WAMID_TTL_SECONDS = 3600
WAMID_MAX_CACHE = 2000
WA_RATE_LIMIT_MAX = 12
WA_RATE_LIMIT_WINDOW = 60

_SEEN_WAMIDS: "OrderedDict[str, float]" = OrderedDict()
_SEEN_LOCK = threading.Lock()
_WA_RATE_LIMITS: Dict[str, List[float]] = {}
_RATE_LOCK = threading.Lock()
_HTTP_SESSION = requests.Session()


def _cfg(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _verify_signature(raw_body: bytes, header_sig: str) -> bool:
    """Valida la firma X-Hub-Signature-256 emitida por Meta cuando WHATSAPP_APP_SECRET está configurado."""
    app_secret = _cfg("WHATSAPP_APP_SECRET")
    if not app_secret:
        logger.warning("WHATSAPP_APP_SECRET no configurado; omitiendo verificación HMAC del webhook.")
        return True
    if not header_sig or not header_sig.startswith("sha256="):
        return False
    expected = hmac.new(app_secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    received = header_sig.split("=", 1)[1].strip()
    return hmac.compare_digest(expected, received)


def _is_duplicate_wamid(wamid: str) -> bool:
    """Evita procesar dos veces un mismo mensaje ante reintentos de Meta."""
    if not wamid:
        return False
    now = time.time()
    with _SEEN_LOCK:
        stale = [k for k, ts in _SEEN_WAMIDS.items() if now - ts > WAMID_TTL_SECONDS]
        for k in stale:
            _SEEN_WAMIDS.pop(k, None)
        if wamid in _SEEN_WAMIDS:
            return True
        _SEEN_WAMIDS[wamid] = now
        while len(_SEEN_WAMIDS) > WAMID_MAX_CACHE:
            _SEEN_WAMIDS.popitem(last=False)
    return False


def _is_wa_rate_limited(sender_id: str) -> bool:
    now = time.time()
    with _RATE_LOCK:
        stamps = [t for t in _WA_RATE_LIMITS.get(sender_id, []) if now - t < WA_RATE_LIMIT_WINDOW]
        if len(stamps) >= WA_RATE_LIMIT_MAX:
            _WA_RATE_LIMITS[sender_id] = stamps
            return True
        stamps.append(now)
        _WA_RATE_LIMITS[sender_id] = stamps
        return False


def split_whatsapp_message(text: str, max_len: int = WA_MAX_TEXT_LEN) -> List[str]:
    """Divide textos largos respetando párrafos y líneas sin exceder el límite de WhatsApp (4096)."""
    clean = (text or "").strip()
    if not clean:
        return []
    if len(clean) <= max_len:
        return [clean]

    chunks: List[str] = []
    remaining = clean
    while len(remaining) > max_len:
        window = remaining[:max_len]
        split_at = window.rfind("\n\n")
        if split_at < max_len // 3:
            split_at = window.rfind("\n")
        if split_at < max_len // 3:
            split_at = window.rfind(" ")
        if split_at <= 0:
            split_at = max_len
        chunks.append(remaining[:split_at].strip())
        remaining = remaining[split_at:].strip()

    if remaining:
        chunks.append(remaining)
    return [c for c in chunks if c]


def _truncate_clean(text: str, limit: int) -> str:
    """Elimina emojis complejos para encabezados estrictos de Meta y recorta al límite."""
    no_emoji = re.sub(r"[\U00010000-\U0010ffff\u2600-\u27bf\ufe0f]", "", text or "").strip()
    no_emoji = re.sub(r"\s+", " ", no_emoji)
    if len(no_emoji) <= limit:
        return no_emoji
    if limit <= 1:
        return no_emoji[:limit]
    return no_emoji[: limit - 1].rstrip() + "…"


def _post_graph_api(payload: Dict[str, Any]) -> bool:
    """Envía un payload JSON a Meta WhatsApp Graph API."""
    phone_id = _cfg("WHATSAPP_PHONE_NUMBER_ID")
    token = _cfg("WHATSAPP_TOKEN")
    if not phone_id or not token:
        logger.error("Faltan WHATSAPP_PHONE_NUMBER_ID o WHATSAPP_TOKEN en el entorno.")
        return False

    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{phone_id}/messages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    try:
        resp = _HTTP_SESSION.post(url, json=payload, headers=headers, timeout=(5, 15))
        if 200 <= resp.status_code < 300:
            logger.info(f"Mensaje WhatsApp enviado OK a {payload.get('to')}: HTTP {resp.status_code}")
            return True
        logger.error(f"Error Graph API Meta HTTP {resp.status_code} para {payload.get('to')}: {resp.text[:350]}")
        return False
    except Exception as e:
        logger.error(f"Excepción llamando a Meta Graph API: {e}")
        return False


def send_whatsapp_text(to: str, text: str) -> bool:
    """Envía texto plano/formateado dividiendo automáticamente si supera 3800 caracteres."""
    chunks = split_whatsapp_message(text)
    all_ok = True
    for idx, chunk in enumerate(chunks):
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {"preview_url": idx == len(chunks) - 1, "body": chunk},
        }
        ok = _post_graph_api(payload)
        all_ok = all_ok and ok
        if idx < len(chunks) - 1:
            time.sleep(0.25)
    return all_ok


def send_whatsapp_interactive_list(to: str, body_text: str, options: List[Dict[str, str]]) -> bool:
    """Envía una lista interactiva nativa de WhatsApp; si falla, usa menú numerado en texto."""
    rows = []
    for opc in options[:10]:
        c_caso = str(opc.get("codigo_caso", "")).strip()
        etiqueta = str(opc.get("etiqueta", "")).strip()
        desc = str(opc.get("descripcion", "")).strip()
        if not c_caso or not etiqueta:
            continue
        rows.append({
            "id": f"caso:{c_caso}"[:200],
            "title": _truncate_clean(etiqueta, 24) or c_caso[:24],
            "description": _truncate_clean(desc, 72),
        })

    if rows:
        safe_body = body_text.strip()
        if len(safe_body) > 1000:
            safe_body = safe_body[:997] + "..."
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": "list",
                "body": {"text": safe_body},
                "footer": {"text": "También puedes responder con el número (1, 2, 3...)"},
                "action": {
                    "button": "Elegir opción",
                    "sections": [{"title": "Opciones de Trámite", "rows": rows}],
                },
            },
        }
        if _post_graph_api(payload):
            return True

    # Fallback determinista a menú numerado si Meta rechaza el mensaje interactivo
    lines = [body_text.strip(), ""]
    for i, opc in enumerate(options[:10], 1):
        lines.append(f"*{i}.* {opc.get('etiqueta', '')} — _{opc.get('descripcion', '')}_")
    lines.append("\nResponde con el *número* de tu opción.")
    return send_whatsapp_text(to, "\n".join(lines))


def _extraer_texto_mensaje(msg: Dict[str, Any]) -> Optional[str]:
    """Extrae la entrada del usuario desde texto libre o respuesta interactiva."""
    mtype = msg.get("type", "")
    if mtype == "text":
        return msg.get("text", {}).get("body", "").strip()
    if mtype == "interactive":
        inter = msg.get("interactive", {})
        itype = inter.get("type", "")
        if itype == "list_reply":
            return inter.get("list_reply", {}).get("id", "").strip()
        if itype == "button_reply":
            return inter.get("button_reply", {}).get("id", "").strip()
    return None


def _procesar_mensaje_async(sender_id: str, msg: Dict[str, Any], sender_name: str):
    """Ejecuta consulta multi-DB + Gemini y despacha la respuesta al usuario en WhatsApp."""
    try:
        mtype = msg.get("type", "")
        if mtype in ("reaction", "system", "unsupported"):
            return

        entrada = _extraer_texto_mensaje(msg)
        if entrada is None:
            send_whatsapp_text(
                sender_id,
                "Por ahora solo puedo atender consultas escritas por *texto* o selecciones del menú. "
                "Escríbeme tu consulta académica (ej. _justificación de faltas_, _prórroga de tesis_, _retiro de materia_) y te ayudo de inmediato.",
            )
            return

        if not entrada:
            return

        if _is_wa_rate_limited(sender_id):
            send_whatsapp_text(
                sender_id,
                "Has enviado varias consultas seguidas. Por favor espera unos segundos antes de enviar la siguiente.",
            )
            return

        public_url = _cfg("PUBLIC_BASE_URL", DEFAULT_PUBLIC_URL)
        session_id = f"wa_{sender_id}"
        logger.info(f"WhatsApp IN de {sender_name or sender_id} ({sender_id}): '{entrada}'")

        res = responder_consulta_estructurada(session_id, entrada, public_base_url=public_url)
        if res.get("kind") == "flow" and res.get("flow_options"):
            send_whatsapp_interactive_list(sender_id, res["whatsapp_text"], res["flow_options"])
        else:
            send_whatsapp_text(sender_id, res["whatsapp_text"])
    except Exception as e:
        logger.error(f"Error procesando mensaje WhatsApp de {sender_id}: {e}", exc_info=True)
        send_whatsapp_text(
            sender_id,
            "Estimado/a estudiante, ocurrió un inconveniente temporal al consultar la normativa institucional. "
            "Por favor reintenta tu consulta en unos instantes.",
        )


def register_whatsapp_routes(app: Flask):
    """Registra los endpoints /webhook (GET y POST) en la aplicación Flask existente."""

    @app.route("/webhook", methods=["GET"])
    def whatsapp_verify_webhook():
        hub_mode = request.args.get("hub.mode", "")
        hub_token = request.args.get("hub.verify_token", "")
        hub_challenge = request.args.get("hub.challenge", "")
        verify_token = _cfg("WHATSAPP_VERIFY_TOKEN", "bot_institucional_seguro_2026")

        if hub_mode == "subscribe" and verify_token and hmac.compare_digest(hub_token, verify_token):
            logger.info("Handshake WhatsApp Webhook verificado con éxito.")
            return Response(hub_challenge, status=200, mimetype="text/plain")

        logger.warning(f"Fallo handshake WhatsApp Webhook: mode={hub_mode}")
        return Response("Token de verificación inválido", status=403, mimetype="text/plain")

    @app.route("/webhook", methods=["POST"])
    def whatsapp_receive_webhook():
        raw_body = request.get_data()
        sig = request.headers.get("X-Hub-Signature-256", "")
        if not _verify_signature(raw_body, sig):
            logger.warning("Firma X-Hub-Signature-256 inválida; petición rechazada.")
            return Response("Firma inválida", status=403, mimetype="text/plain")

        payload = request.get_json(silent=True) or {}
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                contacts = value.get("contacts", [])
                default_name = contacts[0].get("profile", {}).get("name", "") if contacts else ""
                for msg in value.get("messages", []):
                    sender_id = msg.get("from", "")
                    wamid = msg.get("id", "")
                    if not sender_id or _is_duplicate_wamid(wamid):
                        continue
                    t = threading.Thread(
                        target=_procesar_mensaje_async,
                        args=(sender_id, msg, default_name),
                        daemon=True,
                    )
                    t.start()

        return jsonify({"status": "received"}), 200
