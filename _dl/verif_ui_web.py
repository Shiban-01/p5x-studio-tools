"""Verificacion real de la interfaz nueva de P5X Studio Tools.

Abre la app con P5X_STUDIO_UI=web, espera a que aparezca la ventana, la trae al frente,
hace una captura de pantalla, la MIDE (tamano y colores distintos) y la cierra.

Uso:  python verif_ui_web.py <salida.png> [segundos_espera]
"""
from __future__ import annotations

import ctypes
import subprocess
import sys
import time
from ctypes import wintypes
from pathlib import Path

RAIZ = Path(r"C:/Users/Lukas/p5x-datamining/p5x_studio")
PY = RAIZ / ".venv" / "Scripts" / "python.exe"

user32 = ctypes.windll.user32
user32.SetProcessDPIAware()


def ventanas():
    """[(hwnd, titulo)] de las ventanas visibles de nivel superior."""
    out = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def cb(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        n = user32.GetWindowTextLengthW(hwnd)
        if n:
            b = ctypes.create_unicode_buffer(n + 1)
            user32.GetWindowTextW(hwnd, b, n + 1)
            out.append((hwnd, b.value))
        return True

    user32.EnumWindows(cb, 0)
    return out


def al_frente(hwnd):
    user32.ShowWindow(hwnd, 9)          # SW_RESTORE
    user32.SetForegroundWindow(hwnd)
    time.sleep(1.0)


def rect(hwnd):
    r = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    return (r.left, r.top, r.right, r.bottom)


def main():
    destino = Path(sys.argv[1] if len(sys.argv) > 1 else "_dl/ui_web.png")
    espera = int(sys.argv[2]) if len(sys.argv) > 2 else 30

    ent = dict(**__import__("os").environ)
    ent["P5X_STUDIO_UI"] = "web"
    ent["P5X_STUDIO_SIN_INDICES"] = "1"

    print("lanzando P5X Studio Tools con la interfaz nueva ...")
    p = subprocess.Popen([str(PY), "arranque_tools.py"], cwd=str(RAIZ), env=ent,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    hwnd = titulo = None
    limite = time.time() + espera
    while time.time() < limite:
        if p.poll() is not None:
            print("SE CERRO SOLO (exit %s). Salida:" % p.returncode)
            print(p.stdout.read()[:3000])
            return 2
        for h, t in ventanas():
            if "P5X Studio" in t:
                hwnd, titulo = h, t
                break
        if hwnd:
            break
        time.sleep(1.0)

    if not hwnd:
        print("NO APARECIO NINGUNA VENTANA en %ds" % espera)
        p.terminate()
        try:
            print(p.stdout.read()[:3000])
        except Exception:
            pass
        return 3

    print("ventana encontrada: [%s]  hwnd=%s" % (titulo, hwnd))
    al_frente(hwnd)
    x1, y1, x2, y2 = rect(hwnd)
    print("geometria: (%d,%d)-(%d,%d)  %dx%d" % (x1, y1, x2, y2, x2 - x1, y2 - y1))

    from PIL import Image, ImageGrab
    time.sleep(3.0)                      # que termine de pintar el WebView
    im = ImageGrab.grab(bbox=(x1, y1, x2, y2))
    destino.parent.mkdir(parents=True, exist_ok=True)
    im.save(destino)

    cols = im.convert("RGB").getcolors(maxcolors=4000000)
    n = len(cols) if cols else ">4M"
    print("captura: %s  %s  colores=%s" % (destino, im.size, n))
    if cols:
        cols.sort(reverse=True)
        print("dominante: %s (%d px)" % (cols[0][1], cols[0][0]))
        negro = sum(c for c, rgb in cols if sum(rgb) < 12)
        print("negro puro: %.1f%%" % (100.0 * negro / (im.size[0] * im.size[1])))

    p.terminate()
    time.sleep(1.5)
    if p.poll() is None:
        subprocess.run(["taskkill", "/PID", str(p.pid), "/F"], capture_output=True)
    print("cerrada")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
