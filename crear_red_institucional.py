# -*- coding: utf-8 -*-
"""
Construcción integral de D:\ikiam_academic_chatbot\ikiam_network_org.db
Modela la Red Institucional REAL y VERIFICADA de la Universidad Regional Amazónica Ikiam:
- Autoridades 2026 (Rectorado, Vicerrectorado Académico, Dirección Académica, Secretaría General, DBU, DVS)
- 3 Facultades Oficiales (FCTA, FCV, FCSA) con Decanos reales y Delegados de Prácticas reales
- 10 Carreras vigentes con sus Directores/as y correos oficiales verificados + Tronco Común 1er nivel
- Nodos de pasos repetitivos compartidos en la red universitaria
- Casos de uso detallados enlazados a documentos reales (.docx / .pdf)
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
    CREATE TABLE facultades (
        codigo TEXT PRIMARY KEY,
        nombre TEXT NOT NULL,
        decano_nombre TEXT NOT NULL,
        decano_correo TEXT NOT NULL,
        delegado_practicas_nombre TEXT NOT NULL,
        delegado_practicas_correo TEXT NOT NULL,
        delegado_practicas_atencion TEXT NOT NULL,
        area_conocimiento TEXT NOT NULL
    );
    """)

    cur.execute("""
    CREATE TABLE coordinaciones_carrera (
        codigo TEXT PRIMARY KEY,
        carrera TEXT NOT NULL,
        facultad_codigo TEXT NOT NULL,
        facultad_nombre TEXT NOT NULL,
        director_nombre TEXT NOT NULL,
        correo_director TEXT NOT NULL,
        tronco_comun INTEGER DEFAULT 0,
        duracion_semestres INTEGER DEFAULT 8,
        puntaje_ref_iis2026 TEXT,
        cupos_iis2026 TEXT,
        url_oficial TEXT NOT NULL,
        FOREIGN KEY (facultad_codigo) REFERENCES facultades(codigo)
    );
    """)

    cur.execute("""
    CREATE TABLE dependencias (
        id TEXT PRIMARY KEY,
        nombre TEXT NOT NULL,
        tipo TEXT NOT NULL,
        autoridad_actual TEXT NOT NULL,
        correo_oficial TEXT NOT NULL,
        telefono_ext TEXT,
        horario_ubicacion TEXT,
        competencias_clave TEXT,
        enlace_web TEXT
    );
    """)

    cur.execute("""
    CREATE TABLE nodos_pasos_comunes (
        codigo_paso TEXT PRIMARY KEY,
        titulo TEXT NOT NULL,
        dependencia_responsable TEXT NOT NULL,
        correo_contacto TEXT NOT NULL,
        descripcion TEXT NOT NULL
    );
    """)

    cur.execute("""
    CREATE TABLE casos_tramite_red (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo_caso TEXT NOT NULL UNIQUE,
        categoria TEXT NOT NULL,
        documento_archivo TEXT NOT NULL,
        nombre_tramite TEXT NOT NULL,
        perfil_estudiante TEXT NOT NULL,
        descripcion_caso TEXT NOT NULL,
        dependencia_id TEXT NOT NULL,
        autoridad_destinataria TEXT NOT NULL,
        correo_destino TEXT NOT NULL,
        plazo_reglamentario TEXT NOT NULL,
        requisitos_adjuntos TEXT NOT NULL,
        pasos_red_codigos TEXT NOT NULL,
        pasos_procedimiento TEXT NOT NULL,
        requiere_selector_facultad INTEGER DEFAULT 0,
        normativa_respaldo TEXT NOT NULL,
        enlace_descarga TEXT NOT NULL,
        FOREIGN KEY (dependencia_id) REFERENCES dependencias(id)
    );
    """)

    # 1. 3 Facultades Oficiales (Datos verificados en ikiam.edu.ec/index.php/pregrado/, /autoridades/ y /vinculacion-3/)
    facultades_data = [
        (
            "FCTA",
            "Facultad de Ciencias de la Tierra y Agua (FCTA)",
            "Dr. Willin Gabriel Álvarez Irausquin",
            "willin.alvarez@ikiam.edu.ec",
            "Mgs. Wilson Bastidas",
            "practicaspreprofesionales.fcta@ikiam.edu.ec",
            "Quinto piso del edificio administrativo • Martes de 09h20 a 11h20",
            "Geociencias, Hidrología, Agroecología, Electromecánica y Energías Renovables"
        ),
        (
            "FCV",
            "Facultad de Ciencias de la Vida (FCV)",
            "Dra. Diana Estela Callejas de Valero",
            "diana.callejas@ikiam.edu.ec",
            "Mgs. Gabriela Loza Casa",
            "practicaspreprofesionales.fcv@ikiam.edu.ec",
            "Oficina 19 módulo de nivelación • Lunes 08h00-09h00 y Miércoles 11h30-12h30",
            "Biotecnología, Ecosistemas, Medicina Veterinaria y Manejo de Vida Silvestre"
        ),
        (
            "FCSA",
            "Facultad de Ciencias Socioambientales (FCSA)",
            "Dra. María Soledad Solórzano Venegas",
            "maria.solorzano@ikiam.edu.ec",
            "Mgs. Melissa Sánchez Ávila",
            "practicaspreprofesionales.fcsa@ikiam.edu.ec",
            "Oficina 20 de Nivelación • Viernes de 10h00 a 12h00",
            "Biocomercio, Arquitectura Sostenible, Educación en Ciencias Experimentales (ECX)"
        )
    ]
    cur.executemany("INSERT INTO facultades VALUES (?, ?, ?, ?, ?, ?, ?, ?);", facultades_data)

    # 2. 10 Carreras Vigentes por Facultad (Datos reales extraídos de cada página de carrera en ikiam.edu.ec y admisiones.txt)
    coordinaciones_data = [
        # --- FCTA ---
        (
            "GEOCIEN", "Ingeniería en Geociencias", "FCTA", "Facultad de Ciencias de la Tierra y Agua (FCTA)",
            "Jorge Ronny Espín Campos, Ph.D.", "jorge.espin@ikiam.edu.ec",
            1, 8, "802.44 pts", "40 cupos (20 1er sem / 20 niv.)",
            "https://www.ikiam.edu.ec/index.php/geociencias/"
        ),
        (
            "HIDRO", "Ingeniería en Hidrología", "FCTA", "Facultad de Ciencias de la Tierra y Agua (FCTA)",
            "MSc. Víctor Eduardo Espinoza Romero", "victor.espinoza@ikiam.edu.ec",
            1, 8, "808.82 pts", "35 cupos (15 1er sem / 20 niv.)",
            "https://www.ikiam.edu.ec/index.php/ingenieria-en-hidrologia/"
        ),
        (
            "AGROECO", "Ingeniería en Agroecología", "FCTA", "Facultad de Ciencias de la Tierra y Agua (FCTA)",
            "Franco Wilfredo Ramiro, Ph.D.", "wilfredo.franco@ikiam.edu.ec",
            0, 8, "780.05 pts", "35 cupos (25 1er sem / 10 niv.)",
            "https://www.ikiam.edu.ec/index.php/ingenieria-en-agroecologia/"
        ),
        (
            "ELECTROMEC", "Ingeniería en Electromecánica y Energías Renovables", "FCTA", "Facultad de Ciencias de la Tierra y Agua (FCTA)",
            "MSc. Galo Leonardo Cerda Mejía", "galo.cerda@ikiam.edu.ec",
            0, 8, "812.50 pts", "50 cupos (30 1er sem / 20 niv.)",
            "https://www.ikiam.edu.ec/index.php/ingenieria-en-electromecanica-y-energias-renovables/"
        ),
        # --- FCV ---
        (
            "BIOTEC", "Ingeniería en Biotecnología", "FCV", "Facultad de Ciencias de la Vida (FCV)",
            "Julio Lenin Rea Martínez, Ph.D.", "julio.rea@ikiam.edu.ec",
            1, 8, "842.21 pts", "50 cupos (20 1er sem / 30 niv.)",
            "https://www.ikiam.edu.ec/index.php/facultad_ciencias_vida/biotecnologia/"
        ),
        (
            "ECOSIST", "Ingeniería en Ecosistemas", "FCV", "Facultad de Ciencias de la Vida (FCV)",
            "Laura Inés Salazar Cotugno, Ph.D.", "laura.salazar@ikiam.edu.ec",
            1, 8, "811.38 pts", "35 cupos (10 1er sem / 25 niv.)",
            "https://www.ikiam.edu.ec/index.php/facultad_ciencias_vida/ecosistemas/"
        ),
        (
            "VETERINARIA", "Medicina Veterinaria y Manejo de Vida Silvestre", "FCV", "Facultad de Ciencias de la Vida (FCV)",
            "MSc. Verónica Gabriela Rivadeneyra Espín", "veronica.rivadeneyra@ikiam.edu.ec",
            0, 10, "853.91 pts", "60 cupos (40 1er sem / 20 niv.)",
            "https://www.ikiam.edu.ec/index.php/medicina-veterinaria-y-manejo-de-vida-silvestre-2/"
        ),
        # --- FCSA ---
        (
            "BIOCOM", "Licenciatura en Biocomercio", "FCSA", "Facultad de Ciencias Socioambientales (FCSA)",
            "Pedro Alberto Cango Puchaicela, Ph.D.", "pedro.cango@ikiam.edu.ec",
            0, 8, "740.92 pts", "30 cupos (15 1er sem / 15 niv.)",
            "https://www.ikiam.edu.ec/index.php/licenciatura-en-biocomercio/"
        ),
        (
            "ARQUITECTURA", "Arquitectura Sostenible", "FCSA", "Facultad de Ciencias Socioambientales (FCSA)",
            "MSc. Leonardo Francisco Coloma Casañas", "leonardo.coloma@ikiam.edu.ec",
            0, 8, "838.70 pts", "60 cupos (40 1er sem / 20 niv.)",
            "https://www.ikiam.edu.ec/index.php/facultad_ciencias_socio_ambientales/arquitectura_sostenible/"
        ),
        (
            "ECX", "Educación en Ciencias Experimentales (ECX)", "FCSA", "Facultad de Ciencias Socioambientales (FCSA)",
            "Jorge Manuel Ríos Obregón, Ph.D.", "jorge.rios@ikiam.edu.ec",
            0, 8, "Consultar convocatoria vigente", "Oferta oficial FCSA",
            "https://www.ikiam.edu.ec/index.php/pregado/educacion_ciencias_experimentales/"
        ),
    ]
    cur.executemany("INSERT INTO coordinaciones_carrera VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);", coordinaciones_data)

    # 3. Dependencias Institucionales Verificadas
    dependencias_data = [
        (
            "rectorado", "Rectorado Ikiam", "autoridad", "Roldán Torres Gutiérrez, Ph.D.",
            "roldan.torres@ikiam.edu.ec", "(06) 370-0040", "Campus Muyuna • Edificio Administrativo",
            "Máxima autoridad ejecutiva y presidente del Consejo Universitario.",
            "https://www.ikiam.edu.ec/index.php/autoridades/"
        ),
        (
            "vicerrectorado_academico", "Vicerrectorado Académico", "vicerrectorado",
            "Zulay Marina Niño Ruiz, Ph.D.", "zulay.nino@ikiam.edu.ec", "(06) 370-0040",
            "Lunes a Viernes 08h30 - 17h00",
            "Reingresos, homologaciones externas, cambios de carrera, terceras matrículas, matrículas especiales y resoluciones académicas superiores.",
            "https://www.ikiam.edu.ec/index.php/procesos-academicos/"
        ),
        (
            "direccion_academica", "Dirección Académica / Unidad de Admisión y Registro", "direccion",
            "Dr. Jorge Alejandro Batres Quevedo", "direccion.academica@ikiam.edu.ec",
            "+593 (06) 299-9160 Ext. 322", "Lunes a Viernes 08h30 - 17h00 • Campus Muyuna",
            "Recepción oficial de solicitudes de homologación, cambio de carrera, cambio de IES, reingreso, retiros y registro en SGA.",
            "https://www.ikiam.edu.ec/index.php/procesos-academicos/"
        ),
        (
            "oficina_admision", "Oficina de Admisión Pregrado", "unidad",
            "Unidad de Admisión y Registro", "oficina.admision@ikiam.edu.ec",
            "+593 (06) 299-9160 Ext. 322 • WhatsApp 0982142499", "Lunes a Viernes 08h30 - 17h00",
            "Proceso Destino Ikiam, Registro Nacional SENESCYT, evaluaciones de admisión, simulador (eval.ikiam.edu.ec), asignación de cupos y nivelación.",
            "https://www.ikiam.edu.ec/index.php/admisiones/"
        ),
        (
            "secretaria_general", "Secretaría General", "secretaria",
            "Abg. Henry Alberto Cuji Coello, Mgs.", "secretaria.general@ikiam.edu.ec",
            "(06) 370-0040 / (06) 299-9160", "Lunes a Viernes 08h30 - 17h00",
            "Certificaciones oficiales estudiantiles, actas y resoluciones del Consejo Universitario, copias certificadas (facturación: daniela.soria@ikiam.edu.ec).",
            "https://www.ikiam.edu.ec/"
        ),
        (
            "bienestar_universitario", "Dirección de Bienestar Universitario (DBU)", "direccion",
            "Lcdo. Manuel de Jesús Seraquive Poma", "bienestar.universitario@ikiam.edu.ec",
            "+593 (06) 370-0040 Ext. 260", "Lunes a Viernes 08h30 - 17h00",
            "Becas (FO-GBU-40), ayudas económicas excepcionales (FO-GBU-56), impugnaciones (FO-GBU-69), ficha socioeconómica, exoneración/quintiles de aranceles y trabajo social.",
            "https://www.ikiam.edu.ec/index.php/bienestaruniversitario/becas-y-ayudas-economicas/"
        ),
        (
            "centro_salud", "Centro de Salud / Dispensario Médico DBU", "unidad",
            "Dispensario Médico y Psicológico Ikiam", "centro.salud@ikiam.edu.ec",
            "(06) 370-0040 Med. Gral Ext. 258 • Ocupacional Ext. 259 • Psicología Ext. 257 • Odontología Ext. 263",
            "Lunes a Viernes 08h30 - 17h00 • Campus Muyuna (Gratuito)",
            "Atención médica/odontológica/psicológica gratuita y VALIDACIÓN obligatoria de certificados médicos externos (IESS/MSP/particulares).",
            "https://www.ikiam.edu.ec/index.php/servicios-institucionales/"
        ),
        (
            "vinculacion_sociedad", "Dirección de Vinculación con la Sociedad (DVS)", "direccion",
            "Mgs. Jessica Medina Arias (Ext. 247)", "practicas.preprofesionales@ikiam.edu.ec",
            "+593 (06) 299-9160 / (06) 370-0040 Ext. 295-298", "Edificio de Servicios Académicos, 5to Piso (vinculacion@ikiam.edu.ec)",
            "Prácticas laborales y comunitarias (400h / IT-GVI-05), convenios interinstitucionales, ayudantías, certificación final FO-GVI-30 y plataforma JXBS/DVS.",
            "https://www.ikiam.edu.ec/index.php/practicas-pre-profesionales/"
        ),
        (
            "centro_idiomas", "Centro de Idiomas (CDI)", "unidad",
            "Coordinación Centro de Idiomas", "centro.idiomas@ikiam.edu.ec",
            "(06) 370-0040 (ref. docente daniel.robles@ikiam.edu.ec)", "Campus Muyuna",
            "Suficiencia de Inglés B1 para titulación, 6 niveles regulares (100h c/u), Placement Test (ubicación) y Exit Test (salida).",
            "https://www.ikiam.edu.ec/index.php/centro-de-idiomas/"
        ),
        (
            "escuela_posgrados", "Escuela de Posgrados (EPG)", "direccion",
            "Corina Campos (corina.campos@ikiam.edu.ec)", "escuela.posgrados@ikiam.edu.ec",
            "(06) 370-0040 Ext. 223", "Lunes a Viernes 08h30 - 17h00",
            "Maestrías híbridas (Cambio Climático, Arquitectura Sostenible, Biotecnología, Ciencias de la Ingeniería, Hidráulica Ambiental, Emprendimiento).",
            "https://www.ikiam.edu.ec/index.php/posgrado/"
        ),
        (
            "relaciones_interinstitucionales", "Dirección de Relaciones Interinstitucionales", "direccion",
            "Movilidad y Estudiantes Internacionales", "relaciones.interinstitucionales@ikiam.edu.ec",
            "(+593) (2) 2506-726", "Lunes a Viernes 08h30 - 17h00",
            "Asesoría a estudiantes extranjeros, visas de estudiante, movilidad académica internacional e instrumentos de cooperación.",
            "https://www.ikiam.edu.ec/index.php/informacion-util-y-preguntas-frecuentes/"
        ),
        (
            "dti_biblioteca", "Servicios TI (DTI) y Biblioteca General Koha", "unidad",
            "DTI / Centro de Servicios Bibliotecarios", "soporte@ikiam.edu.ec",
            "(06) 370-0040 (Biblioteca: biblioteca@ikiam.edu.ec)", "Biblioteca: Lunes a Viernes 08h00 - 17h00",
            "Activación de cuentas institucionales @ikiam.edu.ec, mesa de ayuda GLPI, SGA, Aula Virtual Moodle, catálogo Koha y paz y salvo biblioteca.",
            "https://www.ikiam.edu.ec/index.php/serviciosti/"
        ),
        (
            "coordinaciones_carrera", "Direcciones / Coordinaciones de Carrera (Por Facultad)", "coordinacion_carrera",
            "Directores/as de Carrera (FCTA, FCV, FCSA)", "direccion.academica@ikiam.edu.ec",
            "(06) 370-0040", "Campus Muyuna (por Facultad)",
            "Justificación de faltas, reprogramación de evaluaciones, retiro de asignaturas, tutorías y análisis de tronco común.",
            "https://www.ikiam.edu.ec/index.php/pregrado/"
        )
    ]
    cur.executemany("INSERT INTO dependencias VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);", dependencias_data)

    # 4. Nodos de Pasos Comunes Reutilizables en la Red Universitaria
    pasos_comunes = [
        (
            "validacion_medica_dbu",
            "Validar certificado médico en Centro de Salud DBU",
            "Centro de Salud / Dispensario Médico Ikiam",
            "centro.salud@ikiam.edu.ec",
            "Todo certificado médico (IESS, MSP o médico particular) debe ser validado por el dispensario médico de Bienestar Universitario antes o al momento de justificar faltas o pedir retiro médico."
        ),
        (
            "solicitud_sga_y_procesos",
            "Registrar solicitud en SGA / Formulario en línea de Dirección Académica",
            "Dirección Académica / DTI",
            "direccion.academica@ikiam.edu.ec",
            "Además del documento PDF firmado (.docx convertido), muchos trámites exigen ingresar la petición en el Sistema de Gestión Académica (módulo solicitudes MA-GTI-16) o en el formulario web oficial de Procesos Académicos."
        ),
        (
            "no_impedimentos_3ra_deudas",
            "Verificar no tener terceras matrículas ni deudas (Paz y Salvo)",
            "Secretaría General / Biblioteca / Financiero",
            "secretaria.general@ikiam.edu.ec",
            "Para movilidad, cambio de carrera/IES o titulación se exige carta/certificación de no tener terceras matrículas pendientes, no tener sanciones disciplinarias y no adeudar a biblioteca (biblioteca@ikiam.edu.ec), laboratorios ni financiero."
        ),
        (
            "apostilla_mineduc_exterior",
            "Legalización / Apostilla y Homologación MinEduc o IES reconocida",
            "Relaciones Interinstitucionales / Admisión",
            "relaciones.interinstitucionales@ikiam.edu.ec",
            "Documentos extranjeros (título de bachiller homologado en MinEduc para primer ingreso, o récord/malla/sílabos apostillados + permiso domiciliario o pasaporte con visa de estudiante para cambio de IES extranjera)."
        ),
        (
            "delegado_practicas_facultad",
            "Canalización obligatoria al Delegado de Prácticas de tu Facultad",
            "Delegados de Facultad DVS (FCTA / FCV / FCSA)",
            "practicaspreprofesionales.fcta@ikiam.edu.ec / .fcv@ / .fcsa@",
            "Según el Instructivo IT-GVI-05 (2026), tras enviar FO-GVI-29 a DVS, el estudiante tiene 5 días hábiles para remitir FO-GVI-31 al correo de prácticas de su Facultad, y al finalizar remite el expediente al Delegado antes de subirlo a DVS."
        )
    ]
    cur.executemany("INSERT INTO nodos_pasos_comunes VALUES (?, ?, ?, ?, ?);", pasos_comunes)

    # 5. Catálogo completo de casos conectados en red
    # (codigo_caso, categoria, documento_archivo, nombre_tramite, perfil_estudiante, descripcion_caso,
    #  dependencia_id, autoridad_destinataria, correo_destino, plazo_reglamentario, requisitos_adjuntos,
    #  pasos_red_codigos, pasos_procedimiento, requiere_selector_facultad, normativa_respaldo, enlace_descarga)
    casos_data = [
        # --- INGRESO Y ADMISIÓN ---
        (
            "ingreso_primera_vez", "Ingreso y Admisión", "admision_bachiller_nacional",
            "Admisión por Primera Vez — Bachiller Nacional (Proceso 1PA 2027)",
            "Bachiller ecuatoriano / residente que postula por primera vez a una carrera de grado o nivelación.",
            "Ingreso por el sistema nacional + proceso propio Destino Ikiam (50% promedio graduación + 50% examen de admisión). Estudiar pregrado en Ikiam en 1ra matrícula es gratuito; nota: no existen residencias estudiantiles propias.",
            "oficina_admision", "Oficina de Admisión Ikiam",
            "oficina.admision@ikiam.edu.ec (Ext. 322 • WhatsApp 0982142499)",
            "Registro Nacional: 1ra Etapa 24-28/11/2026, 2da Etapa 1-5/12/2026; Inscripción en eval.ikiam.edu.ec: 18/12/2026 al 24/1/2027; Simulador: 25/1-19/2/2027; Postulación: 24/3-1/4/2027.",
            "Registro Nacional SENESCYT completo, Título de bachiller / acta refrendada MinEduc, Cédula de identidad, Inscripción en eval.ikiam.edu.ec, Test orientación vocacional (4-9/4/2027).",
            "solicitud_sga_y_procesos",
            "1. Completar el Registro Nacional en las fechas de convocatoria SENESCYT. 2. Inscribirse directamente en eval.ikiam.edu.ec (18/12/2026 al 24/1/2027). 3. Practicar en el simulador (25/1 al 19/2/2027) y rendir examen (presencial en Campus si no dispones de equipo/internet). 4. Postular y aceptar cupo (hasta 3/4/2027) y realizar Test vocacional.",
            0, "PR-GAR-09-V.1.0 / PR-GAR-08-V.1.0 / Web Admisiones 1PA 2027", "https://www.ikiam.edu.ec/index.php/admisiones/"
        ),
        (
            "ingreso_extranjero", "Ingreso y Admisión", "Solicitud-de-cambio-de-universidad.docx",
            "Ingreso / Movilidad para Estudiantes Extranjeros",
            "Aspirantes internacionales (primer ingreso con bachillerato del exterior o transferencia desde universidad extranjera).",
            "Existen 2 vías según estudios previos: (A) Si ingresas desde colegio exterior a 1er nivel, homologar título de bachiller en MinEduc y participar en Admisión (oficina.admision@ikiam.edu.ec). (B) Si ya cursaste materias universitarias en el exterior, aplica Cambio de Universidad Extranjera ante Vicerrectorado Académico.",
            "relaciones_interinstitucionales", "Vicerrector/a Académico/a / Dirección Académica / Relaciones Interinstitucionales",
            "direccion.academica@ikiam.edu.ec, oficina.admision@ikiam.edu.ec y relaciones.interinstitucionales@ikiam.edu.ec",
            "Para cambio/homologación 1PAO 2027: recepción del 1 al 18 de diciembre de 2026. Para admisión general: acorde a cronograma 1PA 2027.",
            "Pasaporte y permiso domiciliario definitivo o visa de estudiante, Récord académico legalizado/apostillado, Constancia fehaciente de universidad reconocida en el exterior, Copia certificada de malla curricular y sílabos (>=80% similitud) o título de bachiller homologado en MinEduc.",
            "apostilla_mineduc_exterior,solicitud_sga_y_procesos",
            "1. Si vienes de secundaria: homologa tu título de bachiller en el MinEduc y escribe a oficina.admision@ikiam.edu.ec y relaciones.interinstitucionales@ikiam.edu.ec. 2. Si vienes de universidad extranjera: descarga Solicitud-de-cambio-de-universidad.docx dirigida a la Vicerrectora Académica (Dra. Zulay Niño). 3. Adjunta pasaporte, visa de estudiante, récord, malla y sílabos legalizados del 1 al 18 de diciembre vía Procesos Académicos y direccion.academica@ikiam.edu.ec.",
            0, "Web Procesos Académicos Ikiam / Preguntas Frecuentes / Calendario Homologación 1PAO2027", "/documentos/Solicitud-de-cambio-de-universidad.docx"
        ),
        (
            "ingreso_homologacion_externa", "Ingreso y Admisión", "Solicitud-de-cambio-de-universidad.docx",
            "Cambio de Universidad / Homologación Externa (IES Nacional Pública o Particular)",
            "Estudiante proveniente de otra universidad ecuatoriana (UCE, EPN, ESPE, Estatal o particular).",
            "Regulado por Art. 96 b) y c) del Reglamento de Régimen Académico (CES) y Calendario 1PAO 2027: debes haber cursado >=2 periodos académicos ordinarios y tener al menos 2 materias homologables (>=80% similitud silábica). Si vienes de IES particular, debes someterte además a asignación de cupos y puntaje de cohorte.",
            "direccion_academica", "Vicerrector/a Académico/a (Dra. Zulay Marina Niño Ruiz)",
            "direccion.academica@ikiam.edu.ec (y Formulario oficial en Procesos Académicos)",
            "Recepción documental 1PAO 2027: del 1 al 18 de diciembre de 2026 (14 días hábiles).",
            "Carta/Formato Solicitud de Cambio de Universidad (.docx) con carrera origen/destino/semestres/materias/contactos, Cédula y papeleta de votación en una sola hoja, Récord académico legalizado, Malla curricular certificada, Sílabos sellados (>=80% afinidad), Carta de no tener impedimentos (sin 3ras matrículas ni deudas).",
            "no_impedimentos_3ra_deudas,solicitud_sga_y_procesos",
            "1. Descarga y llena Solicitud-de-cambio-de-universidad.docx dirigida a la Vicerrectora Académica (Zulay Niño Ruiz, Ph.D.). 2. Reúne los 6 documentos habilitantes sellados de tu universidad de origen. 3. Entrega mediante el formulario web de Procesos Académicos / direccion.academica@ikiam.edu.ec entre el 1 y 18 de diciembre de 2026. 4. Validación del 4-13 ene, análisis por docentes 21 ene-19 feb y examen de cohorte/conocimientos si aplica (15-26 feb 2027).",
            0, "Art. 96 RRA CES / PR-GAR-04 / Calendario-de-Homologacion-1PAO2027.pdf", "/documentos/Solicitud-de-cambio-de-universidad.docx"
        ),
        (
            "ingreso_reingreso", "Ingreso y Admisión", "FORMATO-SOLICITUD-DE-REINGRESO.docx",
            "Reingreso / Continuidad de Estudios (Ex-alumnos Ikiam)",
            "Ex-estudiante de Ikiam que suspendió o se retiró por uno o más periodos académicos.",
            "Aplica tanto para retomar directamente si tu malla sigue vigente como para aplicar homologación interna si la malla cambió durante tu ausencia (PR-GAR-03).",
            "direccion_academica", "Vicerrectorado Académico / Dirección Académica",
            "direccion.academica@ikiam.edu.ec (Formulario Reingreso en Procesos Académicos)",
            "Previo al inicio del periodo académico según calendario oficial.",
            "Formato Solicitud de Reingreso (.docx) completo indicando último PAO aprobado/retirado y carrera, Copia de cédula o pasaporte, Récord/historial SGA.",
            "no_impedimentos_3ra_deudas,solicitud_sga_y_procesos",
            "1. Descarga FORMATO-SOLICITUD-DE-REINGRESO.docx dirigido al Vicerrectorado Académico. 2. Verifica en Biblioteca y Financiero no mantener deudas ni sanciones disciplinarias. 3. Envía el formulario e historial a direccion.academica@ikiam.edu.ec y regístralo en el portal de Procesos Académicos.",
            0, "PR-GAR-03-V.1.0 / Web Procesos Académicos", "/documentos/FORMATO-SOLICITUD-DE-REINGRESO.docx"
        ),

        # --- CAMBIO DE CARRERA Y TRONCO COMÚN ---
        (
            "cambio_carrera_tronco_comun", "Movilidad y Cambio de Carrera", "Solicitud-de-cambio-de-carrera.docx",
            "Cambio entre Carreras de Tronco Común (1er Nivel)",
            "Estudiante de primer nivel en Ingeniería en Hidrología, Biotecnología, Geociencias o Ecosistemas.",
            "EXCEPCIÓN ART. 97 RRA CES: Las carreras de Hidrología, Biotecnología, Geociencias y Ecosistemas mantienen tronco común hasta el primer nivel; conforme Art. 97 del RRA no se considera cambio de carrera regular sino transición dentro de tronco común.",
            "direccion_academica", "Dirección Académica y Directores de Carrera involucrados",
            "direccion.academica@ikiam.edu.ec",
            "Del 1 al 18 de diciembre de 2026 (Calendario de Homologación / Cambio de Carrera 1PAO 2027).",
            "Solicitud de cambio de carrera (.docx) indicando transición de tronco común, Cédula y papeleta en una hoja, Récord del 1er nivel.",
            "solicitud_sga_y_procesos",
            "1. Verifica que tanto tu carrera actual como la destino estén entre las 4 de tronco común (Hidrología, Biotecnología, Geociencias, Ecosistemas) y estés en primer nivel. 2. Descarga Solicitud-de-cambio-de-carrera.docx y detalla las materias de tronco común aprobadas. 3. Remite vía formulario web y direccion.academica@ikiam.edu.ec del 1 al 18 de diciembre.",
            1, "Art. 97 RRA CES / Web Procesos Académicos Ikiam", "/documentos/Solicitud-de-cambio-de-carrera.docx"
        ),
        (
            "cambio_carrera_interno", "Movilidad y Cambio de Carrera", "Solicitud-de-cambio-de-carrera.docx",
            "Cambio de Carrera Interno Estándar en Ikiam",
            "Estudiante regular de Ikiam que desea cambiarse fuera de tronco común o desde 2do nivel.",
            "Art. 96 a) RRA CES: Procede tras cursar al menos 1 PAO, aprobar >50% de asignaturas del periodo, tener al menos 1 homologable y cumplir el puntaje promedio de cohorte de la carrera destino. Para gratuidad se permite un cambio por una sola vez.",
            "direccion_academica", "Vicerrector/a Académico/a (Dra. Zulay Marina Niño Ruiz)",
            "direccion.academica@ikiam.edu.ec (Formulario Cambio de Carrera)",
            "Del 1 al 18 de diciembre de 2026 (Calendario 1PAO 2027).",
            "Solicitud de Cambio de Carrera (.docx) indicando carrera actual/destino/semestres/materias/contactos, Cédula y papeleta en una hoja, Carta de no tener 3ras matrículas ni deudas, Récord académico.",
            "no_impedimentos_3ra_deudas,solicitud_sga_y_procesos",
            "1. Verifica que cumples >50% aprobado y puntaje de corte de la carrera destino (ej. Veterinaria 853.91, Biotecnología 842.21, Arquitectura 838.7, Biocomercio 740.92). 2. Descarga Solicitud-de-cambio-de-carrera.docx. 3. Adjunta los requisitos y envía del 1 al 18 de diciembre a direccion.academica@ikiam.edu.ec y en el portal web.",
            1, "Art. 96 a) RRA CES / Calendario-de-Homologacion-1PAO2027.pdf", "/documentos/Solicitud-de-cambio-de-carrera.docx"
        ),

        # --- RETIROS Y MATRÍCULAS ---
        (
            "retiro_ordinario", "Retiros, Matrículas y Gratuidad", "Formato-Solicitud-Retiro-Voluntario-Asignatura.docx",
            "Retiro Voluntario Ordinario de Asignatura(s) (Art. 45 RRA)",
            "Estudiante regular dentro del plazo inicial que desea retirar materias sin perder gratuidad.",
            "Permite retirar asignaturas sin contabilizar para pérdida definitiva de gratuidad. IMPORTANTE EN 2PA 2026: El periodo ordinario fijado en el calendario vigente fue del 26 al 30 de octubre de 2026; fuera de ese plazo solo procede retiro extraordinario por caso fortuito/fuerza mayor.",
            "coordinaciones_carrera", "Director/a de Carrera de tu Facultad + Dirección Académica",
            "Director/a de Carrera (FCTA/FCV/FCSA) y direccion.academica@ikiam.edu.ec",
            "Dentro de los primeros 30 días / fecha límite calendario (en 2PA 2026: 26 al 30 de octubre de 2026).",
            "Formato-Solicitud-Retiro-Voluntario-Asignatura.docx completo (código, asignatura, paralelo y docente), Cédula.",
            "solicitud_sga_y_procesos",
            "1. Descarga Formato-Solicitud-Retiro-Voluntario-Asignatura.docx. 2. Identifica tu Facultad y dirige la carta a tu Director/a de Carrera. 3. Remite al correo oficial de tu Director/a de Carrera con copia a direccion.academica@ikiam.edu.ec y registra la solicitud en SGA.",
            1, "Art. 45 RRA CES / Calendario 2PA 2026", "/documentos/Formato-Solicitud-Retiro-Voluntario-Asignatura.docx"
        ),
        (
            "retiro_fuerza_mayor", "Retiros, Matrículas y Gratuidad", "Formato-Solicitud-Retiro-Voluntario-Asignatura.docx",
            "Retiro Extraordinario por Caso Fortuito, Salud Grave o Calamidad Doméstica",
            "Estudiante con enfermedad grave sobrevenida o calamidad comprobada fuera del plazo ordinario.",
            "Cuando la fecha ordinaria de retiro ya venció (como después del 30/10/2026 en el 2PA 2026), puedes solicitar retiro extraordinario justificado antes de exámenes finales (3/3/2027) adjuntando pruebas médicas o de calamidad.",
            "coordinaciones_carrera", "Director/a de Carrera + Dirección Académica / Vicerrectorado Académico",
            "Director/a de Carrera + direccion.academica@ikiam.edu.ec (si es médico, validar en centro.salud@ikiam.edu.ec)",
            "Antes del inicio del periodo de exámenes finales (en 2PA 2026: antes del 3 de marzo de 2027).",
            "Formato de Retiro Voluntario (.docx) explicando el caso fortuito, Certificado médico validado por Centro de Salud DBU o actas/denuncias/certificados de la calamidad, Informe social si requiere DBU (bienestar.universitario@ikiam.edu.ec).",
            "validacion_medica_dbu,solicitud_sga_y_procesos",
            "1. Si es causal de salud, valida primero el certificado en Centro de Salud (centro.salud@ikiam.edu.ec). Si es calamidad familiar/catástrofe, reúne documentos probatorios y apoya con Trabajo Social DBU. 2. Llena Formato-Solicitud-Retiro-Voluntario-Asignatura.docx dirigido al Director/a de tu Carrera. 3. Envía a tu Director/a de Carrera y direccion.academica@ikiam.edu.ec para trámite al Vicerrectorado Académico.",
            1, "Formato-Solicitud-Retiro-Voluntario-Asignatura.docx / RRA / Calendario 2PA 2026", "/documentos/Formato-Solicitud-Retiro-Voluntario-Asignatura.docx"
        ),
        (
            "retiro_segunda_matricula", "Retiros, Matrículas y Gratuidad", "Formato-Solicitud-Retiro-Voluntario-Asignatura.docx",
            "Retiro Preventivo en Segunda Matrícula / Solicitud de Tercera Matrícula",
            "Estudiante cursando segunda matrícula en riesgo académico o que solicita tercera matrícula excepcional.",
            "Conforme Art. 80/84 LOES, reprobar una segunda matrícula conlleva el riesgo de agotar la última oportunidad (tercera matrícula solo es excepcional por causa justificada ante Vicerrectorado y conlleva cobro de aranceles diferenciados por quintil). Si estás en curso y sufriste calamidad, el retiro justificado evita que conste como reprobación.",
            "vicerrectorado_academico", "Director/a de Carrera + Vicerrectora Académica (Zulay Niño Ruiz, Ph.D.)",
            "Director/a de Carrera, direccion.academica@ikiam.edu.ec y zulay.nino@ikiam.edu.ec",
            "Retiro por fuerza mayor: antes de exámenes finales (3/3/2027). Solicitud de 3ra matrícula ordinaria para 2PA 2026 venció el 24/9/2026 (siguiente periodo según calendario 1PAO 2027).",
            "Formato de Retiro (.docx) con tabla de asignaturas y docente, Evidencias médicas/calamidad validadas en DBU, Ficha socioeconómica actualizada para quintil en aranceles.",
            "validacion_medica_dbu,solicitud_sga_y_procesos",
            "1. Si aún estás cursando el semestre actual y tienes calamidad/enfermedad, NO dejes que termine con nota reprobatoria: tramita retiro extraordinario validado con DBU (centro.salud@ikiam.edu.ec / bienestar.universitario@ikiam.edu.ec). 2. Dirige la solicitud a tu Director/a de Carrera y a la Vicerrectora Académica. 3. Si llegases a requerir tercera matrícula excepcional, deberás ingresar la solicitud motivada con informe de DBU antes de la fecha límite del próximo periodo.",
            1, "Art. 80 LOES / Res. 032 Tabla Arancelaria / Calendario 2PA 2026", "/documentos/Formato-Solicitud-Retiro-Voluntario-Asignatura.docx"
        ),
        (
            "aranceles_gratuidad", "Retiros, Matrículas y Gratuidad", "30032022-Resolucion-Nro.-032-SG-SE-007-CU-IKIAM-2022-Aprobacion-Tabla-Arancelaria.pdf",
            "Pérdida de Gratuidad y Tabla Arancelaria (Segundas / Terceras Matrículas)",
            "Estudiante que reprobó una o más asignaturas o perdió parcialmente la gratuidad.",
            "Art. 80 LOES y Res. 032-SG-SE-007-CU-IKIAM-2022: La gratuidad cubre únicamente 1ra matrícula regular. Al perder una materia, el cobro combina matrícula base + arancel por crédito/hora de la asignatura, diferenciado según el quintil socioeconómico registrado en DBU.",
            "bienestar_universitario", "Dirección Financiera / Dirección de Bienestar Universitario",
            "bienestar.universitario@ikiam.edu.ec y direccion.academica@ikiam.edu.ec",
            "Durante periodo de matriculación ordinaria/extraordinaria del SGA.",
            "Liquidación generada en el Sistema de Gestión Académica (SGA), Ficha socioeconómica actualizada en DBU (para tarifa mínima según quintil), Comprobante de depósito/transferencia bancaria.",
            "solicitud_sga_y_procesos",
            "1. Actualiza tu ficha socioeconómica en Bienestar Universitario (bienestar.universitario@ikiam.edu.ec) para asegurar tu quintil correcto o exoneración por vulnerabilidad extrema. 2. Genera tu liquidación en el SGA al matricularte. 3. Realiza el depósito/transferencia en la cuenta oficial indicada en la liquidación.",
            0, "Art. 80 LOES / Res. 032-SG-SE-007-CU-IKIAM-2022", "/documentos/30032022-Resolucion-Nro.-032-SG-SE-007-CU-IKIAM-2022-Aprobacion-Tabla-Arancelaria.pdf"
        ),

        # --- JUSTIFICACIÓN DE INASISTENCIAS ---
        (
            "justificacion_salud", "Asistencia y Justificaciones", "Formato-Solicitud-Justificacion-Inasistencias.docx",
            "Justificación de Faltas y Exámenes por Enfermedad / Salud",
            "Estudiante que faltó a clases, evaluaciones o prácticas por enfermedad personal o atención médica.",
            "Asistencia mínima obligatoria: 70%. Plazo improrrogable: 3 días hábiles tras tu reincorporación. Paso previo indispensable en la red: validar el certificado médico en el Centro de Salud DBU de Ikiam.",
            "coordinaciones_carrera", "Director/a de Carrera de tu Facultad (previa validación de Centro de Salud DBU)",
            "Paso 1: centro.salud@ikiam.edu.ec | Paso 2: Correo del Director/a de tu Carrera",
            "Máximo 3 días hábiles contados desde el reintegro a clases.",
            "Formato-Solicitud-Justificacion-Inasistencias.docx marcado causal Médica/Salud con tabla de Asignaturas/Docentes/Fechas, Certificado médico (IESS/MSP/particular) VALIDADO por Centro de Salud Ikiam.",
            "validacion_medica_dbu",
            "1. Acude o escribe a Centro de Salud DBU (centro.salud@ikiam.edu.ec, Ext. 258/259) para validar tu certificado médico. 2. Descarga Formato-Solicitud-Justificacion-Inasistencias.docx, marca 'Médica / Salud' y detalla asignaturas y fechas. 3. Envía el formulario y el certificado validado al correo de tu Director/a de Carrera (FCTA, FCV o FCSA) para autorizar reprogramación de evaluaciones.",
            1, "Formato-Solicitud-Justificacion-Inasistencias.docx / RRA Ikiam", "/documentos/Formato-Solicitud-Justificacion-Inasistencias.docx"
        ),
        (
            "justificacion_calamidad", "Asistencia y Justificaciones", "Formato-Solicitud-Justificacion-Inasistencias.docx",
            "Justificación de Faltas por Calamidad Doméstica o Fuerza Mayor",
            "Estudiante que faltó por fallecimiento familiar, hospitalización de familiar, accidente o siniestro.",
            "No requiere certificado médico personal: se justifica mediante la causal 'Calamidad doméstica o fuerza mayor comprobada' con soportes documentales y carta dirigida al Director/a de Carrera.",
            "coordinaciones_carrera", "Director/a de Carrera según Facultad (FCTA, FCV o FCSA)",
            "Correo del Director/a de tu Carrera",
            "Máximo 3 días hábiles tras la reincorporación.",
            "Formato-Solicitud-Justificacion-Inasistencias.docx marcado causal Calamidad doméstica, Documentos de respaldo (acta de defunción, certificado hospitalario de familiar, denuncia o acta de siniestro).",
            "solicitud_sga_y_procesos",
            "1. Descarga Formato-Solicitud-Justificacion-Inasistencias.docx y marca 'Calamidad doméstica o fuerza mayor comprobada'. 2. Llena la tabla de asignaturas, docentes y fechas exactas de ausencia. 3. Adjunta las evidencias y remite al correo de tu Director/a de Carrera solicitando reprogramación de evaluaciones atrasadas.",
            1, "Formato-Solicitud-Justificacion-Inasistencias.docx", "/documentos/Formato-Solicitud-Justificacion-Inasistencias.docx"
        ),
        (
            "justificacion_representacion", "Asistencia y Justificaciones", "Formato-Solicitud-Justificacion-Inasistencias.docx",
            "Justificación de Faltas por Representación Institucional / Deportiva / Cultural",
            "Estudiante que representa oficialmente a Ikiam en eventos académicos, científicos, deportivos o culturales.",
            "Tercera causal del formulario de justificación. Si además requieres viáticos/apoyo económico, puedes combinarlo con FO-GBU-56 (Ayuda económica para eventos: hasta 37% SBU nacional o 6%-10% SBU/día).",
            "coordinaciones_carrera", "Director/a de Carrera según Facultad",
            "Correo del Director/a de tu Carrera (opcional apoyo DBU: bienestar.universitario@ikiam.edu.ec)",
            "Preferentemente previo al viaje o máximo 3 días hábiles tras el retorno.",
            "Formato-Solicitud-Justificacion-Inasistencias.docx marcado causal Representación institucional, Oficio de invitación o delegación oficial firmada.",
            "solicitud_sga_y_procesos",
            "1. Descarga Formato-Solicitud-Justificacion-Inasistencias.docx y marca 'Representación institucional / deportiva / cultural'. 2. Adjunta la designación oficial del evento. 3. Envía a tu Director/a de Carrera.",
            1, "Formato-Solicitud-Justificacion-Inasistencias.docx / Art. 14-15 Regl. Becas", "/documentos/Formato-Solicitud-Justificacion-Inasistencias.docx"
        ),

        # --- BECAS Y BIENESTAR UNIVERSITARIO ---
        (
            "beca_postulacion", "Becas y Bienestar", "FO-GBU-40-V.5.0-Solicitud-de-becas-1.docx",
            "Postulación a Beca Universitaria (7 Modalidades + Excelencia)",
            "Estudiante regular matriculado (>=60% asignaturas de su malla) en busca de beca semestral.",
            "Cubre rubros de alimentación, insumos académicos y transporte (Art. 4). Excelencia académica: >= 9.0/10 en periodo anterior sin 3ra matrícula (Art. 11.1, pago único). FO-GBU-40 cubre 7 modalidades: escasos recursos, discapacidad, pueblos/nacionalidades, deportistas alto rendimiento, investigación, abanderados/escoltas y casos especiales.",
            "bienestar_universitario", "Director de Bienestar Universitario (Lcdo. Manuel Seraquive / DBU)",
            "bienestar.universitario@ikiam.edu.ec (Ext. 260)",
            "Según cronograma de convocatoria DBU al inicio de cada periodo académico.",
            "Formulario FO-GBU-40 (.docx) firmado, Cédula, Ficha socioeconómica, Pagaré y contrato con garante/responsable solidario al adjudicar (Art. 28-29), Respaldos (ingresos, servicios básicos, CONADIS/MSP o certificado comunitario). Prohibido tener otra beca pública.",
            "solicitud_sga_y_procesos",
            "1. Descarga FO-GBU-40-V.5.0-Solicitud-de-becas-1.docx. 2. Verifica ser estudiante regular (>=60% materias) y no recibir otra beca del Estado. 3. Envía expediente a bienestar.universitario@ikiam.edu.ec en fechas de convocatoria. 4. Si te adjudican, firma contrato y pagaré con garante solidario.",
            0, "CODIFICACION-DEL-REGLAMENTO-DE-BECAS...pdf (Arts. 1-37)", "/documentos/FO-GBU-40-V.5.0-Solicitud-de-becas-1.docx"
        ),
        (
            "ayuda_economica_emergente", "Becas y Bienestar", "FO-GBU-56-V.1.1Solicitud-de-ayudas-economicas-2.docx",
            "Ayuda Económica Excepcional (6 Modalidades, Calamidad y Eventos)",
            "Estudiante regular que enfrenta calamidad doméstica, titulación o viaja a eventos/movilidad.",
            "Subvención no reembolsable en 1 solo desembolso (Art. 13-15): (1) Trabajo de titulación, (2) Calamidad/fuerza mayor, (3) Eventos académicos (<=37% SBU nacional, 50% Galápagos, 2.5 SBU internacional), (4) Eventos culturales/deportivos (6%-10% SBU/día), (5) Movilidad internacional (<=2.5 SBU), (6) Innovación.",
            "bienestar_universitario", "Director de Bienestar Universitario",
            "bienestar.universitario@ikiam.edu.ec (Ext. 260)",
            "Hasta 20 días calendario antes del último día de clases (excepto calamidad/fuerza mayor o invitaciones, que aplican en cualquier momento).",
            "Formulario FO-GBU-56 (.docx), Cédula, Historial SGA, Evidencias de la calamidad o carta de invitación/ponencia.",
            "solicitud_sga_y_procesos",
            "1. Descarga FO-GBU-56-V.1.1Solicitud-de-ayudas-economicas-2.docx y marca la casilla de tu modalidad. 2. Adjunta soportes de emergencia o invitación oficial. 3. Envía a bienestar.universitario@ikiam.edu.ec.",
            0, "CODIFICACION-DEL-REGLAMENTO-DE-BECAS...pdf (Arts. 13-15)", "/documentos/FO-GBU-56-V.1.1Solicitud-de-ayudas-economicas-2.docx"
        ),
        (
            "beca_impugnacion", "Becas y Bienestar", "FO-GBU-69-V.1.0-Solicitud-de-impugnacion-de-becas-y-ayudas-1.docx",
            "Impugnación de Resultados de Beca o Ayuda Económica",
            "Postulante notificado con negativa del Comité de Becas.",
            "Art. 25 del Reglamento Codificado 2026: Derecho a impugnar por escrito ante la Dirección de Bienestar Universitario aportando pruebas o documentación no valorada.",
            "bienestar_universitario", "Comité de Becas / Director de Bienestar Universitario",
            "bienestar.universitario@ikiam.edu.ec (Ext. 260)",
            "Término estricto de tres (3) días contados desde la notificación de resultados.",
            "Formulario FO-GBU-69 (.docx) citando número de resolución, Pruebas documentales de respaldo que no fueron consideradas.",
            "solicitud_sga_y_procesos",
            "1. Descarga FO-GBU-69-V.1.0-Solicitud-de-impugnacion-de-becas-y-ayudas-1.docx. 2. Redacta el motivo objetivo de disconformidad con el Nro. de resolución. 3. Presenta dentro de los 3 días siguientes a bienestar.universitario@ikiam.edu.ec.",
            0, "Art. 25 Reglamento de Becas y Ayudas Económicas 2026", "/documentos/FO-GBU-69-V.1.0-Solicitud-de-impugnacion-de-becas-y-ayudas-1.docx"
        ),
        (
            "servicios_salud_campus", "Becas y Bienestar", "CODIFICACION-DEL-REGLAMENTO-DE-BECAS-Y-AYUDAS-ECONOMICAS-PARA-ESTUDIANTES-REGULARES-DE-LA-UNIVERSIDAD-REGIONAL-AMAZONICA-IKIAM-signed-signed-signed-1-1.pdf",
            "Atención Médica, Odontológica, Psicológica y Validación de Certificados",
            "Todos los estudiantes y comunidad universitaria Ikiam.",
            "Servicios gratuitos presenciales en Campus Muyuna (Lunes a Viernes 08h30 a 17h00): Medicina General (Ext. 258), Ocupacional (Ext. 259), Psicología (Ext. 257), Odontología (Ext. 263). Nota: Ikiam NO cuenta con residencias estudiantiles.",
            "centro_salud", "Centro de Salud / Bienestar Universitario",
            "centro.salud@ikiam.edu.ec y bienestar.universitario@ikiam.edu.ec",
            "Atención en horario laboral 08h30 a 17h00.",
            "Cédula de identidad o carné estudiantil; en caso de validación, certificado médico original del IESS/MSP/particular.",
            "validacion_medica_dbu",
            "1. Escribe a centro.salud@ikiam.edu.ec o llama al (06) 370-0040 (Medicina Ext. 258, Psicología Ext. 257, Odontología Ext. 263). 2. Presenta tu certificado si requieres validación para justificación académica.",
            0, "Web Servicios Institucionales / Admisiones Ikiam", "https://www.ikiam.edu.ec/index.php/servicios-institucionales/"
        ),

        # --- PRÁCTICAS PREPROFESIONALES (RED COMPLETA IT-GVI-05 2026) ---
        (
            "practicas_inicio", "Prácticas Preprofesionales", "FO-GVI-29-V.3.1-Solicitud-para-realizar-practicas-preprofesionales.docx",
            "Paso 1 Prácticas: Solicitud Inicial y Convenio (FO-GVI-29)",
            "Estudiante habilitado por malla para iniciar 400h (240 laborales + servicio comunitario) o pasantía.",
            "Instructivo IT-GVI-05 (2026): Jornada máx. 20h/sem en clases y hasta 40h/sem en interciclo. Ayudantías: 4 a 20h/sem. Recuerda firmar SIEMPRE los formatos en ESFERO AZUL. Causal de terminación: abandono injustificado >3 días.",
            "vinculacion_sociedad", "Directora de Vinculación con la Sociedad (Mgs. Jessica Medina Arias)",
            "practicas.preprofesionales@ikiam.edu.ec (Ext. 295-298 • DVS 5to piso)",
            "Presentar mínimo DOCE (12) DÍAS HÁBILES antes de iniciar la práctica.",
            "1. Revisar convenios en Matriz-de-Convenios-2PA2026.pdf. 2. Formulario FO-GVI-29 (.docx) firmado en esfero azul. 3. Formulario en línea Registro de Solicitud de Prácticas en la web de DVS.",
            "delegado_practicas_facultad,solicitud_sga_y_procesos",
            "1. Verifica en Matriz-de-Convenios_2PA2026.pdf si tu institución tiene convenio vigente. 2. Descarga y llena FO-GVI-29-V.3.1-Solicitud-para-realizar-practicas-preprofesionales.docx (firma en esfero azul) con al menos 12 días hábiles de anticipación. 3. Envía a practicas.preprofesionales@ikiam.edu.ec / registra en portal DVS. 4. Al recibir el oficio de DVS, sigue al Paso 2 (FO-GVI-31) en máximo 5 días hábiles con el Delegado de tu Facultad.",
            1, "IT-GVI-05 V.1.0 (2026) / Matriz de Convenios 2PA 2026", "/documentos/FO-GVI-29-V.3.1-Solicitud-para-realizar-practicas-preprofesionales.docx"
        ),
        (
            "practicas_tutor_facultad", "Prácticas Preprofesionales", "FO-GVI-31-V.3.1-Solicitud-de-asignacion-de-docente-tutor.docx",
            "Paso 2 Prácticas: Asignación de Docente Tutor por Facultad (FO-GVI-31) y Planificación (FO-GVI-04)",
            "Estudiante que ya recibió oficio de aprobación DVS o inicia ayudantía de cátedra/investigación/servicio comunitario.",
            "En la red de DVS, la asignación del Docente Tutor URAI NO la hace solo DVS sino el Delegado de Facultad para Vinculación (FCTA: Mgs. Wilson Bastidas, FCV: Mgs. Gabriela Loza, FCSA: Mgs. Melissa Sánchez) en coordinación con tu Director de Carrera.",
            "coordinaciones_carrera", "Delegado/a de Facultad para Gestión de Vinculación",
            "Correo de prácticas de tu Facultad (practicaspreprofesionales.fcta@ / .fcv@ / .fcsa@ikiam.edu.ec)",
            "FO-GVI-31: plazo de CINCO (5) DÍAS HÁBILES tras notificación DVS. Luego FO-GVI-04 (Planificación): dentro de QUINCE (15) DÍAS HÁBILES desde el inicio.",
            "FO-GVI-31 (.docx) dirigido al Delegado de tu Facultad sugiriendo docente tutor, Oficio previo de DVS, Luego llenar FO-GVI-04 (Planificación) y llevar FO-GVI-05 (Control asistencia diario en esfero azul).",
            "delegado_practicas_facultad",
            "1. Descarga FO-GVI-31 y dirígelo al Delegado de Vinculación de tu Facultad (en esfero azul). 2. Envíalo en máximo 5 días hábiles al correo practicaspreprofesionales de tu Facultad (FCTA, FCV o FCSA). 3. Una vez designado tu Tutor URAI, elabora la Planificación FO-GVI-04 en máximo 15 días hábiles y registra diariamente tu asistencia en FO-GVI-05.",
            1, "IT-GVI-05 V.1.0 (2026) / Web Vinculación Ikiam", "/documentos/FO-GVI-31-V.3.1-Solicitud-de-asignacion-de-docente-tutor.docx"
        ),
        (
            "practicas_certificado", "Prácticas Preprofesionales", "FO-GVI-30-V.2.0-Solicitud-de-certificado-de-practicas-preprofesionales-2.docx",
            "Paso 3 Prácticas: Cierre, Informes (FO-GVI-06/07/36) y Certificado Final (FO-GVI-30)",
            "Estudiante que concluyó las horas de práctica y necesita constancia para titularse.",
            "Cadena final de cierre: (1) Evaluación externa FO-GVI-36, (2) Informe del estudiante FO-GVI-06 en 15 días hábiles, (3) Revisión y evaluación docente FO-GVI-07 (5 días hábiles para subsanar observaciones), (4) Visto bueno del Delegado de Facultad, (5) Carga en plataforma DVS y solicitud FO-GVI-30 anexando certificado de Bolsa de Empleo.",
            "vinculacion_sociedad", "Director/a de Vinculación con la Sociedad + Delegado de Facultad",
            "Delegado de Facultad (FCTA/FCV/FCSA) -> DVS: practicas.preprofesionales@ikiam.edu.ec",
            "Entrega de expediente al Tutor URAI dentro de QUINCE (15) DÍAS HÁBILES desde finalización.",
            "FO-GVI-05 (asistencia en esfero azul), FO-GVI-36 (evaluación entidad), FO-GVI-06 (informe estudiante + fotos/link), FO-GVI-07 (evaluación docente), Certificado de entidad receptora, Certificado curso Bolsa de Empleo Institucional, FO-GVI-30 (.docx).",
            "delegado_practicas_facultad",
            "1. Entrega FO-GVI-06, FO-GVI-05 y FO-GVI-36 a tu Tutor URAI en máximo 15 días hábiles al terminar. 2. El tutor elabora FO-GVI-07 y remiten el expediente al Delegado de tu Facultad para aprobación. 3. Sube los archivos escaneados a la plataforma DVS y presenta FO-GVI-30 (junto al certificado de Bolsa de Empleo) para emitir la constancia oficial.",
            1, "IT-GVI-05 V.1.0 (2026) / FO-GVI-30", "/documentos/FO-GVI-30-V.2.0-Solicitud-de-certificado-de-practicas-preprofesionales-2.docx"
        ),

        # --- TITULACIÓN, INGLÉS B1, POSGRADOS Y TI ---
        (
            "titulacion_requisitos_prorroga", "Titulación e Idiomas", "04102022-Resolucion-No.-101-SG-SO-10-CU-IKIAM-2022-Modificacion-Resolucion-089-copias-certificadas-servidores-ikiam-signed-signed-1.pdf",
            "Requisitos de Titulación, Tesis, Examen Complexivo y Prórrogas",
            "Estudiante egresado o en últimos semestres preparando su graduación.",
            "4 pilares obligatorios para graduación en Ikiam: (1) 100% malla aprobada, (2) Inglés B1 avalado por Centro de Idiomas, (3) 400h prácticas certificadas por DVS (FO-GVI-30), (4) Trabajo de Titulación (Tesis) o Examen Complexivo + Paz y salvo Biblioteca/Laboratorios/Financiero. Si vence tu prórroga de tesis: puedes solicitar cambio de modalidad a Complexivo, curso de actualización de conocimientos o prórroga de gracia por caso fortuito.",
            "vicerrectorado_academico", "Director/a de Carrera / Vicerrectorado Académico / DVS",
            "Director/a de Carrera + direccion.academica@ikiam.edu.ec + centro.idiomas@ikiam.edu.ec",
            "Cumplir antes del vencimiento de prórrogas reglamentarias; Exit Test / calificaciones 2PA 2026 hasta 12/3/2027.",
            "Récord académico 100%, Certificado B1 Centro de Idiomas, Constancia prácticas DVS (FO-GVI-30), Paz y salvo biblioteca (biblioteca@ikiam.edu.ec)/laboratorios/financiero. Si pide prórroga de gracia/complexivo: carta motivada + informe del Director de Tesis.",
            "no_impedimentos_3ra_deudas,solicitud_sga_y_procesos",
            "1. Confirma tus 3 habilitantes previos: prácticas DVS (FO-GVI-30), inglés B1 (centro.idiomas@ikiam.edu.ec) y paz y salvo biblioteca/financiero. 2. Coordina defensa o inscripción a Examen Complexivo con tu Director/a de Carrera. 3. Si venció tu prórroga de tesis, presenta solicitud motivada de cambio a Complexivo o prórroga de gracia con aval de tu tutor a tu Director/a de Carrera y direccion.academica@ikiam.edu.ec.",
            1, "Reglamento de Titulación / RRA / Web Procesos Académicos", "https://www.ikiam.edu.ec/index.php/procesos-academicos/"
        ),
        (
            "idiomas_suficiencia_b1", "Titulación e Idiomas", "05052022-Resolucion-Nro.-047-SG-SE-009-CU-IKIAM-2022-Aprobacion-del-informe-de-rubros-por-concepto-de-examen-de-suficiencia-del-Centro-de-Idiomas.pdf",
            "Centro de Idiomas: Suficiencia Inglés B1, Placement Test y Exit Test",
            "Estudiante que necesita aprobar los 6 niveles de inglés o certificar suficiencia B1 para egresar.",
            "Programa regular de 6 niveles (100 horas c/u) hacia nivel B2; requisito mínimo de graduación en pregrado: nivel B1 mediante Exit Test o certificación internacional (TOEFL / IELTS / Cambridge FCE).",
            "centro_idiomas", "Centro de Idiomas Ikiam (CDI)",
            "centro.idiomas@ikiam.edu.ec (ref. docente daniel.robles@ikiam.edu.ec)",
            "Exit Test vigente: 11 de diciembre de 2026 al 04 de marzo de 2027 (solicitudes habilitadas 1 semana antes). Entrega calificaciones 2PA 2026: 12/3/2027.",
            "Solicitud en línea del Centro de Idiomas (1 semana antes del examen), Matrícula regular o pago de derechos según Res. 047 cuando corresponda.",
            "solicitud_sga_y_procesos",
            "1. Si recién ingresas, rinde el Placement Test para ubicarte entre Niveles 1 a 6. 2. Tras aprobar los 6 niveles (o si ya cuentas con dominio B1), solicita el Exit Test una semana antes de las fechas oficiales en la web del Centro de Idiomas. 3. Escribe a centro.idiomas@ikiam.edu.ec ante dudas de homologación de certificados internacionales.",
            0, "Web Centro de Idiomas Ikiam / Res. 047-SG-SE-009-CU-IKIAM-2022", "https://www.ikiam.edu.ec/index.php/centro-de-idiomas/"
        ),
        (
            "posgrados_admision", "Posgrados y Servicios TI", "04022022-Resolucion-Nro.-012-SG-SE-003-CU-IKIAM-2022-Proyecto-de-Reglamento-de-Posgrado-de-la-Universidad-Regional-Amazonica-Ikiam.pdf",
            "Admisión a Maestrías / Escuela de Posgrados (Modalidad Híbrida)",
            "Profesionales con título de tercer nivel registrado en SENESCYT interesados en maestrías.",
            "6 maestrías en modalidad híbrida: Cambio Climático/Desarrollo Rural, Arquitectura en Construcción Sostenible, Biotecnología mención Salud, Ciencias de la Ingeniería, Hidráulica Ambiental y Energética, Emprendimiento e Innovación Social. Proceso 2da Fase: 2 nov 2026 al 30 mar 2027.",
            "escuela_posgrados", "Directora Escuela de Posgrados (Corina Campos)",
            "escuela.posgrados@ikiam.edu.ec y corina.campos@ikiam.edu.ec (Ext. 223)",
            "Admisión Segunda Fase: del 02 de noviembre de 2026 al 30 de marzo de 2027.",
            "Título de tercer nivel registrado en SENESCYT, Cédula/pasaporte, Récord académico, Carta motivada en formato Ikiam, Hoja de vida en formato Ikiam.",
            "solicitud_sga_y_procesos",
            "1. Reúne cédula, récord académico, carta motivada y hoja de vida en formato Ikiam. 2. Postula en línea desde el portal de Posgrado hasta el 30 de marzo de 2027. 3. Para consultas de aranceles o cohortes escribe a escuela.posgrados@ikiam.edu.ec.",
            0, "Web Posgrado Ikiam / PR-GAR-07 / Res. 012 Posgrado", "https://www.ikiam.edu.ec/index.php/posgrado/"
        ),
        (
            "servicios_ti_biblioteca_campus", "Posgrados y Servicios TI", "11072022-Resolucion-No.-075-SG-S0-006-CU-IKIAM-2022-Reglamento-funcionamiento-centro-serivicios-bibliotecarios.pdf",
            "Soporte TI (Correo/SGA/Moodle), Biblioteca Koha y Campus Muyuna",
            "Estudiantes con problemas de acceso a cuenta institucional, SGA, Moodle, biblioteca o traslados.",
            "Servicios centrales en Campus Muyuna (Km 7 vía Alto Tena). IMPORTANTE: Ikiam NO dispone actualmente de residencias estudiantiles (hay alojamiento privado accesible cerca del campus).",
            "dti_biblioteca", "DTI / Centro de Servicios Bibliotecarios",
            "TI: soporte@ikiam.edu.ec | Biblioteca: biblioteca@ikiam.edu.ec | Secretaría: secretaria.general@ikiam.edu.ec",
            "Biblioteca: Lunes a Viernes 08h00-17h00. Campus/Oficinas: 08h30-17h00.",
            "Correo institucional o cédula de identidad para tickets de soporte TI o préstamo en Biblioteca Koha.",
            "no_impedimentos_3ra_deudas",
            "1. Para activación de correo, clave SGA o Moodle, escribe a soporte@ikiam.edu.ec (o GLPI DTI). 2. Para préstamos o certificado de no adeudar libros (biblioteca.ikiam.edu.ec), escribe a biblioteca@ikiam.edu.ec. 3. Llegada al campus: bus urbano Muyuna desde Terminal de Tena (~15 min).",
            0, "Web Servicios TI / Biblioteca / Admisiones Ikiam", "https://www.ikiam.edu.ec/index.php/serviciosti/"
        ),
    ]

    cur.executemany("""
    INSERT INTO casos_tramite_red (
        codigo_caso, categoria, documento_archivo, nombre_tramite, perfil_estudiante,
        descripcion_caso, dependencia_id, autoridad_destinataria, correo_destino,
        plazo_reglamentario, requisitos_adjuntos, pasos_red_codigos, pasos_procedimiento,
        requiere_selector_facultad, normativa_respaldo, enlace_descarga
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, casos_data)

    conn.commit()
    print(f"ikiam_network_org.db creada con exito:")
    print(f"  Facultades: {cur.execute('SELECT COUNT(1) FROM facultades').fetchone()[0]}")
    print(f"  Carreras (con Directores y correos reales): {cur.execute('SELECT COUNT(1) FROM coordinaciones_carrera').fetchone()[0]}")
    print(f"  Dependencias verificadas: {cur.execute('SELECT COUNT(1) FROM dependencias').fetchone()[0]}")
    print(f"  Nodos pasos comunes: {cur.execute('SELECT COUNT(1) FROM nodos_pasos_comunes').fetchone()[0]}")
    print(f"  Casos mapeados en red: {cur.execute('SELECT COUNT(1) FROM casos_tramite_red').fetchone()[0]}")
    conn.close()


if __name__ == "__main__":
    init_network_db()
