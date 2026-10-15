"""Arranca P5X Studio Tools.exe, lo trae al frente y le hace una foto SOLO a su ventana.

Evidencia de que el ejecutable abre la pestana de herramientas (sin el apartado de modelos) y
responde al idioma guardado. Salida: _dl/tools_<idioma>.png
"""
from __future__ import annotations

import ctypes
import json
import os
import subprocess
import time
from ctypes import wintypes

EXE = r"C:/Users/Lukas/p5x-datamining/p5x_studio/P5X Studio Tools.exe"
CONFIG = r"C:/Users/Lukas/p5x-datamining/p5x_studio/config.json"
SALIDA = r"C:/Users/Lukas/p5x-datamining/_dl"

user32 = ctypes.windll.user32
user32.SetProcessDPIAware()


def fijar_idioma(codigo: str) -> None:
    datos = json.loads(open(CONFIG, encoding="utf-8").read())
    datos["idioma"] = codigo
    open(CONFIG, "w", encoding="utf-8").write(json.dumps(datos, ensure_ascii=False, indent=1))


def matar() -> None:
    subprocess.run(["taskkill", "/IM", "P5X Studio Tools.exe", "/F"], capture_output=True)


def buscar_ventana() -> int:
    encontrados = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def cb(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        n = user32.GetWindowTextLengthW(hwnd)
        if n:
            buf = ctypes.create_unicode_buffer(n + 1)
            user32.GetWindowTextW(hwnd, buf, n + 1)
            if "P5X Studio Tools" in buf.value:
                encontrados.append((hwnd, buf.value))
        return True

    user32.EnumWindows(cb, 0)
    return encontrados[0][0] if encontrados else 0


def foto(codigo: str) -> dict:
    fijar_idioma(codigo)
    matar()
    time.sleep(1)
    subprocess.Popen([EXE], cwd=os.path.dirname(EXE))
    hwnd = 0
    for _ in range(60):
        time.sleep(0.5)
        hwnd = buscar_ventana()
        if hwnd:
            break
    if not hwnd:
        matar()
        return {"idioma": codigo, "error": "no aparece la ventana"}
    time.sleep(9)                      # que rellene el explorador (16.535 bundles del disco)
    user32.ShowWindow(hwnd, 9)         # SW_RESTORE
    # al frente de verdad: topmost + foreground (sin esto el escritorio de Hermes se cuela en la
    # foto, porque ImageGrab copia la PANTALLA, no la ventana)
    HWND_TOPMOST, HWND_NOTOPMOST = -1, -2
    user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, 0x0001 | 0x0002)
    user32.SetForegroundWindow(hwnd)
    user32.BringWindowToTop(hwnd)
    time.sleep(2.5)
    r = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    from PIL import ImageGrab
    pantalla_w = user32.GetSystemMetrics(0)
    pantalla_h = user32.GetSystemMetrics(1)
    # si la ventana baja de la pantalla (la barra de titulo y el borde), se recorta al visible
    bbox = (max(r.left, 0), max(r.top, 0), min(r.right, pantalla_w), min(r.bottom, pantalla_h))
    img = ImageGrab.grab(bbox=bbox)
    ruta = os.path.join(SALIDA, "tools_%s.png" % codigo)
    img.save(ruta)
    user32.SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0, 0x0001 | 0x0002)
    matar()
    time.sleep(1)
    return {"idioma": codigo, "ruta": ruta, "ventana": [r.right - r.left, r.bottom - r.top],
            "foto": [img.width, img.height], "bbox": list(bbox)}


def main():
    print(json.dumps([foto("en"), foto("es")], ensure_ascii=False, indent=1))
    fijar_idioma("en")


if __name__ == "__main__":
    main()
