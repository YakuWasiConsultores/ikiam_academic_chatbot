# -*- coding: utf-8 -*-
"""
Construcción de D:\ikiam_academic_chatbot\ikiam_flows.db
Árbol de decisión conversacional multi-nivel con opciones predeterminadas sencillas:
- Nivel 0: Bienvenida / Menú principal para estudiantes perdidos o saludos.
- Nivel 1: Modalidades de Ingreso, Cambio de Carrera / Tronco Común, Retiros / 2da-3ra Matrícula,
           Justificación Faltas, Becas y Salud, Prácticas (400h), Titulación / Inglés B1, Posgrados / TI.
- Selector de Facultad (FCTA / FCV / FCSA) -> Carrera cuando el trámite depende de Facultad/Carrera.
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
        prioridad INTEGER NOT NULL,
        categoria TEXT NOT NULL,
        palabras_clave TEXT NOT NULL,
        titulo_guia TEXT NOT NULL,
        saludo_cordial TEXT NOT NULL,
        mensaje_orientador TEXT NOT NULL,
        opciones_json TEXT NOT NULL
    );
    """)

    flujos = [
        # 1. INGRESO Y ADMISIÓN (Prioridad alta cuando pregunta cómo ingresar)
        {
            "id": "flujo_ingreso",
            "prioridad": 10,
            "categoria": "Ingreso y Admisión",
            "palabras_clave": "ingresar a ikiam, entrar a ikiam, como ingresar, poder ingresar, quiero estudiar en ikiam, proceso de admision, nuevo ingreso, como entro a ikiam, requisitos para entrar, como postular, quiero entrar, admisiones, extranjero ingresar, homologar universidad",
            "titulo_guia": "Ruta de Ingreso a la Universidad Regional Amazónica Ikiam",
            "saludo_cordial": "¡Hola! Con mucho gusto te doy la bienvenida y te oriento para ingresar a Ikiam.",
            "mensaje_orientador": "En Ikiam no existe un único tipo de ingreso: el trámite, los documentos y los correos cambian según tu perfil. Selecciona tu situación:",
            "opciones": [
                {
                    "id": "opc_ing_1",
                    "etiqueta": "Bachiller Nacional (Primera vez)",
                    "codigo_caso": "caso:ingreso_primera_vez",
                    "descripcion": "Graduado de colegio ecuatoriano que postula por Registro Nacional y examen Ikiam (Proceso 1PA 2027)."
                },
                {
                    "id": "opc_ing_2",
                    "etiqueta": "Estudiante Extranjero",
                    "codigo_caso": "caso:ingreso_extranjero",
                    "descripcion": "Aspirante internacional (título de colegio apostillado/MinEduc o transferencia universitaria extranjera)."
                },
                {
                    "id": "opc_ing_3",
                    "etiqueta": "Cambio de Universidad (Homologación / Cambio IES)",
                    "codigo_caso": "caso:ingreso_homologacion_externa",
                    "descripcion": "Estudiaste al menos 2 periodos en otra universidad pública o particular y deseas convalidar materias (1-18 dic)."
                },
                {
                    "id": "opc_ing_4",
                    "etiqueta": "Reingreso de Ex-Estudiante Ikiam",
                    "codigo_caso": "caso:ingreso_reingreso",
                    "descripcion": "Ex-alumno que suspendió estudios y desea retomar su carrera o reingresar con actualización de malla."
                },
                {
                    "id": "opc_ing_5",
                    "etiqueta": "Maestrías y Escuela de Posgrados",
                    "codigo_caso": "caso:posgrados_admision",
                    "descripcion": "Profesional con título de tercer nivel interesado en nuestras 6 maestrías híbridas (2da fase hasta 30/03/2027)."
                }
            ]
        },

        # 2. CAMBIO DE CARRERA / TRONCO COMÚN
        {
            "id": "flujo_cambio_carrera",
            "prioridad": 11,
            "categoria": "Movilidad y Cambio de Carrera",
            "palabras_clave": "cambio de carrera, cambiar de carrera, cambiarme de carrera, tronco comun, cambio interno, homologacion interna",
            "titulo_guia": "Guía de Cambio Interno de Carrera y Tronco Común",
            "saludo_cordial": "¡Hola! Te ayudamos a identificar la modalidad correcta para cambiar de carrera dentro de Ikiam.",
            "mensaje_orientador": "Dependiendo de si estás en el Tronco Común de 1er nivel o en niveles superiores, la normativa del CES (Arts. 96 y 97) establece rutas distintas:",
            "opciones": [
                {
                    "id": "opc_cc_tronco",
                    "etiqueta": "Primer Nivel - Tronco Común (Art. 97 RRA)",
                    "codigo_caso": "caso:cambio_carrera_tronco_comun",
                    "descripcion": "Transición entre Geociencias, Hidrología, Biotecnología y Ecosistemas (primer nivel compartido)."
                },
                {
                    "id": "opc_cc_estandar",
                    "etiqueta": "Cambio de Carrera Estándar (Art. 96 RRA)",
                    "codigo_caso": "caso:cambio_carrera_interno",
                    "descripcion": "Cambio hacia cualquier carrera aprobando >50% del 1er PAO y cumpliendo puntaje de cohorte (1-18 dic 2026)."
                },
                {
                    "id": "opc_cc_ext",
                    "etiqueta": "Transferencia Externa / Cambio de IES",
                    "codigo_caso": "caso:ingreso_homologacion_externa",
                    "descripcion": "Transferencia externa desde otra universidad nacional o extranjera."
                }
            ]
        },

        # 3. RETIROS, SEGUNDA/TERCERA MATRÍCULA Y ARANCELES
        {
            "id": "flujo_retiro",
            "prioridad": 12,
            "categoria": "Retiros, Matrículas y Gratuidad",
            "palabras_clave": "retirar materia, retiro de asignatura, retirarme, dar de baja, segunda matricula, tercera matricula, perdida de gratuidad, pagar materia, tabla arancelaria, aranceles, cancelar materia",
            "titulo_guia": "Orientación de Retiros, Segundas/Terceras Matrículas y Aranceles",
            "saludo_cordial": "Estimado/a estudiante, comprendo tu preocupación. En temas de retiro y repetición de matrículas, los plazos y la causa influyen directamente en tu gratuidad y permanencia:",
            "mensaje_orientador": "En el calendario 2PA 2026 la fecha ordinaria de retiro voluntario cerró el 30/10/2026, pero existen rutas vigentes por caso fortuito/fuerza mayor. Elige tu situación:",
            "opciones": [
                {
                    "id": "opc_ret_ord",
                    "etiqueta": "Retiro Voluntario Ordinario (Primeros 30 días)",
                    "codigo_caso": "caso:retiro_ordinario",
                    "descripcion": "Retiro dentro de los plazos ordinarios del calendario académico sin afectación a gratuidad."
                },
                {
                    "id": "opc_ret_fm",
                    "etiqueta": "Retiro por Salud Grave o Calamidad Doméstica",
                    "codigo_caso": "caso:retiro_fuerza_mayor",
                    "descripcion": "Retiro extraordinario fuera de plazo (hasta antes de finales) con respaldo médico validado en DBU o calamidad."
                },
                {
                    "id": "opc_ret_2mat",
                    "etiqueta": "Segunda Matrícula o Solicitud de Tercera Matrícula",
                    "codigo_caso": "caso:retiro_segunda_matricula",
                    "descripcion": "Protección de carrera (Art. 80 LOES) y ruta excepcional por fuerza mayor ante Vicerrectorado."
                },
                {
                    "id": "opc_ret_aran",
                    "etiqueta": "Pagos, Aranceles y Pérdida de Gratuidad",
                    "codigo_caso": "caso:aranceles_gratuidad",
                    "descripcion": "Cálculo diferenciado por quintil socioeconómico, liquidación en SGA y exoneraciones en DBU."
                }
            ]
        },

        # 4. ASISTENCIA Y JUSTIFICACIÓN DE INASISTENCIAS
        {
            "id": "flujo_faltas",
            "prioridad": 13,
            "categoria": "Asistencia y Justificaciones",
            "palabras_clave": "justificar falta, falte a clases, inasistencia, justificar inasistencias, falte al examen, reprogramar examen, falte por enfermedad, me enferme, reposo medico, asistencia 70",
            "titulo_guia": "Justificación de Inasistencias y Reprogramación (Plazo: 3 días hábiles)",
            "saludo_cordial": "Estimado/a estudiante, para conservar tu mínimo del 70% de asistencia y reprogramar evaluaciones, debes presentar tu solicitud dentro de 3 días hábiles desde tu reincorporación:",
            "mensaje_orientador": "El formulario es el mismo, pero cambia el paso previo en la red según tu motivo. Selecciona tu caso:",
            "opciones": [
                {
                    "id": "opc_fal_sal",
                    "etiqueta": "Justificación por Enfermedad o Cita Médica",
                    "codigo_caso": "caso:justificacion_salud",
                    "descripcion": "Paso obligatorio previo: validar el certificado médico en Centro de Salud DBU antes de remitir a tu Carrera."
                },
                {
                    "id": "opc_fal_cal",
                    "etiqueta": "Justificación por Calamidad Doméstica o Familiar",
                    "codigo_caso": "caso:justificacion_calamidad",
                    "descripcion": "Sin certificado médico personal: acta/certificado probatorio y carta motivada dirigida a tu Director/a de Carrera."
                },
                {
                    "id": "opc_fal_rep",
                    "etiqueta": "Justificación por Representación Institucional / Deportiva",
                    "codigo_caso": "caso:justificacion_representacion",
                    "descripcion": "Asistencia a eventos científicos, deportivos o culturales en nombre de Ikiam."
                }
            ]
        },

        # 5. BECAS, AYUDAS ECONÓMICAS Y SALUD
        {
            "id": "flujo_becas",
            "prioridad": 14,
            "categoria": "Becas, Ayudas y Salud",
            "palabras_clave": "beca, becas, ayuda economica, bienestar universitario, impugnar beca, consultorio medico, psicologia, odontologia, residencias estudiantiles, vivienda estudiantes",
            "titulo_guia": "Dirección de Bienestar Universitario (DBU): Becas, Ayudas y Salud",
            "saludo_cordial": "¡Hola! La Dirección de Bienestar Universitario gestiona becas, ayudas excepcionales y atención médica gratuita en Campus Muyuna:",
            "mensaje_orientador": "Nota importante: Ikiam NO dispone actualmente de residencias estudiantiles propias. Selecciona el servicio o beneficio que buscas:",
            "opciones": [
                {
                    "id": "opc_bec_post",
                    "etiqueta": "Postular a Beca (7 Modalidades + Excelencia >= 9.0)",
                    "codigo_caso": "caso:beca_postulacion",
                    "descripcion": "Formulario FO-GBU-40: escasos recursos, discapacidad, pueblos/nacionalidades, deportistas, investigación, abanderados."
                },
                {
                    "id": "opc_bec_ayu",
                    "etiqueta": "Solicitar Ayuda Económica (Calamidad, Titulación o Eventos)",
                    "codigo_caso": "caso:ayuda_economica_emergente",
                    "descripcion": "Formulario FO-GBU-56 (6 modalidades; calamidad, titulación, movilidad, eventos hasta 2.5 SBU)."
                },
                {
                    "id": "opc_bec_imp",
                    "etiqueta": "Impugnar Beca o Ayuda Denegada (Plazo 3 días)",
                    "codigo_caso": "caso:beca_impugnacion",
                    "descripcion": "Formulario FO-GBU-69 ante el Comité de Becas dentro de los 3 días siguientes a la notificación."
                },
                {
                    "id": "opc_bec_sal",
                    "etiqueta": "Servicios de Salud: Medicina, Psicología y Odontología",
                    "codigo_caso": "caso:servicios_salud_campus",
                    "descripcion": "Consultorio gratuito L-V 08h30-17h00 y validación de certificados médicos."
                }
            ]
        },

        # 6. PRÁCTICAS PREPROFESIONALES (DVS + DELEGADOS POR FACULTAD)
        {
            "id": "flujo_practicas",
            "prioridad": 15,
            "categoria": "Prácticas Preprofesionales (IT-GVI-05)",
            "palabras_clave": "practicas preprofesionales, practicas laborales, pasantias, 400 horas, vinculacion con la sociedad, servicio comunitario, ayudantia de catedra, ayudantia de investigacion, certificado de practicas, tutor de practicas, convenios practicas",
            "titulo_guia": "Red de Prácticas Preprofesionales (DVS y Delegados por Facultad)",
            "saludo_cordial": "¡Hola! Según el Instructivo vigente IT-GVI-05 (2026), las prácticas (400 horas totales) conectan a la Dirección de Vinculación (DVS) con el Delegado de tu Facultad y tu Tutor:",
            "mensaje_orientador": "Selecciona la etapa exacta en la que te encuentras (recuerda firmar los 8 formatos FO-GVI siempre en esfero azul):",
            "opciones": [
                {
                    "id": "opc_pr_1",
                    "etiqueta": "1. Iniciar Prácticas y Verificar Convenio (FO-GVI-29)",
                    "codigo_caso": "caso:practicas_inicio",
                    "descripcion": "Presentar con mínimo 12 días hábiles de anticipación a DVS (practicas.preprofesionales@ikiam.edu.ec)."
                },
                {
                    "id": "opc_pr_2",
                    "etiqueta": "2. Asignación de Docente Tutor por Facultad (FO-GVI-31)",
                    "codigo_caso": "caso:practicas_tutor_facultad",
                    "descripcion": "Enviar en máximo 5 días hábiles al Delegado de prácticas de tu Facultad (FCTA, FCV o FCSA)."
                },
                {
                    "id": "opc_pr_3",
                    "etiqueta": "3. Informes de Cierre y Certificado 400h (FO-GVI-06/07/36/30)",
                    "codigo_caso": "caso:practicas_certificado",
                    "descripcion": "Entrega en 15 días hábiles al finalizar; constancia final de cumplimiento requerida para titulación."
                }
            ]
        },

        # 7. TITULACIÓN E INGLÉS B1
        {
            "id": "flujo_titulacion_idiomas",
            "prioridad": 16,
            "categoria": "Titulación e Idiomas",
            "palabras_clave": "titulacion, graduarme, tesis, complexivo, prorroga de tesis, ingles b1, suficiencia ingles, exit test, placement test, centro de idiomas",
            "titulo_guia": "Titulación de Grado y Suficiencia de Inglés B1",
            "saludo_cordial": "Estimado/a estudiante, para declararte apto/a y titularte en Ikiam convergen cuatro pilares institucionales (malla 100%, inglés B1, prácticas DVS y trabajo de grado):",
            "mensaje_orientador": "Elige qué parte del proceso necesitas resolver:",
            "opciones": [
                {
                    "id": "opc_tit_1",
                    "etiqueta": "Requisitos de Graduación, Tesis, Complexivo y Prórrogas",
                    "codigo_caso": "caso:titulacion_requisitos_prorroga",
                    "descripcion": "Pasos con tu Carrera, paz y salvo, cambio a Examen Complexivo o solicitud de prórroga de gracia."
                },
                {
                    "id": "opc_tit_2",
                    "etiqueta": "Centro de Idiomas: Inglés B1, Placement y Exit Test",
                    "codigo_caso": "caso:idiomas_suficiencia_b1",
                    "descripcion": "Exámenes de ubicación y salida (11 dic 2026 - 4 mar 2027), 6 niveles y contacto centro.idiomas@ikiam.edu.ec."
                }
            ]
        },

        # 8. POSGRADOS, TI, BIBLIOTECA Y CAMPUS
        {
            "id": "flujo_servicios_campus",
            "prioridad": 17,
            "categoria": "Posgrados, TI, Biblioteca y Campus",
            "palabras_clave": "posgrado, maestria, correo institucional, soporte ti, sga clave, moodle, biblioteca, koha, donde queda ikiam, como llegar",
            "titulo_guia": "Posgrados, Soporte TI, Biblioteca y Campus Muyuna",
            "saludo_cordial": "¡Hola! Te conecto directamente con el área universitaria que atiende tu requerimiento:",
            "mensaje_orientador": "Selecciona el servicio institucional correspondiente:",
            "opciones": [
                {
                    "id": "opc_srv_pos",
                    "etiqueta": "Escuela de Posgrados (Maestrías Híbridas)",
                    "codigo_caso": "caso:posgrados_admision",
                    "descripcion": "Requisitos, cronograma 2da fase hasta 30/03/2027 y contacto con Directora EPG."
                },
                {
                    "id": "opc_srv_ti",
                    "etiqueta": "Soporte TI (SGA / Correo), Biblioteca Koha y Campus Tena",
                    "codigo_caso": "caso:servicios_ti_biblioteca_campus",
                    "descripcion": "Mesa de ayuda soporte@ikiam.edu.ec, biblioteca@ikiam.edu.ec y transporte a Muyuna."
                }
            ]
        },

        # 9. SALUDO INICIAL / MENÚ GENERAL (Prioridad menor para no interceptar consultas específicas)
        {
            "id": "flujo_saludo_inicio",
            "prioridad": 99,
            "categoria": "Menú Principal de Orientación",
            "palabras_clave": "hola, buenos dias, buenas tardes, buenas noches, buenas, saludos, menu, ayudame, ayuda por favor, orientacion, que haces, no se que hacer, estoy perdido",
            "titulo_guia": "Asistente Oficial de la Red Académica de Ikiam",
            "saludo_cordial": "¡Hola! Bienvenido/a al Asesor Académico de la Universidad Regional Amazónica Ikiam.",
            "mensaje_orientador": "Para no abrumarte con reglamentos largos y dirigirte exactamente al correo, documento y Facultad correcta, selecciona en qué área necesitas orientación:",
            "opciones": [
                {
                    "id": "opc_root_ing",
                    "etiqueta": "1. Ingreso a Ikiam (Nuevo Ingreso / Extranjero / Homologación)",
                    "codigo_caso": "flujo:flujo_ingreso",
                    "descripcion": "Bachilleres 1ra vez, extranjeros, cambio desde otra universidad o reingreso."
                },
                {
                    "id": "opc_root_tram",
                    "etiqueta": "2. Faltas, Retiros, 2da/3ra Matrícula o Cambio de Carrera",
                    "codigo_caso": "flujo:flujo_retiro",
                    "descripcion": "Problemas académicos durante el semestre, retiros por calamidad, aranceles y movilidad."
                },
                {
                    "id": "opc_root_just",
                    "etiqueta": "3. Justificar Inasistencias o Reprogramar Exámenes (3 días hábiles)",
                    "codigo_caso": "flujo:flujo_faltas",
                    "descripcion": "Por enfermedad (validación DBU), calamidad doméstica o representación institucional."
                },
                {
                    "id": "opc_root_bec",
                    "etiqueta": "4. Becas, Ayudas Económicas y Salud en Campus",
                    "codigo_caso": "flujo:flujo_becas",
                    "descripcion": "Postulaciones FO-GBU-40/56, impugnaciones y consultorio médico/psicológico."
                },
                {
                    "id": "opc_root_prac",
                    "etiqueta": "5. Prácticas Preprofesionales (400h), Inglés B1 y Titulación",
                    "codigo_caso": "flujo:flujo_practicas",
                    "descripcion": "Ruta DVS + Delegados FCTA/FCV/FCSA (FO-GVI), suficiencia B1 y graduación."
                },
                {
                    "id": "opc_root_fac",
                    "etiqueta": "6. Directorio por Facultades y Carreras (Decanos y Directores)",
                    "codigo_caso": "selector:facultades",
                    "descripcion": "Consulta los contactos oficiales de Ciencias de la Tierra y Agua, Ciencias de la Vida y Ciencias Socioambientales."
                }
            ]
        }
    ]

    for fl in flujos:
        cur.execute("""
        INSERT INTO flujos_decision (id, prioridad, categoria, palabras_clave, titulo_guia, saludo_cordial, mensaje_orientador, opciones_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            fl["id"],
            fl["prioridad"],
            fl["categoria"],
            fl["palabras_clave"],
            fl["titulo_guia"],
            fl["saludo_cordial"],
            fl["mensaje_orientador"],
            json.dumps(fl["opciones"], ensure_ascii=False)
        ))

    conn.commit()
    print(f"ikiam_flows.db reconstruida con exito ({cur.execute('SELECT COUNT(1) FROM flujos_decision').fetchone()[0]} flujos multi-nivel).")
    conn.close()


if __name__ == "__main__":
    init_flows_db()
