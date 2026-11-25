# -*- coding: utf-8 -*-
"""
Script de sincronización de consultas reales entre el servidor en vivo (Render/Local)
y la PC del usuario (con soporte para autenticación segura, exportación a Excel, OneDrive y Google Drive).

Uso:
  1. Descargar consultas del servidor a la PC (usa token por defecto o argumento):
     python sincronizar_consultas_pc.py

  2. Con token explícito si se cambió en el servidor:
     python sincronizar_consultas_pc.py --token ikiam_admin_sec_2027

  3. Descargar continuamente cada N segundos:
     python sincronizar_consultas_pc.py --intervalo 60

  4. Incorporar respuestas corregidas por el usuario a la base de FAQs oficial:
     python sincronizar_consultas_pc.py --incorporar
"""

import argparse
import csv
import os
import shutil
import sys
import time
import urllib.request

DEFAULT_SERVER_URL = os.environ.get("IKIAM_SERVER_URL", "https://ikiam-academic-chatbot.onrender.com")
DEFAULT_ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "ikiam_admin_sec_2027")
LOCAL_CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "registro_consultas_estudiantes.csv")
ONEDRIVE_PATH = os.path.expanduser(r"~\OneDrive\registro_consultas_ikiam.csv")

def descargar_consultas(servidor_url: str = DEFAULT_SERVER_URL, ruta_salida: str = LOCAL_CSV_PATH, token: str = DEFAULT_ADMIN_TOKEN):
    """Descarga el CSV con todas las consultas desde el endpoint de auditoría con autenticación segura."""
    endpoint = f"{servidor_url.rstrip('/')}/api/consultas/exportar?formato=csv"
    headers = {
        "User-Agent": "Ikiam-Sync-PC/1.0",
        "X-Admin-Token": token
    }
    req = urllib.request.Request(endpoint, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            data = resp.read()
            with open(ruta_salida, "wb") as f:
                f.write(data)
            print(f"[OK] {len(data)} bytes descargados correctamente en: {ruta_salida}")
            
            # Sincronización opcional hacia OneDrive si la carpeta existe
            onedrive_dir = os.path.dirname(ONEDRIVE_PATH)
            if os.path.exists(onedrive_dir):
                shutil.copy2(ruta_salida, ONEDRIVE_PATH)
                print(f"[OK] Copia sincronizada en OneDrive: {ONEDRIVE_PATH}")
            return True
    except urllib.error.HTTPError as he:
        if he.code == 401:
            print(f"[ERROR] Acceso denegado (401). El token de administración proporcionado no es válido.")
        else:
            print(f"[ERROR HTTP {he.code}] al descargar del servidor ({servidor_url}): {he}")
        return False
    except Exception as e:
        print(f"[ERROR] No se pudo descargar del servidor ({servidor_url}): {e}")
        return False

def incorporar_respuestas_revisadas(ruta_csv: str = LOCAL_CSV_PATH):
    """
    Lee las filas del CSV donde el usuario colocó una 'Respuesta_Real_Esperada_Humana'
    y las alimenta automáticamente a la base de conocimiento usando ingestar_chats_admisiones.py.
    """
    if not os.path.exists(ruta_csv):
        print(f"[ERROR] No se encontró el archivo de consultas: {ruta_csv}")
        return

    pares_para_ingestar = []
    with open(ruta_csv, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for fila in reader:
            preg = (fila.get("Pregunta_Estudiante_Aspirante") or "").strip()
            resp_esperada = (fila.get("Respuesta_Real_Esperada_Humana") or "").strip()
            scope = (fila.get("Pestaña_Modulo") or "").strip().lower()
            
            # Solo ingestar si el usuario llenó una respuesta real esperada válida
            if preg and resp_esperada and len(resp_esperada) > 10:
                if scope in ("admisiones", "admision"):
                    pares_para_ingestar.append((preg, resp_esperada))

    if not pares_para_ingestar:
        print("[INFO] No se encontraron preguntas con 'Respuesta_Real_Esperada_Humana' nueva para incorporar.")
        print("Abra 'registro_consultas_estudiantes.csv' en Excel, complete esa columna y vuelva a ejecutar con --incorporar.")
        return

    print(f"[INFO] Se encontraron {len(pares_para_ingestar)} respuestas corregidas por el usuario. Ingestando...")
    try:
        from ingestar_chats_admisiones import ingestar_pares
        resumen = ingestar_pares(pares_para_ingestar, dry_run=False)
        print(f"[EXITO] Ingesta completada en ikiam_admisiones_faq.db: {resumen}")
    except Exception as e:
        print(f"[ERROR] Ingesta fallida: {e}")

def main():
    parser = argparse.ArgumentParser(description="Sincronizador de consultas de estudiantes Ikiam")
    parser.add_argument("--servidor", default=DEFAULT_SERVER_URL, help="URL del servidor chatbot")
    parser.add_argument("--token", default=DEFAULT_ADMIN_TOKEN, help="Token administrativo para autenticación")
    parser.add_argument("--intervalo", type=int, default=0, help="Segundos entre sincronizaciones (0 = una sola vez)")
    parser.add_argument("--incorporar", action="store_true", help="Alimentar las respuestas corregidas en Excel a la base de datos de FAQs")
    args = parser.parse_args()

    if args.incorporar:
        incorporar_respuestas_revisadas()
        return

    if args.intervalo > 0:
        print(f"Iniciando sincronización continua cada {args.intervalo}s contra {args.servidor}...")
        while True:
            descargar_consultas(args.servidor, token=args.token)
            time.sleep(args.intervalo)
    else:
        descargar_consultas(args.servidor, token=args.token)

if __name__ == "__main__":
    main()
