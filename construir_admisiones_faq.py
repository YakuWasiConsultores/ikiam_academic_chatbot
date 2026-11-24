# -*- coding: utf-8 -*-
"""
Constructor de la base de datos dedicada exclusiva para Admisiones Ikiam:
`ikiam_admisiones_faq.db`

Fuentes oficiales auditadas y depuradas:
1. Portal en vivo `https://www.ikiam.edu.ec/index.php/admisiones/` (Proceso 1PA 2027,
   3 Facultades / 10 Carreras, puntajes referenciales y cupos IIS-2026).
2. Preguntas frecuentes oficiales depuradas de PII, credenciales Zoom caducadas y
   cronogramas cerrados (2024 / II PA 2026).
"""

import os
import re
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "ikiam_admisiones_faq.db")

CRONOGRAMA_1PA_2027 = [
    (1, "Registro Nacional (1ra Etapa)", "2026-11-24", "2026-11-28", "Obligatorio en plataforma SENESCYT para aspirantes a educación superior pública."),
    (2, "Registro Nacional (2da Etapa)", "2026-12-01", "2026-12-05", "Segunda ventana oficial de Registro Nacional SENESCYT."),
    (3, "Inscripción Institucional Ikiam", "2026-12-18", "2027-01-24", "En https://eval.ikiam.edu.ec/login/index.php (solo con Registro Nacional completo)."),
    (4, "Simulador del Examen de Admisión", "2027-01-25", "2027-02-19", "Credenciales de acceso enviadas al correo tras completar la inscripción."),
    (5, "Primera Postulación", "2027-03-24", "2027-03-25", "Selección de carreras disponibles según puntaje ponderado."),
    (6, "Primera Asignación de Cupo", "2027-03-26", "2027-03-26", "Asignación meritocrática por calificación más alta y cupos ofertados."),
    (7, "Primera Aceptación de Cupo", "2027-03-27", "2027-03-28", "Aceptación libre y voluntaria del cupo asignado."),
    (8, "Segunda Postulación", "2027-03-29", "2027-03-29", "Nueva postulación sobre cupos remanentes tras primera aceptación."),
    (9, "Segunda Asignación de Cupo", "2027-03-30", "2027-03-30", "Publicación de segunda asignación meritocrática."),
    (10, "Segunda Aceptación de Cupo", "2027-03-31", "2027-03-31", "Ventana única de aceptación de segunda asignación."),
    (11, "Tercera Postulación", "2027-04-01", "2027-04-01", "Tercera postulación sobre cupos disponibles."),
    (12, "Tercera Asignación de Cupo", "2027-04-02", "2027-04-02", "Publicación de tercera asignación."),
    (13, "Tercera Aceptación de Cupo", "2027-04-03", "2027-04-03", "Aceptación de tercera asignación."),
    (14, "Test de Orientación Vocacional", "2027-04-04", "2027-04-09", "Apoyo a planificación académica; no influye en el otorgamiento de cupos."),
]

OFERTA_CUPOS = [
    ("GEOCIEN", "Ingeniería en Geociencias", "FCTA", "Facultad de Ciencias de la Tierra y Agua", "650532H01-P-1501", 20, 20, 40, 802.44, 108, "Tronco Común 1er nivel."),
    ("HIDRO", "Ingeniería en Hidrología", "FCTA", "Facultad de Ciencias de la Tierra y Agua", "650532C02-P-1501", 15, 20, 35, 808.82, 72, "Tronco Común 1er nivel."),
    ("AGROECO", "Ingeniería en Agroecología", "FCTA", "Facultad de Ciencias de la Tierra y Agua", "650811F01-P-1501", 25, 10, 35, 780.05, 127, "Malla directa."),
    ("ELECTROMEC", "Ingeniería en Electromecánica y Energías Renovables", "FCTA", "Facultad de Ciencias de la Tierra y Agua", "650713B01-P-1501", 30, 20, 50, 812.50, 152, "Malla directa."),
    ("BIOTEC", "Ingeniería en Biotecnología", "FCV", "Facultad de Ciencias de la Vida", "650511B01-P-1501", 20, 30, 50, 842.21, 337, "Tronco Común 1er nivel."),
    ("ECOSIST", "Ingeniería en Ecosistemas", "FCV", "Facultad de Ciencias de la Vida", "650521C01-P-1501", 10, 25, 35, 811.38, 124, "Tronco Común 1er nivel."),
    ("VETERINARIA", "Medicina Veterinaria y Manejo de Vida Silvestre", "FCV", "Facultad de Ciencias de la Vida", "650841B01-P-1501", 40, 20, 60, 853.91, 380, "10 semestres; mayor demanda."),
    ("BIOCOM", "Licenciatura en Biocomercio", "FCSA", "Facultad de Ciencias Socioambientales", "650416C02-P-1501", 15, 15, 30, 740.92, 126, "Malla directa."),
    ("ARQUITECTURA", "Arquitectura Sostenible", "FCSA", "Facultad de Ciencias Socioambientales", "6507381B02-P-1501", 40, 20, 60, 838.70, 553, "Mayor población estudiantil."),
    ("ECX", "Educación en Ciencias Experimentales (ECX)", "FCSA", "Facultad de Ciencias Socioambientales", "OFICIAL-FCSA-ECX", 0, 0, 0, 0.0, 25, "Parte oficial de las 10 carreras en 3 Facultades; sin cupos en la tabla referencial IIS-2026."),
]


def _strip_html(raw: str) -> str:
    txt = re.sub(r"<[^>]+>", " ", raw or "")
    return re.sub(r"\s+", " ", txt).strip()


FAQS_CURADAS = [
    {
        "slug": "adm_cronograma_1pa2027",
        "categoria": "Cronograma Vigente 1PA 2027",
        "boton_etiqueta": "Cronograma Oficial Admisión 1PA 2027",
        "boton_descripcion": "Fechas exactas vigentes: Registro Nacional (24/11/2026), Inscripciones, Simulador y Postulaciones.",
        "pregunta_canonica": "¿Cuál es el cronograma oficial vigente del proceso de admisión Ikiam (1PA 2027)?",
        "variantes_pregunta": "cuando son las inscripciones | fechas de admision | cronograma admision | cuando inicia el registro nacional | fechas postulacion | aceptacion de cupo | test vocacional",
        "palabras_clave": "cronograma admision, fechas admision, 1pa 2027, registro nacional, inscripciones, simulador, postulacion, aceptacion cupo, cuando inicia, test vocacional, senescyt",
        "ciclo_vigencia": "1PA_2027",
        "frecuencia": 25,
        "es_menu_principal": 1,
        "fuente": "https://www.ikiam.edu.ec/index.php/admisiones/",
        "respuesta_html": """<div style='border-left:3px solid #0d5f3a; padding-left:10px;'>
<div style='color:#0d5f3a; font-weight:700; font-size:13px; margin:0 0 5px;'>Cronograma Oficial de Admisión Ikiam — 1PA 2027</div>
<p style='font-size:12px; line-height:1.45; color:#374151; margin:0 0 6px;'>Las fechas vigentes publicadas en el portal oficial de Admisiones para el periodo <strong>1PA 2027</strong> (el ciclo anterior II PA 2026 ya finalizó) son:</p>
<ul style='font-size:12px; padding-left:16px; line-height:1.45; margin:0 0 6px;'>
  <li><strong>Registro Nacional SENESCYT:</strong> 1ra Etapa del <strong>24/11/2026 al 28/11/2026</strong> • 2da Etapa del <strong>1/12/2026 al 5/12/2026</strong> (paso previo obligatorio).</li>
  <li><strong>Inscripciones en Ikiam:</strong> del <strong>18/12/2026 al 24/01/2027</strong> en <a href='https://eval.ikiam.edu.ec/login/index.php' target='_blank' style='color:#0d5f3a; font-weight:bold;'>eval.ikiam.edu.ec</a>.</li>
  <li><strong>Simulador del Examen:</strong> del <strong>25/01/2027 al 19/02/2027</strong> (usuario y clave llegan al correo tras inscribirse).</li>
  <li><strong>1ra Postulación / Asignación / Aceptación:</strong> Postulación <strong>24–25/03/2027</strong> • Asignación <strong>26/03/2027</strong> • Aceptación <strong>27–28/03/2027</strong>.</li>
  <li><strong>2da Postulación / Asignación / Aceptación:</strong> Postulación <strong>29/03/2027</strong> • Asignación <strong>30/03/2027</strong> • Aceptación <strong>31/03/2027</strong>.</li>
  <li><strong>3ra Postulación / Asignación / Aceptación:</strong> Postulación <strong>01/04/2027</strong> • Asignación <strong>02/04/2027</strong> • Aceptación <strong>03/04/2027</strong>.</li>
  <li><strong>Test de Orientación Vocacional:</strong> del <strong>04/04/2027 al 09/04/2027</strong> (orientativo; no altera asignación de cupos).</li>
</ul>
<p style='font-size:12px; margin:0;'><strong>Canal Oficial Admisión:</strong> <a href='mailto:oficina.admision@ikiam.edu.ec' style='color:#0d5f3a; font-weight:bold;'>oficina.admision@ikiam.edu.ec</a> • Tel: +593 (06) 299 9160 Ext. 322 • WhatsApp: <strong>0982142499</strong></p>
</div>""",
    },
    {
        "slug": "adm_inscripcion_y_requisitos",
        "categoria": "Inscripción y Menores de Edad",
        "boton_etiqueta": "Cómo Inscribirme, Documentos y Menores de Edad",
        "boton_descripcion": "Paso a paso Registro Nacional, eval.ikiam.edu.ec, requisitos tras cupo y matrícula automática.",
        "pregunta_canonica": "¿Cómo me inscribo en Ikiam, qué requisitos piden y cómo funciona para menores de edad?",
        "variantes_pregunta": "como me inscribo en ikiam | requisitos para matricularme | que hago luego de aceptar cupo | menor de edad registro nacional | otra forma de matricularse | nivel 0 matricula automatica",
        "palabras_clave": "inscribirme, inscripcion, menor edad, representante legal, cedula, titulo bachiller, acta grado, aceptar cupo, matricula automatica, eval.ikiam, otra forma",
        "ciclo_vigencia": "1PA_2027",
        "frecuencia": 22,
        "es_menu_principal": 1,
        "fuente": "https://www.ikiam.edu.ec/index.php/admisiones/ + FAQ Admisión",
        "respuesta_html": """<div style='border-left:3px solid #0d5f3a; padding-left:10px;'>
<div style='color:#0d5f3a; font-weight:700; font-size:13px; margin:0 0 5px;'>Guía de Inscripción y Requisitos de Nuevo Ingreso</div>
<ol style='font-size:12px; padding-left:16px; line-height:1.45; margin:0 0 6px;'>
  <li><strong>Paso 1 — Registro Nacional SENESCYT:</strong> Obligatorio (1ra etapa 24–28/11/2026 o 2da etapa 1–5/12/2026). Sin Registro Nacional completo <strong>no existe otra vía directa de ingreso</strong> a 1er nivel ni nivelación.</li>
  <li><strong>¿Eres menor de edad?</strong> Sí puedes hacer el Registro Nacional; la plataforma solicitará además la cédula y el correo de tu representante legal.</li>
  <li><strong>Paso 2 — Inscripción Ikiam (18/12/2026 – 24/01/2027):</strong> Ingresa a <a href='https://eval.ikiam.edu.ec/login/index.php' target='_blank' style='color:#0d5f3a; font-weight:bold;'>eval.ikiam.edu.ec</a> y sigue el enlace oficial de <a href='https://www.ikiam.edu.ec/index.php/admisiones/' target='_blank' style='color:#0d5f3a; font-weight:bold;'>Admisiones Ikiam</a>.</li>
  <li><strong>Paso 3 — Tras aceptar el cupo asignado:</strong> Recibirás notificaciones al correo registrado para cargar en la plataforma SIGUI: <strong>cédula escaneada, título/acta de bachiller escaneada y fotografía tamaño carnet digitalizada</strong>.</li>
  <li><strong>Matrícula nuevo ingreso:</strong> Para estudiantes de nuevo ingreso (tanto primer semestre como nivelación), la matrícula se procesa de forma <strong>automática</strong> tras validar tu documentación.</li>
</ol>
<p style='font-size:12px; margin:0;'><strong>Consultas de Admisión:</strong> <a href='mailto:oficina.admision@ikiam.edu.ec' style='color:#0d5f3a; font-weight:bold;'>oficina.admision@ikiam.edu.ec</a> • WhatsApp: <strong>0982142499</strong></p>
</div>""",
    },
    {
        "slug": "adm_examen_simulador_puntaje",
        "categoria": "Examen, Puntaje y Simulador",
        "boton_etiqueta": "Examen de Admisión, Puntaje (50/50) y Simulador",
        "boton_descripcion": "Temario evaluado, ponderación bachillerato + examen, modalidad virtual/presencial y simulador.",
        "pregunta_canonica": "¿Qué evalúa el examen de admisión, cómo se calcula el puntaje y cómo accedo al simulador?",
        "variantes_pregunta": "que se evalua en el examen | como se compone el puntaje de postulacion | no puedo acceder al simulador | modalidad del examen | virtual o presencial examen | no tengo internet para rendir",
        "palabras_clave": "examen admision, simulador, puntaje postulacion, 50%, bachillerato, fisica, quimica, biologia, verbal, logico, numerico, presencial examen, credenciales",
        "ciclo_vigencia": "1PA_2027",
        "frecuencia": 24,
        "es_menu_principal": 1,
        "fuente": "FAQ II PA 2026 + https://www.ikiam.edu.ec/index.php/admisiones/",
        "respuesta_html": """<div style='border-left:3px solid #0d5f3a; padding-left:10px;'>
<div style='color:#0d5f3a; font-weight:700; font-size:13px; margin:0 0 5px;'>Examen de Admisión, Cálculo de Puntaje y Simulador</div>
<ul style='font-size:12px; padding-left:16px; line-height:1.45; margin:0 0 6px;'>
  <li><strong>Composición del puntaje (sobre 1,000 puntos):</strong> <strong>50% promedio general de graduación</strong> de bachillerato + <strong>50% calificación del examen de admisión</strong>.</li>
  <li><strong>Temario evaluado (selección múltiple):</strong> Razonamiento lógico y numérico, razonamiento verbal y conocimientos en <strong>física, química y biología</strong>.</li>
  <li><strong>Modalidad del examen:</strong> Puedes rendirlo de forma <strong>virtual o presencial</strong> (si no dispones de computadora o internet estable, puedes rendirlo en las instalaciones de Ikiam).</li>
  <li><strong>Simulador oficial (25/01/2027 – 19/02/2027):</strong> Primero debes completar tu inscripción en Ikiam; luego recibirás en tu correo electrónico tus credenciales de acceso al simulador.</li>
  <li><strong>¿Cuándo elijo carrera?</strong> Eliges la carrera de tu interés durante la etapa oficial de <strong>postulación</strong> (a partir del 24/03/2027).</li>
</ul>
<p style='font-size:12px; margin:0;'><strong>Soporte de credenciales / admisión:</strong> <a href='mailto:oficina.admision@ikiam.edu.ec' style='color:#0d5f3a; font-weight:bold;'>oficina.admision@ikiam.edu.ec</a> o <a href='mailto:soporte@ikiam.edu.ec' style='color:#0d5f3a; font-weight:bold;'>soporte@ikiam.edu.ec</a></p>
</div>""",
    },
    {
        "slug": "adm_carreras_cupos_puntajes",
        "categoria": "Oferta Académica y Puntajes",
        "boton_etiqueta": "3 Facultades, 10 Carreras, Cupos y Puntajes de Corte",
        "boton_descripcion": "Oferta completa por Facultad (FCTA, FCV, FCSA), puntajes referenciales IIS-2026 y cupos.",
        "pregunta_canonica": "¿Cuántas facultades y carreras ofrece Ikiam y cuáles fueron los puntajes y cupos referenciales?",
        "variantes_pregunta": "cuantas carreras tiene ikiam | puntaje minimo para ingresar | puntajes referenciales | cupos disponibles | tiene carrera de derecho | existe medicina humana | arquitectura biotecnologia veterinaria",
        "palabras_clave": "carreras, facultades, 10 carreras, 9 carreras, puntajes, puntaje minimo, cupos, derecho, medicina, arquitectura, biotecnologia, veterinaria, agroecologia, hidrologia, geociencias, ecosistemas, biocomercio, electromecanica, ecx",
        "ciclo_vigencia": "1PA_2027",
        "frecuencia": 26,
        "es_menu_principal": 1,
        "fuente": "https://www.ikiam.edu.ec/index.php/admisiones/ + Dossier Oficial",
        "respuesta_html": """<div style='border-left:3px solid #0d5f3a; padding-left:10px;'>
<div style='color:#0d5f3a; font-weight:700; font-size:13px; margin:0 0 5px;'>3 Facultades, 10 Carreras Oficiales y Puntajes Referenciales (IIS-2026)</div>
<p style='font-size:12px; line-height:1.45; color:#374151; margin:0 0 6px;'>Ikiam organiza sus <strong>10 carreras presenciales de pregrado en 3 Facultades</strong> (2,004 estudiantes activos en 2026). Nota: documentos anteriores citan 9 carreras porque <em>Educación en Ciencias Experimentales (ECX)</em> no ofertó cupos en la tabla referencial IIS-2026.</p>
<ul style='font-size:12px; padding-left:16px; line-height:1.45; margin:0 0 6px;'>
  <li><strong>Facultad de Ciencias de la Tierra y Agua (FCTA):</strong>
    <br>• Electromecánica y Energías Renovables — Ref. <strong>812.50</strong> (30 1er sem + 20 niv = 50 cupos)
    <br>• Hidrología — Ref. <strong>808.82</strong> (15 + 20 = 35 cupos)
    <br>• Geociencias — Ref. <strong>802.44</strong> (20 + 20 = 40 cupos)
    <br>• Agroecología — Ref. <strong>780.05</strong> (25 + 10 = 35 cupos)</li>
  <li><strong>Facultad de Ciencias de la Vida (FCV):</strong>
    <br>• Medicina Veterinaria y Manejo de Vida Silvestre — Ref. <strong>853.91</strong> (40 + 20 = 60 cupos)
    <br>• Biotecnología — Ref. <strong>842.21</strong> (20 + 30 = 50 cupos)
    <br>• Ecosistemas — Ref. <strong>811.38</strong> (10 + 25 = 35 cupos)</li>
  <li><strong>Facultad de Ciencias Socioambientales (FCSA):</strong>
    <br>• Arquitectura Sostenible — Ref. <strong>838.70</strong> (40 + 20 = 60 cupos)
    <br>• Biocomercio — Ref. <strong>740.92</strong> (15 + 15 = 30 cupos)
    <br>• Educación en Ciencias Experimentales (ECX) — Carrera oficial de FCSA (25 estudiantes activos; sin oferta referencial en tabla IIS-2026).</li>
</ul>
<p style='font-size:11.5px; color:#4b5563; margin:0;'><strong>Importante:</strong> Los cupos se asignan de manera meritocrática (mayor calificación primero), totalizando 395 cupos referenciales en IIS-2026. Alcanzar el puntaje mínimo no garantiza 1er semestre directo si otros postulantes obtuvieron mayor puntaje; en ese caso pasas a Nivelación. Ikiam no oferta Derecho ni Medicina Humana.</p>
</div>""",
    },
    {
        "slug": "adm_nivelacion_modalidad_horarios",
        "categoria": "Nivelación vs Primer Semestre",
        "boton_etiqueta": "Nivelación (Virtual) vs Carrera (Presencial), Horarios y Ponderación",
        "boton_descripcion": "Diferencia entre nivelación y 1er semestre, módulos, ponderación (>=5 pts) y cortes de energía.",
        "pregunta_canonica": "¿Cuál es la diferencia entre nivelación y primer semestre, qué modalidad tienen y cómo funciona la ponderación?",
        "variantes_pregunta": "diferencia entre nivelacion y primer semestre | modalidad virtual carreras | horarios de ikiam | matutina o vespertina | ponderacion nivelacion | no tengo electricidad clases | me sale curso nivelacion pero ingrese a primer nivel",
        "palabras_clave": "nivelacion, primer semestre, modalidad virtual, presencial, horarios, matutina, vespertina, modulos, ponderacion, electricidad, grabacion, aula virtual",
        "ciclo_vigencia": "PERENNE",
        "frecuencia": 18,
        "es_menu_principal": 1,
        "fuente": "FAQ Admisión Ikiam",
        "respuesta_html": """<div style='border-left:3px solid #0d5f3a; padding-left:10px;'>
<div style='color:#0d5f3a; font-weight:700; font-size:13px; margin:0 0 5px;'>Nivelación vs. Primer Semestre, Horarios y Ponderación</div>
<ul style='font-size:12px; padding-left:16px; line-height:1.45; margin:0;'>
  <li><strong>Modalidad:</strong> La <strong>Nivelación</strong> se cursa en modalidad <strong>virtual</strong> (duración aprox. 4 meses; normalmente en 2 módulos de 8 semanas, jornada vespertina). Al aprobarla ingresas a 1er semestre: <strong>todas las carreras de Ikiam son 100% presenciales</strong> en Tena-Muyuna (no hay carreras en línea).</li>
  <li><strong>Horarios de carrera:</strong> Semestres <strong>impares</strong> (1°, 3°, 5°...) en jornada <strong>matutina</strong> y semestres <strong>pares</strong> (2°, 4°, 6°...) en jornada <strong>vespertina</strong>.</li>
  <li><strong>¿Por qué en SIGUI aparece "CURSO: NIVELACIÓN" si gané cupo a 1er nivel?</strong> La plataforma muestra esa etiqueta provisional mientras Dirección Académica valida tu título/documentos subidos.</li>
  <li><strong>Ponderación automática en Nivelación:</strong> Si repruebas <strong>únicamente una asignatura</strong> con calificación mínima de <strong>5 puntos</strong>, se reemplaza automáticamente por el promedio de las asignaturas aprobadas.</li>
  <li><strong>Falta de electricidad en nivelación:</strong> La grabación de la clase sincrónica queda en <a href='https://aulavirtual.ikiam.edu.ec/' target='_blank' style='color:#0d5f3a; font-weight:bold;'>Aula Virtual</a> para revisar contenidos y entregar actividades.</li>
</ul>
</div>""",
    },
    {
        "slug": "adm_cupo_sin_asignar_cancelar",
        "categoria": "Postulación y Gestión de Cupos",
        "boton_etiqueta": "Sin Cupo Asignado, Segunda Postulación o Liberar Cupo",
        "boton_descripcion": "Qué hacer si no obtienes cupo en 1ra ronda o si necesitas cancelar un cupo ya aceptado.",
        "pregunta_canonica": "¿Qué hago si no obtuve cupo, si quiero postular a otra carrera o cancelar/liberar un cupo aceptado?",
        "variantes_pregunta": "no tengo cupo asignado | no acepte el cupo | postular a carrera diferente | cancelar cupo aceptado | liberar cupo | segunda postulacion",
        "palabras_clave": "sin cupo, no tengo cupo, no acepte, liberar cupo, cancelar cupo, segunda postulacion, tercera postulacion, direccion academica",
        "ciclo_vigencia": "1PA_2027",
        "frecuencia": 16,
        "es_menu_principal": 0,
        "fuente": "Preguntas frecuentes.md + admisiones/",
        "respuesta_html": """<div style='border-left:3px solid #0d5f3a; padding-left:10px;'>
<div style='color:#0d5f3a; font-weight:700; font-size:13px; margin:0 0 5px;'>Gestión de Cupos: Nueva Postulación o Liberación de Cupo</div>
<ul style='font-size:12px; padding-left:16px; line-height:1.45; margin:0;'>
  <li><strong>No obtuviste cupo en 1ra asignación:</strong> Si no aceptaste cupo o no quedaste asignado en 1ra ronda, puedes volver a postular en las carreras con cupos disponibles durante la <strong>2da Postulación (29/03/2027)</strong> o <strong>3ra Postulación (01/04/2027)</strong>.</li>
  <li><strong>No aceptaste dentro del plazo en todas las etapas:</strong> Deberás esperar y volver a participar en el siguiente periodo de admisión.</li>
  <li><strong>Cancelar o liberar un cupo ya aceptado:</strong> Debes enviar una solicitud formal dirigida a Dirección Académica al correo <a href='mailto:direccion.academica@ikiam.edu.ec' style='color:#0d5f3a; font-weight:bold;'>direccion.academica@ikiam.edu.ec</a> adjuntando tu cédula y datos completos.</li>
</ul>
</div>""",
    },
    {
        "slug": "adm_costos_becas_vivienda",
        "categoria": "Gratuidad, Becas y Vivienda",
        "boton_etiqueta": "Costos, Pérdida de Gratuidad, Becas y Residencias",
        "boton_descripcion": "Pregrado gratuito, aranceles si perdió gratuidad (~$40–$50/materia), becas DBU y alojamiento en Tena.",
        "pregunta_canonica": "¿Tiene costo estudiar en Ikiam, ofrecen becas y cuentan con residencias estudiantiles?",
        "variantes_pregunta": "tiene costo estudiar | cuanto pagar si perdi gratuidad | ficha socioeconomica | ofrece becas | tiene residencias estudiantiles | vivienda para estudiantes | alojamiento",
        "palabras_clave": "costo, arancel, gratuidad, perdi gratuidad, quintil, ficha socioeconomica, beca, becas, residencia, residencias estudiantiles, vivienda, alojamiento, terna, muyuna",
        "ciclo_vigencia": "PERENNE",
        "frecuencia": 20,
        "es_menu_principal": 1,
        "fuente": "https://www.ikiam.edu.ec/index.php/admisiones/ + FAQ II PA 2026",
        "respuesta_html": """<div style='border-left:3px solid #0d5f3a; padding-left:10px;'>
<div style='color:#0d5f3a; font-weight:700; font-size:13px; margin:0 0 5px;'>Costos, Gratuidad, Becas y Vivienda Estudiantil</div>
<ul style='font-size:12px; padding-left:16px; line-height:1.45; margin:0;'>
  <li><strong>¿Tiene costo estudiar en Ikiam?</strong> <strong>No.</strong> Como universidad pública del Ecuador, la carrera de pregrado goza de gratuidad en primera matrícula (debes cubrir manutención, alimentación y transporte si vienes de otra provincia).</li>
  <li><strong>Si perdiste la gratuidad (segunda carrera o pérdida de créditos):</strong> Al ingresar completas la <strong>ficha socioeconómica</strong> para fijar tu quintil de descuento; según la orientación de Admisión, el costo referencial promedio ronda entre <strong>$40 y $50 por asignatura</strong> (varía según nivel socioeconómico y créditos). Dudas de ficha socioeconómica: <a href='mailto:bienestar.universitario@ikiam.edu.ec' style='color:#0d5f3a; font-weight:bold;'>bienestar.universitario@ikiam.edu.ec</a> (<a href='mailto:manuel.seraquive@ikiam.edu.ec' style='color:#0d5f3a;'>manuel.seraquive@ikiam.edu.ec</a>).</li>
  <li><strong>Becas y Ayudas Económicas:</strong> Disponibles para estudiantes matriculados; consulta fechas y requisitos en <a href='https://www.ikiam.edu.ec/index.php/becas-y-ayudas-economicas/' target='_blank' style='color:#0d5f3a; font-weight:bold;'>Becas Ikiam</a> (DBU Ext. 260).</li>
  <li><strong>Residencias estudiantiles:</strong> <strong>Ikiam NO dispone actualmente de residencias estudiantiles propias</strong> dentro del campus (Km 7 vía Tena-Muyuna), pero existen arriendos accesibles en Muyuna y Tena.</li>
</ul>
</div>""",
    },
    {
        "slug": "adm_soporte_credenciales_adeudos",
        "categoria": "Accesos, Claves y Soporte",
        "boton_etiqueta": "Recuperar Contraseña, SIGUI, Adeudos e Inducción",
        "boton_descripcion": "Autoservicio de credenciales, correo institucional, Aula Virtual y verificación de valores adeudados.",
        "pregunta_canonica": "¿Cómo recupero mi contraseña o correo institucional, reviso adeudos o justifico la inducción?",
        "variantes_pregunta": "recuperar contrasena | recuperar correo institucional | no puedo acceder a sigui | links para clases | no puedo asistir a la induccion | adeudos valores pendientes | soporte tics",
        "palabras_clave": "contrasena, clave, correo institucional, autoservicio, sigui, aula virtual, adeudos, induccion, soporte",
        "ciclo_vigencia": "PERENNE",
        "frecuencia": 14,
        "es_menu_principal": 0,
        "fuente": "Preguntas frecuentes.md (depurado)",
        "respuesta_html": """<div style='border-left:3px solid #0d5f3a; padding-left:10px;'>
<div style='color:#0d5f3a; font-weight:700; font-size:13px; margin:0 0 5px;'>Accesos Digitales, Adeudos e Inducción de Nuevo Ingreso</div>
<ul style='font-size:12px; padding-left:16px; line-height:1.45; margin:0;'>
  <li><strong>Recuperar contraseña / correo institucional:</strong> Utiliza la plataforma <a href='https://autoservicio.ikiam.edu.ec/autoservicio' target='_blank' style='color:#0d5f3a; font-weight:bold;'>Ikiam Autoservicio</a> o escribe a <a href='mailto:soporte@ikiam.edu.ec' style='color:#0d5f3a; font-weight:bold;'>soporte@ikiam.edu.ec</a> (TICS, piso 3 Edificio Administrativo).</li>
  <li><strong>Aula Virtual y links de clases:</strong> Ingresa a <a href='https://aulavirtual.ikiam.edu.ec/' target='_blank' style='color:#0d5f3a; font-weight:bold;'>aulavirtual.ikiam.edu.ec</a> con tu correo institucional.</li>
  <li><strong>Valores adeudados / aranceles previos:</strong> Escribe a <a href='mailto:daniel.coronel@ikiam.edu.ec' style='color:#0d5f3a; font-weight:bold;'>daniel.coronel@ikiam.edu.ec</a> indicando tu número de cédula y nombres completos para verificar tu estado de cuenta.</li>
  <li><strong>Inasistencia a Inducción:</strong> La inducción brinda lineamientos obligatorios para inicio de clases; si no puedes asistir por causa justificada, notifica oportunamente a <a href='mailto:oficina.admision@ikiam.edu.ec' style='color:#0d5f3a; font-weight:bold;'>oficina.admision@ikiam.edu.ec</a>.</li>
</ul>
</div>""",
    },
    {
        "slug": "adm_extranjeros_homologacion_posgrado",
        "categoria": "Vías Especiales y Extranjeros",
        "boton_etiqueta": "Extranjeros, Homologación / Cambio IES y Posgrados",
        "boton_descripcion": "Título extranjero en MinEduc, cambio desde otra universidad (1–18 dic 2026) y maestrías.",
        "pregunta_canonica": "¿Cómo ingreso si soy extranjero, vengo de otra universidad o busco un posgrado/maestría?",
        "variantes_pregunta": "soy extranjero | bachiller extranjero | cambio de universidad | homologacion de materias | maestrias disponibles | posgrados ikiam",
        "palabras_clave": "extranjero, mineduc, homologacion, cambio universidad, otra ies, maestria, posgrado, posgrados",
        "ciclo_vigencia": "1PA_2027",
        "frecuencia": 15,
        "es_menu_principal": 1,
        "fuente": "https://www.ikiam.edu.ec/index.php/admisiones/ + Calendario 1PAO 2027 + FAQ",
        "respuesta_html": """<div style='border-left:3px solid #0d5f3a; padding-left:10px;'>
<div style='color:#0d5f3a; font-weight:700; font-size:13px; margin:0 0 5px;'>Aspirantes Extranjeros, Movilidad desde otra IES y Posgrados</div>
<ul style='font-size:12px; padding-left:16px; line-height:1.45; margin:0;'>
  <li><strong>Bachiller graduado en el extranjero (1er ingreso):</strong> Debes primero homologar/reconocer tu título de bachiller ante el Ministerio de Educación (MinEduc) del Ecuador y cumplir el Registro Nacional SENESCYT + inscripción en Ikiam (<a href='mailto:oficina.admision@ikiam.edu.ec' style='color:#0d5f3a; font-weight:bold;'>oficina.admision@ikiam.edu.ec</a>).</li>
  <li><strong>Cambio desde otra Universidad (nacional o extranjera con materias aprobadas):</strong> No participa por examen de primer nivel si ya cursaste &ge;2 periodos académicos ordinarios y tienes al menos 2 asignaturas homologables (&ge;80% similitud silábica, Art. 96 RRA). Recepción documental <strong>1PAO 2027: del 1 al 18 de diciembre de 2026</strong> ante <a href='mailto:direccion.academica@ikiam.edu.ec' style='color:#0d5f3a; font-weight:bold;'>direccion.academica@ikiam.edu.ec</a>.</li>
  <li><strong>Maestrías / Posgrados:</strong> Escribe a <a href='mailto:escuela.posgrados@ikiam.edu.ec' style='color:#0d5f3a; font-weight:bold;'>escuela.posgrados@ikiam.edu.ec</a> (Ext. 223) o revisa <a href='https://www.ikiam.edu.ec/index.php/posgrado/' target='_blank' style='color:#0d5f3a; font-weight:bold;'>Oferta de Posgrado Ikiam</a>.</li>
</ul>
</div>""",
    },
    {
        "slug": "adm_por_que_ikiam_dossier",
        "categoria": "Información Institucional",
        "boton_etiqueta": "¿Por qué elegir Ikiam? Laboratorios, Rankings y Reserva",
        "boton_descripcion": "Reserva Colonso Chalupas (93,000 ha), 90% PhDs, rankings THE/QS 2026, movilidad internacional.",
        "pregunta_canonica": "¿Qué diferencia a Ikiam de otras universidades (rankings, investigación, laboratorios y movilidad)?",
        "variantes_pregunta": "por que estudiar en ikiam | rankings ikiam | laboratorios | docentes phd | intercambio movilidad internacional | reserva biologica",
        "palabras_clave": "por que ikiam, rankings, the, qs, webometrics, premios verdes, unesco, reserva, colonso chalupas, 93000, phd, laboratorios, movilidad, bioeconomia",
        "ciclo_vigencia": "PERENNE",
        "frecuencia": 10,
        "es_menu_principal": 0,
        "fuente": "Dossier Oficial Ikiam (PREGUNTAS FRECUENTES II PA 2026.docx.md)",
        "respuesta_html": """<div style='border-left:3px solid #0d5f3a; padding-left:10px;'>
<div style='color:#0d5f3a; font-weight:700; font-size:13px; margin:0 0 5px;'>¿Por qué estudiar en Ikiam?</div>
<ul style='font-size:12px; padding-left:16px; line-height:1.45; margin:0;'>
  <li><strong>Laboratorio vivo de 93,000 hectáreas:</strong> Vinculación académica y científica directa con la <strong>Reserva Biológica Colonso Chalupas</strong> (reconocimiento UNESCO).</li>
  <li><strong>Alta calificación docente e infraestructura:</strong> ~<strong>90% de docentes con Ph.D.</strong> y laboratorios Clase A en biotecnología, geociencias, hidrología y vida silvestre.</li>
  <li><strong>Rankings e impacto 2026:</strong> Posicionada en <strong>THE Latin America University Rankings 2026</strong> (#5 del Ecuador y #3 pública del país), menciones destacadas en <strong>QS World University Rankings</strong> ("Citas por Artículo"), <strong>Webometrics</strong> (Open Science) y <strong>Premios Verdes</strong>.</li>
  <li><strong>Movilidad internacional y bienestar:</strong> Intercambios mediante Dirección de Relaciones Internacionales (<a href='mailto:relaciones.interinstitucionales@ikiam.edu.ec' style='color:#0d5f3a;'>relaciones.interinstitucionales@ikiam.edu.ec</a>) y atención gratuita en medicina, odontología y psicología en Bienestar Universitario.</li>
</ul>
</div>""",
    },
]


def construir():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE admisiones_cronograma (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            orden INTEGER NOT NULL,
            etapa TEXT NOT NULL,
            fecha_inicio TEXT NOT NULL,
            fecha_fin TEXT NOT NULL,
            detalle TEXT NOT NULL
        )
    """)
    cur.executemany(
        "INSERT INTO admisiones_cronograma (orden, etapa, fecha_inicio, fecha_fin, detalle) VALUES (?, ?, ?, ?, ?)",
        CRONOGRAMA_1PA_2027,
    )

    cur.execute("""
        CREATE TABLE admisiones_oferta_cupos (
            codigo_carrera TEXT PRIMARY KEY,
            carrera TEXT NOT NULL,
            facultad_codigo TEXT NOT NULL,
            facultad_nombre TEXT NOT NULL,
            codigo_senescyt TEXT,
            cupos_primer_semestre INTEGER,
            cupos_nivelacion INTEGER,
            cupos_totales_iis2026 INTEGER,
            puntaje_ref_iis2026 REAL,
            estudiantes_activos_2026 INTEGER,
            observacion TEXT
        )
    """)
    cur.executemany(
        "INSERT INTO admisiones_oferta_cupos VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        OFERTA_CUPOS,
    )

    cur.execute("""
        CREATE TABLE admisiones_faq (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slug TEXT UNIQUE NOT NULL,
            categoria TEXT NOT NULL,
            boton_etiqueta TEXT NOT NULL,
            boton_descripcion TEXT NOT NULL,
            pregunta_canonica TEXT NOT NULL,
            variantes_pregunta TEXT NOT NULL,
            respuesta_html TEXT NOT NULL,
            respuesta_texto TEXT NOT NULL,
            palabras_clave TEXT NOT NULL,
            ciclo_vigencia TEXT NOT NULL,
            frecuencia INTEGER DEFAULT 1,
            es_menu_principal INTEGER DEFAULT 0,
            fuente TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE VIRTUAL TABLE admisiones_faq_fts USING fts5(
            slug,
            categoria,
            pregunta_canonica,
            variantes_pregunta,
            respuesta_texto,
            palabras_clave
        )
    """)

    cur.execute("""
        CREATE TABLE admisiones_ingesta_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lote TEXT NOT NULL,
            archivo_fuente TEXT NOT NULL,
            total_entradas INTEGER NOT NULL,
            aceptadas INTEGER NOT NULL,
            actualizadas INTEGER NOT NULL,
            descartadas INTEGER NOT NULL,
            fecha_ingesta TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    for row in FAQS_CURADAS:
        resp_txt = _strip_html(row["respuesta_html"])
        cur.execute("""
            INSERT INTO admisiones_faq (
                slug, categoria, boton_etiqueta, boton_descripcion,
                pregunta_canonica, variantes_pregunta, respuesta_html,
                respuesta_texto, palabras_clave, ciclo_vigencia,
                frecuencia, es_menu_principal, fuente
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            row["slug"], row["categoria"], row["boton_etiqueta"], row["boton_descripcion"],
            row["pregunta_canonica"], row["variantes_pregunta"], row["respuesta_html"],
            resp_txt, row["palabras_clave"], row["ciclo_vigencia"],
            row["frecuencia"], row["es_menu_principal"], row["fuente"],
        ))
        cur.execute("""
            INSERT INTO admisiones_faq_fts (slug, categoria, pregunta_canonica, variantes_pregunta, respuesta_texto, palabras_clave)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            row["slug"], row["categoria"], row["pregunta_canonica"],
            row["variantes_pregunta"], resp_txt, row["palabras_clave"],
        ))

    conn.commit()
    n_cron = cur.execute("SELECT COUNT(*) FROM admisiones_cronograma").fetchone()[0]
    n_of = cur.execute("SELECT COUNT(*) FROM admisiones_oferta_cupos").fetchone()[0]
    n_faq = cur.execute("SELECT COUNT(*) FROM admisiones_faq").fetchone()[0]
    conn.close()
    print(f"DB generada OK -> {DB_PATH} | Cronograma 1PA 2027: {n_cron} etapas | Oferta: {n_of} carreras | FAQs curadas: {n_faq}")


if __name__ == "__main__":
    construir()
