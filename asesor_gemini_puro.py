import sys, json, sqlite3, os, urllib.request, re
from cognitive_memory_ikiam import UserCognitiveMemory

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "ikiam_knowledge.db")
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
    'vincul': 'vinculacion sociedad dvs 160',
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

def buscar_contexto_db(pregunta):
    conn = sqlite3.connect(DB_PATH)
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
    rows = []
    if terminos_list:
        q = ' OR '.join(terminos_list[:8]) + '*'
        try:
            cur.execute("SELECT titulo, contenido, documentos_requeridos, url_fuente FROM ikiam_docs WHERE ikiam_docs MATCH ? ORDER BY rank LIMIT 3", (q,))
            rows = cur.fetchall()
        except:
            pass
            
    if not rows:
        cur.execute("SELECT titulo, contenido, documentos_requeridos, url_fuente FROM ikiam_docs LIMIT 2")
        rows = cur.fetchall()
        
    conn.close()
    return rows

def limpiar_formato_html(texto):
    t = re.sub(r'```(?:html)?\s*', '', texto)
    t = t.replace('```', '')
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

    # 2. Consultar base de conocimiento de Ikiam
    rows = buscar_contexto_db(pregunta)
    contexto_str = "\n\n".join([f"TEMA: {r[0]}\nCONTENIDO OFICIAL: {r[1]}\nREQUISITOS Y DOCUMENTOS: {r[2]}\nENLACE: {r[3]}" for r in rows])
    
    # 3. Resumen cognitivo individual
    resumen_cognitivo = memoria.obtener_resumen_cognitivo()

    system_instruction_text = """Eres el asesor oficial de la Dirección Académica de la Universidad Regional Amazónica Ikiam.
Tu labor es responder consultas estudiantiles con empatía, precisión reglamentaria y en estricto español.

NORMAS OBLIGATORIAS:
- Piensa y analiza exactamente lo que el estudiante está preguntando. Responde DIRECTO al grano, de forma CONCISA, clara y estructurada.
- NUNCA respondas con evasivas como "acérquese a la oficina", "vaya al campus" o "consulte en secretaría".
- Entrega tu respuesta directamente estructurada y limpia (usa negritas y viñetas).
- Siempre que menciones un trámite, proceso o portal de Ikiam, DEBES proporcionar el hipervínculo en formato markdown [Nombre del Trámite o Sitio](URL). Nunca dejes URLs sueltas en texto plano sin enlace.
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
  - Cambio de Universidad: [Descargar Solicitud de Cambio de Universidad (.docx)](/documentos/Solicitud-de-cambio-de-universidad.docx)
  - Reingreso: [Descargar Formato de Reingreso (.docx)](/documentos/FORMATO-SOLICITUD-DE-REINGRESO.docx)
  - Calendario Nivelación: [Descargar Calendario de Nivelación (.pdf)](/documentos/Calendario-Academico-de-Nivelacion-octubre-2025-marzo-2026.pdf)
  - Calendario Homologación: [Descargar Calendario de Homologación (.pdf)](/documentos/Calendario-de-Homologacion-1PAO2027.pdf)
  - Régimen Académico CES: [Descargar Reglamento de Régimen Académico CES (.pdf)](/documentos/Reglamento-Regimen-Academico-del-Consejo-de-Educacion-Superior.pdf)
- Si el trámite consultado NO tiene un archivo específico en esta lista, remite a [Portal de Procesos Académicos Ikiam](https://www.ikiam.edu.ec/index.php/procesos-academicos/)."""

    user_content_text = f"""INFORMACIÓN INSTITUCIONAL DE REFERENCIA:
{contexto_str}

{resumen_cognitivo}

PREGUNTA DEL ESTUDIANTE:
{pregunta}

RESPUESTA PRECISA, COMPLETA Y CON HIPERVÍNCULOS CLICABLES EN ESPAÑOL:"""

    # 4. Llamada a Gemini API
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

    # 5. Fallback con base de datos oficial
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
