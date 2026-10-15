"""Arranque de P5X Studio Tools: elige la interfaz nueva (pywebview/WebView2) o la clasica.

Reglas (lo pidio el usuario):
  - El motor elegido es WebView2 (lo trae Windows 11), pero **no abre navegador**: pywebview usa el
    runtime Evergreen del sistema.
  - Si WebView2 no esta disponible, la app arranca con la interfaz CLASICA de tkinter en vez de
    fallar.
  - La deteccion va por DOS vias, porque cada una falla distinto:
        (a) mirar si el runtime esta REGISTRADO en Windows (clave del cliente de EdgeUpdate); y
        (b) INTENTAR abrir de verdad una ventana WebView2 y capturar el fallo.
  - Se puede forzar la clasica con la variable de entorno `P5X_STUDIO_UI=clasica` (o el parametro
    `--ui=clasica`), y forzar la nueva con `P5X_STUDIO_UI=web`.
  - `P5X_STUDIO_UI=auto` (por defecto) decide: nueva si pasa las dos vias, si no clasica.
  - `P5X_STUDIO_WEBVIEW2_OFF=1` finge que WebView2 no esta instalado, para probar la caida real a
    la interfaz clasica sin tocar el equipo.

La decision se deja escrita en `cache/ui_decision.txt` para poder comprobarla.

Modo de verificacion (solo cuando se pide por entorno):
  - `P5X_STUDIO_UI_CAPTURA=<ruta.png>`  -> al abrir la ventana nueva, guarda una captura de pantalla.
  - `P5X_STUDIO_UI_AUTOCIERRE=<segundos>` -> cierra la ventana nueva sola (para no dejarla colgada).
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

from . import ajustes, idiomas

WEBVIEW2_GUID = "{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"


# --------------------------------------------------------------------------- deteccion
def webview2_registrado() -> str | None:
    """Version del runtime WebView2 Evergreen si esta registrado en Windows, o None.

    Mira las tres ubicaciones que el instalador de Microsoft usa: HKLM 32/64 y HKCU.

    `P5X_STUDIO_WEBVIEW2_OFF=1` hace como si NO estuviera instalado. Sirve para comprobar el camino
    de emergencia (la interfaz clasica) en un equipo donde si esta, que es el unico caso que de
    otra forma no se puede probar sin desinstalar nada.
    """
    if os.environ.get("P5X_STUDIO_WEBVIEW2_OFF"):
        return None
    try:
        import winreg
    except Exception:
        return None
    sitios = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\\" + WEBVIEW2_GUID),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\EdgeUpdate\Clients\\" + WEBVIEW2_GUID),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\EdgeUpdate\Clients\\" + WEBVIEW2_GUID),
    ]
    for hive, ruta in sitios:
        try:
            with winreg.OpenKey(hive, ruta) as k:
                v, _ = winreg.QueryValueEx(k, "pv")
                if v:
                    return str(v)
        except OSError:
            continue
    return None


_PROBE = (
    "import webview\n"
    "w = webview.create_window('p5x-probe', html='<html><body></body></html>', hidden=True)\n"
    "def _q():\n"
    "    import time; time.sleep(1.0)\n"
    "    try: w.destroy()\n"
    "    except Exception: pass\n"
    "webview.start(_q, gui='edgechromium')\n"
)


def webview2_funciona(timeout: int = 45) -> bool:
    """Intenta ABRIR de verdad una ventana WebView2 en un proceso aparte y captura el fallo.

    Se hace en un subproceso a proposito: asi no ensucia este proceso y, si se cuelga, se mata
    por tiempo sin arrastrar a la aplicacion. Solo aplica sin congelar (un .exe congelado no puede
    ejecutar `python -c`); congelado, el intento real es abrir la ventana de verdad y capturar su
    excepcion (ver `arrancar`).
    """
    if getattr(sys, "frozen", False):
        return False
    try:
        r = subprocess.run([sys.executable, "-c", _PROBE], capture_output=True, text=True,
                           timeout=timeout,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return r.returncode == 0
    except Exception:
        return False


def _modo_pedido() -> str:
    """`clasica`, `web` o `auto` (por defecto), desde --ui=... o P5X_STUDIO_UI."""
    v = ""
    for a in sys.argv[1:]:
        if a.startswith("--ui="):
            v = a.split("=", 1)[1]
    v = (v or os.environ.get("P5X_STUDIO_UI", "") or "auto").strip().lower()
    if v in ("clasica", "clásica", "classic", "tk", "tkinter", "vieja"):
        return "clasica"
    if v in ("web", "nueva", "html", "webview"):
        return "web"
    return "auto"


def _anotar(texto: str) -> None:
    try:
        ajustes.CACHE.mkdir(parents=True, exist_ok=True)
        with open(ajustes.CACHE / "ui_decision.txt", "a", encoding="utf-8") as f:
            f.write("[%s] %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), texto))
    except Exception:
        pass


# --------------------------------------------------------------------------- arranques
def _clasica(razon: str = "") -> None:
    _anotar("ui=classic  %s" % razon)
    from .gui_tools import arrancar as arrancar_clasica
    arrancar_clasica()


def _web() -> None:
    from . import ui_web
    ui_web.arrancar()


def arrancar() -> None:
    """Punto de entrada de la version Tools."""
    # La Tools se publica SOLO en ingles: no hay selector ni se lee el idioma guardado (ese
    # ajuste es de la app de modelos, que si es bilingue).
    idiomas._ACTIVO["v"] = "en"
    modo = _modo_pedido()
    ver = webview2_registrado()
    _anotar("requested=%s  webview2_registered=%s" % (modo, ver or "no"))

    if modo == "clasica":
        _clasica("asked for by the user")
        return

    if modo == "web":
        # forzada: se intenta la ventana real; si falla, se cae a la clasica (salvo pedido estricto)
        try:
            _anotar("ui=web  real attempt (forced)")
            _web()
            return
        except Exception as e:
            _anotar("the web ui failed: %r" % e)
            if os.environ.get("P5X_STUDIO_UI_ESTRICTO"):
                raise
            _clasica("the web ui failed: %r" % e)
            return

    # modo auto
    if not ver:
        _clasica("WebView2 is not registered")
        return
    if os.environ.get("P5X_STUDIO_UI_PROBE", "1") != "0":
        if getattr(sys, "frozen", False):
            # Congelado NO se puede lanzar la sonda en subproceso (no hay interprete que ejecutar):
            # la segunda via es abrir la ventana de verdad a continuacion y capturar su excepcion,
            # que es justo lo que hace el try/except de mas abajo. Si aqui usaramos
            # `webview2_funciona()` (que devuelve False al estar congelado) la app caeria SIEMPRE a
            # la clasica aunque WebView2 funcione, y la interfaz nueva no se veria nunca.
            _anotar("frozen: the second check is the real window attempt")
        else:
            ok = webview2_funciona()
            _anotar("real WebView2 window attempt = %s" % ("ok" if ok else "failed"))
            if not ok:
                _clasica("WebView2 registered (%s) but the real window failed" % ver)
                return
    try:
        _anotar("ui=web  (auto, both checks ok)")
        _web()
    except Exception as e:
        _anotar("the web ui failed: %r" % e)
        _clasica("the web ui fell back: %r" % e)


if __name__ == "__main__":
    arrancar()
