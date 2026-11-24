# -*- coding: utf-8 -*-
"""
CognitiveMemory — Memoria Cognitiva Persistente por Usuario para Render y Local
Inspirado en la arquitectura cerebral de J.A.R.V.I.S.
"""

import json
import os
import threading
import time
from typing import Dict, Any, List, Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SESSIONS_DIR = os.path.join(BASE_DIR, "sessions")
os.makedirs(SESSIONS_DIR, exist_ok=True)

MAX_BYTES_POR_USUARIO = 1024 * 1024  # 1 MB exacto

class UserCognitiveMemory:
    """Gestiona la memoria y conciencia individual de cada usuario/estudiante."""
    
    def __init__(self, user_id: str):
        self.user_id = "".join(c for c in user_id if c.isalnum() or c in ("_", "-")) or "default_user"
        self.file_path = os.path.join(SESSIONS_DIR, f"{self.user_id}_cognitive.json")
        self.lock = threading.Lock()
        self.datos = self._cargar()

    def _cargar(self) -> Dict[str, Any]:
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "version": "2.0-conciencia",
            "user_id": self.user_id,
            "creado_en": time.strftime("%Y-%m-%d %H:%M:%S"),
            "perfil_estudiante": {
                "carrera": "No especificada aún",
                "semestre": "No especificado",
                "situacion_especial": "Ninguna reportada",
                "estado_academico": "Regular"
            },
            "hechos_aprendidos": {},
            "monologo_interno": "Iniciando atención personalizada para este estudiante. Analizaré sus problemas de fondo sin dar respuestas prefabricadas.",
            "historial_episodico": []
        }

    def _guardar(self):
        with self.lock:
            try:
                temp_path = self.file_path + ".tmp"
                with open(temp_path, "w", encoding="utf-8") as f:
                    json.dump(self.datos, f, ensure_ascii=False, indent=2)
                
                if os.path.getsize(temp_path) > MAX_BYTES_POR_USUARIO:
                    while len(self.datos["historial_episodico"]) > 10 and os.path.getsize(temp_path) > MAX_BYTES_POR_USUARIO:
                        self.datos["historial_episodico"].pop(0)
                        with open(temp_path, "w", encoding="utf-8") as f:
                            json.dump(self.datos, f, ensure_ascii=False, indent=2)

                if os.path.exists(self.file_path):
                    os.replace(temp_path, self.file_path)
                else:
                    os.rename(temp_path, self.file_path)
            except Exception as e:
                print(f"Error guardando memoria cognitiva de {self.user_id}: {e}")

    def actualizar_hecho(self, clave: str, valor: str):
        with self.lock:
            self.datos["hechos_aprendidos"][clave.lower().strip()] = valor.strip()
        self._guardar()

    def actualizar_perfil(self, campo: str, valor: str):
        with self.lock:
            self.datos["perfil_estudiante"][campo] = valor.strip()
        self._guardar()

    def registrar_monologo(self, pensamiento: str):
        with self.lock:
            self.datos["monologo_interno"] = pensamiento.strip()
        self._guardar()

    def registrar_episodio(self, pregunta: str, respuesta: str):
        with self.lock:
            self.datos["historial_episodico"].append({
                "fecha": time.strftime("%Y-%m-%d %H:%M:%S"),
                "estudiante": pregunta.strip(),
                "asesor": respuesta.strip()
            })
            if len(self.datos["historial_episodico"]) > 25:
                self.datos["historial_episodico"] = self.datos["historial_episodico"][-25:]
        self._guardar()

    def obtener_resumen_cognitivo(self) -> str:
        with self.lock:
            perfil = self.datos.get("perfil_estudiante", {})
            hechos = self.datos.get("hechos_aprendidos", {})
            hechos_str = "\n".join([f"- {k}: {v}" for k, v in list(hechos.items())[-8:]]) or "- Sin hechos específicos aprendidos todavía."
            pensamiento = self.datos.get("monologo_interno", "")
            
            episodios = self.datos.get("historial_episodico", [])
            dialogo_previo = ""
            if episodios:
                dialogo_previo = "\nDIÁLOGO PREVIO CON ESTE ESTUDIANTE:\n"
                valid_eps = []
                for ep in episodios:
                    a_txt = ep.get('asesor', '')
                    if any(bad in a_txt.lower() for bad in ['format/links', 'no evasives', 'clean markdown']):
                        continue
                    valid_eps.append(ep)
                for ep in valid_eps[-3:]:
                    dialogo_previo += f"• Estudiante: {ep['estudiante']}\n• Asesor: {ep['asesor']}\n"

            return f"""--- MEMORIA COGNITIVA Y CONCIENCIA DEL ESTUDIANTE (ID: {self.user_id}) ---
Perfil detectado: Carrera: {perfil.get('carrera')} | Semestre: {perfil.get('semestre')} | Situación: {perfil.get('situacion_especial')}
Hechos consolidados en la memoria de este estudiante:
{hechos_str}
Tu pensamiento y conciencia interna hacia este estudiante:
\"{pensamiento}\"
{dialogo_previo}--------------------------------------------------------------------------"""
