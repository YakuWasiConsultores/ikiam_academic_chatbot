# -*- coding: utf-8 -*-
"""
Módulo de Seguridad Institucional para el Chatbot de Ikiam.
Protección multinivel contra:
1. Inyección de Prompts y Jailbreaks (DAN, Persona Hijacking, System Prompt Leaking).
2. Intentos de volcado de información técnica (SQL Injection, Env vars, API keys, esquemas DB).
3. Data Loss Prevention (DLP) en respuestas del modelo.
4. Desbordamiento de búfer y ataques DoS por longitud de payload.
"""

import html
import re

MAX_PREGUNTA_LONGITUD = 600

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
