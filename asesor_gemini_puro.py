# -*- coding: utf-8 -*-
"""
Motor Conversacional Asesor Gemini Puro para Ikiam (Web + WhatsApp).
Integra:
1. ikiam_flows.db: Flujos de decisión y opciones predeterminadas interactivas.
2. ikiam_network_org.db: Red institucional de 3 facultades, 10 carreras, dependencias y casos de trámite.
3. ikiam_catalog_docs.db: Catálogo oficial de 175 documentos indexados (FTS5).
4. ikiam_knowledge.db: Base normativa institucional (FTS5: ikiam_docs y enlaces_ikiam).
"""

import html as html_lib
import json
import logging
import os
import re
import sqlite3
import sys
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

from cognitive_memory_ikiam import UserCognitiveMemory

logger = logging.getLogger("ikiam_asesor")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_KNOWLEDGE = os.path.join(BASE_DIR, "ikiam_knowledge.db")
DB_CATALOG = os.path.join(BASE_DIR, "ikiam_catalog_docs.db")
DB_NETWORK = os.path.join(BASE_DIR, "ikiam_network_org.db")
DB_FLOWS = os.path.join(BASE_DIR, "ikiam_flows.db")
DOCS_DIR = os.path.join(BASE_DIR, "documentos_oficiales")
ARCHIVOS_REALES = set(os.listdir(DOCS_DIR)) if os.path.exists(DOCS_DIR) else set()

DEFAULT_PUBLIC_URL = "https://ikiam-academic-chatbot.onrender.com"
MODELS_TO_TRY = ["gemini-3.5-flash-lite", "gemini-flash-lite-latest", "gemini-3.5-flash"]

STOP_WORDS = {
    "que", "por", "para", "con", "los", "las", "una", "uno", "unos", "unas",
    "del", "como", "cuando", "donde", "cual", "cuales", "puedo", "hacer",
    "tener", "hola", "buenas", "buenos", "dias", "tardes", "noches", "dime",
    "esto", "esta", "este", "son", "hay", "sobre", "necesito", "quiero",
    "saber", "informacion", "favor", "ayuda", "ikiam",
}

GREETING_WORDS = {
    "hola", "holi", "buenas", "buenos dias", "buenas tardes", "buenas noches",
    "saludos", "hey", "menu", "menú", "inicio", "empezar", "ayuda", "info",
    "informacion", "información", "que haces", "qué haces", "ok", "gracias",
}

LEMAS_EXPANSION = {
    "falt": "falta inasistencia ausencias",
    "ausen": "inasistencia falta",
    "asist": "asistencia faltas 70",
    "seman": "semana inasistencias horas",
    "famili": "calamidad domestica familiar justificacion",
    "justifi": "justificar justificacion certificados",
    "enferm": "medico salud justificacion reposo",
    "dengu": "salud medico hospital justificacion",
    "reprob": "reprobar perder asistencia notas",
    "perd": "perder reprobar materia carrera prorroga gratuidad",
    "practic": "practicas laborales tutor fo-gvi",
    "vincul": "vinculacion sociedad dvs 160 400",
    "homolog": "homologacion convalidacion cambio 80",
    "cambi": "cambio carrera universidad modalidad complexivo",
    "bec": "beca ayudas bienestar fo-gbu",
    "titul": "titulacion grado tesis complexivo prorroga vencimiento",
    "tesis": "tesis prorroga complexivo titulacion grado vencimiento",
    "prorrog": "prorroga plazo vencimiento tesis complexivo extension gracia segunda tercera",
    "venc": "vencimiento prorroga plazo gracia caducidad",
    "complexiv": "complexivo examen grado modalidad tesis",
    "ingl": "ingles b1 idiomas suficiencia",
    "matricul": "matricula tercera especial retiro",
    "supletor": "supletorio calificacion nota 7",
    "pago": "aranceles cobro pagos perdida gratuidad materias segunda tercera",
    "pagar": "aranceles cobro pagos perdida gratuidad materias",
    "cobr": "aranceles cobro pagos perdida gratuidad",
    "arancel": "aranceles cobro pagos perdida gratuidad tabla",
    "gratuidad": "gratuidad perdida aranceles pagos segunda loes ces",
    "tabla": "tabla arancelaria pagos cobro aranceles",
    "facult": "facultad carreras pregrado oferta academica",
    "carrer": "carrera facultad pregrado oferta academica",
    "ofert": "oferta academica carreras facultades posgrados",
}


def _cargar_env_local():
    """Carga variables desde .env local (si existe) sin sobrescribir variables ya definidas."""
    env_path = os.path.join(BASE_DIR, ".env")
    if not os.path.exists(env_path):
        return
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith("#") or "=" not in s:
                    continue
                k, v = s.split("=", 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if k and k not in os.environ:
                    os.environ[k] = v
    except OSError as e:
        logger.warning(f"No se pudo leer .env local: {e}")


_cargar_env_local()


def _get_gemini_key() -> str:
    return os.environ.get("GEMINI_API_KEY", "").strip()


def _connect_ro(db_path: str) -> sqlite3.Connection:
    """Abre la base SQLite en modo estrictamente de solo lectura."""
    return sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)


def _limpiar_tokens(texto: str) -> List[str]:
    """Extrae palabras seguras para consultas SQL/FTS5."""
    tokens = re.findall(r"[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ0-9]+", texto.lower())
    return [t for t in tokens if len(t) > 2 and t not in STOP_WORDS]


def _construir_query_fts(palabras: List[str]) -> str:
    """Construye una consulta FTS5 segura y libre de errores de sintaxis."""
    reservadas = {"and", "or", "not", "near"}
    terminos: List[str] = []
    vistos = set()

    for w in palabras:
        if w not in vistos and w not in reservadas:
            vistos.add(w)
            terminos.append(w)
        for raiz, expansion in LEMAS_EXPANSION.items():
            if w.startswith(raiz):
                for exp in expansion.split():
                    limpio = re.sub(r"[^a-záéíóúüñ0-9]", "", exp.lower())
                    if limpio and limpio not in vistos and limpio not in reservadas:
                        vistos.add(limpio)
                        terminos.append(limpio)

    if not terminos:
        return ""
    return " OR ".join(f'"{t}"*' for t in terminos[:14])


def html_a_whatsapp(html_text: str, public_base_url: str = "") -> str:
    """Convierte HTML del asesor en texto limpio compatible con WhatsApp y enlaces absolutos."""
    if not html_text:
        return ""
    base = (public_base_url or os.environ.get("PUBLIC_BASE_URL", DEFAULT_PUBLIC_URL)).rstrip("/")
    text = html_text

    # Reemplazar enlaces <a href="...">Texto</a>
    def _repl_link(match: re.Match) -> str:
        href = match.group(1).strip()
        label = re.sub(r"<[^>]+>", "", match.group(2)).strip()
        if href.startswith("mailto:"):
            email = href[7:].strip()
            if email.lower() in label.lower():
                return f"*{email}*"
            return f"{label}: {email}"
        if href.startswith("/documentos/"):
            href = f"{base}{href}"
        elif href.startswith("/"):
            href = f"{base}{href}"
        if not label or label == href:
            return href
        return f"*{label}*: {href}"

    text = re.sub(r'<a\s+[^>]*href=[\'"]([^\'"]+)[\'"][^>]*>(.*?)</a>', _repl_link, text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<h[1-6][^>]*>(.*?)</h[1-6]>", r"\n*\1*\n", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"</?(?:strong|b)>", "*", text, flags=re.IGNORECASE)
    text = re.sub(r"</?(?:em|i)>", "_", text, flags=re.IGNORECASE)
    text = re.sub(r"<li[^>]*>", "• ", text, flags=re.IGNORECASE)
    text = re.sub(r"</li>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</p>|</div>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = html_lib.unescape(text)
    # Limpiar líneas con espacios sobrantes
    lines = [ln.rstrip() for ln in text.splitlines()]
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def consultar_caso_red(codigo_caso: str) -> Optional[Tuple[Tuple[Any, ...], Dict[str, List[Tuple[str, str]]]]]:
    """Obtiene la ficha oficial estructurada de un caso desde ikiam_network_org.db."""
    if not os.path.exists(DB_NETWORK):
        return None
    try:
        conn = _connect_ro(DB_NETWORK)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT c.documento_archivo, c.nombre_tramite, c.perfil_estudiante,
                   c.descripcion_caso, c.dependencia_id, c.autoridad_destinataria,
                   c.correo_destino, c.plazo_reglamentario, c.requisitos_adjuntos,
                   c.pasos_procedimiento, c.enlace_descarga, d.nombre as nombre_dep
            FROM casos_tramite_red c
            LEFT JOIN dependencias d ON c.dependencia_id = d.id
            WHERE c.codigo_caso = ? OR CAST(c.id AS TEXT) = ?
            """,
            (codigo_caso, codigo_caso),
        )
        row = cur.fetchone()

        coordinaciones_por_facultad: Dict[str, List[Tuple[str, str]]] = {}
        if row and ("coordinacion" in str(row[4]).lower() or "coordinacion" in str(row[6]).lower()):
            cur.execute(
                """
                SELECT facultad_nombre, carrera, correo_coordinacion
                FROM coordinaciones_carrera
                ORDER BY facultad_codigo, carrera
                """
            )
            for fac, carr, email in cur.fetchall():
                coordinaciones_por_facultad.setdefault(fac, []).append((carr, email))

        conn.close()
        return (row, coordinaciones_por_facultad) if row else None
    except Exception as e:
        logger.error(f"Error consultando caso red '{codigo_caso}': {e}")
        return None


def formatear_respuesta_caso(
    row: Tuple[Any, ...],
    coordinaciones_por_facultad: Dict[str, List[Tuple[str, str]]],
) -> str:
    """Construye HTML estilizado para la ficha del caso seleccionado estructurado por Facultades."""
    doc_archivo, nombre_tramite, _perfil, desc, dep_id, autoridad, correo_dest, plazo, reqs, pasos, enlace, nom_dep = row

    enlace_html = ""
    if doc_archivo and doc_archivo in ARCHIVOS_REALES:
        enlace_html = (
            f"<div style='margin: 12px 0;'>"
            f"<a href='/documentos/{doc_archivo}' target='_blank' "
            f"style='display:inline-block; background-color:#0d5f3a; color:#ffffff; padding:10px 16px; border-radius:6px; font-weight:bold; text-decoration:none;'>"
            f"📥 Descargar Formato Oficial (.docx)</a></div>"
        )
    elif enlace and enlace.startswith("http"):
        enlace_html = (
            f"<div style='margin: 12px 0;'>"
            f"<a href='{enlace}' target='_blank' "
            f"style='display:inline-block; background-color:#0d5f3a; color:#ffffff; padding:10px 16px; border-radius:6px; font-weight:bold; text-decoration:none;'>"
            f"🌐 Ir al Portal Oficial</a></div>"
        )

    correos_html = ""
    if coordinaciones_por_facultad and ("coordinacion" in dep_id.lower() or "coordinacion" in correo_dest.lower()):
        correos_html = (
            "<div style='background-color:#f0fdf4; border:1px solid #bbf7d0; padding:12px; border-radius:8px; margin:10px 0;'>"
            "<strong style='color:#0d5f3a; font-size:13.5px;'>🏛️ Correos Oficiales de Coordinación de Carrera (Por Facultad):</strong>"
        )
        for fac_nombre, carreras in coordinaciones_por_facultad.items():
            correos_html += (
                f"<div style='margin-top:8px;'>"
                f"<span style='color:#065f46; font-weight:bold; font-size:12.5px;'>📁 {fac_nombre}:</span>"
                f"<ul style='margin:4px 0 6px 18px; padding:0; font-size:12px;'>"
            )
            for carr, email in carreras:
                correos_html += f"<li><strong>{carr}:</strong> <a href='mailto:{email}' style='color:#0d5f3a; font-weight:bold;'>{email}</a></li>"
            correos_html += "</ul></div>"
        correos_html += "</div>"
    else:
        emails_list = [e.strip() for e in re.split(r"\s+y\s+|,", correo_dest) if "@" in e]
        if emails_list:
            enlaces_email = " y ".join(
                f"<a href='mailto:{em}' style='color:#0d5f3a; font-weight:bold; text-decoration:underline;'>{em}</a>"
                for em in emails_list
            )
            correos_html = f"<p style='margin:4px 0;'><strong>📬 Correo(s) Oficial(es) de Recepción:</strong> {enlaces_email}</p>"
        else:
            correos_html = f"<p style='margin:4px 0;'><strong>📬 Canal de Recepción:</strong> {correo_dest}</p>"

    req_items = [r.strip() for r in reqs.split(",") if r.strip()]
    req_html = "".join(f"<li>{r}</li>" for r in req_items)

    paso_items = [p.strip() for p in re.split(r"\s*\d+\.\s*", pasos) if p.strip()]
    pasos_html = "".join(f"<li>{p}</li>" for p in paso_items)

    return f"""<div style='border-left:4px solid #0d5f3a; padding-left:12px; margin-bottom:12px;'>
<h3 style='color:#0d5f3a; margin-top:0;'>🏛️ {nombre_tramite}</h3>
<p style='color:#4b5563; font-style:italic;'>{desc}</p>
<div style='background:#f9fafb; border:1px solid #e5e7eb; border-radius:8px; padding:12px; margin:10px 0;'>
  <p style='margin:4px 0;'><strong>🏢 Dependencia Responsable:</strong> {nom_dep or autoridad}</p>
  <p style='margin:4px 0;'><strong>👤 Dirigido a:</strong> {autoridad}</p>
  <p style='margin:4px 0;'><strong>⏳ Plazo Reglamentario:</strong> <span style='color:#b91c1c; font-weight:bold;'>{plazo}</span></p>
  {correos_html}
</div>
{enlace_html}
<h4 style='color:#0d5f3a; margin-bottom:6px;'>📋 Requisitos y Documentos Obligatorios:</h4>
<ul style='margin-top:0;'>{req_html}</ul>
<h4 style='color:#0d5f3a; margin-bottom:6px;'>🚀 Pasos a seguir:</h4>
<ol style='margin-top:0;'>{pasos_html}</ol>
</div>"""


def evaluar_flujo_guiado(pregunta: str) -> Optional[Dict[str, Any]]:
    """Verifica si la pregunta coincide con un flujo general guiado y devuelve HTML + opciones."""
    if not os.path.exists(DB_FLOWS):
        return None

    p_low = re.sub(r"[¿?¡!.,]", " ", pregunta.lower()).strip()
    p_low = re.sub(r"\s+", " ", p_low)
    # Normalizar sin artículos/preposiciones comunes para empatar frases naturales ("retirar una materia" -> "retirar materia")
    p_sin_art = " ".join(w for w in p_low.split() if w not in {"un", "una", "el", "la", "los", "las", "mi", "mis", "de", "del", "a"})

    # Consultas muy específicas (porcentaje, valor, cálculo o regla concreta) deben ir directo al motor RAG + IA
    es_consulta_especifica = any(
        k in p_low for k in ("%", "porcentaje", "arancel", "cuesta", "costo", "valor", "pagar", "pago", "repruebo", "reprobar", "nota", "70")
    )
    if es_consulta_especifica:
        return None

    # Reglas flexibles por intención para variaciones naturales en español
    intenciones_extra = {
        "flujo_ingreso": lambda s: ("ingres" in s or "entrar" in s or "postul" in s or "admision" in s or "admisión" in s) and ("ikiam" in s or "universidad" in s or "estudiar" in s or "carrera" in s),
        "flujo_retiro": lambda s: ("retir" in s or "baja" in s or "cancel" in s) and ("mater" in s or "asignat" in s or "semestre" in s or "segunda" in s),
        "flujo_faltas": lambda s: ("justific" in s or "falte" in s or "falté" in s or "inasisten" in s) and ("falt" in s or "clas" in s or "examen" in s or "enferm" in s or "medic" in s or "calamidad" in s),
        "flujo_becas": lambda s: "beca" in s or ("ayuda" in s and "economic" in s),
        "flujo_practicas": lambda s: "practic" in s or "400 horas" in s or "vinculacion" in s or "vinculación" in s,
    }

    try:
        conn = _connect_ro(DB_FLOWS)
        cur = conn.cursor()
        cur.execute(
            "SELECT id, titulo_guia, saludo_cordial, mensaje_orientador, opciones_json, palabras_clave FROM flujos_decision"
        )
        filas = cur.fetchall()
        conn.close()

        for f_id, titulo, saludo, msg_orientador, opciones_json, keywords in filas:
            claves = [k.strip().lower() for k in keywords.split(",") if k.strip()]
            coincide = any(
                re.search(rf"\b{re.escape(c)}\b", p_low)
                or re.search(rf"\b{re.escape(c)}\b", p_sin_art)
                or (len(c) > 6 and (c in p_low or c in p_sin_art))
                for c in claves
            )
            if not coincide and f_id in intenciones_extra:
                coincide = intenciones_extra[f_id](p_low)

            if coincide:
                opciones = json.loads(opciones_json)
                botones_html = "<div class='opciones-guiadas-grid' style='display:flex; flex-direction:column; gap:8px; margin:14px 0;'>"
                for opc in opciones:
                    c_caso = opc.get("codigo_caso", "")
                    etiqueta = opc.get("etiqueta", "")
                    desc = opc.get("descripcion", "")
                    botones_html += (
                        f"<button class='btn-opcion-guia' onclick='seleccionarOpcionCaso(\"{c_caso}\", \"{etiqueta}\")' "
                        f"style='text-align:left; background:#ffffff; border:1.5px solid #0d5f3a; color:#0d5f3a; padding:10px 14px; "
                        f"border-radius:8px; cursor:pointer; font-weight:600; font-size:13.5px; transition:all 0.2s;'>"
                        f"<div style='font-size:14px;'>{etiqueta}</div>"
                        f"<div style='font-size:11.5px; color:#4b5563; font-weight:normal; margin-top:2px;'>{desc}</div>"
                        f"</button>"
                    )
                botones_html += "</div>"

                respuesta_html = (
                    f"<p><strong>{saludo}</strong></p>"
                    f"<p>{msg_orientador}</p>"
                    f"{botones_html}"
                    f"<p style='font-size:12px; color:#6b7280; font-style:italic;'>"
                    f"💡 Haz clic sobre tu caso particular para ver los requisitos, correo de entrega y formulario oficial.</p>"
                )
                return {
                    "titulo": titulo,
                    "saludo": saludo,
                    "mensaje_orientador": msg_orientador,
                    "opciones": opciones,
                    "html": respuesta_html,
                }
    except Exception as e:
        logger.error(f"Error evaluando flujo guiado: {e}")
    return None


def buscar_contexto_db(pregunta: str) -> Tuple[List[Tuple[str, str, str, str]], List[str], List[str]]:
    """Consulta las 3 bases de conocimiento (ikiam_knowledge, ikiam_catalog_docs, ikiam_network_org)."""
    rows: List[Tuple[str, str, str, str]] = []
    docs_catalogo: List[str] = []
    info_red: List[str] = []

    palabras = _limpiar_tokens(pregunta)
    fts_query = _construir_query_fts(palabras)
    p_low = pregunta.lower()

    # 1. ikiam_knowledge.db -> tabla FTS5 ikiam_docs (corregido: antes consultaba 'normativas_ikiam')
    if os.path.exists(DB_KNOWLEDGE) and fts_query:
        try:
            conn = _connect_ro(DB_KNOWLEDGE)
            cur = conn.cursor()
            cur.execute(
                "SELECT titulo, contenido, documentos_requeridos, url_fuente "
                "FROM ikiam_docs WHERE ikiam_docs MATCH ? ORDER BY rank LIMIT 4",
                (fts_query,),
            )
            rows = cur.fetchall()

            if not rows and palabras:
                like_clauses = " OR ".join(["titulo LIKE ? OR contenido LIKE ? OR documentos_requeridos LIKE ?" for _ in palabras[:5]])
                params = []
                for w in palabras[:5]:
                    pat = f"%{w}%"
                    params.extend([pat, pat, pat])
                cur.execute(
                    f"SELECT titulo, contenido, documentos_requeridos, url_fuente FROM ikiam_docs WHERE {like_clauses} LIMIT 3",
                    params,
                )
                rows = cur.fetchall()
            conn.close()
        except Exception as e:
            logger.error(f"Error consultando ikiam_knowledge.db: {e}")

    # 2. ikiam_catalog_docs.db -> catalogo_fts (175 documentos reales)
    if os.path.exists(DB_CATALOG) and fts_query:
        try:
            conn = _connect_ro(DB_CATALOG)
            cur = conn.cursor()
            cur.execute(
                "SELECT archivo, titulo, categoria, descripcion FROM catalogo_fts "
                "WHERE catalogo_fts MATCH ? ORDER BY rank LIMIT 4",
                (fts_query,),
            )
            for arch, tit, cat, desc in cur.fetchall():
                ruta = f"/documentos/{arch}" if arch in ARCHIVOS_REALES else "https://www.ikiam.edu.ec/index.php/procesos-academicos/"
                docs_catalogo.append(f"- {tit} ({cat}): {desc} | Enlace: {ruta}")
            conn.close()
        except Exception as e:
            logger.error(f"Error consultando ikiam_catalog_docs.db: {e}")

    # 3. ikiam_network_org.db -> facultades, coordinaciones_carrera, dependencias, casos_tramite_red
    if os.path.exists(DB_NETWORK):
        try:
            conn = _connect_ro(DB_NETWORK)
            cur = conn.cursor()

            # Casos por trámite (corregido: usa columna real 'nombre_tramite', antes 'titulo_caso')
            filtros_caso = []
            if any(k in p_low for k in ("retiro", "retirar", "segunda matricula")):
                filtros_caso.append("retiro%")
            if any(k in p_low for k in ("ingres", "admision", "homolog", "reingres", "cambio")):
                filtros_caso.extend(["ingreso%", "cambio%"])
            if any(k in p_low for k in ("falt", "inasist", "enferm", "calamidad", "medico")):
                filtros_caso.append("justificacion%")
            if any(k in p_low for k in ("bec", "ayuda", "economic")):
                filtros_caso.extend(["beca%", "ayuda%"])
            if any(k in p_low for k in ("practic", "400", "vincul", "dvs")):
                filtros_caso.append("practicas%")

            for pat in dict.fromkeys(filtros_caso):
                cur.execute(
                    "SELECT nombre_tramite, autoridad_destinataria, correo_destino, plazo_reglamentario, documento_archivo "
                    "FROM casos_tramite_red WHERE codigo_caso LIKE ?",
                    (pat,),
                )
                for nom, aut, cor, plazo, doc_arch in cur.fetchall():
                    doc_url = f"/documentos/{doc_arch}" if doc_arch in ARCHIVOS_REALES else ""
                    info_red.append(
                        f"TRÁMITE: {nom} | AUTORIDAD: {aut} | CORREO: {cor} | PLAZO: {plazo}"
                        + (f" | FORMULARIO: {doc_url}" if doc_url else "")
                    )

            # Facultades y coordinaciones si preguntan por oferta, facultades o carreras
            claves_fac = (
                "facultad", "carrera", "oferta", "pregrado", "estudiar", "coordinacion",
                "tierra", "agua", "vida", "socioambiental", "geocien", "hidrolog",
                "agroecolog", "electromec", "biotec", "ecosist", "veterinar",
                "biocomerc", "arquitect", "educacion",
            )
            if any(k in p_low for k in claves_fac):
                cur.execute(
                    """
                    SELECT f.nombre, c.carrera, c.correo_coordinacion, c.titulo_otorgado
                    FROM coordinaciones_carrera c
                    JOIN facultades f ON c.facultad_codigo = f.codigo
                    ORDER BY f.codigo, c.carrera
                    """
                )
                por_fac: Dict[str, List[str]] = {}
                for fac, carr, mail, tit in cur.fetchall():
                    por_fac.setdefault(fac, []).append(f"{carr} ({tit}, correo: {mail})")
                for fac, lista in por_fac.items():
                    info_red.append(f"FACULTAD: {fac} -> Carreras: " + "; ".join(lista))

            # Dependencias institucionales generales
            cur.execute("SELECT nombre, correo_oficial, competencias_clave, enlace_web FROM dependencias")
            for nom, mail, comp, web in cur.fetchall():
                if any(w in (nom + " " + comp).lower() for w in palabras) or any(
                    k in p_low for k in ("titul", "tesis", "prorrog", "complexiv", "contacto", "correo")
                ):
                    info_red.append(f"DEPENDENCIA: {nom} | CORREO: {mail} | COMPETENCIAS: {comp} | WEB: {web}")

            conn.close()
        except Exception as e:
            logger.error(f"Error consultando ikiam_network_org.db: {e}")

    return rows, docs_catalogo, list(dict.fromkeys(info_red))


def limpiar_formato_html(texto: str) -> str:
    t = texto.strip()
    t = re.sub(r"```(?:html)?\s*", "", t)
    t = t.replace("```", "")

    t = re.sub(r"###\s*(.*?)\n", r'<h4 style="color:#0d5f3a; margin-top:12px; margin-bottom:6px;">\1</h4>', t)
    t = re.sub(r"##\s*(.*?)\n", r'<h3 style="color:#0d5f3a; margin-top:14px; margin-bottom:6px;">\1</h3>', t)

    lines = t.split("\n")
    in_list = False
    out_lines = []
    for line in lines:
        s_line = line.strip()
        if s_line.startswith("* ") or s_line.startswith("- "):
            if not in_list:
                out_lines.append('<ul style="margin-top:4px; margin-bottom:8px; padding-left:20px;">')
                in_list = True
            out_lines.append(f"<li>{s_line[2:].strip()}</li>")
        else:
            if in_list:
                out_lines.append("</ul>")
                in_list = False
            out_lines.append(line)
    if in_list:
        out_lines.append("</ul>")
    t = "\n".join(out_lines)

    t = t.replace("\n\n", "<br><br>").replace("\n", "<br>")
    t = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", t)

    def repl_md(m: re.Match) -> str:
        txt, url = m.group(1), m.group(2)
        if url.startswith("/documentos/"):
            fname = os.path.basename(url)
            if fname in ARCHIVOS_REALES:
                return f"<a href='/documentos/{fname}' target='_blank' style='color:#0d5f3a; font-weight:bold; text-decoration:underline;'>{txt}</a>"
            return f"{txt} (<a href='https://www.ikiam.edu.ec/index.php/procesos-academicos/' target='_blank' style='color:#0d5f3a; font-weight:bold; text-decoration:underline;'>Portal de Procesos Académicos Ikiam</a>)"
        return f"<a href='{url}' target='_blank' style='color:#0d5f3a; font-weight:bold; text-decoration:underline;'>{txt}</a>"

    t = re.sub(r"\[([^\]]+)\]\((https?://[^\s\)]+|/[^\s\)]+)\)", repl_md, t)

    def repl_url(m: re.Match) -> str:
        return f"<a href='{m.group(0)}' target='_blank' style='color:#0d5f3a; font-weight:bold; text-decoration:underline;'>{m.group(0)}</a>"

    t = re.sub(r"(?<![\'\"=])(https?://[^\s<]+)", repl_url, t)
    t = t.replace("<ul><br>", "<ul>").replace("</ul><br>", "</ul>")
    t = t.replace("<br><ul>", "<ul>").replace("<br><li>", "<li>")
    return t.strip()


def extraer_hechos_automaticos(memoria: UserCognitiveMemory, pregunta: str):
    p_low = pregunta.lower()
    if ("prorroga" in p_low or "tesis" in p_low or "complexivo" in p_low) and any(
        w in p_low for w in ("venci", "caduc", "perdi", "plazo", "gracia", "segunda", "tercera", "tiempo")
    ):
        memoria.actualizar_hecho("situacion_titulacion", "Estudiante reporta dificultades con plazos o prórrogas en su proceso de titulación.")
        memoria.registrar_monologo("El estudiante indica vencimiento o apuro en plazos de grado. Orientarlo con los requisitos de cambio a complexivo o solicitud de gracia.")
    elif ("dengue" in p_low or "hospital" in p_low or "enfermo" in p_low or "medico" in p_low) and any(
        w in p_low for w in ("estoy", "tengo", "falte", "estuve", "estube", "grave", "reposo")
    ):
        memoria.actualizar_hecho("salud", "Estudiante reportó hospitalización o enfermedad médica personal.")
        memoria.registrar_monologo("El estudiante tiene una situación médica real. Priorizar su bienestar y orientarlo con la ruta de excepción por fuerza mayor.")
    elif ("familiar" in p_low or "familiares" in p_low or "calamidad" in p_low) and any(
        w in p_low for w in ("falleci", "murio", "enfermo", "problema", "urgencia")
    ):
        memoria.actualizar_hecho("situacion_personal", "Reporta faltas o atrasos por problemas familiares o calamidad doméstica.")
        memoria.registrar_monologo("Orientarlo a dialogar con docentes y presentar carta motivada a Coordinación para reprogramar evaluaciones.")
    elif any(w in p_low for w in ("homologar", "convalidar", "uce", "epn")) and any(
        w in p_low for w in ("vengo", "cambiarme", "estudio en", "estudiaba")
    ):
        memoria.actualizar_hecho("origen_academico", "Interesado en homologación externa proveniente de otra universidad.")
        memoria.registrar_monologo("Aspirante o estudiante en homologación. Recordar fechas de diciembre (1 al 18), 80% de similitud y carta a Vicerrectorado.")


def _es_saludo_simple(pregunta: str) -> bool:
    limpio = re.sub(r"[¿?¡!.,]", " ", pregunta.lower()).strip()
    limpio = re.sub(r"\s+", " ", limpio)
    return limpio in GREETING_WORDS


def responder_consulta_estructurada(
    session_id: str,
    pregunta: str,
    public_base_url: str = "",
) -> Dict[str, Any]:
    """
    Resuelve la consulta académica devolviendo tanto HTML enriquecido (Web)
    como texto estructurado y opciones interactivas (WhatsApp Cloud API).
    """
    low = pregunta.lower().strip()
    memoria = UserCognitiveMemory(session_id)
    extraer_hechos_automaticos(memoria, pregunta)

    # 0. Saludo simple / Menú inicial
    if _es_saludo_simple(pregunta):
        opciones_inicio = [
            {"codigo_caso": "justificacion_salud", "etiqueta": "🩺 Justificar Faltas", "descripcion": "Inasistencias médicas o calamidad (plazo 3 días)."},
            {"codigo_caso": "retiro_ordinario", "etiqueta": "📋 Retiro de Materia", "descripcion": "Retiro ordinario (30 días) o por fuerza mayor."},
            {"codigo_caso": "ingreso_primera_vez", "etiqueta": "🎓 Admisión / Ingreso", "descripcion": "Nuevos bachilleres, homologación y reingreso."},
            {"codigo_caso": "practicas_inicio", "etiqueta": "📝 Prácticas (400h)", "descripcion": "Solicitud inicial o certificado DVS."},
            {"codigo_caso": "beca_postulacion", "etiqueta": "🏅 Becas y Ayudas", "descripcion": "Postulación semestral o ayudas emergentes."},
        ]
        memoria.guardar_opciones_flujo(opciones_inicio)
        saludo_html = (
            "<p><strong>¡Hola! Soy el Asesor de la Dirección Académica de la Universidad Regional Amazónica Ikiam.</strong></p>"
            "<p>Puedo ayudarte con normativas, requisitos, formularios oficiales, facultades y contactos de trámite. "
            "Escríbeme tu consulta (ej. <em>\"prórroga de tesis\"</em>, <em>\"carreras por facultad\"</em>, <em>\"segunda matrícula\"</em>) "
            "o elige uno de los trámites frecuentes:</p>"
        )
        botones_html = "".join(
            f"<button class='btn-opcion-guia' onclick='seleccionarOpcionCaso(\"{o['codigo_caso']}\", \"{o['etiqueta']}\")' "
            f"style='display:block; width:100%; margin:6px 0; text-align:left; background:#ffffff; border:1.5px solid #0d5f3a; color:#0d5f3a; padding:10px 14px; border-radius:8px; cursor:pointer; font-weight:600;'>"
            f"{o['etiqueta']} — <span style='font-weight:normal; color:#4b5563;'>{o['descripcion']}</span></button>"
            for o in opciones_inicio
        )
        html_out = f"{saludo_html}<div>{botones_html}</div>"
        wa_out = (
            "🏛️ *Asistente Académico - Universidad Regional Amazónica Ikiam*\n\n"
            "¡Hola! Puedo orientarte sobre trámites estudiantiles, normativas, facultades y formularios oficiales.\n\n"
            "Escribe directamente tu duda (ej. _\"prórroga de tesis\"_, _\"carreras por facultad\"_, _\"aranceles por segunda matrícula\"_) "
            "o selecciona una opción del menú:"
        )
        return {
            "kind": "flow",
            "html": html_out,
            "whatsapp_text": wa_out,
            "flow_options": opciones_inicio,
        }

    # 1. Filtro estricto: Compras Públicas / SERCOP
    if any(k in low for k in ("compras publicas", "compras públicas", "sercop", "licitacion", "licitación", "contratos proveedores", "proveedor")):
        ans_filtro = (
            "Estimado/a usuario/a:<br><br>"
            "Le recordamos que este canal pertenece exclusivamente a la <strong>Dirección Académica</strong> de Ikiam "
            "(procesos estudiantiles de pregrado: homologaciones, cambios de carrera, titulación, matrículas y prácticas).<br><br>"
            "Para procesos de <strong>Compras Públicas o Licitaciones</strong>, consulte a la Dirección Administrativa en el portal institucional: "
            "<a href='https://www.ikiam.edu.ec/index.php/procedimientos-de-licitacion/' target='_blank' style='color:#0d5f3a; font-weight:bold; text-decoration:underline;'>"
            "Procedimientos de Licitación Ikiam</a>."
        )
        memoria.registrar_episodio(pregunta, ans_filtro)
        return {
            "kind": "filter",
            "html": ans_filtro,
            "whatsapp_text": html_a_whatsapp(ans_filtro, public_base_url),
            "flow_options": [],
        }

    # 2. Resolución de opción numérica si el usuario respondió "1", "2"... tras un menú
    codigo_num = memoria.resolver_opcion_numerica(pregunta)
    codigo_limpio = codigo_num or low.replace("caso:", "").strip()

    # 3. Evaluación de caso específico de red institucional
    caso_res = consultar_caso_red(codigo_limpio)
    if caso_res:
        memoria.limpiar_opciones_flujo()
        row, coords = caso_res
        ans_caso = formatear_respuesta_caso(row, coords)
        memoria.registrar_episodio(pregunta, ans_caso)
        return {
            "kind": "case",
            "html": ans_caso,
            "whatsapp_text": html_a_whatsapp(ans_caso, public_base_url),
            "flow_options": [],
        }

    # 4. Evaluación de flujo general guiado
    flujo_ans = evaluar_flujo_guiado(pregunta)
    if flujo_ans:
        memoria.guardar_opciones_flujo(flujo_ans["opciones"])
        memoria.registrar_episodio(pregunta, flujo_ans["html"])
        wa_body = f"*{flujo_ans['titulo']}*\n\n{flujo_ans['saludo']}\n\n{flujo_ans['mensaje_orientador']}"
        return {
            "kind": "flow",
            "html": flujo_ans["html"],
            "whatsapp_text": wa_body,
            "flow_options": flujo_ans["opciones"],
        }

    # 5. Consulta abierta / casos complejos: RAG Multi-DB + Gemini
    memoria.limpiar_opciones_flujo()
    rows, docs_catalogo, info_red = buscar_contexto_db(pregunta)

    secciones = []
    if rows:
        secciones.append(
            "\n\n".join(
                f"TEMA: {r[0]}\nCONTENIDO OFICIAL: {r[1]}\nREQUISITOS Y DOCUMENTOS: {r[2]}\nENLACE: {r[3]}"
                for r in rows
            )
        )
    if docs_catalogo:
        secciones.append("DOCUMENTOS Y RESOLUCIONES EN EL CATÁLOGO OFICIAL:\n" + "\n".join(docs_catalogo))
    if info_red:
        secciones.append("RED INSTITUCIONAL, FACULTADES Y CONTACTOS OFICIALES:\n" + "\n".join(info_red))

    contexto_str = "\n\n".join(secciones) if secciones else "Normativa académica general de la Universidad Regional Amazónica Ikiam."
    resumen_cognitivo = memoria.obtener_resumen_cognitivo()

    system_instruction_text = """Eres el asesor oficial de la Dirección Académica de la Universidad Regional Amazónica Ikiam (Tena, Ecuador).
Tu labor es responder consultas estudiantiles con empatía, precisión reglamentaria y en estricto español.

NORMAS OBLIGATORIAS:
- Responde DIRECTO al grano, con tono cordial, empático y estructurado (negritas y viñetas).
- NUNCA respondas con evasivas como "acérquese a la oficina", "vaya al campus" o "consulte en secretaría".
- Las carreras de pregrado de Ikiam se organizan estrictamente en 3 Facultades:
  1. Facultad de Ciencias de la Tierra y Agua (Geociencias, Hidrología, Agroecología, Electromecánica y Energías Renovables).
  2. Facultad de Ciencias de la Vida (Biotecnología, Ecosistemas, Medicina Veterinaria y Manejo de Vida Silvestre).
  3. Facultad de Ciencias Socioambientales (Biocomercio, Arquitectura Sostenible, Educación en Ciencias Experimentales).
- Siempre que menciones un trámite o formulario de Ikiam, DEBES proporcionar el hipervínculo en formato markdown [Nombre](URL).
- Siempre indica con claridad a qué autoridad y a qué correo institucional debe remitirse la solicitud.
- REGLA ESTRICTA DE DOCUMENTOS: SOLO puedes proporcionar enlaces a documentos que REALMENTE existan en el repositorio oficial:
  - Justificación de Faltas: [Descargar Formulario de Justificación (.docx)](/documentos/Formato-Solicitud-Justificacion-Inasistencias.docx)
  - Retiro de Asignaturas: [Descargar Solicitud de Retiro Voluntario (.docx)](/documentos/Formato-Solicitud-Retiro-Voluntario-Asignatura.docx) y [Portal de Procesos Académicos Ikiam](https://www.ikiam.edu.ec/index.php/procesos-academicos/)
  - Becas: [Descargar Formato FO-GBU-40 Solicitud de Becas (.docx)](/documentos/FO-GBU-40-V.5.0-Solicitud-de-becas-1.docx)
  - Ayudas Económicas: [Descargar Formato FO-GBU-56 (.docx)](/documentos/FO-GBU-56-V.1.1Solicitud-de-ayudas-economicas-2.docx)
  - Prácticas Preprofesionales: [Descargar Formato FO-GVI-29 Solicitud de Prácticas (.docx)](/documentos/FO-GVI-29-V.3.1-Solicitud-para-realizar-practicas-preprofesionales.docx)
  - Planificación de Prácticas: [Descargar Planificación FO-GVI-04 (.docx)](/documentos/FO-GVI-04-V.3.1-Planificacion-de-practicas-preprofesionales-pregrado.docx)
  - Certificado de Prácticas: [Descargar Solicitud Certificado FO-GVI-30 (.docx)](/documentos/FO-GVI-30-V.2.0-Solicitud-de-certificado-de-practicas-preprofesionales-2.docx)
  - Cambio de Carrera: [Descargar Solicitud de Cambio de Carrera (.docx)](/documentos/Solicitud-de-cambio-de-carrera.docx)
  - Cambio de Universidad / Admisión Extranjera: [Descargar Solicitud de Cambio de Universidad (.docx)](/documentos/Solicitud-de-cambio-de-universidad.docx)
  - Reingreso: [Descargar Formato de Reingreso (.docx)](/documentos/FORMATO-SOLICITUD-DE-REINGRESO.docx)
  - Calendario Homologación: [Descargar Calendario de Homologación (.pdf)](/documentos/Calendario-de-Homologacion-1PAO2027.pdf)
- Si el trámite consultado NO tiene un archivo específico en esta lista o en el catálogo provisto, remite a [Portal de Procesos Académicos Ikiam](https://www.ikiam.edu.ec/index.php/procesos-academicos/)."""

    user_content_text = (
        f"INFORMACIÓN INSTITUCIONAL DE REFERENCIA:\n{contexto_str}\n\n"
        f"{resumen_cognitivo}\n\n"
        f"PREGUNTA DEL ESTUDIANTE:\n{pregunta}\n\n"
        f"RESPUESTA PRECISA, COMPLETA, CON CONTACTOS OFICIALES Y CON HIPERVÍNCULOS CLICABLES EN ESPAÑOL:"
    )

    gemini_key = _get_gemini_key()
    if not gemini_key:
        logger.warning("GEMINI_API_KEY no configurada en el entorno; usando respuesta directa de base de datos.")
    else:
        for model_name in MODELS_TO_TRY:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={gemini_key}"
            payload = {
                "system_instruction": {"parts": [{"text": system_instruction_text}]},
                "contents": [{"role": "user", "parts": [{"text": user_content_text}]}],
                "generationConfig": {"temperature": 0.2, "maxOutputTokens": 2400},
            }
            try:
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    parts = data["candidates"][0]["content"]["parts"]
                    ans = "".join(p.get("text", "") for p in parts if "text" in p).strip()
                    if any(bad in ans.lower() for bad in ("format/links", "clean markdown", "no evasives", "required list")):
                        logger.warning(f"Descartada posible fuga de prompt en modelo {model_name}")
                        continue
                    if len(ans) > 20:
                        ans_html = limpiar_formato_html(ans)
                        memoria.registrar_episodio(pregunta, ans_html)
                        return {
                            "kind": "ai",
                            "html": ans_html,
                            "whatsapp_text": html_a_whatsapp(ans_html, public_base_url),
                            "flow_options": [],
                        }
            except urllib.error.HTTPError as e:
                body_err = e.read().decode("utf-8", "ignore")[:220]
                logger.warning(f"Gemini {model_name} HTTP {e.code}: {body_err}")
                continue
            except Exception as e:
                logger.warning(f"Gemini {model_name} excepción: {e}")
                continue

    # 6. Fallback estructurado con base de datos oficial
    if rows:
        r = rows[0]
        pasos_list = "".join(f"<li>{item.strip()}</li>" for item in r[2].split(". ") if item.strip())
        fallback = (
            f"<p><strong>{r[0]}:</strong></p>"
            f"<p>{r[1]}</p>"
            f"<p><strong>Requisitos y documentos:</strong></p><ul>{pasos_list}</ul>"
            f"<p>🌐 <a href='{r[3]}' target='_blank' style='color:#0d5f3a; font-weight:bold; text-decoration:underline;'>Portal Oficial Ikiam</a></p>"
        )
        memoria.registrar_episodio(pregunta, fallback)
        return {
            "kind": "fallback",
            "html": fallback,
            "whatsapp_text": html_a_whatsapp(fallback, public_base_url),
            "flow_options": [],
        }

    if info_red:
        fallback_red = "<p><strong>Información de Red Institucional Ikiam:</strong></p><ul>" + "".join(
            f"<li>{item}</li>" for item in info_red[:6]
        ) + "</ul>"
        memoria.registrar_episodio(pregunta, fallback_red)
        return {
            "kind": "fallback",
            "html": fallback_red,
            "whatsapp_text": html_a_whatsapp(fallback_red, public_base_url),
            "flow_options": [],
        }

    default_msg = (
        "Estimado/a estudiante, por favor indíquenos qué trámite académico específico desea consultar "
        "(ej. prórroga de tesis, justificación de faltas, retiro de materia, becas, prácticas o facultades/carreras) "
        "para orientarle con los requisitos oficiales."
    )
    return {
        "kind": "fallback",
        "html": default_msg,
        "whatsapp_text": default_msg,
        "flow_options": [],
    }


def responder_consulta(session_id: str, pregunta: str) -> str:
    """Interfaz compatible con el portal web (/api/chat)."""
    return responder_consulta_estructurada(session_id, pregunta)["html"]


if __name__ == "__main__":
    sid = sys.argv[1] if len(sys.argv) > 1 else "default_sid"
    msg = sys.argv[2] if len(sys.argv) > 2 else "prorroga de tesis"
    print(responder_consulta(sid, msg))
