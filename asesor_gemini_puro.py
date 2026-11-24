# -*- coding: utf-8 -*-
"""
Motor Conversacional Asesor Gemini Puro para Ikiam
Integra:
1. ikiam_flows.db: Flujos de decision y opciones predeterminadas interactivas.
2. ikiam_network_org.db: Red institucional de dependencias, coordinaciones de carrera y correos oficiales.
3. ikiam_catalog_docs.db: Catalogo oficial de 175 documentos indexados.
4. ikiam_knowledge.db: Base normativa historica.
"""

import sys
import json
import sqlite3
import os
import urllib.request
import re
from cognitive_memory_ikiam import UserCognitiveMemory

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_KNOWLEDGE = os.path.join(BASE_DIR, "ikiam_knowledge.db")
DB_CATALOG = os.path.join(BASE_DIR, "ikiam_catalog_docs.db")
DB_NETWORK = os.path.join(BASE_DIR, "ikiam_network_org.db")
DB_FLOWS = os.path.join(BASE_DIR, "ikiam_flows.db")
DOCS_DIR = os.path.join(BASE_DIR, "documentos_oficiales")
ARCHIVOS_REALES = set(os.listdir(DOCS_DIR)) if os.path.exists(DOCS_DIR) else set()

GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
MODELS_TO_TRY = ['gemini-3.5-flash-lite', 'gemini-flash-lite-latest', 'gemini-3-flash-preview']

LEMAS_EXPANSION = {
    'falt': 'falta inasistencia ausencias',
    'ausen': 'inasistencia falta',
    'asist': 'asistencia faltas 70',
    'seman': 'semana inasistencias horas',
    'famili': 'calamidad domestica familiar justificacion',
    'justifi': 'justificar justificacion certificados',
    'enferm': 'medico salud justificacion reposo',
    'dengu': 'salud medico hospital justificacion',
    'reprob': 'reprobar perder asistencia notas',
    'perd': 'perder reprobar materia carrera prorroga',
    'practic': 'practicas laborales tutor fo-gvi',
    'vincul': 'vinculacion sociedad dvs 160 400',
    'homolog': 'homologacion convalidacion cambio 80',
    'cambi': 'cambio carrera universidad modalidad complexivo',
    'bec': 'beca ayudas bienestar fo-gbu',
    'titul': 'titulacion grado tesis complexivo prorroga vencimiento',
    'tesis': 'tesis prorroga complexivo titulacion grado vencimiento',
    'prorrog': 'prorroga plazo vencimiento tesis complexivo extension gracia segunda tercera',
    'venc': 'vencimiento prorroga plazo gracia caducidad',
    'complexiv': 'complexivo examen grado modalidad tesis',
    'ingl': 'ingles b1 idiomas suficiencia',
    'matricul': 'matricula tercera especial retiro',
    'supletor': 'supletorio calificacion nota 7',
    'pago': 'aranceles cobro pagos perdida gratuidad materias segunda tercera',
    'pagar': 'aranceles cobro pagos perdida gratuidad materias',
    'cobr': 'aranceles cobro pagos perdida gratuidad',
    'arancel': 'aranceles cobro pagos perdida gratuidad tabla',
    'gratuidad': 'gratuidad perdida aranceles pagos segunda loes ces',
    'tabla': 'tabla arancelaria pagos cobro aranceles'
}

def consultar_caso_red(codigo_caso):
    """Obtiene la ficha oficial estructurada de un caso desde ikiam_network_org.db"""
    if not os.path.exists(DB_NETWORK):
        return None
    try:
        conn = sqlite3.connect(DB_NETWORK)
        cur = conn.cursor()
        cur.execute("""
            SELECT c.documento_archivo, c.nombre_tramite, c.perfil_estudiante,
                   c.descripcion_caso, c.dependencia_id, c.autoridad_destinataria,
                   c.correo_destino, c.plazo_reglamentario, c.requisitos_adjuntos,
                   c.pasos_procedimiento, c.enlace_descarga, d.nombre as nombre_dep
            FROM casos_tramite_red c
            LEFT JOIN dependencias d ON c.dependencia_id = d.id
            WHERE c.codigo_caso = ? OR c.id = ?
        """, (codigo_caso, codigo_caso))
        row = cur.fetchone()
        
        # Obtener lista de coordinaciones de carrera si el caso involucra coordinacion
        coordinaciones = []
        if row and ('coordinacion' in row[4].lower() or 'coordinacion' in row[6].lower()):
            cur.execute("SELECT carrera, correo_coordinacion FROM coordinaciones_carrera ORDER BY carrera")
            coordinaciones = cur.fetchall()
            
        conn.close()
        return (row, coordinaciones) if row else None
    except Exception as e:
        print(f"Error consultando caso red: {e}")
        return None

def formatear_respuesta_caso(row, coordinaciones):
    """Construye HTML estilizado para la ficha del caso seleccionado"""
    doc_archivo, nombre_tramite, perfil, desc, dep_id, autoridad, correo_dest, plazo, reqs, pasos, enlace, nom_dep = row
    
    # Preparar enlace de descarga
    enlace_html = ""
    if doc_archivo and doc_archivo in ARCHIVOS_REALES:
        enlace_html = f"<div style='margin: 12px 0;'><a href='/documentos/{doc_archivo}' target='_blank' style='display:inline-block; background-color:#0d5f3a; color:#ffffff; padding:10px 16px; border-radius:6px; font-weight:bold; text-decoration:none;'>📥 Descargar Formato Oficial (.docx)</a></div>"
    elif enlace and enlace.startswith('http'):
        enlace_html = f"<div style='margin: 12px 0;'><a href='{enlace}' target='_blank' style='display:inline-block; background-color:#0d5f3a; color:#ffffff; padding:10px 16px; border-radius:6px; font-weight:bold; text-decoration:none;'>🌐 Ir al Portal Oficial</a></div>"

    # Preparar correos
    correos_html = ""
    if coordinaciones and ('coordinacion' in dep_id.lower() or 'coordinacion' in correo_dest.lower()):
        correos_html = "<div style='background-color:#f0fdf4; border:1px solid #bbf7d0; padding:10px; border-radius:6px; margin:10px 0;'><strong style='color:#0d5f3a;'>📍 Correos Oficiales de Coordinación según tu Carrera:</strong><ul style='margin:6px 0 0 18px; padding:0;'>"
        for carr, email in coordinaciones:
            correos_html += f"<li><strong>{carr}:</strong> <a href='mailto:{email}' style='color:#0d5f3a; font-weight:bold;'>{email}</a></li>"
        correos_html += "</ul></div>"
    else:
        emails_list = [e.strip() for e in correo_dest.split('y')]
        enlaces_email = " y ".join([f"<a href='mailto:{em}' style='color:#0d5f3a; font-weight:bold; text-decoration:underline;'>{em}</a>" for em in emails_list])
        correos_html = f"<p style='margin:4px 0;'><strong>📬 Correo(s) Oficial(es) de Recepción:</strong> {enlaces_email}</p>"

    # Formatear requisitos en viñetas
    req_items = [r.strip() for r in reqs.split(',') if r.strip()]
    req_html = "".join([f"<li>{r}</li>" for r in req_items])

    # Formatear pasos respetando puntos y correos electronicos
    paso_items = [p.strip() for p in re.split(r'\s*\d+\.\s*', pasos) if p.strip()]
    pasos_html = "".join([f"<li>{p}</li>" for p in paso_items])

    html = f"""<div style='border-left:4px solid #0d5f3a; padding-left:12px; margin-bottom:12px;'>
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
    return html

def evaluar_flujo_guiado(pregunta):
    """Verifica si la pregunta coincide con un flujo general guiado y genera los botones interactivos"""
    if not os.path.exists(DB_FLOWS):
        return None
        
    p_low = pregunta.lower().strip()
    try:
        conn = sqlite3.connect(DB_FLOWS)
        cur = conn.cursor()
        cur.execute("SELECT id, titulo_guia, saludo_cordial, mensaje_orientador, opciones_json, palabras_clave FROM flujos_decision")
        filas = cur.fetchall()
        conn.close()

        for f_id, titulo, saludo, msg_orientador, opciones_json, keywords in filas:
            claves = [k.strip() for k in keywords.split(',') if k.strip()]
            coincide = False
            for c in claves:
                # Coincidencia por palabra clave completa o frase
                if c in p_low:
                    coincide = True
                    break
            
            if coincide:
                opciones = json.loads(opciones_json)
                botones_html = "<div class='opciones-guiadas-grid' style='display:flex; flex-direction:column; gap:8px; margin:14px 0;'>"
                for opc in opciones:
                    c_caso = opc.get("codigo_caso", "")
                    etiqueta = opc.get("etiqueta", "")
                    desc = opc.get("descripcion", "")
                    botones_html += f"""<button class='btn-opcion-guia' onclick='seleccionarOpcionCaso("{c_caso}", "{etiqueta}")' style='text-align:left; background:#ffffff; border:1.5px solid #0d5f3a; color:#0d5f3a; padding:10px 14px; border-radius:8px; cursor:pointer; font-weight:600; font-size:13.5px; transition:all 0.2s;'>
  <div style='font-size:14px;'>{etiqueta}</div>
  <div style='font-size:11.5px; color:#4b5563; font-weight:normal; margin-top:2px;'>{desc}</div>
</button>"""
                botones_html += "</div>"

                respuesta = f"""<p><strong>{saludo}</strong></p>
<p>{msg_orientador}</p>
{botones_html}
<p style='font-size:12px; color:#6b7280; font-style:italic;'>💡 Haz clic sobre tu caso particular para ver los requisitos, correo de entrega y formulario oficial.</p>"""
                return respuesta
    except Exception as e:
        print(f"Error evaluando flujo guiado: {e}")
        return None
    return None

def buscar_contexto_db(pregunta):
    """Consulta las bases de datos para armar el contexto relevante"""
    rows = []
    
    # 1. ikiam_knowledge.db
    if os.path.exists(DB_KNOWLEDGE):
        conn = sqlite3.connect(DB_KNOWLEDGE)
        cur = conn.cursor()
        stop_words = {'que', 'por', 'para', 'con', 'los', 'las', 'una', 'del', 'como', 'cuando', 'donde', 'cual', 'cuales', 'puedo', 'hacer', 'tener', 'hola', 'buenas', 'dime', 'esto', 'esta'}
        clean = re.sub(r'[^\w\s]', ' ', pregunta.lower())
        palabras = [w for w in clean.split() if len(w) > 2 and w not in stop_words]
        
        terminos_busqueda = set()
        for w in palabras:
            terminos_busqueda.add(w)
            for raiz, expansion in LEMAS_EXPANSION.items():
                if w.startswith(raiz):
                    for exp in expansion.split():
                        terminos_busqueda.add(exp)
                        
        terminos_list = list(terminos_busqueda)
        if terminos_list:
            condiciones = " OR ".join(["tema LIKE ? OR contenido LIKE ? OR requisitos LIKE ?" for _ in terminos_list])
            params = []
            for t in terminos_list:
                params.extend([f"%{t}%", f"%{t}%", f"%{t}%"])
            
            cur.execute(f"""
                SELECT tema, contenido, requisitos, enlace,
                (CASE WHEN tema LIKE '%{palabras[0] if palabras else ""}%' THEN 5 ELSE 0 END) as score
                FROM normativas_ikiam
                WHERE {condiciones}
                ORDER BY score DESC, id ASC
                LIMIT 4
            """, params)
            rows = cur.fetchall()
        conn.close()

    # 2. ikiam_network_org.db (obtener contactos y casos pertinentes)
    info_red = []
    if os.path.exists(DB_NETWORK):
        conn = sqlite3.connect(DB_NETWORK)
        cur = conn.cursor()
        p_low = pregunta.lower()
        if 'retiro' in p_low or 'retirarme' in p_low:
            cur.execute("SELECT titulo_caso, autoridad_destinataria, correo_destino, plazo_reglamentario FROM casos_tramite_red WHERE codigo_caso LIKE 'retiro%'")
            info_red.extend([f"TRÁMITE: {r[0]} | AUTORIDAD: {r[1]} | CORREO: {r[2]} | PLAZO: {r[3]}" for r in cur.fetchall()])
        elif 'ingres' in p_low or 'admision' in p_low:
            cur.execute("SELECT titulo_caso, autoridad_destinataria, correo_destino, plazo_reglamentario FROM casos_tramite_red WHERE codigo_caso LIKE 'ingreso%'")
            info_red.extend([f"TRÁMITE: {r[0]} | AUTORIDAD: {r[1]} | CORREO: {r[2]} | PLAZO: {r[3]}" for r in cur.fetchall()])
        elif 'falt' in p_low or 'inasist' in p_low:
            cur.execute("SELECT titulo_caso, autoridad_destinataria, correo_destino, plazo_reglamentario FROM casos_tramite_red WHERE codigo_caso LIKE 'justificacion%'")
            info_red.extend([f"TRÁMITE: {r[0]} | AUTORIDAD: {r[1]} | CORREO: {r[2]} | PLAZO: {r[3]}" for r in cur.fetchall()])
        conn.close()

    return rows, info_red

def limpiar_formato_html(texto):
    t = texto.strip()
    t = re.sub(r'```(?:html)?\s*', '', t)
    t = t.replace('```', '')
    
    # Titulos markdown
    t = re.sub(r'###\s*(.*?)\n', r'<h4 style="color:#0d5f3a; margin-top:12px; margin-bottom:6px;">\1</h4>', t)
    t = re.sub(r'##\s*(.*?)\n', r'<h3 style="color:#0d5f3a; margin-top:14px; margin-bottom:6px;">\1</h3>', t)
    
    # Viñetas
    lines = t.split('\n')
    in_list = False
    out_lines = []
    for line in lines:
        s_line = line.strip()
        if s_line.startswith('* ') or s_line.startswith('- '):
            if not in_list:
                out_lines.append('<ul style="margin-top:4px; margin-bottom:8px; padding-left:20px;">')
                in_list = True
            content = s_line[2:].strip()
            out_lines.append(f"<li>{content}</li>")
        else:
            if in_list:
                out_lines.append('</ul>')
                in_list = False
            out_lines.append(line)
    if in_list:
        out_lines.append('</ul>')
    t = '\n'.join(out_lines)
    
    t = t.replace('\n\n', '<br><br>').replace('\n', '<br>')
    t = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', t)
    
    def repl_md(m):
        txt, url = m.group(1), m.group(2)
        if url.startswith('/documentos/'):
            fname = os.path.basename(url)
            if fname in ARCHIVOS_REALES:
                return f"<a href='/documentos/{fname}' target='_blank' style='color:#0d5f3a; font-weight:bold; text-decoration:underline;'>{txt}</a>"
            else:
                return f"{txt} (gestión en el <a href='https://www.ikiam.edu.ec/index.php/procesos-academicos/' target='_blank' style='color:#0d5f3a; font-weight:bold; text-decoration:underline;'>Portal de Procesos Académicos Ikiam</a>)"
        return f"<a href='{url}' target='_blank' style='color:#0d5f3a; font-weight:bold; text-decoration:underline;'>{txt}</a>"
        
    t = re.sub(r'\[([^\]]+)\]\((https?://[^\s\)]+|/[^\s\)]+)\)', repl_md, t)
    
    def repl_url(m):
        return f"<a href='{m.group(0)}' target='_blank' style='color:#0d5f3a; font-weight:bold; text-decoration:underline;'>{m.group(0)}</a>"
    t = re.sub(r'(?<![\'\"=])(https?://[^\s<]+)', repl_url, t)
    
    t = t.replace('<ul><br>', '<ul>').replace('</ul><br>', '</ul>')
    t = t.replace('<br><ul>', '<ul>').replace('<br><li>', '<li>')
    return t.strip()

def extraer_hechos_automaticos(memoria: UserCognitiveMemory, pregunta: str):
    p_low = pregunta.lower()
    if ('prorroga' in p_low or 'tesis' in p_low or 'complexivo' in p_low) and any(w in p_low for w in ['venci', 'caduc', 'perdi', 'plazo', 'gracia', 'segunda', 'tercera', 'tiempo']):
        memoria.actualizar_hecho("situacion_titulacion", "Estudiante reporta dificultades con plazos o prórrogas en su proceso de titulación.")
        memoria.registrar_monologo("El estudiante indica vencimiento o apuro en plazos de grado. Orientarlo con los requisitos de cambio a complexivo o solicitud de gracia.")
    elif ('dengue' in p_low or 'hospital' in p_low or 'enfermo' in p_low or 'medico' in p_low) and any(w in p_low for w in ['estoy', 'tengo', 'falte', 'estuve', 'estube', 'grave', 'reposo']):
        memoria.actualizar_hecho("salud", "Estudiante reportó hospitalización o enfermedad médica personal.")
        memoria.registrar_monologo("El estudiante tiene una situación médica real. Priorizar su bienestar y orientarlo con la ruta de excepción por fuerza mayor sin exigirle trámites presenciales inmediatos.")
    elif ('familiar' in p_low or 'familiares' in p_low or 'calamidad' in p_low) and any(w in p_low for w in ['falleci', 'murio', 'enfermo', 'problema', 'urgencia']):
        memoria.actualizar_hecho("situacion_personal", "Reporta faltas o atrasos por problemas familiares o calamidad doméstica.")
        memoria.registrar_monologo("No tiene certificado médico por ser tema familiar. Orientarlo a dialogar con docentes y presentar carta motivada a Coordinación para reprogramar evaluaciones.")
    elif any(w in p_low for w in ['homologar', 'convalidar', 'uce', 'epn']) and any(w in p_low for w in ['vengo', 'cambiarme', 'estudio en', 'estudiaba']):
        memoria.actualizar_hecho("origen_academico", "Interesado en homologación externa proveniente de otra universidad.")
        memoria.registrar_monologo("Aspirante o estudiante en homologación. Recordar fechas de diciembre (1 al 18), 80% de similitud y los 6 documentos de la carta a Vicerrectorado.")

def responder_consulta(session_id, pregunta):
    low = pregunta.lower().strip()
    memoria = UserCognitiveMemory(session_id)
    extraer_hechos_automaticos(memoria, pregunta)
    
    # 1. Filtro estricto: Compras Públicas / SERCOP
    if any(k in low for k in ['compras publicas', 'sercop', 'licitacion', 'contratos proveedores', 'proveedor']):
        ans_filtro = "Estimado/a usuario/a:<br><br>Le recordamos que este canal pertenece exclusivamente a la <strong>Dirección Académica</strong> de Ikiam (procesos estudiantiles de pregrado: homologaciones, cambios de carrera, titulación, matrículas y prácticas).<br><br>Para procesos de <strong>Compras Públicas o Licitaciones</strong>, por favor consulte a la Dirección Administrativa en el portal institucional: <a href='https://www.ikiam.edu.ec/index.php/procedimientos-de-licitacion/' target='_blank' style='color:#0d5f3a; font-weight:bold; text-decoration:underline;'>Procedimientos de Licitación Ikiam</a>."
        memoria.registrar_episodio(pregunta, ans_filtro)
        return ans_filtro

    # 2. EVALUACIÓN DE CASO ESPECÍFICO DE LA RED (Si el usuario hizo clic en un botón o dio un código de caso)
    codigo_limpio = low.replace('caso:', '').strip()
    caso_res = consultar_caso_red(codigo_limpio)
    if caso_res:
        row, coords = caso_res
        ans_caso = formatear_respuesta_caso(row, coords)
        memoria.registrar_episodio(pregunta, ans_caso)
        return ans_caso

    # 3. EVALUACIÓN DE FLUJO GENERAL GUIADO (Árbol de Decisión con Botones Interactivos)
    flujo_ans = evaluar_flujo_guiado(pregunta)
    if flujo_ans:
        memoria.registrar_episodio(pregunta, flujo_ans)
        return flujo_ans

    # 4. CONSULTA ABIERTA / CASOS COMPLEJOS: Conectar RAG Multi-DB y Gemini
    rows, info_red = buscar_contexto_db(pregunta)
    contexto_str = "\n\n".join([f"TEMA: {r[0]}\nCONTENIDO OFICIAL: {r[1]}\nREQUISITOS Y DOCUMENTOS: {r[2]}\nENLACE: {r[3]}" for r in rows])
    if info_red:
        contexto_str += "\n\nRED INSTITUCIONAL Y CONTACTOS OFICIALES:\n" + "\n".join(info_red)
        
    resumen_cognitivo = memoria.obtener_resumen_cognitivo()

    system_instruction_text = """Eres el asesor oficial de la Dirección Académica de la Universidad Regional Amazónica Ikiam.
Tu labor es responder consultas estudiantiles con empatía, precisión reglamentaria y en estricto español.

NORMAS OBLIGATORIAS:
- Responde DIRECTO al grano, con tono cordial, empático y estructurado (negritas y viñetas).
- NUNCA respondas con evasivas como "acérquese a la oficina", "vaya al campus" o "consulte en secretaría".
- Siempre que menciones un trámite o formulario de Ikiam, DEBES proporcionar el hipervínculo en formato markdown [Nombre](URL).
- Siempre indica con claridad a qué autoridad y a qué correo institucional debe remitirse la solicitud.
- REGLA ESTRICTA DE DOCUMENTOS: SOLO puedes proporcionar enlaces a documentos que REALMENTE existan en el repositorio oficial.
  LISTA EXCLUSIVA DE DOCUMENTOS OFICIALES DISPONIBLES:
  - Justificación de Faltas: [Descargar Formulario de Justificación (.docx)](/documentos/Formato-Solicitud-Justificacion-Inasistencias.docx)
  - Retiro de Asignaturas: [Descargar Solicitud de Retiro Voluntario (.docx)](/documentos/Formato-Solicitud-Retiro-Voluntario-Asignatura.docx) y portal [Portal de Procesos Académicos Ikiam](https://www.ikiam.edu.ec/index.php/procesos-academicos/)
  - Becas: [Descargar Formato FO-GBU-40 Solicitud de Becas (.docx)](/documentos/FO-GBU-40-V.5.0-Solicitud-de-becas-1.docx)
  - Ayudas Económicas: [Descargar Formato FO-GBU-56 (.docx)](/documentos/FO-GBU-56-V.1.1Solicitud-de-ayudas-economicas-2.docx)
  - Prácticas Preprofesionales: [Descargar Formato FO-GVI-29 Solicitud de Prácticas (.docx)](/documentos/FO-GVI-29-V.3.1-Solicitud-para-realizar-practicas-preprofesionales.docx)
  - Planificación de Prácticas: [Descargar Planificación FO-GVI-04 (.docx)](/documentos/FO-GVI-04-V.3.1-Planificacion-de-practicas-preprofesionales-pregrado.docx)
  - Certificado de Prácticas: [Descargar Solicitud Certificado FO-GVI-30 (.docx)](/documentos/FO-GVI-30-V.2.0-Solicitud-de-certificado-de-practicas-preprofesionales-2.docx)
  - Cambio de Carrera: [Descargar Solicitud de Cambio de Carrera (.docx)](/documentos/Solicitud-de-cambio-de-carrera.docx)
  - Cambio de Universidad / Admisión Extranjera: [Descargar Solicitud de Cambio de Universidad (.docx)](/documentos/Solicitud-de-cambio-de-universidad.docx)
  - Reingreso: [Descargar Formato de Reingreso (.docx)](/documentos/FORMATO-SOLICITUD-DE-REINGRESO.docx)
  - Calendario Homologación: [Descargar Calendario de Homologación (.pdf)](/documentos/Calendario-de-Homologacion-1PAO2027.pdf)
- Si el trámite consultado NO tiene un archivo específico en esta lista, remite a [Portal de Procesos Académicos Ikiam](https://www.ikiam.edu.ec/index.php/procesos-academicos/)."""

    user_content_text = f"""INFORMACIÓN INSTITUCIONAL DE REFERENCIA:
{contexto_str}

{resumen_cognitivo}

PREGUNTA DEL ESTUDIANTE:
{pregunta}

RESPUESTA PRECISA, COMPLETA, CON CONTACTOS OFICIALES Y CON HIPERVÍNCULOS CLICABLES EN ESPAÑOL:"""

    for model_name in MODELS_TO_TRY:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_KEY}"
        payload = {
            "system_instruction": {
                "parts": [{"text": system_instruction_text}]
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_content_text}]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 3500
            }
        }
        try:
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=14) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                parts = data["candidates"][0]["content"]["parts"]
                ans = "".join([p.get("text", "") for p in parts if "text" in p]).strip()
                if any(bad in ans.lower() for bad in ['format/links', 'clean markdown', 'no evasives', 'required list']):
                    continue
                if len(ans) > 20:
                    ans_html = limpiar_formato_html(ans)
                    memoria.registrar_episodio(pregunta, ans_html)
                    return ans_html
        except Exception:
            continue

    # Fallback con base de datos oficial
    if rows:
        r = rows[0]
        fallback = f"<p><strong>{r[0]}:</strong></p><p>{r[1]}</p><p><strong>Requisitos y pasos:</strong></p><ul><li>" + r[2].replace(". ", "</li><li>") + "</li></ul>"
        memoria.registrar_episodio(pregunta, fallback)
        return fallback

    return "Estimado/a estudiante, por favor indíquenos qué trámite académico específico desea consultar para orientarle detalladamente con los requisitos oficiales."

if __name__ == "__main__":
    sid = sys.argv[1] if len(sys.argv) > 1 else "default_sid"
    msg = sys.argv[2] if len(sys.argv) > 2 else "practicas preprofesionales"
    print(responder_consulta(sid, msg))
