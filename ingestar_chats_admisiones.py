# -*- coding: utf-8 -*-
"""
Pipeline reutilizable de ingesta y curaduría de chats reales hacia `ikiam_admisiones_faq.db`.

Objetivo:
Cuando se comparta un lote futuro de historiales de chat o preguntas frecuentes reales,
este script:
1. Limpia datos personales (saludos con nombres propios, cédulas, teléfonos personales,
   IDs/claves Zoom privados, imágenes base64 y enlaces Google Forms antiguos).
2. Filtra fechas/ciclos vencidos (2024, 2025, II PA 2026) para no contaminar 1PA 2027.
3. Rechaza temas estrictamente de estudiantes regulares / ajenos a Admisión
   (3ra matrícula, prórroga de tesis, retiro de materia, compras públicas).
4. Agrupa preguntas similares contra la base existente, incrementa `frecuencia` cuando ya
   están cubiertas o inserta nuevas FAQs curadas en `admisiones_faq` + `admisiones_faq_fts`.

Uso CLI:
    python ingestar_chats_admisiones.py "<ruta_archivo.md|.txt|.json|.jsonl|.csv>" --lote "chats_nov_2026" --dry-run
    python ingestar_chats_admisiones.py "<ruta_archivo>" --lote "chats_nov_2026"
"""

import argparse
import csv
import difflib
import html as html_lib
import json
import os
import re
import sqlite3
from typing import Dict, List, Tuple

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "ikiam_admisiones_faq.db")

# Temas exclusivos de carrera avanzada o administrativos que NO corresponden a /admisiones/
PATRONES_FUERA_DE_ADMISION = (
    "tercera matricula", "3era matricula", "prorroga de tesis", "examen complexivo",
    "retiro de materia", "retiro voluntario", "reingreso", "justificar falta",
    "justificacion de faltas", "practicas preprofesionales", "fo-gvi", "fo-gbu",
    "compras publicas", "sercop", "licitacion", "matricula de ingles", "cruce de horarios",
    "cultura fisica", "certificado en secretaria", "homologacion de materias",
    "maestrias disponibles", "posgrados",
)

# Ciclos caducados o links temporales antiguos a bloquear si aparecen en respuestas
PATRONES_CADUCADOS = (
    "2024", "2025", "ii pa 2026", "2pa 2026", "2/6/2026", "11 de marzo",
    "8 de abril", "08 de abril", "28 de abril", "7 de noviembre", "11 de noviembre",
    "14 de septiembre", "19 de marzo", "19 al 30 de agosto", "24 al 26 de marzo",
    "mes de agosto", "mes de junio", "ultima semana de septiembre",
    "tiene 9 carreras", "9 carreras", "gancho inicial", "killer facts", "dossier de prensa",
    "forms.gle/", "docs.google.com/forms", "passcode:", "meeting id:", "maria.hernandez@",
)

SALUDO_PII_RE = re.compile(
    r"(?im)^(?:estimad[oa]/a?|estimad[oa]|buen[oa]s?\s+(?:d[ií]as?|tardes?|noches?)|hola)(?:\s+[A-ZÁÉÍÓÚÑa-záéíóúñ/]+){0,3}[,\s:]*(?:esperamos te encuentres[^,\n]*[,\s]*)?"
)
CORREO_NO_IKIAM_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@(?!ikiam\.edu\.ec\b)[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
CEDULA_RE = re.compile(r"\b\d{10}\b")
BASE64_IMG_RE = re.compile(r"\[[^\]]+\]:\s*<data:image/[^>]+>")


def limpiar_pii_texto(texto: str) -> str:
    t = BASE64_IMG_RE.sub("", texto or "")
    t = re.sub(r"!\[[^\]]*\]\[[^\]]*\]", "", t)
    t = re.sub(r"https?://(?:[\w.-]*\.)?zoom\.us/[^\s\)]+", "[Enlace Zoom institucional]", t, flags=re.I)
    t = SALUDO_PII_RE.sub("", t)
    t = re.sub(r"(?im)^saludos(?:\s+cordiales)?[,\s!.]*$", "", t)
    t = CORREO_NO_IKIAM_RE.sub("[correo-externo]", t)
    t = CEDULA_RE.sub("[cédula]", t)
    t = re.sub(r"[\U00010000-\U0010ffff\u2600-\u27bf\ufe0f\u20e3]", "", t)
    t = re.sub(r"\\([._\-\\/#&])", r"\1", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def normalizar_pregunta(q: str) -> str:
    s = re.sub(r"[^\w\sáéíóúñü]", " ", (q or "").lower())
    return re.sub(r"\s+", " ", s).strip()


def es_valido_para_admisiones(pregunta: str, respuesta: str) -> Tuple[bool, str]:
    q_low = normalizar_pregunta(pregunta)
    r_low = (respuesta or "").lower()
    if len(q_low) < 6 or len(respuesta.strip()) < 15:
        return False, "vacio_o_muy_corto"
    combined = f"{q_low} {r_low}"
    if any(p in combined for p in PATRONES_FUERA_DE_ADMISION):
        return False, "fuera_de_admision"
    if any(p in r_low for p in PATRONES_CADUCADOS):
        return False, "ciclo_o_enlace_caducado"
    return True, "ok"


def parsear_archivo_fuente(path: str) -> List[Tuple[str, str]]:
    """Lee pares (pregunta, respuesta) desde JSON, JSONL, CSV o Markdown estructurado."""
    ext = os.path.splitext(path)[1].lower()
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        raw = f.read()

    pares: List[Tuple[str, str]] = []
    if ext == ".json":
        data = json.loads(raw)
        items = data if isinstance(data, list) else data.get("preguntas", [])
        for it in items:
            if isinstance(it, dict):
                q = it.get("pregunta") or it.get("question") or it.get("user") or ""
                a = it.get("respuesta") or it.get("answer") or it.get("assistant") or ""
                pares.append((str(q), str(a)))
    elif ext == ".jsonl":
        for line in raw.splitlines():
            if not line.strip():
                continue
            it = json.loads(line)
            q = it.get("pregunta") or it.get("question") or it.get("user") or ""
            a = it.get("respuesta") or it.get("answer") or it.get("assistant") or ""
            pares.append((str(q), str(a)))
    elif ext == ".csv":
        reader = csv.DictReader(raw.splitlines())
        for row in reader:
            q = row.get("pregunta") or row.get("question") or ""
            a = row.get("respuesta") or row.get("answer") or ""
            pares.append((str(q), str(a)))
    else:
        # Markdown / Texto con bloques "**Pregunta**" o "1. **Pregunta**"
        raw_clean = BASE64_IMG_RE.sub("", raw)
        bloques = re.split(r"\n(?=(?:\d+\.\s*)?\*\*[^*\n]{8,160}\*\*)", raw_clean)
        for bl in bloques:
            m = re.match(r"^(?:\d+\.\s*)?\*\*([^*\n]{8,160})\*\*\s*\n+(.*)$", bl.strip(), flags=re.S)
            if m:
                pares.append((m.group(1).strip(), m.group(2).strip()))
    return pares


_STOPWORDS_Q = {
    "cual", "cuál", "cuales", "cuáles", "como", "cómo", "cuando", "cuándo", "donde",
    "dónde", "para", "sobre", "tiene", "puedo", "hacer", "cual", "es", "el", "la",
    "los", "las", "del", "de", "en", "una", "uno", "que", "qué", "ikiam", "fecha", "fechas",
}


def _similitud_pregunta(a_norm: str, b_norm: str) -> float:
    seq = difflib.SequenceMatcher(None, a_norm, b_norm).ratio()
    tok_a = {w for w in a_norm.split() if len(w) >= 4 and w not in _STOPWORDS_Q}
    tok_b = {w for w in b_norm.split() if len(w) >= 4 and w not in _STOPWORDS_Q}
    jac = (len(tok_a & tok_b) / len(tok_a | tok_b)) if (tok_a and tok_b) else 0.0
    return max(seq, jac)


def ingestar_pares(
    pares: List[Tuple[str, str]],
    lote: str,
    fuente: str,
    db_path: str = DB_PATH,
    dry_run: bool = False,
) -> Dict[str, int]:
    """Limpia, deduplica y carga pares (pregunta, respuesta) en `ikiam_admisiones_faq.db`."""
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"No existe {db_path}. Ejecuta primero construir_admisiones_faq.py")

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    existentes = cur.execute(
        "SELECT id, slug, pregunta_canonica, variantes_pregunta FROM admisiones_faq"
    ).fetchall()

    stats = {"total": len(pares), "aceptadas": 0, "actualizadas": 0, "descartadas": 0}
    nuevas_vistas: List[Tuple[int, str, str]] = list(
        (row[0], normalizar_pregunta(row[2]), row[3]) for row in existentes
    )

    for q_raw, a_raw in pares:
        q_clean = limpiar_pii_texto(q_raw)
        a_clean = limpiar_pii_texto(a_raw)
        ok, _ = es_valido_para_admisiones(q_clean, a_clean)
        if not ok:
            stats["descartadas"] += 1
            continue

        q_norm = normalizar_pregunta(q_clean)
        mejor_id = None
        mejor_sim = 0.0
        for row_id, ex_norm, ex_vars in nuevas_vistas:
            sim = _similitud_pregunta(q_norm, ex_norm)
            if sim > mejor_sim:
                mejor_sim = sim
                mejor_id = row_id
            for v in (ex_vars or "").split("|"):
                s2 = _similitud_pregunta(q_norm, normalizar_pregunta(v))
                if s2 > mejor_sim:
                    mejor_sim = s2
                    mejor_id = row_id

        if mejor_sim >= 0.60 and mejor_id is not None:
            stats["actualizadas"] += 1
            if not dry_run:
                cur.execute("UPDATE admisiones_faq SET frecuencia = frecuencia + 1 WHERE id = ?", (mejor_id,))
        else:
            stats["aceptadas"] += 1
            if not dry_run:
                slug = "chat_" + re.sub(r"[^a-z0-9]+", "_", q_norm)[:48].strip("_")
                suffix = 1
                base_slug = slug
                while cur.execute("SELECT 1 FROM admisiones_faq WHERE slug = ?", (slug,)).fetchone():
                    suffix += 1
                    slug = f"{base_slug}_{suffix}"
                esc_q = html_lib.escape(q_clean)
                esc_a = "<br>".join(html_lib.escape(ln) for ln in a_clean.splitlines() if ln.strip())
                resp_html = (
                    f"<div style='border-left:3px solid #0d5f3a; padding-left:10px;'>"
                    f"<div style='color:#0d5f3a; font-weight:700; font-size:12.5px; margin:0 0 4px;'>{esc_q}</div>"
                    f"<p style='font-size:12px; line-height:1.45; color:#374151; margin:0;'>{esc_a}</p></div>"
                )
                kw = ", ".join([w for w in q_norm.split() if len(w) > 3][:8])
                cur.execute("""
                    INSERT INTO admisiones_faq (
                        slug, categoria, boton_etiqueta, boton_descripcion,
                        pregunta_canonica, variantes_pregunta, respuesta_html,
                        respuesta_texto, palabras_clave, ciclo_vigencia,
                        frecuencia, es_menu_principal, fuente
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    slug, "Chat Histórico Curado", q_clean[:70], "Pregunta frecuente validada de soporte",
                    q_clean, q_clean, resp_html, a_clean, kw, "PERENNE", 1, 0, fuente
                ))
                new_id = cur.lastrowid
                cur.execute("""
                    INSERT INTO admisiones_faq_fts (slug, categoria, pregunta_canonica, variantes_pregunta, respuesta_texto, palabras_clave)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (slug, "Chat Histórico Curado", q_clean, q_clean, a_clean, kw))
                nuevas_vistas.append((new_id, q_norm, q_clean))

    if not dry_run:
        cur.execute("""
            INSERT INTO admisiones_ingesta_log (lote, archivo_fuente, total_entradas, aceptadas, actualizadas, descartadas)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (lote, os.path.basename(fuente), stats["total"], stats["aceptadas"], stats["actualizadas"], stats["descartadas"]))
        conn.commit()
    conn.close()
    return stats


def main():
    parser = argparse.ArgumentParser(description="Ingesta saneada de chats reales para Admisiones Ikiam")
    parser.add_argument("archivo", help="Ruta al archivo (.md, .txt, .json, .jsonl, .csv)")
    parser.add_argument("--lote", default="lote_manual", help="Identificador de lote")
    parser.add_argument("--dry-run", action="store_true", help="Simular sin escribir en la base SQLite")
    args = parser.parse_args()

    pares = parsear_archivo_fuente(args.archivo)
    res = ingestar_pares(pares, lote=args.lote, fuente=args.archivo, dry_run=args.dry_run)
    print(json.dumps({"dry_run": args.dry_run, "lote": args.lote, **res}, ensure_ascii=False))


if __name__ == "__main__":
    main()
