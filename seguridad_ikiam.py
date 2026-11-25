# -*- coding: utf-8 -*-
"""
Módulo de Seguridad Institucional para el Chatbot de Ikiam.
Protección multinivel contra:
1. Inyección de Prompts y Jailbreaks (DAN, Persona Hijacking, System Prompt Leaking).
2. Intentos de volcado de información técnica (SQL Injection, Env vars, API keys, esquemas DB).
3. Data Loss Prevention (DLP) en respuestas del modelo.
4. Desbordamiento de búfer y ataques DoS por longitud de payload.
5. Control de Tasa (Rate Limiting) Multinivel: Anti-Ráfaga (Burst), Cuota Horaria por IP y por Dispositivo (Client Fingerprint).
6. Token Budget Guard: Presupuesto diario de tokens y conmutación automática a Modo RAG Determinista (Zero-Token).
"""

import datetime
import html
import os
import re
import threading
import time

MAX_PREGUNTA_LONGITUD = 600

# Presupuesto diario de tokens de IA (configurable por variable de entorno)
MAX_DAILY_TOKENS = int(os.environ.get("MAX_DAILY_TOKENS", 400000))
MAX_OUTPUT_TOKENS_PER_CALL = 600

MENSAJE_BLOQUEO_SEGURIDAD = (
    "<div style='border-left:3px solid #b45309; padding-left:10px;'>"
    "<div style='color:#b45309; font-weight:700; font-size:12.5px; margin:0 0 4px;'>Aviso de Seguridad y Uso Aceptable</div>"
    "<p style='font-size:12px; margin:0 0 5px;'>Por políticas de seguridad informática y protección de datos de la Universidad Regional Amazónica Ikiam, este asistente atiende exclusivamente consultas académicas y de admisión en lenguaje natural.</p>"
    "<p style='font-size:11.5px; color:#64748b; margin:0;'>Por favor formule su pregunta sobre trámites, carreras, fechas o requisitos institucionales.</p>"
    "</div>"
)

MENSAJE_LONGITUD_EXCEDIDA = (
    "<div style='border-left:3px solid #b45309; padding-left:10px;'>"
    "<div style='color:#b45309; font-weight:700; font-size:12.5px; margin:0 0 4px;'>Longitud de Consulta Excedida</div>"
    "<p style='font-size:12px; margin:0;'>Su consulta excede la longitud máxima permitida (600 caracteres). Por favor formule una pregunta más breve y directa.</p>"
    "</div>"
)

MENSAJE_BURST_EXCEDIDO = (
    "<div style='border-left:3px solid #b45309; padding-left:10px;'>"
    "<div style='color:#b45309; font-weight:700; font-size:12.5px; margin:0 0 4px;'>Control de Frecuencia de Consultas</div>"
    "<p style='font-size:12px; margin:0;'>Ha enviado varias consultas en pocos segundos. Por favor espere unos momentos antes de enviar su siguiente mensaje.</p>"
    "</div>"
)

MENSAJE_CUOTA_HORARIA_EXCEDIDA = (
    "<div style='border-left:3px solid #b45309; padding-left:10px;'>"
    "<div style='color:#b45309; font-weight:700; font-size:12.5px; margin:0 0 4px;'>Límite Temporal de Consultas Alcanzado</div>"
    "<p style='font-size:12px; margin:0;'>Ha alcanzado el límite de consultas permitidas para este período horario. Si requiere atención inmediata, por favor comuníquese a través de los canales oficiales institucionales.</p>"
    "</div>"
)

# Patrones vigilados de inyección de prompts, jailbreak y extracción de directivas internas
PATRONES_INYECCION = [
    # Extracción de prompt del sistema
    r"\b(?:system\s*prompt|system_instruction|prompt\s*inicial|prompt\s*del\s*sistema)\b",
    r"\b(?:repite|muestra|dame|imprime|revela|escribe|copia)\b.*?\b(?:instrucci[oó]n(?:es)?|prompts?|reglas?|directrices?)\b",
    r"\b(?:instrucci[oó]n(?:es)?|prompts?)\s+(?:del\s+sistema|anteriores|de\s+arriba|iniciales)\b",
    r"\b(?:what\s+is\s+your\s+system\s+prompt|repeat\s+the\s+words\s+above|print\s+your\s+instructions)\b",
    r"\b(?:cu[aá]les\s+son\s+tus\s+instrucciones|qu[eé]\s+te\s+dijeron\s+que\s+hagas|cu[aá]les\s+son\s+tus\s+reglas\s+secretas)\b",
    
    # Anulación de directivas / Jailbreaks
    r"\b(?:ignor\w*|olvid\w*|desobedec\w*|desobedezc\w*|omit\w*|descart\w*)\b.*?\b(?:instrucci[oó]n(?:es)?|reglas?|directrices?|prompts?)\b",
    r"\b(?:disregard\s+all\s+previous\s+instructions|override\s+all\s+rules|bypass\s+restrictions)\b",
    r"\b(?:dan\s*mode|developer\s*mode|modo\s*desarrollador|jailbreak|modo\s*dios|sin\s*censura|sin\s*restricciones)\b",
    r"\b(?:act[uú]a\s+como\s+(?:un\s+)?(?:terminal|consola|hacker|root|linux|bash|cmd|powershell))\b",
    r"\b(?:you\s+are\s+now|a\s+partir\s+de\s+ahora\s+eres)\s+(?:un\s+)?(?:ia\s+sin\s+reglas|asistente\s+sin\s+filtros)\b",
    
    # Reconocimiento y volcado técnico / SQL / Backend
    r"\b(?:select\s+.*\s+from|union\s+select|drop\s+table|insert\s+into|delete\s+from|sqlite_master)\b",
    r"\b(?:gemini_api_key|api_key|aiza[0-9a-za-z_-]{20,}|claves?\s+api|token\s+secreto)\b",
    r"\b(?:variables?\s+de\s+entorno|env\s*vars|os\.environ|process\.env|cat\s+/etc|ls\s+-la)\b",
    r"\b(?:volcar|vuelca|dump)\s+(?:la\s+)?(?:base\s+de\s+datos|memoria|schema|tablas?)\b",
]

REGEX_INYECCION = re.compile("|".join(PATRONES_INYECCION), re.IGNORECASE)

# Patrones para Data Loss Prevention (DLP) en respuestas del sistema
REGEX_API_KEY = re.compile(r"AIza[0-9A-Za-z-_]{35}")
REGEX_RUTAS_INTERNAS = re.compile(r"[A-Za-z]:\\[a-zA-Z0-9_\-\\]+\.(?:py|db|json|env)|/(?:home|etc|var|app)/[a-zA-Z0-9_\-/]+\.(?:py|db|json|env)", re.IGNORECASE)
REGEX_ETIQUETAS_PELIGROSAS = re.compile(r"<\s*(?:script|iframe|object|embed|applet|style|meta|link|svg)\b[^>]*>.*?</\s*(?:script|iframe|object|embed|applet|style|meta|link|svg)\s*>|<\s*(?:script|iframe|object|embed|applet|style|meta|link|svg)\b[^>]*>", re.IGNORECASE | re.DOTALL)
REGEX_EVENTOS_PELIGROSOS = re.compile(r"\b(?:on\w+|javascript:|data:|vbscript:)\s*=", re.IGNORECASE)

# Whitelist de IPs de campus universitario / CEDIA / Intranet RFC 1918
DEFAULT_CAMPUS_SUBNETS = "190.15.,186.,10.,172.16.,172.17.,172.18.,172.19.,172.2,172.3,192.168.,127.0.0.1,::1,localhost"
CAMPUS_IP_PREFIXES = [p.strip() for p in os.environ.get("IKIAM_CAMPUS_IPS", DEFAULT_CAMPUS_SUBNETS).split(",") if p.strip()]

# Estructuras en memoria para Rate Limiting
_RATE_LOCK = threading.Lock()
_IP_BURST = {}          # IP -> list of timestamps within 12s
_CLIENT_BURST = {}      # ClientID -> list of timestamps within 12s (max 6)
_IP_HOURLY = {}         # IP -> list of timestamps within 3600s (max 50 external, 600 campus)
_CLIENT_HOURLY = {}     # ClientID -> list of timestamps within 3600s (max 35)

MAX_BURST_EXTERNAL_IP = 8
MAX_BURST_CAMPUS_IP = 50
MAX_BURST_CLIENT = 6
BURST_WINDOW_SECONDS = 12

MAX_HOURLY_EXTERNAL_IP = 50
MAX_HOURLY_CAMPUS_IP = 600
MAX_HOURLY_CLIENT_DEVICE = 35
HOURLY_WINDOW_SECONDS = 3600

# Estructuras para Token Budget Guard
_BUDGET_LOCK = threading.Lock()
_ESTADO_PRESUPUESTO = {
    "fecha": "",
    "tokens_consumidos": 0,
    "consultas_ia": 0,
    "consultas_rag_puro": 0
}

def _fecha_hoy_ecuador() -> str:
    tz_ec = datetime.timezone(datetime.timedelta(hours=-5))
    return datetime.datetime.now(tz_ec).strftime("%Y-%m-%d")

def registrar_consumo_tokens(tokens_estimados: int, es_ia: bool = True):
    """Registra de forma segura el consumo de tokens del día actual."""
    with _BUDGET_LOCK:
        hoy = _fecha_hoy_ecuador()
        if _ESTADO_PRESUPUESTO["fecha"] != hoy:
            _ESTADO_PRESUPUESTO["fecha"] = hoy
            _ESTADO_PRESUPUESTO["tokens_consumidos"] = 0
            _ESTADO_PRESUPUESTO["consultas_ia"] = 0
            _ESTADO_PRESUPUESTO["consultas_rag_puro"] = 0
        
        if es_ia:
            _ESTADO_PRESUPUESTO["tokens_consumidos"] += max(0, tokens_estimados)
            _ESTADO_PRESUPUESTO["consultas_ia"] += 1
        else:
            _ESTADO_PRESUPUESTO["consultas_rag_puro"] += 1

def presupuesto_tokens_agotado() -> bool:
    """Verifica si el presupuesto diario de tokens asignado se ha consumido."""
    with _BUDGET_LOCK:
        hoy = _fecha_hoy_ecuador()
        if _ESTADO_PRESUPUESTO["fecha"] != hoy:
            return False
        return _ESTADO_PRESUPUESTO["tokens_consumidos"] >= MAX_DAILY_TOKENS

def obtener_estadisticas_presupuesto() -> dict:
    """Devuelve el balance actual del presupuesto diario de tokens para el panel de administración."""
    with _BUDGET_LOCK:
        hoy = _fecha_hoy_ecuador()
        if _ESTADO_PRESUPUESTO["fecha"] != hoy:
            return {
                "fecha": hoy,
                "tokens_consumidos": 0,
                "limite_diario": MAX_DAILY_TOKENS,
                "porcentaje_usado": 0.0,
                "consultas_ia": 0,
                "consultas_rag_puro": 0,
                "modo_resguardo_activo": False
            }
        usado = _ESTADO_PRESUPUESTO["tokens_consumidos"]
        return {
            "fecha": hoy,
            "tokens_consumidos": usado,
            "limite_diario": MAX_DAILY_TOKENS,
            "porcentaje_usado": round((usado / MAX_DAILY_TOKENS) * 100, 2) if MAX_DAILY_TOKENS else 0,
            "consultas_ia": _ESTADO_PRESUPUESTO["consultas_ia"],
            "consultas_rag_puro": _ESTADO_PRESUPUESTO["consultas_rag_puro"],
            "modo_resguardo_activo": usado >= MAX_DAILY_TOKENS
        }

def es_ip_campus(ip: str) -> bool:
    """Determina si una dirección IP pertenece a la red de campus de Ikiam o subredes autorizadas."""
    if not ip:
        return False
    norm_ip = ip.strip().lower()
    return any(norm_ip.startswith(prefix.lower()) for prefix in CAMPUS_IP_PREFIXES)

def verificar_limites_trafico(client_ip: str, client_id: str = "") -> (bool, str):
    """
    Control de tráfico multicapa:
    1. Anti-ráfaga por dispositivo (Client Fingerprint): máximo 6 peticiones en 12 segundos.
    2. Anti-ráfaga por IP: máximo 8 peticiones en 12s para IPs externas, 50 en 12s para campus (NAT).
    3. Cuota horaria por dispositivo: máximo 35 peticiones/hora por dispositivo persistente.
    4. Cuota horaria por IP: 50/hora para IPs externas, 600/hora para campus universitario (NAT).
    """
    now = time.time()
    with _RATE_LOCK:
        # 1. Control Anti-Ráfaga por Dispositivo (si viene con client_id)
        if client_id and len(client_id) >= 8:
            cb_times = _CLIENT_BURST.setdefault(client_id, [])
            cb_times[:] = [t for t in cb_times if now - t < BURST_WINDOW_SECONDS]
            if len(cb_times) >= MAX_BURST_CLIENT:
                return False, MENSAJE_BURST_EXCEDIDO

        # 2. Control Anti-Ráfaga por IP
        b_times = _IP_BURST.setdefault(client_ip, [])
        b_times[:] = [t for t in b_times if now - t < BURST_WINDOW_SECONDS]
        limite_burst_ip = MAX_BURST_CAMPUS_IP if es_ip_campus(client_ip) else MAX_BURST_EXTERNAL_IP
        if len(b_times) >= limite_burst_ip:
            return False, MENSAJE_BURST_EXCEDIDO

        # 3. Control por Huella de Dispositivo Horario (Persistente frente a reinicios de chat)
        if client_id and len(client_id) >= 8:
            c_times = _CLIENT_HOURLY.setdefault(client_id, [])
            c_times[:] = [t for t in c_times if now - t < HOURLY_WINDOW_SECONDS]
            if len(c_times) >= MAX_HOURLY_CLIENT_DEVICE:
                return False, MENSAJE_CUOTA_HORARIA_EXCEDIDA

        # 4. Control por IP Horario (adaptable a NAT Campus)
        h_times = _IP_HOURLY.setdefault(client_ip, [])
        h_times[:] = [t for t in h_times if now - t < HOURLY_WINDOW_SECONDS]
        limite_ip = MAX_HOURLY_CAMPUS_IP if es_ip_campus(client_ip) else MAX_HOURLY_EXTERNAL_IP
        if len(h_times) >= limite_ip:
            return False, MENSAJE_CUOTA_HORARIA_EXCEDIDA

        # Registrar timestamp en todos los buckets
        b_times.append(now)
        h_times.append(now)
        if client_id and len(client_id) >= 8:
            _CLIENT_BURST.setdefault(client_id, []).append(now)
            _CLIENT_HOURLY.setdefault(client_id, []).append(now)

        return True, ""

def validar_tamano_consulta(texto: str) -> (bool, str):
    """Verifica que la consulta cumpla los límites seguros de longitud y caracteres."""
    if not texto:
        return True, ""
    if len(texto) > MAX_PREGUNTA_LONGITUD:
        return False, MENSAJE_LONGITUD_EXCEDIDA
    # Rechazar caracteres nulos o secuencias de control anómalas
    if "\x00" in texto:
        return False, MENSAJE_BLOQUEO_SEGURIDAD
    return True, ""

def detectar_intento_inyeccion(texto: str) -> bool:
    """Detecta si la consulta del usuario intenta anular instrucciones, extraer prompts o atacar el backend."""
    if not texto:
        return False
    norm = re.sub(r"[\s_]+", " ", texto).strip()
    return bool(REGEX_INYECCION.search(norm))

def sanitizar_salida_segura(html_resp: str) -> str:
    """
    Data Loss Prevention (DLP): neutraliza cualquier fuga involuntaria de claves de API,
    rutas de servidor, scripts maliciosos o eventos javascript.
    """
    if not html_resp:
        return ""
    
    # 1. Eliminar etiquetas de script o iframes potencialmente inyectados
    t = REGEX_ETIQUETAS_PELIGROSAS.sub("", html_resp)
    
    # 2. Desactivar manejadores inline peligrosos (excepto seleccionarOpcionCaso seguro)
    def repl_eventos(m):
        ev = m.group(0)
        if "seleccionarOpcionCaso" in ev:
            return ev
        return "data-sanitized="
    t = REGEX_EVENTOS_PELIGROSOS.sub(repl_eventos, t)
    
    # 3. Ocultar claves de API o secretos accidentales
    t = REGEX_API_KEY.sub("[REDACTADO POR SEGURIDAD]", t)
    
    # 4. Ocultar rutas del sistema de archivos interno
    t = REGEX_RUTAS_INTERNAS.sub("[ARCHIVO INSTITUCIONAL]", t)
    
    return t

def escapar_para_tabla(texto: str) -> str:
    """Escapa entidades HTML para renderizado seguro en tablas administrativas."""
    return html.escape(texto or "")
