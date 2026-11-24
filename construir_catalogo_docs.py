# -*- coding: utf-8 -*-
"""
Construcción integral de D:\ikiam_academic_chatbot\ikiam_catalog_docs.db
Lee e indexa los 175 archivos reales de documentos_oficiales/ (.docx y .pdf),
extrayendo su contenido real, órgano emisor real, ámbito (estudiantil vs interno),
fragmentos normativos FTS5 y el mapeo 1:N de casos de uso por documento.
"""

import os
import re
import sqlite3
import fitz
from docx import Document

BASE_DIR = r"D:\ikiam_academic_chatbot"
DOCS_DIR = os.path.join(BASE_DIR, "documentos_oficiales")
KB_DIR = r"D:\n8n-email-chatbot\knowledge-base"
DB_PATH = os.path.join(BASE_DIR, "ikiam_catalog_docs.db")


DOCX_META = {
    "FO-GBU-40-V.5.0-Solicitud-de-becas-1.docx": (
        "Solicitud Oficial de Becas Ikiam (FO-GBU-40 V.5.0)",
        "Becas y Ayudas Económicas",
        "estudiantil_pregrado",
        "Dirección de Bienestar Universitario (DBU)",
        "Directora/Director de Bienestar Universitario (bienestar.universitario@ikiam.edu.ec)",
        "Postulación a becas universitarias en 7 modalidades: escasos recursos económicos, discapacidad, comunidades/pueblos/nacionalidades, deportistas de alto rendimiento, investigación/iniciación científica, abanderados/escoltas y casos especiales (y excelencia académica Art. 11.1 >= 9.0/10).",
        "Cédula/pasaporte, ficha socioeconómica, historial SGA, declaración de no percibir otra beca pública y respaldos según modalidad.",
        7,
    ),
    "FO-GBU-56-V.1.1Solicitud-de-ayudas-economicas-2.docx": (
        "Solicitud de Ayudas Económicas (FO-GBU-56 V.1.1)",
        "Becas y Ayudas Económicas",
        "estudiantil_pregrado",
        "Dirección de Bienestar Universitario (DBU)",
        "Directora/Director de Bienestar Universitario (bienestar.universitario@ikiam.edu.ec)",
        "Solicitud de subvención excepcional no reembolsable en 6 modalidades: trabajo de titulación, calamidad doméstica/fuerza mayor, eventos académicos nacionales (hasta 37% SBU) o internacionales (hasta 2.5 SBU; Galápagos 50% SBU), eventos artísticos/culturales/deportivos (6%-10% SBU/día), movilidad internacional (hasta 2.5 SBU) e innovación.",
        "Presentar hasta 20 días calendario antes del fin de clases (excepto fuerza mayor o invitaciones), historial académico, cédula y soportes/invitación.",
        6,
    ),
    "FO-GBU-69-V.1.0-Solicitud-de-impugnacion-de-becas-y-ayudas-1.docx": (
        "Impugnación de Becas y Ayudas Económicas (FO-GBU-69 V.1.0)",
        "Becas y Ayudas Económicas",
        "estudiantil_pregrado",
        "Comité de Becas y Ayudas Económicas / DBU",
        "Dirección de Bienestar Universitario (bienestar.universitario@ikiam.edu.ec)",
        "Recurso formal para impugnar la resolución del Comité de Becas cuando se niega una beca o ayuda económica.",
        "Presentar dentro del término de tres (3) días tras la notificación de resultados, adjuntando pruebas de respaldo no valoradas.",
        2,
    ),
    "FO-GVI-29-V.3.1-Solicitud-para-realizar-practicas-preprofesionales.docx": (
        "Solicitud de Prácticas Preprofesionales (FO-GVI-29 V.3.1)",
        "Prácticas Preprofesionales",
        "estudiantil_pregrado",
        "Dirección de Vinculación con la Sociedad (DVS)",
        "Dirección de Vinculación con la Sociedad (practicas.preprofesionales@ikiam.edu.ec / vinculacion@ikiam.edu.ec)",
        "Formulario de inicio de prácticas preprofesionales externas o internas (laborales o pasantías remuneradas). Debe presentarse con mínimo 12 días hábiles de anticipación según IT-GVI-05.",
        "Revisar Matriz de Convenios vigentes, indicar entidad receptora, tipo/entorno de práctica y completar registro institucional.",
        3,
    ),
    "FO-GVI-31-V.3.1-Solicitud-de-asignacion-de-docente-tutor.docx": (
        "Solicitud de Asignación de Docente Tutor (FO-GVI-31 V.3.1)",
        "Prácticas Preprofesionales",
        "estudiantil_pregrado",
        "Delegado/a de Facultad para Gestión de Vinculación",
        "Delegado de Facultad para Vinculación (practicaspreprofesionales.fcta@ikiam.edu.ec / .fcv@ / .fcsa@)",
        "Petición formal en 5 modalidades (laborales, servicio comunitario, pasantías, ayudantía de cátedra 4-20h/sem o ayudantía de investigación) para designar Tutor URAI dentro de 5 días hábiles tras notificación de DVS.",
        "Enviar dentro de los 5 días hábiles al correo de prácticas de tu Facultad indicando entidad, fechas y docente tutor sugerido.",
        5,
    ),
    "FO-GVI-04-V.3.1-Planificacion-de-practicas-preprofesionales-pregrado.docx": (
        "Planificación de Prácticas Preprofesionales (FO-GVI-04 V.3.1)",
        "Prácticas Preprofesionales",
        "estudiantil_pregrado",
        "Docente Tutor URAI / DVS",
        "Docente Tutor URAI y Delegado de Facultad",
        "Plan de objetivos, horario (máx. 20h/sem en clases, 40h en interciclo; ayudantías 4-20h) y actividades planificadas en 5 modalidades. Legalizado en esfero azul.",
        "Presentar dentro de los 15 días hábiles desde el inicio de la práctica.",
        5,
    ),
    "FO-GVI-05-V.2.0-Control-de-asistencia-practicas-pregrado.docx": (
        "Control de Asistencia de Prácticas Preprofesionales (FO-GVI-05 V.2.0)",
        "Prácticas Preprofesionales",
        "estudiantil_pregrado",
        "Tutor Externo / Docente Tutor URAI / DVS",
        "Tutor de Entidad Receptora y Docente Tutor URAI",
        "Registro obligatorio diario de entrada, salida, actividad y horas cumplidas. Firmado en esfero azul y validado por entidad receptora.",
        "Registro diario obligatorio; ausencia injustificada mayor a 3 días consecutivos es causal de terminación.",
        4,
    ),
    "FO-GVI-06-V.4.1-Informe-de-practicas-preprofesionales-estudiante-pregrado.docx": (
        "Informe Final de Prácticas del Estudiante (FO-GVI-06 V.4.1)",
        "Prácticas Preprofesionales",
        "estudiantil_pregrado",
        "Docente Tutor URAI / DVS",
        "Docente Tutor URAI y Delegado de Facultad",
        "Memoria final de resultados, logros de aprendizaje, control de asistencia y anexos (fotos/link libre acceso o QR) al culminar prácticas laborales, comunitarias, pasantías o ayudantías.",
        "Entregar al tutor URAI dentro de los 15 días hábiles tras finalizar prácticas (5 días hábiles para subsanar observaciones).",
        5,
    ),
    "FO-GVI-07-V.4.1-Informe-de-evaluacion-de-practicas-del-docente-pregrado.docx": (
        "Informe de Evaluación del Docente Tutor (FO-GVI-07 V.4.1)",
        "Prácticas Preprofesionales",
        "estudiantil_pregrado",
        "Docente Tutor URAI / Delegado de Facultad",
        "Delegado de Facultad para Vinculación y DVS",
        "Evaluación académica oficial y validación de horas realizada por el docente tutor de Ikiam sobre el informe del estudiante.",
        "Requiere FO-GVI-06 y control de asistencia aprobados para remitir al Delegado de Facultad.",
        5,
    ),
    "FO-GVI-36-V.2.1-Evaluacion-de-practicas-preprofesionales.docx": (
        "Evaluación de Prácticas por Entidad Receptora (FO-GVI-36 V.2.1)",
        "Prácticas Preprofesionales",
        "estudiantil_pregrado",
        "Entidad Receptora / Responsable Comunitario / Docente",
        "Docente Tutor URAI y DVS",
        "Rúbrica externa de desempeño del estudiante y del acompañamiento del tutor Ikiam (Art. 42 y 44 RRA). Evalúa el tutor externo, líder comunitario, docente de cátedra o investigador.",
        "Firma y validación del evaluador externo o responsable interno del proyecto/laboratorio.",
        5,
    ),
    "FO-GVI-30-V.2.0-Solicitud-de-certificado-de-practicas-preprofesionales-2.docx": (
        "Solicitud de Certificado de Cumplimiento de Prácticas (FO-GVI-30 V.2.0)",
        "Prácticas Preprofesionales",
        "estudiantil_pregrado",
        "Dirección de Vinculación con la Sociedad (DVS)",
        "Directora de Vinculación con la Sociedad (practicas.preprofesionales@ikiam.edu.ec / vinculacion@ikiam.edu.ec)",
        "Solicitud formal para obtener el certificado oficial de cumplimiento de las horas obligatorias (requisito de titulación) una vez cargado el expediente completo en la plataforma de DVS.",
        "Expediente validado por tutor y delegado de facultad + certificado del curso de formación en Bolsa de Empleo Institucional.",
        2,
    ),
    "FORMATO-SOLICITUD-DE-REINGRESO.docx": (
        "Solicitud de Reingreso / Continuidad de Estudios",
        "Admisión, Matrícula y Reingreso",
        "estudiantil_pregrado",
        "Vicerrectorado Académico / Dirección Académica",
        "Vicerrectorado Académico (zulay.nino@ikiam.edu.ec) y Dirección Académica (direccion.academica@ikiam.edu.ec)",
        "Formato para ex-estudiantes que interrumpieron sus estudios (aprobados o retirados) y desean reincorporarse a su carrera u homologar por cambio de malla.",
        "Cédula/pasaporte, récord académico del último periodo cursado e ingreso en el portal de Procesos Académicos según calendario.",
        2,
    ),
    "Formato-Solicitud-Justificacion-Inasistencias.docx": (
        "Formulario de Justificación de Inasistencia y Reprogramación",
        "Asistencia y Justificaciones",
        "estudiantil_pregrado",
        "Coordinación / Dirección de Carrera",
        "Director/a de Carrera según Facultad (FCTA, FCV, FCSA)",
        "Solicitud multi-uso en 3 causales: (1) Médica/Salud con certificado validado, (2) Calamidad doméstica o fuerza mayor comprobada, (3) Representación institucional/deportiva/cultural; incluye tabla de asignaturas y reprogramación de evaluaciones.",
        "Presentar en máximo 3 días hábiles tras el reintegro; si es causal médica requiere validación del Centro de Salud DBU (centro.salud@ikiam.edu.ec).",
        3,
    ),
    "Formato-Solicitud-Retiro-Voluntario-Asignatura.docx": (
        "Solicitud de Retiro Voluntario de Asignatura(s)",
        "Retiro y Matrículas",
        "estudiantil_pregrado",
        "Dirección Académica / Coordinación de Carrera",
        "Director/a de Carrera y Dirección Académica (direccion.academica@ikiam.edu.ec)",
        "Formulario basado en Art. 45 RRA para 3 escenarios: (1) Retiro voluntario ordinario dentro de los primeros 30 días calendario sin perder gratuidad, (2) Retiro extemporáneo por caso fortuito/fuerza mayor o calamidad antes de finales, (3) Retiro preventivo en segunda/tercera matrícula.",
        "Presentar dentro del plazo del calendario académico (en 2PA 2026 fecha límite ordinaria fue 26-30 oct 2026) o adjuntar justificativos de fuerza mayor.",
        3,
    ),
    "Solicitud-de-cambio-de-carrera.docx": (
        "Solicitud de Cambio de Carrera Interno",
        "Homologación y Movilidad",
        "estudiantil_pregrado",
        "Vicerrectorado Académico / Dirección Académica",
        "Vicerrectorado Académico y Dirección Académica (direccion.academica@ikiam.edu.ec)",
        "Solicitud para cambio interno de carrera conforme Art. 96 a) RRA (haber aprobado >50% del 1er PAO, al menos 1 homologable, cumplir puntaje promedio de cohorte). Nota: cambios entre carreras de Tronco Común hasta 1er nivel siguen Art. 97 RRA.",
        "Cédula y papeleta en una sola hoja, carta de no tener 3ras matrículas ni deudas, listado de asignaturas a homologar y entrega del 1 al 18 de diciembre.",
        2,
    ),
    "Solicitud-de-cambio-de-universidad.docx": (
        "Solicitud de Cambio de Universidad (IES Nacional o Extranjera)",
        "Admisión, Homologación e Ingreso",
        "estudiantil_pregrado",
        "Vicerrectorado Académico / Dirección Académica",
        "Vicerrectorado Académico y Dirección Académica (direccion.academica@ikiam.edu.ec)",
        "Petición de transferencia externa para 3 casos según Art. 96 RRA y Procesos Académicos: (1) Desde IES pública nacional (>=2 PAO, >=2 homologables), (2) Desde IES particular nacional (>=2 PAO, asignación de cupos y puntaje de cohorte), (3) Desde universidad extranjera (pasaporte/visa, récord/malla/sílabos legalizados).",
        "Cédula/pasaporte, récord legalizado, malla curricular certificada, sílabos sellados (>=80% similitud) y carta de no impedimentos ni 3ras matrículas. Recepción 1 al 18 de diciembre.",
        3,
    ),
}


CASOS_POR_DOC = [
    ("FO-GBU-40-V.5.0-Solicitud-de-becas-1.docx", "beca_escasos_recursos", "Beca por situación socioeconómica / escasos recursos", "Dirección de Bienestar Universitario", "bienestar.universitario@ikiam.edu.ec"),
    ("FO-GBU-40-V.5.0-Solicitud-de-becas-1.docx", "beca_discapacidad", "Beca para estudiantes con discapacidad (carné MSP/CONADIS)", "Dirección de Bienestar Universitario", "bienestar.universitario@ikiam.edu.ec"),
    ("FO-GBU-40-V.5.0-Solicitud-de-becas-1.docx", "beca_pueblos", "Beca para comunidades, pueblos y nacionalidades", "Dirección de Bienestar Universitario", "bienestar.universitario@ikiam.edu.ec"),
    ("FO-GBU-40-V.5.0-Solicitud-de-becas-1.docx", "beca_deportista", "Beca para deportistas de alto rendimiento", "Dirección de Bienestar Universitario", "bienestar.universitario@ikiam.edu.ec"),
    ("FO-GBU-40-V.5.0-Solicitud-de-becas-1.docx", "beca_investigacion", "Beca de investigación o iniciación científica", "Dirección de Bienestar Universitario", "bienestar.universitario@ikiam.edu.ec"),
    ("FO-GBU-40-V.5.0-Solicitud-de-becas-1.docx", "beca_abanderados", "Beca para abanderados, portaestandartes y escoltas", "Dirección de Bienestar Universitario", "bienestar.universitario@ikiam.edu.ec"),
    ("FO-GBU-40-V.5.0-Solicitud-de-becas-1.docx", "beca_casos_especiales", "Beca por casos especiales (y excelencia Art. 11.1 >= 9.0/10)", "Dirección de Bienestar Universitario", "bienestar.universitario@ikiam.edu.ec"),

    ("FO-GBU-56-V.1.1Solicitud-de-ayudas-economicas-2.docx", "ayuda_titulacion", "Ayuda económica para modalidad de trabajo de titulación", "Dirección de Bienestar Universitario", "bienestar.universitario@ikiam.edu.ec"),
    ("FO-GBU-56-V.1.1Solicitud-de-ayudas-economicas-2.docx", "ayuda_calamidad", "Ayuda económica por calamidad doméstica, caso fortuito o fuerza mayor", "Dirección de Bienestar Universitario", "bienestar.universitario@ikiam.edu.ec"),
    ("FO-GBU-56-V.1.1Solicitud-de-ayudas-economicas-2.docx", "ayuda_eventos_academicos", "Ayuda para eventos académicos nacionales (<=37% SBU) o internacionales (<=2.5 SBU)", "Dirección de Bienestar Universitario", "bienestar.universitario@ikiam.edu.ec"),
    ("FO-GBU-56-V.1.1Solicitud-de-ayudas-economicas-2.docx", "ayuda_eventos_culturales", "Ayuda para eventos artísticos, culturales o deportivos (6%-10% SBU/día)", "Dirección de Bienestar Universitario", "bienestar.universitario@ikiam.edu.ec"),
    ("FO-GBU-56-V.1.1Solicitud-de-ayudas-economicas-2.docx", "ayuda_movilidad", "Ayuda para programas de movilidad internacional (<=2.5 SBU)", "Dirección de Bienestar Universitario", "bienestar.universitario@ikiam.edu.ec"),
    ("FO-GBU-56-V.1.1Solicitud-de-ayudas-economicas-2.docx", "ayuda_innovacion", "Ayuda económica para innovación", "Dirección de Bienestar Universitario", "bienestar.universitario@ikiam.edu.ec"),

    ("FO-GBU-69-V.1.0-Solicitud-de-impugnacion-de-becas-y-ayudas-1.docx", "impugnacion_beca", "Impugnación a resolución denegatoria de beca (término 3 días)", "Comité de Becas / DBU", "bienestar.universitario@ikiam.edu.ec"),
    ("FO-GBU-69-V.1.0-Solicitud-de-impugnacion-de-becas-y-ayudas-1.docx", "impugnacion_ayuda", "Impugnación a resolución denegatoria de ayuda económica (término 3 días)", "Comité de Becas / DBU", "bienestar.universitario@ikiam.edu.ec"),

    ("Formato-Solicitud-Justificacion-Inasistencias.docx", "justificacion_salud", "Justificación de inasistencias por enfermedad/salud (requiere validación DBU)", "Dirección de Carrera + Centro de Salud", "centro.salud@ikiam.edu.ec y Director/a de Carrera"),
    ("Formato-Solicitud-Justificacion-Inasistencias.docx", "justificacion_calamidad", "Justificación por calamidad doméstica o fuerza mayor comprobada", "Dirección de Carrera según Facultad", "Director/a de Carrera (FCTA/FCV/FCSA)"),
    ("Formato-Solicitud-Justificacion-Inasistencias.docx", "justificacion_representacion", "Justificación por representación institucional, deportiva o cultural", "Dirección de Carrera según Facultad", "Director/a de Carrera (FCTA/FCV/FCSA)"),

    ("Formato-Solicitud-Retiro-Voluntario-Asignatura.docx", "retiro_ordinario", "Retiro voluntario ordinario dentro de los primeros 30 días (no afecta gratuidad)", "Dirección de Carrera / Dirección Académica", "Director/a de Carrera y direccion.academica@ikiam.edu.ec"),
    ("Formato-Solicitud-Retiro-Voluntario-Asignatura.docx", "retiro_fuerza_mayor", "Retiro extemporáneo por caso fortuito, salud grave o calamidad antes de finales", "Dirección de Carrera y Vicerrectorado Académico", "Director/a de Carrera y direccion.academica@ikiam.edu.ec"),
    ("Formato-Solicitud-Retiro-Voluntario-Asignatura.docx", "retiro_segunda_matricula", "Retiro preventivo en segunda matrícula para evitar pérdida de carrera (Art. 80 LOES)", "Dirección de Carrera / Dirección Académica", "Director/a de Carrera y direccion.academica@ikiam.edu.ec"),

    ("Solicitud-de-cambio-de-carrera.docx", "cambio_carrera_tronco_comun", "Movilidad dentro del Tronco Común 1er nivel (Geociencias, Hidrología, Biotecnología, Ecosistemas - Art. 97 RRA)", "Dirección Académica / Decanatos", "direccion.academica@ikiam.edu.ec"),
    ("Solicitud-de-cambio-de-carrera.docx", "cambio_carrera_interno", "Cambio de carrera estándar tras aprobar >50% 1er PAO (Art. 96 a RRA)", "Vicerrectorado Académico / Dirección Académica", "direccion.academica@ikiam.edu.ec"),

    ("Solicitud-de-cambio-de-universidad.docx", "homologacion_ies_publica", "Transferencia desde IES pública nacional (>=2 PAO, >=2 materias homologables >=80%)", "Vicerrectorado Académico / Dirección Académica", "direccion.academica@ikiam.edu.ec"),
    ("Solicitud-de-cambio-de-universidad.docx", "homologacion_ies_particular", "Transferencia desde IES particular nacional (>=2 PAO, cupo y puntaje de cohorte)", "Vicerrectorado Académico / Dirección Académica", "direccion.academica@ikiam.edu.ec"),
    ("Solicitud-de-cambio-de-universidad.docx", "homologacion_extranjera", "Transferencia desde universidad extranjera (pasaporte, visa estudiante, documentos legalizados)", "Vicerrectorado Académico / Dirección Académica", "direccion.academica@ikiam.edu.ec y relaciones.interinstitucionales@ikiam.edu.ec"),

    ("FORMATO-SOLICITUD-DE-REINGRESO.docx", "reingreso_directo", "Reingreso de ex-estudiante aprobado o retirado sin cambio de malla", "Vicerrectorado Académico / Dirección Académica", "direccion.academica@ikiam.edu.ec"),
    ("FORMATO-SOLICITUD-DE-REINGRESO.docx", "reingreso_homologacion", "Reingreso con actualización o homologación interna por cambio de malla", "Vicerrectorado Académico / Dirección Académica", "direccion.academica@ikiam.edu.ec"),

    ("FO-GVI-29-V.3.1-Solicitud-para-realizar-practicas-preprofesionales.docx", "practica_laboral_externa", "Inicio de práctica laboral en institución/empresa externa (12 días hábiles antes)", "Dirección de Vinculación con la Sociedad", "practicas.preprofesionales@ikiam.edu.ec"),
    ("FO-GVI-29-V.3.1-Solicitud-para-realizar-practicas-preprofesionales.docx", "practica_laboral_interna", "Inicio de práctica laboral interna en unidades/laboratorios Ikiam", "Dirección de Vinculación con la Sociedad", "practicas.preprofesionales@ikiam.edu.ec"),
    ("FO-GVI-29-V.3.1-Solicitud-para-realizar-practicas-preprofesionales.docx", "pasantia_remunerada", "Inicio de pasantía preprofesional remunerada", "Dirección de Vinculación con la Sociedad", "practicas.preprofesionales@ikiam.edu.ec"),

    ("FO-GVI-31-V.3.1-Solicitud-de-asignacion-de-docente-tutor.docx", "tutor_laboral_comunitaria_ayudantia", "Solicitud de docente tutor URAI para laboral, servicio comunitario, pasantía, ayudantía de cátedra o investigación (plazo 5 días hábiles)", "Delegado de Facultad para Vinculación", "practicaspreprofesionales.fcta@ / .fcv@ / .fcsa@ikiam.edu.ec"),
    ("FO-GVI-30-V.2.0-Solicitud-de-certificado-de-practicas-preprofesionales-2.docx", "certificado_400h", "Solicitud de constancia final de cumplimiento de prácticas para titulación", "Dirección de Vinculación con la Sociedad", "practicas.preprofesionales@ikiam.edu.ec / vinculacion@ikiam.edu.ec"),
]


MANUAL_SCAN_OVERRIDES = {
    "Calendario-Academico-de-Nivelacion-octubre-2025-marzo-2026.pdf": (
        "Calendario Académico de Nivelación (Octubre 2025 - Marzo 2026)",
        "Calendario Académico y Fechas",
        "estudiantil_pregrado",
        "Vicerrectorado Académico Ikiam",
        "Dirección Académica / Nivelación (direccion.academica@ikiam.edu.ec)",
        "Calendario oficial de Nivelación Oct 2025 - Mar 2026 (19 semanas, 78 días clase): Matriculación 15 sep - 03 oct 2025; Inicio clases 20 oct 2025; Exámenes interciclo 15-19 dic 2025; Exámenes finales 02-06 mar 2026; Recuperación 09-11 mar 2026; Exit Test 12 mar 2026; Fin de periodo 13 mar 2026.",
        "Estudiantes admitidos a Nivelación de carrera; respetar fechas de matrícula y exámenes.",
    ),
    "24022022-Resolucion-No.-016-SG-SO-002-CU-IKIAM-2022-Lineamientos-grupos-prioritarios.pdf": (
        "Resolución 016-SG-SO-002-CU-IKIAM-2022: Lineamientos Grupos Prioritarios",
        "Resoluciones Normativas Internas",
        "normativa_interna",
        "Consejo Universitario Ikiam",
        "Vicerrectorado Académico / Talento Humano",
        "Lineamientos institucionales para el personal académico titular y ocasional perteneciente a grupos de atención prioritaria.",
        "Aplica a personal académico en situación prioritaria acreditada.",
    ),
    "27102021-Resolucion-SE004-002-CU-IKIAM-2021-Aprobacion-segundo-debate-Codigo-de-Etica.pdf": (
        "Resolución SE004-002-CU-IKIAM-2021: Código de Ética Ikiam",
        "Ética y Convivencia Institucional",
        "normativa_estudiantil",
        "Consejo Universitario Ikiam",
        "Comité de Ética / Secretaría General (secretaria.general@ikiam.edu.ec)",
        "Aprobación en segundo debate del Código de Ética institucional aplicable a autoridades, docentes, administrativos y estudiantes de Ikiam.",
        "Cumplimiento general en comunidad universitaria.",
    ),
}

MASK_2026_TITLES = {
    "RESOLUCION-No.-034": "Nómina de personas ausentes en juntas receptoras del voto en elecciones de Rector/a y Vicerrector/a Académico/a 2026.",
    "RESOLUCION-No.-050": "Aprobación del Informe de Ajuste No Sustantivo de la Carrera de Biocomercio (FCSA, sept. 2026).",
    "RESOLUCION-No.-051": "Conocimiento del Informe IKIAM-DBU-RD-2026-001 referente a presunta denuncia de deshonestidad académica en asignatura (DBU, sept. 2026).",
    "RESOLUCION-No.-046-SG-SE-025": "Inicio de proceso de régimen disciplinario Talento Humano (sept. 2026).",
    "RESOLUCION-No.-058-SG-SO-009": "Rectificación a la Resolución No. 046-SG-SE-025-CU-IKIAM-2026 (Talento Humano).",
    "RESOLUCION-No.-071": "Aprobación del informe final del procedimiento disciplinario Nro. 001-CES-IKIAM-2026 (nov. 2026).",
}


def clean_space(txt):
    return re.sub(r'\s+', ' ', txt).strip()


def extract_resuelve_summary(full_text, filename):
    """Extrae el órgano emisor real y un resumen concreto del apartado RESUELVE / Artículos."""
    norm_txt = clean_space(full_text)
    low = norm_txt.lower()

    # Emisor real
    if "consejo de educación superior" in filename.lower() or "reglamento régimen académico del consejo de educación superior" in low[:300]:
        emisor = "Consejo de Educación Superior (CES)"
    elif "it-gvi-05" in filename.lower() or "dirección de vinculación" in low[:400]:
        emisor = "Dirección de Vinculación con la Sociedad (DVS) / Rectorado Ikiam"
    elif "codificación del reglamento de becas" in low[:300]:
        emisor = "Consejo Universitario de Ikiam / DBU"
    elif "consejo universitario" in low[:600]:
        emisor = "Consejo Universitario de Ikiam"
    elif "vicerrectorado" in low[:500] or "homologaci" in filename.lower():
        emisor = "Vicerrectorado Académico / Dirección Académica Ikiam"
    else:
        emisor = "Universidad Regional Amazónica Ikiam"

    # Resumen del contenido
    m_res = re.search(r'(?:RESUELVE|Resuelve)\s*:?\s*(.{80,900})', norm_txt)
    if m_res:
        res_sn = m_res.group(1)
        res_sn = re.split(r'\s*DISPOSICI[ÓO]N\s+FINAL|\s*Dado en la ciudad', res_sn)[0].strip()
        return emisor, res_sn[:550]

    # Buscar artículos si es reglamento
    arts = re.findall(r'(Artículo\s+\d+\.?[^\.]{15,200}\.)', norm_txt)
    if arts:
        return emisor, " | ".join(arts[:4])[:550]

    return emisor, norm_txt[:500]


def classify_pdf(fn, full_text):
    low = fn.lower()
    if fn in MANUAL_SCAN_OVERRIDES:
        tit, cat, amb, aut, cont, desc, req = MANUAL_SCAN_OVERRIDES[fn]
        return tit, cat, amb, aut, cont, desc, req, 1

    if "_public_mask" in low:
        prefix = fn.split("_public_mask")[0]
        matched_desc = None
        for k, v in MASK_2026_TITLES.items():
            if prefix.startswith(k):
                matched_desc = v
                break
        if matched_desc is None:
            if any(f"-0{n}-" in prefix for n in range(36, 42)):
                matched_desc = "Resolución de apelación de evaluación integral del desempeño docente (Componente Docencia 1PA 2026)."
            elif any(f"-0{n}-" in prefix for n in range(42, 50)):
                matched_desc = "Resolución de apelación de evaluación docente (Componente Vinculación con la Sociedad 1PA 2026)."
            elif any(f"-0{n}-" in prefix for n in range(53, 58)):
                matched_desc = "Resolución de apelación de evaluación docente (Componente Investigación 1PA 2026)."
            else:
                matched_desc = f"Resolución institucional de Consejo Universitario 2026 ({prefix})."

        amb = "normativa_estudiantil" if ("050" in prefix or "051" in prefix) else "resolucion_interna"
        cat = "Oferta Académica / Régimen Estudiantil 2026" if amb == "normativa_estudiantil" else "Resoluciones Administrativas 2026 (Enmascaradas)"
        return (
            prefix.replace("-", " "),
            cat,
            amb,
            "Consejo Universitario Ikiam",
            "Secretaría General (secretaria.general@ikiam.edu.ec)",
            matched_desc,
            "Documento oficial escaneado y enmascarado de sesión de Consejo Universitario 2026.",
            1,
        )

    emisor, real_desc = extract_resuelve_summary(full_text, fn)
    pretty_title = os.path.splitext(fn)[0].replace("-", " ").replace("_", " ")

    if "reglamento-regimen-academico" in low:
        return (
            "Reglamento de Régimen Académico del CES (Arts. 96-97 Movilidad)",
            "Reglamentos y Normativa Nacional",
            "normativa_estudiantil",
            emisor,
            "Dirección Académica (direccion.academica@ikiam.edu.ec)",
            "Norma nacional obligatoria sobre cambio de carrera (>50% 1er PAO, 1 homologable, cohorte), cambio de IES pública (>=2 PAO, >=2 homologables), IES particular a pública y excepción de Tronco Común (Art. 97).",
            "Aplicable a toda solicitud de movilidad interna o transferencia externa en Ikiam.",
            4,
        )
    if "codificacion-del-reglamento-de-becas" in low:
        return (
            "Codificación del Reglamento de Becas y Ayudas Económicas (2026)",
            "Becas y Ayudas Económicas",
            "normativa_estudiantil",
            emisor,
            "Dirección de Bienestar Universitario (bienestar.universitario@ikiam.edu.ec)",
            "Norma vigente (30 págs.) que regula becas (Excelencia >= 9.0/10 directa desde 2do semestre, socioeconómica, discapacidad, nacionalidades, deportistas), ayudas económicas (plazo 20 días calendario antes fin de clases; montos hasta 37% SBU nacional / 2.5 SBU internacional / 50% Galápagos), responsable solidario, impugnación en 3 días y suspensión/terminación.",
            "Ser estudiante regular (>=60% asignaturas matriculadas), no tener 3ra matrícula ni otra beca pública.",
            10,
        )
    if "it-gvi-05" in low:
        return (
            "Instructivo IT-GVI-05 V.1.0 Gestión de Prácticas Preprofesionales (2026)",
            "Prácticas Preprofesionales",
            "normativa_estudiantil",
            emisor,
            "DVS (practicas.preprofesionales@ikiam.edu.ec) y Delegados FCTA/FCV/FCSA",
            "Instructivo oficial 2026 (27 págs.): 400 horas (240 laborales + comunitarias), solicitud FO-GVI-29 con 12 días hábiles de anticipación, 5 días hábiles para asignar tutor FO-GVI-31 al correo de prácticas de facultad, 15 días hábiles planificación FO-GVI-04 e informe final FO-GVI-06, máx 20h/sem en clases (40h interciclo) y pérdida por abandono >3 días.",
            "Uso obligatorio de los 8 formatos FO-GVI, firma en esfero azul y carga en plataforma DVS.",
            6,
        )
    if "matriz-de-convenios" in low:
        return (
            "Matriz de Convenios Institucionales Prácticas Preprofesionales (2PA 2026)",
            "Prácticas Preprofesionales",
            "estudiantil_pregrado",
            "Dirección de Vinculación con la Sociedad (DVS)",
            "DVS (practicas.preprofesionales@ikiam.edu.ec)",
            "Listado actualizado 2PA 2026 de convenios marco y específicos vigentes (PUCE, Yachay Tech, MAATE, GADs amazónicos, institutos y empresas) con links de Secretaría General.",
            "Verificar si la entidad elegida consta vigente antes de presentar FO-GVI-29.",
            2,
        )
    if "calendario-de-homologacion" in low:
        return (
            "Calendario del Proceso de Homologación 1PAO 2027",
            "Calendario Académico y Fechas",
            "calendario_vigente",
            "Vicerrectorado Académico / Dirección Académica",
            "Dirección Académica (direccion.academica@ikiam.edu.ec)",
            "Cronograma oficial 1PAO 2027: Entrega documentos 1-18 dic 2026; validación 4-13 ene 2027; reasignación carreras 14-15 ene; análisis contenidos 21 ene-19 feb; puntaje cohorte 15-17 feb; evaluación conocimientos 25-26 feb; resultados 8-10 mar; cuentas DTI 11-12 mar 2027.",
            "Cumplir fechas improrrogables de recepción (1 al 18 de diciembre de 2026).",
            3,
        )
    if "reforma-propuesta-de-calendario-academico-2pa2026" in low:
        return (
            "Calendario Académico Vigente de Carrera — 2PA 2026 (Oct 2026 - Mar 2027)",
            "Calendario Académico y Fechas",
            "calendario_vigente",
            "Vicerrectorado Académico (Dra. Zulay Niño Ruiz)",
            "Dirección Académica (direccion.academica@ikiam.edu.ec)",
            "Fechas oficiales 2PA 2026: Solicitudes 3ra matrícula hasta 24/9/2026; Matrícula Ordinaria 28/9-2/10; Extraordinaria 5-9/10; Especial/Placement 12-16/10; Inicio clases 19/10/2026; Retiro voluntario hasta 26-30/10/2026; 1er Parcial 30/11-4/12/2026; Homologación 1-18/12/2026; 2do Parcial 18-22/1/2027; Finales 3-9/3/2027; Recuperación 10-11/3/2027; Exit Test 12/3/2027.",
            "Calendario rector vigente del Segundo Periodo Académico 2026 (16 semanas de clase / 80 días).",
            5,
        )
    if "tabla-arancelaria" in low or "copias-certificadas" in low or "rubros-por-concepto" in low:
        return (
            pretty_title,
            "Tasas, Pagos y Aranceles",
            "normativa_estudiantil",
            emisor,
            "Dirección Financiera / Dirección de Bienestar Universitario / Secretaría General",
            real_desc,
            "Liquidación financiera emitida en SGA o Secretaría General y comprobante bancario oficial.",
            2,
        )
    if "proyecto-carrera" in low or "nivelacion" in low or "estatuto" in low or "biblioteca" in low or "idiomas" in low or "estudiantes" in low or "receso" in low:
        return (
            pretty_title,
            "Normativa Académica y Oferta Institucional",
            "normativa_estudiantil",
            emisor,
            "Vicerrectorado Académico / Secretaría General",
            real_desc,
            "Resolución de Consejo Universitario aplicable al régimen académico o creación de carrera.",
            1,
        )
    if "calendario" in low:
        return (
            pretty_title,
            "Calendario Académico Histórico (2021-2022)",
            "calendario_historico",
            emisor,
            "Secretaría General / Dirección Académica",
            real_desc,
            "Referencia histórica de periodos 2021-2022; para fechas vigentes usar calendario 2PA 2026 / 1PAO 2027.",
            1,
        )

    # Resoluciones administrativas / docentes / internas 2021-2022
    return (
        pretty_title,
        "Resoluciones Consejo Universitario (Gestión Interna 2021-2022)",
        "resolucion_interna",
        emisor,
        "Secretaría General (secretaria.general@ikiam.edu.ec)",
        real_desc,
        "Resolución administrativa/institucional de Consejo Universitario.",
        1,
    )


def build_catalog():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE catalogo_documentos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        archivo TEXT NOT NULL UNIQUE,
        titulo TEXT NOT NULL,
        categoria TEXT NOT NULL,
        ambito TEXT NOT NULL,
        formato TEXT NOT NULL,
        ente_emisor TEXT NOT NULL,
        paginas INTEGER DEFAULT 1,
        texto_extraido_chars INTEGER DEFAULT 0,
        descripcion TEXT NOT NULL,
        destinatario TEXT NOT NULL,
        autoridad_destino TEXT NOT NULL,
        requisitos TEXT NOT NULL,
        casos_uso_count INTEGER DEFAULT 1,
        enlace_descarga TEXT NOT NULL
    );
    """)

    cur.execute("""
    CREATE VIRTUAL TABLE catalogo_fts USING fts5(
        archivo, titulo, categoria, ambito, ente_emisor, descripcion, requisitos,
        content='catalogo_documentos', content_rowid='id'
    );
    """)

    cur.execute("""
    CREATE TABLE documento_casos_uso (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        archivo TEXT NOT NULL,
        codigo_caso TEXT NOT NULL,
        descripcion_caso TEXT NOT NULL,
        dependencia_destino TEXT NOT NULL,
        correo_destino TEXT NOT NULL,
        FOREIGN KEY (archivo) REFERENCES catalogo_documentos(archivo)
    );
    """)

    cur.execute("""
    CREATE TABLE fragmentos_normativos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fuente TEXT NOT NULL,
        tema TEXT NOT NULL,
        ambito TEXT NOT NULL,
        texto TEXT NOT NULL,
        enlace_doc TEXT NOT NULL
    );
    """)

    cur.execute("""
    CREATE VIRTUAL TABLE fragmentos_fts USING fts5(
        fuente, tema, texto, enlace_doc,
        content='fragmentos_normativos', content_rowid='id'
    );
    """)

    files = sorted(os.listdir(DOCS_DIR))
    for fn in files:
        p = os.path.join(DOCS_DIR, fn)
        ext = os.path.splitext(fn)[1].lower().lstrip('.')
        if ext == 'docx':
            doc = Document(p)
            txt = "\n".join(pa.text.strip() for pa in doc.paragraphs if pa.text.strip())
            if fn in DOCX_META:
                tit, cat, amb, emisor, aut_dest, desc, req, cnt_uso = DOCX_META[fn]
            else:
                tit, cat, amb, emisor, aut_dest, desc, req, cnt_uso = (
                    fn, "Formularios Oficiales", "estudiantil_pregrado", "Ikiam",
                    "Dirección Académica", txt[:400], "Completar y firmar formato oficial.", 1
                )
            cur.execute("""
            INSERT INTO catalogo_documentos
            (archivo, titulo, categoria, ambito, formato, ente_emisor, paginas, texto_extraido_chars,
             descripcion, destinatario, autoridad_destino, requisitos, casos_uso_count, enlace_descarga)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (fn, tit, cat, amb, 'docx', emisor, 1, len(txt), desc, "Estudiantes / Postulantes Ikiam", aut_dest, req, cnt_uso, f"/documentos/{fn}"))
        elif ext == 'pdf':
            doc = fitz.open(p)
            pages = len(doc)
            full_txt = "\n".join(pg.get_text() for pg in doc)
            doc.close()
            tit, cat, amb, emisor, aut_dest, desc, req, cnt_uso = classify_pdf(fn, full_txt)
            cur.execute("""
            INSERT INTO catalogo_documentos
            (archivo, titulo, categoria, ambito, formato, ente_emisor, paginas, texto_extraido_chars,
             descripcion, destinatario, autoridad_destino, requisitos, casos_uso_count, enlace_descarga)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (fn, tit, cat, amb, 'pdf', emisor, pages, len(full_txt.strip()), desc, "Comunidad Universitaria Ikiam", aut_dest, req, cnt_uso, f"/documentos/{fn}"))

            # Indexar fragmentos de reglamentos y documentos clave con texto real en fragmentos_normativos
            if amb in ("normativa_estudiantil", "calendario_vigente", "estudiantil_pregrado") and len(full_txt.strip()) > 300:
                chunks = []
                if "codificacion-del-reglamento-de-becas" in fn.lower() or "it-gvi-05" in fn.lower() or "reglamento-regimen-academico" in fn.lower():
                    # Partir en bloques por Articulo o secciones de ~1200 chars
                    clean_f = clean_space(full_txt)
                    step = 1100
                    for idx_c in range(0, min(len(clean_f), 32000), step):
                        chunks.append(clean_f[idx_c:idx_c+step+120])
                elif "matriz-de-convenios" in fn.lower():
                    # Guardar resumen por bloques para búsqueda de convenios por entidad
                    clean_f = clean_space(full_txt)
                    step = 1400
                    for idx_c in range(0, len(clean_f), step):
                        chunks.append(clean_f[idx_c:idx_c+step+100])
                else:
                    clean_f = clean_space(full_txt)
                    chunks.append(clean_f[:2200])
                for ch in chunks:
                    cur.execute(
                        "INSERT INTO fragmentos_normativos (fuente, tema, ambito, texto, enlace_doc) VALUES (?, ?, ?, ?, ?)",
                        (fn, tit, amb, ch, f"/documentos/{fn}")
                    )

    # Insertar también transcripciones verificadas de PDFs escaneados clave + TXTs oficiales sin contradicciones
    extra_frags = [
        (
            "Calendario-Academico-de-Nivelacion-octubre-2025-marzo-2026.pdf",
            "Calendario Nivelación Oct 2025 - Mar 2026",
            "calendario_vigente",
            "Inicio clases Nivelación: 20 de octubre de 2025. Fin periodo: 13 de marzo de 2026. Matriculación: 15 sep al 03 oct 2025. Exámenes interciclo: 15 al 19 dic 2025. Exámenes finales: 02 al 06 mar 2026. Exámenes recuperación: 09 al 11 mar 2026. Entrega calificaciones / Exit Test: 12 mar 2026. Aprobado por Ph.D. Roldán Torres Gutiérrez.",
            "/documentos/Calendario-Academico-de-Nivelacion-octubre-2025-marzo-2026.pdf"
        ),
        (
            "Reforma-Propuesta-de-Calendario-Academico-2PA2026-1-signed-1.pdf",
            "Calendario Vigente Carrera 2PA 2026 (Fechas Oficiales)",
            "calendario_vigente",
            "Segundo Periodo Académico 2026 (2PA 2026): Entrega máxima solicitudes 3ra matrícula: 24/9/2026. Matrícula Ordinaria: 28/9 al 2/10/2026. Matrícula Extraordinaria: 5 al 9/10/2026. Matrícula Especial / Placement Test: 12 al 16/10/2026. Inicio de clases: 19/10/2026. Fecha máxima para retiro voluntario ordinario: 26 al 30/10/2026. Exámenes 1er Parcial: 30/11 al 4/12/2026. Proceso de Homologación 1PAO 2027: 1 al 18/12/2026. Exámenes 2do Parcial: 18 al 22/1/2027. Exámenes Finales: 3 al 9/3/2027. Exámenes de Recuperación: 10 al 11/3/2027. Exit Test y cierre: 12/3/2027.",
            "/documentos/Reforma-Propuesta-de-Calendario-Academico-2PA2026-1-signed-1.pdf"
        ),
        (
            "admisiones.txt (Web Oficial Ikiam 1PA 2027)",
            "Admisión Destino Ikiam 1PA 2027, Cupos y Puntajes Referenciales IIS-2026",
            "estudiantil_pregrado",
            "Proceso Admisión 1PA 2027: Registro Nacional 1ra Etapa 24/11/2026 al 28/11/2026, 2da Etapa 1/12/2026 al 5/12/2026. Inscripciones en eval.ikiam.edu.ec del 18/12/2026 al 24/1/2027. Simulador del 25/1/2027 al 19/2/2027. Postulaciones 24/3 al 1/4/2027, aceptación hasta 3/4/2027, Test vocacional 4/4 al 9/4/2027. Puntaje: 50% promedio graduación + 50% examen admisión. Puntajes referenciales IIS-2026: Veterinaria 853.91, Biotecnología 842.21, Arquitectura 838.7, Electromecánica 812.5, Ecosistemas 811.38, Hidrología 808.82, Geociencias 802.44, Agroecología 780.05, Biocomercio 740.92. Nota oficial: Ikiam NO cuenta actualmente con residencias estudiantiles. Contacto: oficina.admision@ikiam.edu.ec / Ext. 322 / 0982142499.",
            "https://www.ikiam.edu.ec/index.php/admisiones/"
        ),
        (
            "procesos_academicos.txt (Web Oficial Ikiam)",
            "Tronco Común, Cambio de Carrera, Cambio IES y Reingreso",
            "estudiantil_pregrado",
            "Recepción documentos homologación/cambio carrera/cambio IES: 1 al 18 de diciembre de 2026. Tronco Común hasta primer nivel aplica para: Ingeniería en Hidrología, Biotecnología, Geociencias y Ecosistemas (Art. 97 RRA). Cambio IES Nacional o Extranjera requiere carta dirigida al Vicerrector Académico, cédula y papeleta en una sola hoja (o pasaporte y visa de estudiante para extranjeros), récord académico legalizado, malla certificada, sílabos sellados (>=80% similitud) y carta de no impedimentos (sin 3ras matrículas ni deudas). Contacto: direccion.academica@ikiam.edu.ec Ext. 322.",
            "https://www.ikiam.edu.ec/index.php/procesos-academicos/"
        ),
        (
            "centro_idiomas.txt (Web Oficial Ikiam)",
            "Centro de Idiomas: Inglés B1, Placement Test y Exit Test",
            "estudiantil_pregrado",
            "Programa regular de 6 niveles (100 horas c/u) hacia nivel B2/requisito egreso B1. Placement Test asigna nivel 1-6 (ej. 16 octubre 2026). Exit Test para aprobar suficiencia B1 tras 6 niveles: fechas 11 diciembre 2026 - 04 marzo 2027 (solicitudes se habilitan 1 semana antes). Preparación TOEFL, IELTS, FCE, TKT. Correos oficiales: centro.idiomas@ikiam.edu.ec y daniel.robles@ikiam.edu.ec.",
            "https://www.ikiam.edu.ec/index.php/centro-de-idiomas/"
        ),
    ]
    for f_src, tema, amb, txt_f, link in extra_frags:
        cur.execute(
            "INSERT INTO fragmentos_normativos (fuente, tema, ambito, texto, enlace_doc) VALUES (?, ?, ?, ?, ?)",
            (f_src, tema, amb, txt_f, link)
        )

    # Poblar casos de uso por documento (1:N)
    cur.executemany("""
    INSERT INTO documento_casos_uso (archivo, codigo_caso, descripcion_caso, dependencia_destino, correo_destino)
    VALUES (?, ?, ?, ?, ?)
    """, CASOS_POR_DOC)

    # Construir índices FTS5
    cur.execute("INSERT INTO catalogo_fts(catalogo_fts) VALUES('rebuild');")
    cur.execute("INSERT INTO fragmentos_fts(fragmentos_fts) VALUES('rebuild');")

    conn.commit()
    print("ikiam_catalog_docs.db reconstruida con exito.")
    print("  catalogo_documentos:", cur.execute("SELECT COUNT(1) FROM catalogo_documentos").fetchone()[0])
    print("  documento_casos_uso:", cur.execute("SELECT COUNT(1) FROM documento_casos_uso").fetchone()[0])
    print("  fragmentos_normativos:", cur.execute("SELECT COUNT(1) FROM fragmentos_normativos").fetchone()[0])
    print("  ambito breakdown:", cur.execute("SELECT ambito, COUNT(1) FROM catalogo_documentos GROUP BY ambito").fetchall())
    conn.close()


if __name__ == "__main__":
    build_catalog()
