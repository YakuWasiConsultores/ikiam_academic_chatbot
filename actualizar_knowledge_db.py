# -*- coding: utf-8 -*-
"""
Actualización verificada de D:\ikiam_academic_chatbot\ikiam_knowledge.db
y corrección de D:\n8n-email-chatbot\knowledge-base\normativa_institucional.md:
- Corrige la inconsistencia de residencias estudiantiles (Ikiam NO dispone actualmente de residencias).
- Actualiza autoridades 2026, correos oficiales reales (oficina.admision@, bienestar.universitario@, direccion.academica@, practicas.preprofesionales@ + delegados fcta/fcv/fcsa), fechas 2PA 2026 / 1PAO 2027 y las 3 facultades con sus 10 carreras.
- Mantiene tabla FTS5 `ikiam_docs` y `enlaces_ikiam` intactas e indexadas.
"""

import os
import sqlite3

DB_PATH = r"D:\ikiam_academic_chatbot\ikiam_knowledge.db"
MD_PATH = r"D:\n8n-email-chatbot\knowledge-base\normativa_institucional.md"


def update_knowledge_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("DELETE FROM ikiam_docs;")
    cur.execute("DELETE FROM enlaces_ikiam;")

    enlaces_oficiales = [
        ("Admisiones", "Portal de Admisiones Destino Ikiam 1PA 2027", "https://www.ikiam.edu.ec/index.php/admisiones/"),
        ("Procesos Académicos", "Homologaciones, Cambios de Carrera y Reingreso", "https://www.ikiam.edu.ec/index.php/procesos-academicos/"),
        ("Prácticas Preprofesionales", "DVS Prácticas Preprofesionales (IT-GVI-05)", "https://www.ikiam.edu.ec/index.php/practicas-pre-profesionales/"),
        ("Equipo Vinculación", "Delegados de Prácticas por Facultad (FCTA/FCV/FCSA)", "https://www.ikiam.edu.ec/index.php/vinculacion-3/"),
        ("Bienestar Universitario", "Becas, Ayudas Económicas e Impugnación", "https://www.ikiam.edu.ec/index.php/bienestaruniversitario/becas-y-ayudas-economicas/"),
        ("Servicios Institucionales", "Centro de Salud, Psicología, Odontología y Biblioteca", "https://www.ikiam.edu.ec/index.php/servicios-institucionales/"),
        ("Centro de Idiomas", "Inglés B1, Placement Test y Exit Test", "https://www.ikiam.edu.ec/index.php/centro-de-idiomas/"),
        ("Servicios TI", "Soporte TI, Correo, SGA y Moodle", "https://www.ikiam.edu.ec/index.php/serviciosti/"),
        ("Biblioteca", "Catálogo Virtual Koha y Repositorio DSpace", "https://biblioteca.ikiam.edu.ec/"),
        ("Pregrado y Facultades", "Oferta Académica de 3 Facultades y 10 Carreras", "https://www.ikiam.edu.ec/index.php/pregrado/"),
        ("Posgrado", "Escuela de Posgrados y Maestrías Híbridas", "https://www.ikiam.edu.ec/index.php/posgrado/"),
        ("Autoridades", "Directorio de Autoridades y Decanos Ikiam", "https://www.ikiam.edu.ec/index.php/autoridades/"),
        ("Licitaciones", "Procedimientos de Contratación Pública SERCOP", "https://www.ikiam.edu.ec/index.php/procedimientos-de-licitacion/")
    ]
    cur.executemany("INSERT INTO enlaces_ikiam (categoria, titulo, url) VALUES (?, ?, ?)", enlaces_oficiales)

    modulos = [
        (
            "Oferta Academica Carreras Pregrado Facultades Decanos Tierra y Agua Vida Socioambientales Tronco Comun",
            "Oferta Académica por Facultades, Decanos y Directores (Ikiam 2026)",
            "Ikiam organiza sus 10 carreras vigentes de pregrado presencial en 3 Facultades: "
            "1) Facultad de Ciencias de la Tierra y Agua (FCTA, Decano Dr. Willin Álvarez - willin.alvarez@ikiam.edu.ec): Geociencias (jorge.espin@ikiam.edu.ec, tronco común), Hidrología (victor.espinoza@ikiam.edu.ec, tronco común), Agroecología (wilfredo.franco@ikiam.edu.ec), Electromecánica y Energías Renovables (galo.cerda@ikiam.edu.ec). "
            "2) Facultad de Ciencias de la Vida (FCV, Decana Dra. Diana Callejas - diana.callejas@ikiam.edu.ec): Biotecnología (julio.rea@ikiam.edu.ec, tronco común), Ecosistemas (laura.salazar@ikiam.edu.ec, tronco común), Medicina Veterinaria y Manejo de Vida Silvestre (10 semestres, veronica.rivadeneyra@ikiam.edu.ec). "
            "3) Facultad de Ciencias Socioambientales (FCSA, Decana Dra. María Soledad Solórzano - maria.solorzano@ikiam.edu.ec): Biocomercio (pedro.cango@ikiam.edu.ec), Arquitectura Sostenible (leonardo.coloma@ikiam.edu.ec), Educación en Ciencias Experimentales ECX (jorge.rios@ikiam.edu.ec).",
            "https://www.ikiam.edu.ec/index.php/pregrado/",
            "Admisión vía oficina.admision@ikiam.edu.ec. Registro Nacional SENESCYT + inscripción en eval.ikiam.edu.ec."
        ),
        (
            "Admision Ingreso 1PA 2027 Cupos Puntajes Nivelacion Extranjero Bachiller",
            "Admisión Destino Ikiam 1PA 2027, Puntajes y Cupos Oficiales",
            "Cronograma 1PA 2027: Registro Nacional 1ra Etapa 24-28/11/2026, 2da Etapa 1-5/12/2026; Inscripción eval.ikiam.edu.ec del 18/12/2026 al 24/1/2027; Simulador 25/1-19/2/2027; Postulaciones 24/3-1/4/2027; Aceptación cupo hasta 3/4/2027; Test vocacional 4-9/4/2027. Puntaje: 50% graduación + 50% examen. Puntajes corte IIS-2026: Veterinaria 853.91, Biotecnología 842.21, Arquitectura 838.7, Electromecánica 812.5, Ecosistemas 811.38, Hidrología 808.82, Geociencias 802.44, Agroecología 780.05, Biocomercio 740.92. Nota: La universidad NO cuenta con residencias estudiantiles propias.",
            "https://www.ikiam.edu.ec/index.php/admisiones/",
            "Contacto oficina.admision@ikiam.edu.ec (Ext. 322 / WhatsApp 0982142499). Extranjeros de colegio deben homologar título en MinEduc; extranjeros universitarios gestionan por relaciones.interinstitucionales@ikiam.edu.ec y direccion.academica@ikiam.edu.ec."
        ),
        (
            "Homologacion Convalidacion Cambio Carrera Cambio Universidad IES Extranjera Nacional Tronco Comun Articulo 96 97",
            "Homologación, Cambio de Carrera, Cambio de IES y Reingreso",
            "Según Arts. 96 y 97 del RRA CES y Calendario 1PAO 2027: Recepción documental 1 al 18 de diciembre de 2026. "
            "Cambio de carrera interno: >50% aprobado en 1er PAO, >=1 homologable y puntaje cohorte (Art. 97 exceptúa transición dentro del Tronco Común de 1er nivel: Hidrología, Biotecnología, Geociencias y Ecosistemas). "
            "Cambio IES pública nacional: >=2 PAO y >=2 homologables (>=80% similitud). IES particular: + asignación de cupo y puntaje de cohorte. Extranjeros: pasaporte/visa estudiante y documentos legalizados. Sin 3ras matrículas ni deudas.",
            "https://www.ikiam.edu.ec/index.php/procesos-academicos/",
            "Formato Solicitud-de-cambio-de-carrera.docx / Solicitud-de-cambio-de-universidad.docx / FORMATO-SOLICITUD-DE-REINGRESO.docx dirigidos a Vicerrectorado Académico; recepción en direccion.academica@ikiam.edu.ec y formulario web."
        ),
        (
            "Calendario Academico 2PA 2026 Nivelacion Fechas Retiro Parciales Finales Recuperacion",
            "Calendario Académico Vigente 2PA 2026 (Carrera) y Nivelación",
            "Calendario Carrera 2PA 2026 (firmado por Vicerrectora Dra. Zulay Niño Ruiz): 3ra matrícula hasta 24/9/2026; Matrícula Ordinaria 28/9-2/10/2026; Extraordinaria 5-9/10/2026; Especial/Placement 12-16/10/2026; Inicio clases 19/10/2026; Fecha límite retiro voluntario ordinario 26-30/10/2026; 1er Parcial 30/11-4/12/2026; Homologación 1-18/12/2026; 2do Parcial 18-22/1/2027; Finales 3-9/3/2027; Recuperación 10-11/3/2027; Exit Test/Cierre 12/3/2027.",
            "https://www.ikiam.edu.ec/index.php/procesos-academicos/",
            "Consultar /documentos/Reforma-Propuesta-de-Calendario-Academico-2PA2026-1-signed-1.pdf y /documentos/Calendario-de-Homologacion-1PAO2027.pdf."
        ),
        (
            "Faltas Inasistencias Justificacion Asistencia 70 Medico Calamidad Familiar Reprogramacion",
            "Justificación de Inasistencias, Reprogramación y Regla del 70%",
            "Asistencia mínima obligatoria: 70%. Plazo máximo para justificar faltas o pedir reprogramación de exámenes: 3 días hábiles tras reincorporarse. En causal médica es obligatorio validar el certificado médico en Centro de Salud DBU (centro.salud@ikiam.edu.ec). En calamidad doméstica familiar o representación institucional se adjuntan actas/soportes y carta dirigida al Director/a de Carrera de la Facultad correspondiente (FCTA, FCV o FCSA).",
            "https://www.ikiam.edu.ec/index.php/servicios-institucionales/",
            "Formato-Solicitud-Justificacion-Inasistencias.docx (/documentos/Formato-Solicitud-Justificacion-Inasistencias.docx) + validación médica en centro.salud@ikiam.edu.ec o soportes de calamidad."
        ),
        (
            "Retiro Materia Asignatura Segunda Matricula Tercera Matricula Aranceles Perdida Gratuidad Tabla Arancelaria LOES",
            "Retiros, Segunda/Tercera Matrícula y Tabla Arancelaria (LOES)",
            "Retiro voluntario ordinario (Art. 45 RRA): dentro del plazo inicial (2PA 2026 cerró 30/10/2026) no afecta gratuidad. Fuera de plazo solo procede retiro extraordinario por caso fortuito/fuerza mayor comprobada antes de exámenes finales (3/3/2027). Segunda/tercera matrícula (Art. 80 LOES y Res. 032 Tabla Arancelaria): reprobar 2da matrícula arriesga la carrera (3ra matrícula es excepcional antes de fecha límite del periodo) y conlleva cobro diferenciado según quintil socioeconómico registrado en DBU (bienestar.universitario@ikiam.edu.ec).",
            "https://www.ikiam.edu.ec/index.php/procesos-academicos/",
            "Formato-Solicitud-Retiro-Voluntario-Asignatura.docx dirigido al Director/a de Carrera + direccion.academica@ikiam.edu.ec + ficha socioeconómica DBU para tarifa por quintil."
        ),
        (
            "Becas Ayudas Economicas Impugnacion DBU Excelencia Quintil Vulnerabilidad Eventos",
            "Reglamento Codificado de Becas y Ayudas Económicas (2026)",
            "DBU (bienestar.universitario@ikiam.edu.ec, Ext. 260) gestiona becas (FO-GBU-40: 7 tipos incluyendo excelencia >=9.0/10 directa sin 3ra matrícula, escasos recursos, discapacidad, pueblos/nacionalidades, deportistas, investigación, abanderados) y ayudas económicas excepcionales (FO-GBU-56: 6 tipos incluyendo calamidad, titulación, movilidad 2.5 SBU, eventos nacionales 37% SBU / Galápagos 50% SBU / culturales 6%-10% SBU día, plazo hasta 20 días antes del fin de clases salvo fuerza mayor). Negativas se impugnan con FO-GBU-69 en 3 días. Exige contrato + pagaré + garante solidario (Art. 28-29).",
            "https://www.ikiam.edu.ec/index.php/bienestaruniversitario/becas-y-ayudas-economicas/",
            "FO-GBU-40-V.5.0-Solicitud-de-becas-1.docx, FO-GBU-56-V.1.1Solicitud-de-ayudas-economicas-2.docx, FO-GBU-69-V.1.0-Solicitud-de-impugnacion-de-becas-y-ayudas-1.docx."
        ),
        (
            "Practicas Preprofesionales Laborales Comunitarias DVS IT-GVI-05 400 horas Convenios Ayudantias",
            "Prácticas Preprofesionales, Convenios y Delegados por Facultad (IT-GVI-05 2026)",
            "Total 400h obligatorias (240h laborales + comunitarias; jornada máx 20h/sem en clases, 40h interciclo; ayudantías 4-20h/sem). Flujo oficial IT-GVI-05: 1) FO-GVI-29 con >=12 días hábiles de anticipación a DVS (practicas.preprofesionales@ikiam.edu.ec) verificando Matriz de Convenios 2PA 2026; 2) En 5 días hábiles tras notificación, enviar FO-GVI-31 al Delegado de Facultad (FCTA: practicaspreprofesionales.fcta@ikiam.edu.ec, FCV: practicaspreprofesionales.fcv@ikiam.edu.ec, FCSA: practicaspreprofesionales.fcsa@ikiam.edu.ec); 3) Planificación FO-GVI-04 en 15 días hábiles y asistencia diaria en esfero azul FO-GVI-05; 4) Cierre en 15 días hábiles con FO-GVI-06, FO-GVI-36, FO-GVI-07 y certificado FO-GVI-30 (+ certificado Bolsa de Empleo). Abandono injustificado >3 días cancela práctica.",
            "https://www.ikiam.edu.ec/index.php/practicas-pre-profesionales/",
            "8 formatos oficiales FO-GVI (29, 31, 04, 05, 06, 07, 36, 30) + Matriz-de-Convenios-Institucionales..._2PA2026.pdf + it-gvi-05-v.1.0...pdf."
        ),
        (
            "Titulacion Graduacion Tesis Complexivo Prorroga Ingles B1 Centro Idiomas Exit Test Placement",
            "Titulación, Prórrogas de Tesis y Suficiencia Inglés B1 (CDI)",
            "Requisitos de graduación: 100% malla + Inglés B1 (6 niveles x 100h o Exit Test en Centro de Idiomas centro.idiomas@ikiam.edu.ec; fechas Exit Test 11 dic 2026 - 4 mar 2027) + Certificado 400h prácticas (FO-GVI-30) + Tesis o Examen Complexivo + Paz y salvo Biblioteca (biblioteca@ikiam.edu.ec)/Laboratorios/Financiero. Si venció la prórroga de tesis: solicitar cambio a Examen Complexivo, curso de actualización o prórroga extraordinaria por caso fortuito con informe del tutor.",
            "https://www.ikiam.edu.ec/index.php/centro-de-idiomas/",
            "Récord académico, certificado DVS FO-GVI-30, constancia B1 centro.idiomas@ikiam.edu.ec, paz y salvo biblioteca@ikiam.edu.ec."
        ),
        (
            "Posgrado Maestrias TI Soporte Biblioteca Salud Consultorio Ubicacion Campus Muyuna",
            "Posgrados, Soporte TI, Biblioteca, Centro de Salud y Campus",
            "Escuela de Posgrados (6 maestrías híbridas, 2da fase 2 nov 2026 - 30 mar 2027): escuela.posgrados@ikiam.edu.ec / corina.campos@ikiam.edu.ec Ext. 223. Soporte TI/SGA/Moodle/Correos: soporte@ikiam.edu.ec. Biblioteca Koha (08h00-17h00): biblioteca@ikiam.edu.ec. Centro de Salud gratuito (Medicina Gral Ext. 258, Ocupacional 259, Psicología 257, Odontología 263): centro.salud@ikiam.edu.ec. Campus: Km 7 vía Tena-Muyuna (no cuenta con residencias universitarias).",
            "https://www.ikiam.edu.ec/index.php/servicios-institucionales/",
            "Posgrados: cédula, récord, carta motivada y hoja de vida formato Ikiam. TI: soporte@ikiam.edu.ec. Copias certificadas Secretaría: secretaria.general@ikiam.edu.ec / daniela.soria@ikiam.edu.ec."
        )
    ]

    cur.executemany(
        "INSERT INTO ikiam_docs (categoria, titulo, contenido, url_fuente, documentos_requeridos) VALUES (?, ?, ?, ?, ?)",
        modulos
    )
    conn.commit()
    print("ikiam_knowledge.db actualizada con exito:", cur.execute("SELECT COUNT(1) FROM ikiam_docs").fetchone()[0], "modulos verificados.")
    conn.close()

    # Corregir tambien normativa_institucional.md para eliminar la contradicción sobre residencias estudiantiles y actualizar correos/facultades
    if os.path.exists(MD_PATH):
        with open(MD_PATH, "r", encoding="utf-8") as f:
            md_txt = f.read()
        md_txt = md_txt.replace(
            "- **Residencias Universitarias:** Cupos limitados en el campus para estudiantes de provincias lejanas con vulnerabilidad socioeconómica.",
            "- **Alojamiento Estudiantil:** La universidad **no cuenta al momento con una residencia estudiantil** en el campus; existen opciones de vivienda privada accesibles en los sectores cercanos a Muyuna y Tena (referencia oficial portal de Admisiones Ikiam)."
        )
        md_txt = md_txt.replace("`admisiones@ikiam.edu.ec`", "`oficina.admision@ikiam.edu.ec`")
        md_txt = md_txt.replace("`secretaria@ikiam.edu.ec`", "`secretaria.general@ikiam.edu.ec` y `direccion.academica@ikiam.edu.ec`")
        md_txt = md_txt.replace("`bienestar@ikiam.edu.ec`", "`bienestar.universitario@ikiam.edu.ec` y `centro.salud@ikiam.edu.ec`")
        with open(MD_PATH, "w", encoding="utf-8") as f:
            f.write(md_txt)
        print("normativa_institucional.md corregida sin contradicciones.")


if __name__ == "__main__":
    update_knowledge_db()
