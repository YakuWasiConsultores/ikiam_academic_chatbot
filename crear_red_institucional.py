# -*- coding: utf-8 -*-
"""
Script de creación y población de ikiam_network_org.db
Modela la Red Institucional de la Universidad Regional Amazónica Ikiam:
- Dependencias universitarias, autoridades y coordinaciones de carrera.
- Correos oficiales validados.
- Mapeo relacional de trámites y casos de uso por documento.
"""

import os
import sqlite3

BASE_DIR = r"D:\ikiam_academic_chatbot"
DB_PATH = os.path.join(BASE_DIR, "ikiam_network_org.db")

def init_network_db():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE dependencias (
        id TEXT PRIMARY KEY,
        nombre TEXT NOT NULL,
        tipo TEXT NOT NULL,
        correo_oficial TEXT NOT NULL,
        responsable_cargo TEXT,
        horario_atencion TEXT,
        competencias_clave TEXT,
        enlace_web TEXT
    );
    """)

    cur.execute("""
    CREATE TABLE coordinaciones_carrera (
        codigo TEXT PRIMARY KEY,
        carrera TEXT NOT NULL,
        facultad TEXT NOT NULL,
        correo_coordinacion TEXT NOT NULL,
        coordinador TEXT,
        titulo_otorgado TEXT
    );
    """)

    cur.execute("""
    CREATE TABLE casos_tramite_red (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo_caso TEXT NOT NULL UNIQUE,
        documento_archivo TEXT NOT NULL,
        nombre_tramite TEXT NOT NULL,
        perfil_estudiante TEXT NOT NULL,
        descripcion_caso TEXT NOT NULL,
        dependencia_id TEXT NOT NULL,
        autoridad_destinataria TEXT NOT NULL,
        correo_destino TEXT NOT NULL,
        plazo_reglamentario TEXT NOT NULL,
        requisitos_adjuntos TEXT NOT NULL,
        pasos_procedimiento TEXT NOT NULL,
        enlace_descarga TEXT NOT NULL,
        FOREIGN KEY (dependencia_id) REFERENCES dependencias(id)
    );
    """)

    # 1. Inserción de dependencias institucionales
    dependencias_data = [
        (
            "vicerrectorado_academico",
            "Vicerrectorado Académico y de Investigación",
            "vicerrectorado",
            "vicerrectorado.academico@ikiam.edu.ec",
            "Vicerrector/a Académico/a",
            "Lunes a Viernes 08h00 - 17h00",
            "Reingresos, homologaciones externas, cambios de carrera, terceras matrículas, prórrogas extraordinarias de titulación, régimen disciplinario y apelaciones académicas.",
            "https://www.ikiam.edu.ec/index.php/procesos-academicos/"
        ),
        (
            "admision_secretaria",
            "Dirección de Admisión y Registro / Secretaría General",
            "direccion",
            "admision@ikiam.edu.ec",
            "Director/a de Admisión y Registro",
            "Lunes a Viernes 08h00 - 17h00",
            "Admisión por primera vez, cupos SENESCYT / examen propio, asignación de aulas, legalización de matrículas ordinarias y extraordinarias, convalidación de títulos de bachiller extranjero, emisión de certificados y récords académicos.",
            "https://www.ikiam.edu.ec/index.php/admision/"
        ),
        (
            "bienestar_universitario",
            "Dirección de Bienestar Universitario (DBU)",
            "direccion",
            "bienestar@ikiam.edu.ec",
            "Director/a de Bienestar Universitario",
            "Lunes a Viernes 08h00 - 17h00",
            "Becas (excelencia, socioeconómica, pueblos y nacionalidades, discapacidad), ayudas económicas emergentes por catástrofe/calamidad, validación de certificados médicos (IESS/MSP/Privados) y asignación/revisión de quintil socioeconómico.",
            "https://www.ikiam.edu.ec/index.php/bienestar-universitario/"
        ),
        (
            "vinculacion_sociedad",
            "Dirección de Vinculación con la Sociedad (DVS)",
            "direccion",
            "vinculacion@ikiam.edu.ec",
            "Director/a de Vinculación con la Sociedad",
            "Lunes a Viernes 08h00 - 17h00",
            "Gestión, seguimiento y validación de las 400 horas obligatorias de prácticas preprofesionales (laborales y de servicio comunitario), convenios interinstitucionales y certificación oficial para titulación.",
            "https://www.ikiam.edu.ec/index.php/vinculacion/"
        ),
        (
            "unidad_titulacion",
            "Unidad de Titulación de Grado",
            "unidad",
            "titulacion@ikiam.edu.ec",
            "Responsable de Titulación",
            "Lunes a Viernes 08h00 - 17h00",
            "Modalidades de titulación (Proyecto de Integración Curricular o Examen Complexivo), prórrogas ordinarias (hasta 1 año) y extraordinarias (periodo de gracia), designación de tribunales y defensa de grado.",
            "https://www.ikiam.edu.ec/index.php/procesos-academicos/"
        ),
        (
            "coordinaciones_carrera",
            "Coordinaciones de Carrera de Pregrado",
            "coordinacion_carrera",
            "coordinaciones@ikiam.edu.ec",
            "Coordinadores de Carrera",
            "Lunes a Viernes 08h00 - 17h00",
            "Justificación de inasistencias (plazo 3 días hábiles), reprogramación de evaluaciones/tareas, retiro voluntario ordinario de asignaturas, designación de tutores de prácticas y acompañamiento de matrícula.",
            "https://www.ikiam.edu.ec/index.php/oferta-academica/"
        )
    ]

    cur.executemany("""
    INSERT INTO dependencias VALUES (?, ?, ?, ?, ?, ?, ?, ?);
    """, dependencias_data)

    # 2. Inserción de coordinaciones de carrera
    coordinaciones_data = [
        (
            "BIOCOM",
            "Licenciatura en Biocomercio",
            "Ciencias de la Vida",
            "biocomercio@ikiam.edu.ec",
            "Coordinación de Biocomercio",
            "Licenciado/a en Biocomercio"
        ),
        (
            "BIOTEC",
            "Ingeniería en Biotecnología",
            "Ciencias de la Vida",
            "biotecnologia@ikiam.edu.ec",
            "Coordinación de Biotecnología",
            "Ingeniero/a en Biotecnología"
        ),
        (
            "GEOCIEN",
            "Ingeniería en Geociencias",
            "Ciencias de la Tierra y el Agua",
            "geociencias@ikiam.edu.ec",
            "Coordinación de Geociencias",
            "Ingeniero/a en Geociencias"
        ),
        (
            "ECOSIST",
            "Ingeniería en Ecosistemas",
            "Ciencias de la Tierra y el Agua",
            "ecosistemas@ikiam.edu.ec",
            "Coordinación de Ecosistemas",
            "Ingeniero/a en Ecosistemas"
        ),
        (
            "AGROECO",
            "Ingeniería en Agroecología",
            "Ciencias de la Vida",
            "agroecologia@ikiam.edu.ec",
            "Coordinación de Agroecología",
            "Ingeniero/a en Agroecología"
        ),
        (
            "CIENAGUA",
            "Ingeniería en Ciencias del Agua",
            "Ciencias de la Tierra y el Agua",
            "cienciasdelagua@ikiam.edu.ec",
            "Coordinación de Ciencias del Agua",
            "Ingeniero/a en Ciencias del Agua"
        )
    ]

    cur.executemany("""
    INSERT INTO coordinaciones_carrera VALUES (?, ?, ?, ?, ?, ?);
    """, coordinaciones_data)

    # 3. Inserción de casos específicos por documento
    # Formato de tupla:
    # 0: codigo_caso
    # 1: documento_archivo
    # 2: nombre_tramite
    # 3: perfil_estudiante
    # 4: descripcion_caso
    # 5: dependencia_id
    # 6: autoridad_destinataria
    # 7: correo_destino
    # 8: plazo_reglamentario
    # 9: requisitos_adjuntos
    # 10: pasos_procedimiento
    # 11: enlace_descarga
    casos_data = [
        # --- INGRESO Y ADMISIÓN ---
        (
            "ingreso_primera_vez",
            "admision_bachiller_nacional",
            "Admisión por Primera Vez (Bachiller Nacional)",
            "Bachiller nacional recién graduado o aspirante por proceso general",
            "Ruta oficial para bachilleres ecuatorianos que ingresan por asignación de cupo a primer nivel o nivelación de carrera.",
            "admision_secretaria",
            "Dirección de Admisión y Registro",
            "admision@ikiam.edu.ec",
            "Dentro del cronograma oficial del periodo académico en curso",
            "Cédula de identidad ecuatoriana, Título de bachiller o acta de grado refrendada en MinEduc, Comprobante de asignación de cupo oficial.",
            "1. Registrarse en el portal de Admisión Ikiam en las fechas de convocatoria. 2. Rendir la evaluación de competencias. 3. Aceptar el cupo. 4. Enviar expediente digital a admision@ikiam.edu.ec.",
            "https://www.ikiam.edu.ec/index.php/admision/"
        ),
        (
            "ingreso_extranjero",
            "Solicitud-de-cambio-de-universidad.docx",
            "Admisión para Estudiantes Extranjeros",
            "Aspirante de nacionalidad extranjera con estudios secundarios o universitarios",
            "Procedimiento especial para postulantes extranjeros que desean ingresar a Ikiam convalidando sus estudios internacionales.",
            "admision_secretaria",
            "Dirección de Admisión y Registro / Vicerrectorado Académico",
            "admision@ikiam.edu.ec y vicerrectorado.academico@ikiam.edu.ec",
            "Hasta 30 días antes del inicio de matrículas ordinarias",
            "Pasaporte vigente o visa correspondiente, Título de bachiller debidamente legalizado o apostillado por el Convenio de La Haya, Homologación de título de bachiller emitida por el Ministerio de Educación del Ecuador, En caso de convalidación universitaria: récord académico y sílabos apostillados.",
            "1. Homologar el título de bachiller ante el MinEduc de Ecuador. 2. Llenar y firmar el formulario formal. 3. Remitir expediente apostillado completo en formato PDF a admision@ikiam.edu.ec y vicerrectorado.academico@ikiam.edu.ec.",
            "/documentos/Solicitud-de-cambio-de-universidad.docx"
        ),
        (
            "ingreso_homologacion_externa",
            "Solicitud-de-cambio-de-universidad.docx",
            "Homologación Externa (Transferencia desde otra Universidad)",
            "Estudiante de otra universidad pública o cofinanciada que desea transferirse a Ikiam",
            "Proceso para estudiantes que han aprobado al menos el primer semestre regular o 20% de créditos en otra institución de educación superior.",
            "vicerrectorado_academico",
            "Vicerrectorado Académico",
            "vicerrectorado.academico@ikiam.edu.ec",
            "Fechas oficiales según Calendario: del 1 al 18 de diciembre (o periodos intersemestrales)",
            "Formulario Solicitud de Cambio de Universidad (.docx), Récord académico oficial con calificaciones y número de horas/créditos, Certificado de no haber sido sancionado disciplinariamente, Sílabos o programas analíticos sellados por la universidad de origen (mínimo 80% de coincidencia temática).",
            "1. Descargar y firmar el formulario oficial de cambio de universidad. 2. Adjuntar récord oficial y sílabos sellados. 3. Enviar a vicerrectorado.academico@ikiam.edu.ec dentro del plazo de calendario. 4. La comisión de carrera emitirá el dictamen de equivalencia.",
            "/documentos/Solicitud-de-cambio-de-universidad.docx"
        ),
        (
            "ingreso_reingreso",
            "FORMATO-SOLICITUD-DE-REINGRESO.docx",
            "Reingreso a Carrera (Ex-alumnos Ikiam)",
            "Estudiante que interrumpió sus estudios en Ikiam por uno o más semestres",
            "Trámite formal para ex-estudiantes de Ikiam que abandonaron voluntariamente sus estudios y desean retomar su formación profesional.",
            "vicerrectorado_academico",
            "Vicerrectorado Académico / Consejo Académico",
            "vicerrectorado.academico@ikiam.edu.ec",
            "Hasta 30 días antes del inicio del periodo académico a cursar",
            "Formulario Solicitud de Reingreso (.docx) debidamente llenado, Copia de cédula o pasaporte, Historial académico descargado del sistema SGA.",
            "1. Descargar el formato oficial de reingreso. 2. Especificar el último semestre cursado y motivo de la interrupción. 3. Remitir al Vicerrectorado Académico. 4. Si la malla curricular cambió, se aplicará homologación interna.",
            "/documentos/FORMATO-SOLICITUD-DE-REINGRESO.docx"
        ),
        (
            "cambio_carrera_interno",
            "Solicitud-de-cambio-de-carrera.docx",
            "Cambio de Carrera Interno en Ikiam",
            "Estudiante regular de Ikiam que ha aprobado al menos el primer semestre",
            "Movilidad académica interna para cambiarse a otra oferta académica dentro de Ikiam cumpliendo el puntaje referencial.",
            "vicerrectorado_academico",
            "Vicerrectorado Académico",
            "vicerrectorado.academico@ikiam.edu.ec",
            "Durante las fechas fijadas en el Calendario Académico previo a matrículas",
            "Formulario de Cambio de Carrera (.docx), Historial de notas del SGA, Justificación escrita de la vocación hacia la nueva carrera.",
            "1. Verificar el cumplimiento del puntaje de corte de la carrera destino. 2. Completar y firmar el formulario oficial. 3. Enviar a vicerrectorado.academico@ikiam.edu.ec.",
            "/documentos/Solicitud-de-cambio-de-carrera.docx"
        ),

        # --- RETIRO DE ASIGNATURAS Y MATRÍCULAS ---
        (
            "retiro_ordinario",
            "Formato-Solicitud-Retiro-Voluntario-Asignatura.docx",
            "Retiro Voluntario Ordinario de Asignatura",
            "Estudiante que decide no continuar una materia en curso regular",
            "Retiro temprano para no perjudicar el promedio ni incurrir en faltas ni pérdida de gratuidad.",
            "coordinaciones_carrera",
            "Coordinación de Carrera correspondiente",
            "coordinacion_carrera (utilizar el correo institucional de su carrera)",
            "Dentro de los primeros 30 días calendario contados desde el inicio oficial de clases",
            "Formulario de Solicitud de Retiro Voluntario (.docx) firmado, Copia de cédula de identidad.",
            "1. Descargar el formulario oficial de retiro. 2. Detallar la(s) asignatura(s) a retirar. 3. Enviar por correo a la Coordinación de Carrera y registrar la solicitud en el Portal de Procesos Académicos.",
            "/documentos/Formato-Solicitud-Retiro-Voluntario-Asignatura.docx"
        ),
        (
            "retiro_fuerza_mayor",
            "Formato-Solicitud-Retiro-Voluntario-Asignatura.docx",
            "Retiro Extraordinario por Fuerza Mayor o Calamidad Doméstica",
            "Estudiante que atraviesa enfermedad grave sobrevenida o calamidad doméstica comprobada",
            "Retiro fuera del plazo ordinario de 30 días por motivos de caso fortuito o fuerza mayor personal/familiar.",
            "coordinaciones_carrera",
            "Coordinación de Carrera y Vicerrectorado Académico",
            "coordinacion_carrera y vicerrectorado.academico@ikiam.edu.ec",
            "Hasta antes de la fecha de inicio del periodo de exámenes finales",
            "Formulario de Solicitud de Retiro (.docx), Certificado médico validado por Bienestar Universitario (bienestar@ikiam.edu.ec) o Documentos probatorios de la calamidad.",
            "1. Obtener certificado médico o soporte legal de la calamidad. 2. Validar con Bienestar Universitario. 3. Remitir solicitud a Coordinación de Carrera y Vicerrectorado Académico.",
            "/documentos/Formato-Solicitud-Retiro-Voluntario-Asignatura.docx"
        ),
        (
            "retiro_segunda_matricula",
            "Formato-Solicitud-Retiro-Voluntario-Asignatura.docx",
            "Retiro Preventivo en Segunda Matrícula",
            "Estudiante que cursa segunda matrícula en riesgo de reprobar la materia",
            "Trámite urgente para evitar la reprobación en segunda matrícula, la cual causaría la pérdida definitiva de la carrera según el Art. 80 de la LOES.",
            "coordinaciones_carrera",
            "Coordinación de Carrera y Vicerrectorado Académico",
            "coordinacion_carrera y vicerrectorado.academico@ikiam.edu.ec",
            "Dentro de los primeros 30 días o por causa fortuita antes de exámenes finales",
            "Formulario de Retiro (.docx), Justificativos de fuerza mayor si es extemporáneo, Historial de matrícula.",
            "1. Tramitar con urgencia el retiro para que conste como 'Retirado' y no 'Reprobado'. 2. Adjuntar informe a DBU si existió causa médica o familiar.",
            "/documentos/Formato-Solicitud-Retiro-Voluntario-Asignatura.docx"
        ),

        # --- JUSTIFICACIÓN DE INASISTENCIAS ---
        (
            "justificacion_salud",
            "Formato-Solicitud-Justificacion-Inasistencias.docx",
            "Justificación de Faltas por Enfermedad o Salud",
            "Estudiante con problemas de salud, reposo médico u hospitalización",
            "Justificación oficial de inasistencias a clases o evaluaciones por afección médica.",
            "coordinaciones_carrera",
            "Coordinación de Carrera",
            "coordinacion_carrera (con copia a bienestar@ikiam.edu.ec)",
            "Máximo 3 días hábiles contados a partir de la reincorporación a clases",
            "Formulario de Justificación de Inasistencias (.docx), Certificado médico avalado por IESS/MSP o validado por el consultorio de Bienestar Universitario.",
            "1. Validar certificado en Bienestar Universitario (bienestar@ikiam.edu.ec). 2. Llenar el formulario indicando fechas y materias afectadas. 3. Enviar a Coordinación de Carrera para reprogramación de exámenes.",
            "/documentos/Formato-Solicitud-Justificacion-Inasistencias.docx"
        ),
        (
            "justificacion_calamidad",
            "Formato-Solicitud-Justificacion-Inasistencias.docx",
            "Justificación de Faltas por Calamidad Doméstica o Familiar",
            "Estudiante que sufrió accidente familiar, fallecimiento o evento fortuito",
            "Justificación formal de ausencias sin certificado médico mediante evidencias y carta motivada.",
            "coordinaciones_carrera",
            "Coordinación de Carrera",
            "coordinacion_carrera (utilizar el correo institucional de su carrera)",
            "Máximo 3 días hábiles tras la reincorporación a clases",
            "Formulario de Justificación (.docx), Carta motivada detallando los hechos, Documentos probatorios (actas de defunción, siniestro, etc.).",
            "1. Completar la solicitud detallando asignaturas y evaluaciones pendientes. 2. Remitir con los respaldos a la Coordinación de Carrera para coordinar reprogramación con los docentes.",
            "/documentos/Formato-Solicitud-Justificacion-Inasistencias.docx"
        ),

        # --- BECAS Y AYUDAS ECONÓMICAS ---
        (
            "beca_postulacion",
            "FO-GBU-40-V.5.0-Solicitud-de-becas-1.docx",
            "Postulación a Beca Universitaria",
            "Estudiante regular legalmente matriculado con mérito académico o vulnerabilidad",
            "Acceso a becas semestrales de colegiatura, manutención o transporte según reglamento de Bienestar Universitario.",
            "bienestar_universitario",
            "Dirección de Bienestar Universitario / Comisión de Becas",
            "bienestar@ikiam.edu.ec",
            "Durante el periodo de convocatoria semestral de becas (primer mes de clases)",
            "Formulario FO-GBU-40 (.docx), Ficha socioeconómica institucional, Documentos de respaldo (ingresos familiares, carné CONADIS, certificado de pueblo/nacionalidad).",
            "1. Descargar formulario FO-GBU-40. 2. Completar los campos de la ficha socioeconómica. 3. Enviar a bienestar@ikiam.edu.ec dentro del plazo de convocatoria.",
            "/documentos/FO-GBU-40-V.5.0-Solicitud-de-becas-1.docx"
        ),
        (
            "ayuda_economica_emergente",
            "FO-GBU-56-V.1.1Solicitud-de-ayudas-economicas-2.docx",
            "Solicitud de Ayuda Económica Emergente",
            "Estudiante en situación de vulnerabilidad extrema, accidente grave o calamidad",
            "Asignación de recursos extraordinarios para continuar los estudios universitarios ante contingencias críticas sobrevenidas.",
            "bienestar_universitario",
            "Dirección de Bienestar Universitario",
            "bienestar@ikiam.edu.ec",
            "En cualquier momento del periodo académico ante el suceso imprevisto",
            "Formulario FO-GBU-56 (.docx), Evidencias documentales de la emergencia (informes de salud, denuncias, certificados de afectación).",
            "1. Llenar el formulario FO-GBU-56. 2. Adjuntar soportes de la calamidad. 3. Remitir a bienestar@ikiam.edu.ec para evaluación social expedita.",
            "/documentos/FO-GBU-56-V.1.1Solicitud-de-ayudas-economicas-2.docx"
        ),

        # --- PRÁCTICAS PREPROFESIONALES ---
        (
            "practicas_inicio",
            "FO-GVI-29-V.3.1-Solicitud-para-realizar-practicas-preprofesionales.docx",
            "Inicio de Prácticas Preprofesionales (400 Horas)",
            "Estudiante que ha alcanzado el número de créditos habilitantes según su malla",
            "Autorización y registro para el inicio de prácticas preprofesionales laborales o de servicio comunitario.",
            "vinculacion_sociedad",
            "Dirección de Vinculación con la Sociedad (DVS)",
            "vinculacion@ikiam.edu.ec",
            "Previo al inicio de las actividades en la entidad receptora",
            "Formulario FO-GVI-29 (.docx) firmado, Carta de aceptación de la entidad receptora, Plan de trabajo preliminar FO-GVI-04.",
            "1. Descargar formulario FO-GVI-29. 2. Gestionar aceptación con empresa o entidad en convenio. 3. Remitir a vinculacion@ikiam.edu.ec para designación de tutor docente.",
            "/documentos/FO-GVI-29-V.3.1-Solicitud-para-realizar-practicas-preprofesionales.docx"
        ),
        (
            "practicas_certificado",
            "FO-GVI-30-V.2.0-Solicitud-de-certificado-de-practicas-preprofesionales-2.docx",
            "Certificado de Culminación de Prácticas (400 Horas)",
            "Estudiante que completó las 400 horas y entregó todos los informes aprobados",
            "Obtención de la certificación institucional obligatoria para la carpeta de titulación de grado.",
            "vinculacion_sociedad",
            "Dirección de Vinculación con la Sociedad (DVS)",
            "vinculacion@ikiam.edu.ec",
            "Al finalizar y aprobar los informes de prácticas (FO-GVI-06 y FO-GVI-07)",
            "Formulario FO-GVI-30 (.docx), Copia de los informes de estudiante y docente aprobados, Rúbrica de evaluación empresarial FO-GVI-36.",
            "1. Descargar FO-GVI-30. 2. Verificar que el tutor docente haya subido el informe de calificación. 3. Solicitar el certificado oficial a vinculacion@ikiam.edu.ec.",
            "/documentos/FO-GVI-30-V.2.0-Solicitud-de-certificado-de-practicas-preprofesionales-2.docx"
        )
    ]

    cur.executemany("""
    INSERT INTO casos_tramite_red (
        codigo_caso, documento_archivo, nombre_tramite, perfil_estudiante,
        descripcion_caso, dependencia_id, autoridad_destinataria, correo_destino,
        plazo_reglamentario, requisitos_adjuntos, pasos_procedimiento, enlace_descarga
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, casos_data)

    conn.commit()
    print(f"Base de datos {DB_PATH} creada con exito.")
    print(f"Dependencias: {cur.execute('SELECT COUNT(1) FROM dependencias').fetchone()[0]}")
    print(f"Coordinaciones: {cur.execute('SELECT COUNT(1) FROM coordinaciones_carrera').fetchone()[0]}")
    print(f"Casos Mapeados: {cur.execute('SELECT COUNT(1) FROM casos_tramite_red').fetchone()[0]}")
    conn.close()

if __name__ == "__main__":
    init_network_db()
