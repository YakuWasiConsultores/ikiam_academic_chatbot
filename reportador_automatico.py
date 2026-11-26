# -*- coding: utf-8 -*-
"""
Generador y Despachador Automático de Reportes y Dashboards cada 10 Chats.
Destinatario único autorizado: castro.1997.3@gmail.com
"""

import datetime
import html
import json
import logging
import os
import smtplib
import sqlite3
import urllib.request
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from auditoria_consultas import DB_AUDITORIA, _LOCK
from seguridad_ikiam import obtener_estadisticas_presupuesto

logger = logging.getLogger("ikiam_reportador")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

DESTINATARIO_UNICO = "castro.1997.3@gmail.com"

def compilar_dashboard_10_chats(total_registros: int) -> dict:
    """
    Extrae los últimos 10 chats de SQLite y compila las estadísticas, resumen y bugs.
    """
    with _LOCK:
        conn = sqlite3.connect(DB_AUDITORIA, timeout=20.0)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT id, timestamp, scope, session_id, client_ip, pregunta_usuario, 
                   respuesta_sistema, fue_reinicio, tipo_fuente, estado_revision
            FROM consultas_historial
            ORDER BY id DESC LIMIT 10
        """)
        filas = cur.fetchall()
        conn.close()

    if not filas:
        return None

    # Invertir para orden cronológico
    chats = list(reversed(filas))
    primer_id = chats[0]["id"]
    ultimo_id = chats[-1]["id"]

    # Estadísticas de presupuesto de tokens
    stats_b = obtener_estadisticas_presupuesto()

    # Análisis de los 10 chats
    scope_conteo = {"admisiones": 0, "academico": 0}
    avisos_seguridad = 0
    quejas_detectadas = []

    patrones_queja = ["no sirve", "rector", "inutil", "inútil", "queja", "estafa", "mentira", "pesimo", "pésimo", "hablar con alguien"]

    filas_resumen = []
    for c in chats:
        c_id = c["id"]
        sc = c["scope"]
        scope_conteo[sc] = scope_conteo.get(sc, 0) + 1
        preg = c["pregunta_usuario"] or ""
        resp = c["respuesta_sistema"] or ""

        es_seguridad = "Aviso de Seguridad y Uso Aceptable" in resp or "Control de Frecuencia" in resp or "Límite Temporal" in resp
        if es_seguridad:
            avisos_seguridad += 1

        # Detectar potenciales quejas o bugs
        es_queja = any(p in preg.lower() for p in patrones_queja)
        if es_queja or "error" in resp.lower() or "inconveniente temporal" in resp.lower():
            detalle_bug = "Queja de usuario sobre atención" if es_queja else "Fallo o respuesta de error"
            quejas_detectadas.append(f"Chat #{c_id} - {detalle_bug}: \"{preg[:80]}\"")

        filas_resumen.append({
            "id": c_id,
            "hora": c["timestamp"],
            "scope": sc,
            "pregunta": preg,
            "respuesta_corta": (resp[:160] + "...") if len(resp) > 160 else resp,
            "es_seguridad": es_seguridad
        })

    return {
        "primer_id": primer_id,
        "ultimo_id": ultimo_id,
        "total_historico": total_registros,
        "chats": filas_resumen,
        "scope_conteo": scope_conteo,
        "avisos_seguridad": avisos_seguridad,
        "quejas_detectadas": quejas_detectadas,
        "tokens_consumidos": stats_b.get("tokens_consumidos", 0),
        "limite_tokens": stats_b.get("limite_diario", 400000),
        "pct_tokens": stats_b.get("porcentaje_usado", 0.0),
        "modo_resguardo": stats_b.get("modo_resguardo_activo", False),
        "consultas_ia": stats_b.get("consultas_ia", 0),
        "consultas_rag": stats_b.get("consultas_rag_puro", 0)
    }

def generar_html_dashboard(data: dict) -> str:
    """Genera la plantilla HTML visual para el correo electrónico y panel administrativo."""
    p_id = data["primer_id"]
    u_id = data["ultimo_id"]
    tot = data["total_historico"]
    tok_usados = f"{data['tokens_consumidos']:,}"
    tok_lim = f"{data['limite_tokens']:,}"
    pct = data["pct_tokens"]
    n_adm = data["scope_conteo"].get("admisiones", 0)
    n_acad = data["scope_conteo"].get("academico", 0)
    n_sec = data["avisos_seguridad"]
    
    # Bloque de bugs / quejas
    if data["quejas_detectadas"]:
        bugs_items = "".join(f"<li style='margin-bottom:4px;'><strong>{html.escape(q)}</strong></li>" for q in data["quejas_detectadas"])
        bloque_bugs = f"""
        <div style='background:#fef2f2; border:1px solid #fecaca; border-left:4px solid #ef4444; border-radius:6px; padding:12px; margin:16px 0;'>
            <div style='color:#991b1b; font-weight:700; font-size:12.5px; margin-bottom:6px;'>Alertas / Quejas y Posibles Bugs Detectados:</div>
            <ul style='margin:0; padding-left:18px; font-size:11.5px; color:#7f1d1d;'>{bugs_items}</ul>
        </div>
        """
    else:
        bloque_bugs = """
        <div style='background:#f0fdf4; border:1px solid #bbf7d0; border-left:4px solid #16a34a; border-radius:6px; padding:10px 14px; margin:16px 0; font-size:11.5px; color:#166534;'>
            <strong>Cero incidencias críticas:</strong> No se detectaron fallos de ejecución ni quejas abiertas en este bloque de 10 chats.
        </div>
        """

    # Filas de la tabla de chats
    filas_tr = ""
    for c in data["chats"]:
        color_sc = "#065f46" if c["scope"] == "admisiones" else "#1e40af"
        bg_sc = "#ecfdf5" if c["scope"] == "admisiones" else "#eff6ff"
        tag_sec = " <span style='background:#fef3c7; color:#92400e; font-size:9.5px; padding:1px 5px; border-radius:3px;'>Aviso Seguridad</span>" if c["es_seguridad"] else ""
        
        filas_tr += f"""
        <tr style='border-bottom:1px solid #e2e8f0; font-size:11.5px;'>
            <td style='padding:7px 10px; font-weight:700;'>#{c['id']}</td>
            <td style='padding:7px 10px; color:#64748b; white-space:nowrap;'>{html.escape(c['hora'])}</td>
            <td style='padding:7px 10px;'><span style='background:{bg_sc}; color:{color_sc}; padding:2px 6px; border-radius:4px; font-weight:600; font-size:10px;'>{html.escape(c['scope'])}</span>{tag_sec}</td>
            <td style='padding:7px 10px; max-width:240px; word-break:break-word; color:#0f172a; font-weight:600;'>{html.escape(c['pregunta'])}</td>
            <td style='padding:7px 10px; max-width:320px; word-break:break-word; color:#334155;'>{html.escape(c['respuesta_corta'])}</td>
        </tr>
        """

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Reporte Automático de 10 Chats — Ikiam</title>
</head>
<body style="font-family:-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background:#f8fafc; color:#1e293b; margin:0; padding:20px;">
    <div style="max-width:850px; margin:0 auto; background:#ffffff; border:1px solid #e2e8f0; border-top:4px solid #0d5f3a; border-radius:8px; padding:24px; box-shadow:0 2px 4px rgba(0,0,0,0.03);">
        
        <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #e2e8f0; padding-bottom:14px; margin-bottom:18px;">
            <div>
                <h1 style="margin:0; font-size:18px; color:#0d5f3a;">Dashboard y Reporte de Auditoría (Bloque #{tot//10})</h1>
                <p style="margin:4px 0 0; font-size:12px; color:#64748b;">Chats analizados: <strong>#{p_id} al #{u_id}</strong> (Total acumulado: {tot} interacciones)</p>
            </div>
            <div style="text-align:right;">
                <span style="background:#ecfdf5; color:#065f46; border:1px solid #a7f3d0; font-weight:700; font-size:11px; padding:4px 8px; border-radius:5px;">Servidor Ikiam Producción</span>
            </div>
        </div>

        <!-- Métricas KPI Rápidas -->
        <div style="display:grid; grid-template-columns:1fr 1fr 1fr 1fr; gap:10px; margin-bottom:18px;">
            <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:6px; padding:10px; text-align:center;">
                <div style="font-size:10px; color:#64748b; font-weight:700; text-transform:uppercase;">Presupuesto Tokens</div>
                <div style="font-size:14px; font-weight:700; color:#0d5f3a; margin-top:3px;">{tok_usados} ({pct}%)</div>
                <div style="font-size:9.5px; color:#94a3b8;">Límite diario: {tok_lim}</div>
            </div>
            <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:6px; padding:10px; text-align:center;">
                <div style="font-size:10px; color:#64748b; font-weight:700; text-transform:uppercase;">Módulo Académico</div>
                <div style="font-size:16px; font-weight:700; color:#1e40af; margin-top:3px;">{n_acad} chats</div>
                <div style="font-size:9.5px; color:#94a3b8;">Procesos regulares</div>
            </div>
            <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:6px; padding:10px; text-align:center;">
                <div style="font-size:10px; color:#64748b; font-weight:700; text-transform:uppercase;">Módulo Admisiones</div>
                <div style="font-size:16px; font-weight:700; color:#065f46; margin-top:3px;">{n_adm} chats</div>
                <div style="font-size:9.5px; color:#94a3b8;">Proceso 1PA 2027</div>
            </div>
            <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:6px; padding:10px; text-align:center;">
                <div style="font-size:10px; color:#64748b; font-weight:700; text-transform:uppercase;">Bloqueos Seguridad</div>
                <div style="font-size:16px; font-weight:700; color:#b45309; margin-top:3px;">{n_sec}</div>
                <div style="font-size:9.5px; color:#94a3b8;">Firewall activo</div>
            </div>
        </div>

        {bloque_bugs}

        <!-- Tabla Resumen de los 10 Chats -->
        <div style="margin-top:16px;">
            <div style="font-size:13px; font-weight:700; color:#0f172a; margin-bottom:8px;">Detalle de los 10 Mensajes Recibidos:</div>
            <table style="width:100%; border-collapse:collapse; border:1px solid #e2e8f0; border-radius:6px; overflow:hidden;">
                <thead>
                    <tr style="background:#f1f5f9; text-align:left; font-size:11px; color:#475569;">
                        <th style="padding:8px 10px;">ID</th>
                        <th style="padding:8px 10px;">Hora</th>
                        <th style="padding:8px 10px;">Módulo</th>
                        <th style="padding:8px 10px;">Pregunta del Estudiante</th>
                        <th style="padding:8px 10px;">Respuesta Resumida</th>
                    </tr>
                </thead>
                <tbody>
                    {filas_tr}
                </tbody>
            </table>
        </div>

        <div style="margin-top:20px; padding-top:12px; border-top:1px solid #e2e8f0; font-size:10.5px; color:#94a3b8; text-align:center;">
            Reporte institucional generado automáticamente por el subsistema de auditoría de Ikiam Academic Chatbot.<br>
            Destinatario único autorizado: <strong>{DESTINATARIO_UNICO}</strong>. Prohibida su retransmisión no autorizada.
        </div>
    </div>
</body>
</html>"""

def enviar_correo_reporte(data: dict) -> bool:
    """
    Despacha el correo electrónico exclusivamente a castro.1997.3@gmail.com.
    Prohíbe rotundamente adjuntar cualquier otro correo.
    """
    html_content = generar_html_dashboard(data)
    asunto = f"[Ikiam Chatbot] Reporte Automático: Chats #{data['primer_id']} al #{data['ultimo_id']} ({data['total_historico']} total)"

    # Variable de transporte configurada en el entorno
    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", 587))
    smtp_user = os.environ.get("SMTP_USER", "").strip()
    smtp_pass = os.environ.get("SMTP_PASS", "").strip()

    enviado = False
    resend_key = os.environ.get("RESEND_API_KEY", "").strip()

    # 1. Intento vía Resend API (HTTP POST) si está disponible
    if resend_key:
        try:
            req_data = json.dumps({
                "from": "Ikiam Chatbot Auditor <onboarding@resend.dev>",
                "to": [DESTINATARIO_UNICO],
                "subject": asunto,
                "html": html_content
            }).encode("utf-8")
            req = urllib.request.Request(
                "https://api.resend.com/emails",
                data=req_data,
                headers={"Authorization": f"Bearer {resend_key}", "Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                if 200 <= resp.status < 300:
                    logger.info(f"Reporte enviado exitosamente vía Resend API a {DESTINATARIO_UNICO}")
                    enviado = True
        except Exception as e:
            logger.error(f"Fallo enviando reporte vía Resend API: {e}")

    # 2. Intento vía SMTP TLS estándar si no se envió por Resend y las credenciales están presentes
    if not enviado and smtp_user and smtp_pass:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = asunto
            msg["From"] = f"Ikiam Chatbot Auditor <{smtp_user}>"
            msg["To"] = DESTINATARIO_UNICO  # ESTRICTAMENTE UN SOLO DESTINATARIO
            msg.attach(MIMEText(html_content, "html", "utf-8"))

            server = smtplib.SMTP(smtp_host, smtp_port, timeout=12)
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, [DESTINATARIO_UNICO], msg.as_string())
            server.quit()
            logger.info(f"Reporte enviado exitosamente vía SMTP a {DESTINATARIO_UNICO}")
            enviado = True
        except Exception as e:
            logger.error(f"Fallo en conexión SMTP ({smtp_host}:{smtp_port}): {e}")
            enviado = False
    else:
        logger.warning(f"No se configuraron credenciales SMTP_USER/SMTP_PASS ni RESEND_API_KEY en el entorno. Dashboard compilado y almacenado localmente.")
        enviado = False

    # Archivar en la base de datos de auditoría
    tz_ec = datetime.timezone(datetime.timedelta(hours=-5))
    ahora_str = datetime.datetime.now(tz_ec).strftime("%Y-%m-%d %H:%M:%S")
    with _LOCK:
        try:
            conn = sqlite3.connect(DB_AUDITORIA, timeout=20.0)
            conn.execute("""
                INSERT INTO reportes_historial (fecha, primer_id, ultimo_id, total_historico, html_dashboard, enviado_correo)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (ahora_str, data['primer_id'], data['ultimo_id'], data['total_historico'], html_content, 1 if enviado else 0))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error archivando reporte en base de datos: {e}")

    return enviado

def procesar_disparo_cada_10_chats(total_registros: int):
    """
    Función que evalúa si corresponde despachar el reporte y ejecuta el proceso.
    """
    if total_registros <= 0 or (total_registros % 10) != 0:
        return
    logger.info(f"Disparador de 10 chats alcanzado (Total: {total_registros}). Compilando reporte...")
    data = compilar_dashboard_10_chats(total_registros)
    if data:
        enviar_correo_reporte(data)
