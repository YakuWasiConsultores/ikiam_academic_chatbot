# -*- coding: utf-8 -*-
"""
Script de creación y población de ikiam_flows.db
Modela los árboles de decisión guiados:
- Detección de intenciones generales (ingreso, retiros, inasistencias, becas, prácticas).
- Saludo cordial y mensajes orientadores sin abrumar con texto.
- Opciones predeterminadas y botones clicables.
"""

import os
import sqlite3
import json

BASE_DIR = r"D:\ikiam_academic_chatbot"
DB_PATH = os.path.join(BASE_DIR, "ikiam_flows.db")

def init_flows_db():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE flujos_decision (
        id TEXT PRIMARY KEY,
        categoria TEXT NOT NULL,
        palabras_clave TEXT NOT NULL,
        titulo_guia TEXT NOT NULL,
        saludo_cordial TEXT NOT NULL,
        mensaje_orientador TEXT NOT NULL,
        opciones_json TEXT NOT NULL
    );
    """)

    flujos = [
        {
            "id": "flujo_ingreso",
            "categoria": "Ingreso y Admisión",
            "palabras_clave": "ingresar, admision, entrar a ikiam, quiero estudiar, cupo, nuevo ingreso, como ingreso, requisitos para entrar, como puedo postular, estudiar en ikiam",
            "titulo_guia": "Guía de Ingreso y Admisión a Ikiam",
            "saludo_cordial": "¡Hola! Con mucho gusto te oriento para que conozcas la ruta exacta de ingreso a la Universidad Regional Amazónica Ikiam.",
            "mensaje_orientador": "En Ikiam existen diferentes modalidades de ingreso según tu trayectoria académica previa. Por favor selecciona tu caso:",
            "opciones": [
                {
                    "id": "opc_ingreso_primera_vez",
                    "etiqueta": "🎓 Bachiller Nacional (Primera vez)",
                    "codigo_caso": "ingreso_primera_vez",
                    "descripcion": "Graduados de secundaria en Ecuador que postulan por proceso general de admisión."
                },
                {
                    "id": "opc_ingreso_extranjero",
                    "etiqueta": "🌍 Estudiante Extranjero",
                    "codigo_caso": "ingreso_extranjero",
                    "descripcion": "Aspirantes internacionales con título de secundaria o estudios universitarios en el exterior."
                },
                {
                    "id": "opc_ingreso_homologacion",
                    "etiqueta": "🔄 Vengo de otra universidad (Homologación)",
                    "codigo_caso": "ingreso_homologacion_externa",
                    "descripcion": "Estudiantes que han aprobado al menos un semestre en otra universidad y desean transferirse."
                },
                {
                    "id": "opc_ingreso_reingreso",
                    "etiqueta": "📋 Ya estudié antes en Ikiam (Reingreso)",
                    "codigo_caso": "ingreso_reingreso",
                    "descripcion": "Ex-alumnos de Ikiam que abandonaron o suspendieron sus estudios y desean retomar la carrera."
                },
                {
                    "id": "opc_cambio_carrera",
                    "etiqueta": "🔀 Cambio de Carrera Interno",
                    "codigo_caso": "cambio_carrera_interno",
                    "descripcion": "Estudiantes regulares activos de Ikiam que desean cambiarse a otra carrera."
                }
            ]
        },
        {
            "id": "flujo_retiro",
            "categoria": "Retiro de Asignaturas",
            "palabras_clave": "retirar materia, retiro de asignatura, retirarme, dar de baja materia, segunda matricula retiro, me quiero retirar, cancelar materia",
            "titulo_guia": "Guía de Retiro de Asignaturas",
            "saludo_cordial": "Estimado/a estudiante, comprendo tu consulta sobre el retiro de asignaturas. Para evitar la pérdida de gratuidad o problemas con segundas matrículas, identifiquemos tu situación:",
            "mensaje_orientador": "El trámite y los plazos varían según el momento del semestre y las circunstancias que motivan tu retiro:",
            "opciones": [
                {
                    "id": "opc_retiro_ordinario",
                    "etiqueta": "⏱️ Retiro Ordinario (Primeros 30 días)",
                    "codigo_caso": "retiro_ordinario",
                    "descripcion": "Retiro voluntario dentro de las primeras 4 semanas del periodo académico sin justificación médica."
                },
                {
                    "id": "opc_retiro_fuerza_mayor",
                    "etiqueta": "🏥 Caso Fortuito / Calamidad / Salud",
                    "codigo_caso": "retiro_fuerza_mayor",
                    "descripcion": "Retiro fuera del plazo ordinario por enfermedad sobrevenida grave o calamidad doméstica comprobada."
                },
                {
                    "id": "opc_retiro_segunda_mat",
                    "etiqueta": "⚠️ En Segunda Matrícula (Protección de Carrera)",
                    "codigo_caso": "retiro_segunda_matricula",
                    "descripcion": "Estudiantes en segunda matrícula que buscan retirar la asignatura para evitar la pérdida definitiva de carrera."
                }
            ]
        },
        {
            "id": "flujo_faltas",
            "categoria": "Asistencia y Justificaciones",
            "palabras_clave": "justificar falta, falte a clases, justificacion de inasistencia, falte por enfermedad, calamidad domestica faltas, falte al examen, reprogramar examen",
            "titulo_guia": "Guía de Justificación de Inasistencias",
            "saludo_cordial": "Estimado/a estudiante, las inasistencias deben justificarse formalmente dentro del plazo reglamentario de 3 días hábiles tras tu reincorporación.",
            "mensaje_orientador": "Por favor indícanos el motivo de tu inasistencia para guiarte con el respaldo documental exigido:",
            "opciones": [
                {
                    "id": "opc_falta_salud",
                    "etiqueta": "🩺 Enfermedad o Cita Médica",
                    "codigo_caso": "justificacion_salud",
                    "descripcion": "Ausencias justificadas con certificado del IESS, MSP o validación de Bienestar Universitario."
                },
                {
                    "id": "opc_falta_calamidad",
                    "etiqueta": "🏠 Calamidad Doméstica o Familiar",
                    "codigo_caso": "justificacion_calamidad",
                    "descripcion": "Ausencias justificadas con carta motivada y evidencias de fuerza mayor personal/familiar."
                }
            ]
        },
        {
            "id": "flujo_becas",
            "categoria": "Becas y Ayudas Económicas",
            "palabras_clave": "becas, solicitar beca, ayuda economica, bienestar universitario beca, quintil, apoyo economico, emergencia economica",
            "titulo_guia": "Guía de Becas y Ayudas Universitarias",
            "saludo_cordial": "¡Hola! La Dirección de Bienestar Universitario cuenta con programas de apoyo para garantizar tu permanencia académica.",
            "mensaje_orientador": "Selecciona el tipo de apoyo que necesitas gestionar:",
            "opciones": [
                {
                    "id": "opc_beca_postulacion",
                    "etiqueta": "🏅 Postulación a Beca Semestral (FO-GBU-40)",
                    "codigo_caso": "beca_postulacion",
                    "descripcion": "Becas por excelencia, situación socioeconómica, pueblos y nacionalidades o discapacidad."
                },
                {
                    "id": "opc_ayuda_emergente",
                    "etiqueta": "🚨 Ayuda Económica Emergente (FO-GBU-56)",
                    "codigo_caso": "ayuda_economica_emergente",
                    "descripcion": "Apoyo financiero urgente ante catástrofes, accidentes graves o calamidad sobrevenida."
                }
            ]
        },
        {
            "id": "flujo_practicas",
            "categoria": "Prácticas Preprofesionales",
            "palabras_clave": "practicas preprofesionales, 400 horas, iniciar practicas, certificado de practicas, tutor de practicas, vinculacion practicas",
            "titulo_guia": "Guía de Prácticas Preprofesionales (DVS)",
            "saludo_cordial": "Estimado/a estudiante, el proceso de prácticas preprofesionales (400 horas) es gestionado por la Dirección de Vinculación con la Sociedad.",
            "mensaje_orientador": "Selecciona en qué fase del proceso te encuentras:",
            "opciones": [
                {
                    "id": "opc_practicas_inicio",
                    "etiqueta": "📝 Iniciar Prácticas (FO-GVI-29)",
                    "codigo_caso": "practicas_inicio",
                    "descripcion": "Solicitud inicial para aprobación de entidad receptora y designación de tutor."
                },
                {
                    "id": "opc_practicas_certificado",
                    "etiqueta": "📜 Solicitar Certificado de 400 Horas (FO-GVI-30)",
                    "codigo_caso": "practicas_certificado",
                    "descripcion": "Emisión del certificado de haber culminado y aprobado las 400 horas para titulación."
                }
            ]
        }
    ]

    for fl in flujos:
        cur.execute("""
        INSERT INTO flujos_decision (id, categoria, palabras_clave, titulo_guia, saludo_cordial, mensaje_orientador, opciones_json)
        VALUES (?, ?, ?, ?, ?, ?, ?);
        """, (
            fl["id"],
            fl["categoria"],
            fl["palabras_clave"],
            fl["titulo_guia"],
            fl["saludo_cordial"],
            fl["mensaje_orientador"],
            json.dumps(fl["opciones"], ensure_ascii=False)
        ))

    conn.commit()
    print(f"Base de datos {DB_PATH} creada con exito.")
    print(f"Flujos de decision registrados: {cur.execute('SELECT COUNT(1) FROM flujos_decision').fetchone()[0]}")
    conn.close()

if __name__ == "__main__":
    init_flows_db()
