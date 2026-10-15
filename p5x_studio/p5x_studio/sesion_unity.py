"""Sesion de Unity: comprobar la licencia y abrir el editor para iniciar sesion una vez.

Por que existe esto: Unity en modo lote (que es como la herramienta saca el esqueleto y los pesos)
exige una licencia. Unity Personal se activa iniciando sesion UNA vez desde la ventana del editor;
a partir de ahi la licencia queda guardada en el equipo y el modo lote ya funciona solo.

Asi que la herramienta no puede pedir la licencia por su cuenta, pero si puede:
  1. decir si ya la tienes o no,
  2. abrir el editor en modo ventana para que inicies sesion,
  3. y volver a comprobar despues, sin que tengas que tocar nada mas.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from .idiomas import t

# donde Unity guarda la licencia, segun version y sistema
RUTAS_LICENCIA = (
    Path(r"C:/ProgramData/Unity/Unity_lic.ulf"),
    Path(r"C:/ProgramData/Unity/licenses"),
    Path(os.environ.get("PROGRAMDATA", r"C:/ProgramData")) / "Unity" / "licenses",
    Path(os.environ.get("APPDATA", "")) / "Unity" / "licenses" if os.environ.get("APPDATA") else None,
    Path(os.environ.get("LOCALAPPDATA", "")) / "Unity" / "licenses" if os.environ.get("LOCALAPPDATA") else None,
)

# El Hub es quien activa la licencia de verdad: el editor instalado a mano puede abrir una ventana
# de licencia, pero la activacion de Unity Personal vive en el Hub, que es donde se inicia sesion.
RUTAS_HUB = (
    Path(r"C:/Program Files/Unity Hub/Unity Hub.exe"),
    Path(os.environ.get("LOCALAPPDATA", "")) / "Programs/Unity Hub/Unity Hub.exe"
    if os.environ.get("LOCALAPPDATA") else None,
    Path(r"C:/Program Files/UnityHub/UnityHub.exe"),
)

# donde puede estar el editor instalado
RUTAS_UNITY = (
    Path(r"C:/Program Files/Unity/Hub/Editor"),
    Path(r"C:/Users/Lukas/Unity"),
    Path(r"C:/Program Files/Unity"),
)


def ruta_editor(version: str = "2022.3.49f1") -> Path | None:
    """Devuelve el Unity.exe del editor, buscando en las ubicaciones habituales."""
    candidatos = []
    for base in RUTAS_UNITY:
        if not base or not base.is_dir():
            continue
        candidatos.append(base / version / "Editor/Unity.exe")
        candidatos.append(base / "Editor/Unity.exe")
        try:
            for sub in base.iterdir():
                if sub.is_dir():
                    candidatos.append(sub / "Editor/Unity.exe")
        except Exception:
            pass
    for c in candidatos:
        if c.is_file():
            return c
    return None


def ruta_hub() -> Path | None:
    """Devuelve el Unity Hub si esta instalado. Es quien activa la licencia."""
    for c in RUTAS_HUB:
        if c and c.is_file():
            return c
    return None


def licencia_presente() -> bool:
    """Si hay licencia de Unity guardada en el equipo. Es lo que decide si el modo lote funciona."""
    for r in RUTAS_LICENCIA:
        if not r:
            continue
        try:
            if r.is_file() and r.stat().st_size > 0:
                return True
            # El Hub moderno no escribe `.ulf`: guarda `UnityEntitlementLicense.xml`. Buscar solo
            # `.ulf` daba falso negativo con la licencia perfectamente activa.
            if r.is_dir() and (any(r.glob("*.ulf")) or any(r.glob("*.xml"))):
                return True
        except Exception:
            continue
    return False


def abrir_para_iniciar_sesion(proyecto: Path | str | None = None,
                              version: str = "2022.3.49f1") -> tuple[bool, str]:
    """Abre el editor de Unity con ventana, para que el usuario inicie sesion una vez.

    Devuelve (bien, mensaje). No espera a que Unity se cierre: el editor tarda en arrancar y el
    usuario tiene que interactuar con el.
    """
    # El Hub primero: es quien activa la licencia de verdad. El editor instalado a mano puede
    # abrir una ventana de licencia, pero no siempre, asi que se usa como ultimo recurso.
    hub = ruta_hub()
    if hub:
        try:
            subprocess.Popen([str(hub)], creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))
        except Exception as e:
            return False, t("su_err_hub", e)
        return True, t("su_msg_hub", version)

    exe = ruta_editor(version)
    if not exe:
        return False, t("su_msg_sin_hub")
    orden = [str(exe)]
    if proyecto:
        orden += ["-projectPath", str(proyecto)]
    try:
        subprocess.Popen(orden, creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))
    except Exception as e:
        return False, t("su_err_unity", e)
    return True, t("su_msg_editor")


def resumen() -> dict:
    """Estado de la parte de Unity, para pintarlo en la interfaz."""
    exe = ruta_editor()
    hub = ruta_hub()
    return {
        "editor": str(exe) if exe else "",
        "editor_instalado": bool(exe),
        "hub": str(hub) if hub else "",
        "hub_instalado": bool(hub),
        "licencia": licencia_presente(),
        "listo": bool(exe) and licencia_presente(),
    }


if __name__ == "__main__":
    import json
    print(json.dumps(resumen(), ensure_ascii=False, indent=1))