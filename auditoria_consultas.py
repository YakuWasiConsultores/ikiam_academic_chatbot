import csv
import datetime
import io
import json
import os
import sqlite3
import threading
import urllib.request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_AUDITORIA = os.path.join(BASE_DIR, "consultas_auditoria.db")
_LOCK = threading.Lock()

def inicializar_db_auditoria():
    """Crea la tabla de consultas si no existe y habilita modo WAL para alta concurrencia."""
    with _LOCK:
        conn = sqlite3.connect(DB_AUDITORIA, timeout=20.0)
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS consultas_historial (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    client_ip TEXT,
                    pregunta_usuario TEXT NOT NULL,
                    respuesta_sistema TEXT NOT NULL,
                    fue_reinicio INTEGER DEFAULT 0,
                    tipo_fuente TEXT DEFAULT 'sistema',
                    respuesta_esperada TEXT DEFAULT NULL,
                    estado_revision TEXT DEFAULT 'pendiente',
                    notas_auditoria TEXT DEFAULT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_consultas_scope ON consultas_historial(scope)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_consultas_fecha ON consultas_historial(timestamp)")
            conn.commit()
        finally:
            conn.close()

def _enviar_webhook_remoto(payload: dict):
    """Envía la consulta en segundo plano a Google Sheets / Drive webhook si está configurado."""
    # En modo de prueba o con envío deshabilitado, se bloquea cualquier salida externa
    if os.environ.get("DISABLE_OUTBOUND_MESSAGES", "true").lower() in ("true", "1", "yes"):
        return

    webhook_url = os.environ.get("WEBHOOK_GOOGLE_SHEETS_URL", "").strip()
    if not webhook_url:
        return
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            webhook_url,
            data=data,
            headers={"Content-Type": "application/json", "User-Agent": "Ikiam-Chatbot-Auditor/1.0"}
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass

def sanitizar_celda_csv(valor) -> str:
    """Mitiga CSV / Formula Injection (CWE-1236) en Microsoft Excel."""
    s = str(valor or "")
    if s and s[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + s
    return s

def registrar_consulta(scope: str, session_id: str, client_ip: str, pregunta: str, respuesta: str, fue_reinicio: bool = False, tipo_fuente: str = "sistema"):
    """Registra una interacción de forma segura en SQLite y dispara webhook si existe."""
    # Hora local de Ecuador (UTC-5)
    tz_ec = datetime.timezone(datetime.timedelta(hours=-5))
    ahora_str = datetime.datetime.now(tz_ec).strftime("%Y-%m-%d %H:%M:%S")

    # Limpiar etiquetas HTML excesivas de la respuesta para el CSV de auditoría
    import re
    resp_limpia = re.sub(r"<[^>]+>", " ", respuesta or "")
    resp_limpia = re.sub(r"\s+", " ", resp_limpia).strip()

    record_id = None
    with _LOCK:
        try:
            conn = sqlite3.connect(DB_AUDITORIA, timeout=20.0)
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO consultas_historial 
                (timestamp, scope, session_id, client_ip, pregunta_usuario, respuesta_sistema, fue_reinicio, tipo_fuente)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (ahora_str, scope, session_id, client_ip or "anon", pregunta, resp_limpia, 1 if fue_reinicio else 0, tipo_fuente))
            conn.commit()
            record_id = cur.lastrowid
            conn.close()
        except Exception as e:
            print("Error registrando consulta en auditoría:", e)

    # Disparar sincronización asíncrona a Google Sheets / Drive si configurado
    payload = {
        "id": record_id,
        "timestamp": ahora_str,
        "scope": scope,
        "session_id": session_id,
        "pregunta": pregunta,
        "respuesta": resp_limpia,
        "fue_reinicio": fue_reinicio
    }
    t = threading.Thread(target=_enviar_webhook_remoto, args=(payload,), daemon=True)
    t.start()

def exportar_csv_consultas(scope: str = None, limite: int = 5000) -> str:
    """Exporta las consultas a formato CSV compatible con Microsoft Excel (UTF-8 con BOM y sanitización anti-fórmulas)."""
    with _LOCK:
        conn = sqlite3.connect(DB_AUDITORIA, timeout=20.0)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        if scope:
            cur.execute("""
                SELECT id, timestamp, scope, session_id, pregunta_usuario, respuesta_sistema, 
                       respuesta_esperada, estado_revision, notas_auditoria
                FROM consultas_historial
                WHERE scope = ?
                ORDER BY id DESC LIMIT ?
            """, (scope, limite))
        else:
            cur.execute("""
                SELECT id, timestamp, scope, session_id, pregunta_usuario, respuesta_sistema, 
                       respuesta_esperada, estado_revision, notas_auditoria
                FROM consultas_historial
                ORDER BY id DESC LIMIT ?
            """, (limite,))
        filas = cur.fetchall()
        conn.close()

    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_ALL)
    # Encabezados formales y claros para el usuario
    writer.writerow([
        "ID",
        "Fecha_Hora_Ecuador",
        "Pestaña_Modulo",
        "ID_Sesion",
        "Pregunta_Estudiante_Aspirante",
        "Respuesta_Emitida_Chatbot",
        "Respuesta_Real_Esperada_Humana",
        "Estado_Revision",
        "Notas_Observaciones"
    ])

    for row in filas:
        writer.writerow([
            row["id"],
            sanitizar_celda_csv(row["timestamp"]),
            sanitizar_celda_csv(row["scope"]),
            sanitizar_celda_csv(row["session_id"]),
            sanitizar_celda_csv(row["pregunta_usuario"]),
            sanitizar_celda_csv(row["respuesta_sistema"]),
            sanitizar_celda_csv(row["respuesta_esperada"] or ""),
            sanitizar_celda_csv(row["estado_revision"] or "pendiente"),
            sanitizar_celda_csv(row["notas_auditoria"] or "")
        ])

    # Devolver con BOM UTF-8 para apertura directa en Excel sin caracteres rotos
    return "\ufeff" + output.getvalue()

def exportar_json_consultas(scope: str = None, limite: int = 5000):
    """Devuelve las consultas en formato JSON para integraciones."""
    with _LOCK:
        conn = sqlite3.connect(DB_AUDITORIA, timeout=20.0)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        if scope:
            cur.execute("SELECT * FROM consultas_historial WHERE scope = ? ORDER BY id DESC LIMIT ?", (scope, limite))
        else:
            cur.execute("SELECT * FROM consultas_historial ORDER BY id DESC LIMIT ?", (limite,))
        rows = cur.fetchall()
        conn.close()
    return [dict(r) for r in rows]

def actualizar_feedback_humano(consulta_id: int, respuesta_esperada: str, estado: str = "revisado", notas: str = ""):
    """Actualiza una consulta con la respuesta humana correcta."""
    with _LOCK:
        conn = sqlite3.connect(DB_AUDITORIA, timeout=20.0)
        cur = conn.cursor()
        cur.execute("""
            UPDATE consultas_historial
            SET respuesta_esperada = ?, estado_revision = ?, notas_auditoria = ?
            WHERE id = ?
        """, (respuesta_esperada, estado, notas, consulta_id))
        conn.commit()
        conn.close()

# Auto-inicializar tabla al importar
inicializar_db_auditoria()
