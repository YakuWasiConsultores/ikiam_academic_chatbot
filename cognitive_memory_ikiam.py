# -*- coding: utf-8 -*-
"""
CognitiveMemory — Memoria Cognitiva Persistente por Usuario para Render y Local.
Asegura bloqueo por usuario (RLock) y escritura atómica por hilo para evitar
condiciones de carrera ante mensajes concurrentes.
"""

import json
import os
import threading
import time
from typing import Any, Dict, List, Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SESSIONS_DIR = os.path.join(BASE_DIR, "sessions")

MAX_BYTES_POR_USUARIO = 1024 * 1024  # 1 MB exacto

_LOCKS_GUARD = threading.Lock()
_USER_LOCKS: Dict[str, threading.RLock] = {}


def _get_user_lock(user_id: str) -> threading.RLock:
    """Devuelve un RLock compartido por identificador de usuario."""
    with _LOCKS_GUARD:
        if user_id not in _USER_LOCKS:
            _USER_LOCKS[user_id] = threading.RLock()
        return _USER_LOCKS[user_id]


class UserCognitiveMemory:
    """Gestiona la memoria y conciencia individual de cada usuario/estudiante."""

    def __init__(self, user_id: str):
        self.user_id = "".join(c for c in user_id if c.isalnum() or c in ("_", "-")) or "default_user"
        self.file_path = os.path.join(SESSIONS_DIR, f"{self.user_id}_cognitive.json")
        self.lock = _get_user_lock(self.user_id)
        try:
            os.makedirs(SESSIONS_DIR, exist_ok=True)
        except OSError:
            pass
        self.datos = self._cargar()

    def _cargar(self) -> Dict[str, Any]:
        with self.lock:
            if os.path.exists(self.file_path):
                try:
                    with open(self.file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, dict):
                            return data
                except Exception:
                    pass
            return {
                "version": "2.1-conciencia",
                "user_id": self.user_id,
                "creado_en": time.strftime("%Y-%m-%d %H:%M:%S"),
                "perfil_estudiante": {
                    "carrera": "No especificada aún",
                    "semestre": "No especificado",
                    "situacion_especial": "Ninguna reportada",
                    "estado_academico": "Regular",
                },
                "hechos_aprendidos": {},
                "monologo_interno": (
                    "Iniciando atención personalizada para este estudiante. "
                    "Analizaré sus problemas de fondo sin dar respuestas prefabricadas."
                ),
                "ultima_opciones_flujo": [],
                "historial_episodico": [],
            }

    def _guardar(self):
        with self.lock:
            temp_path = f"{self.file_path}.{os.getpid()}.{threading.get_ident()}.tmp"
            try:
                os.makedirs(SESSIONS_DIR, exist_ok=True)
                with open(temp_path, "w", encoding="utf-8") as f:
                    json.dump(self.datos, f, ensure_ascii=False, indent=2)

                while (
                    len(self.datos.get("historial_episodico", [])) > 8
                    and os.path.exists(temp_path)
                    and os.path.getsize(temp_path) > MAX_BYTES_POR_USUARIO
                ):
                    self.datos["historial_episodico"].pop(0)
                    with open(temp_path, "w", encoding="utf-8") as f:
                        json.dump(self.datos, f, ensure_ascii=False, indent=2)

                os.replace(temp_path, self.file_path)
            except Exception as e:
                print(f"Error guardando memoria cognitiva de {self.user_id}: {e}")
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except OSError:
                        pass

    def actualizar_hecho(self, clave: str, valor: str):
        with self.lock:
            self.datos.setdefault("hechos_aprendidos", {})[clave.lower().strip()] = valor.strip()
            self._guardar()

    def actualizar_perfil(self, campo: str, valor: str):
        with self.lock:
            self.datos.setdefault("perfil_estudiante", {})[campo] = valor.strip()
            self._guardar()

    def registrar_monologo(self, pensamiento: str):
        with self.lock:
            self.datos["monologo_interno"] = pensamiento.strip()
            self._guardar()

    def guardar_opciones_flujo(self, opciones: List[Dict[str, str]]):
        """Guarda el último menú interactivo mostrado para resolver selecciones numéricas ('1', '2'...)."""
        with self.lock:
            compact = [
                {
                    "idx": i + 1,
                    "codigo_caso": str(o.get("codigo_caso", "")).strip(),
                    "etiqueta": str(o.get("etiqueta", "")).strip(),
                }
                for i, o in enumerate(opciones)
                if o.get("codigo_caso")
            ]
            self.datos["ultima_opciones_flujo"] = compact
            self._guardar()

    def resolver_opcion_numerica(self, texto: str) -> Optional[str]:
        """Si el usuario envía un número ('1', '2'...) tras un menú, devuelve el codigo_caso correspondiente."""
        limpio = texto.strip()
        if not limpio.isdigit():
            return None
        num = int(limpio)
        with self.lock:
            for opc in self.datos.get("ultima_opciones_flujo", []):
                if opc.get("idx") == num:
                    return opc.get("codigo_caso")
        return None

    def limpiar_opciones_flujo(self):
        with self.lock:
            if self.datos.get("ultima_opciones_flujo"):
                self.datos["ultima_opciones_flujo"] = []
                self._guardar()

    def registrar_episodio(self, pregunta: str, respuesta: str):
        with self.lock:
            hist = self.datos.setdefault("historial_episodico", [])
            hist.append({
                "fecha": time.strftime("%Y-%m-%d %H:%M:%S"),
                "estudiante": pregunta.strip(),
                "asesor": respuesta.strip(),
            })
            if len(hist) > 25:
                self.datos["historial_episodico"] = hist[-25:]
            self._guardar()

    def obtener_resumen_cognitivo(self) -> str:
        with self.lock:
            perfil = self.datos.get("perfil_estudiante", {})
            hechos = self.datos.get("hechos_aprendidos", {})
            hechos_str = (
                "\n".join([f"- {k}: {v}" for k, v in list(hechos.items())[-8:]])
                or "- Sin hechos específicos aprendidos todavía."
            )
            pensamiento = self.datos.get("monologo_interno", "")

            episodios = self.datos.get("historial_episodico", [])
            dialogo_previo = ""
            if episodios:
                valid_eps = [
                    ep for ep in episodios
                    if not any(b in ep.get("asesor", "").lower() for b in ("format/links", "no evasives", "clean markdown"))
                ]
                if valid_eps:
                    dialogo_previo = "\nDIÁLOGO PREVIO CON ESTE ESTUDIANTE:\n"
                    for ep in valid_eps[-3:]:
                        dialogo_previo += f"• Estudiante: {ep['estudiante']}\n• Asesor: {ep['asesor']}\n"

            return (
                f"--- MEMORIA COGNITIVA Y CONCIENCIA DEL ESTUDIANTE (ID: {self.user_id}) ---\n"
                f"Perfil detectado: Carrera: {perfil.get('carrera')} | Semestre: {perfil.get('semestre')} | "
                f"Situación: {perfil.get('situacion_especial')}\n"
                f"Hechos consolidados en la memoria de este estudiante:\n{hechos_str}\n"
                f"Tu pensamiento y conciencia interna hacia este estudiante:\n\"{pensamiento}\""
                f"{dialogo_previo}"
                f"\n--------------------------------------------------------------------------"
            )
