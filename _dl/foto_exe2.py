"""Arranca el .exe reconstruido, lo trae al frente y le hace una foto SOLO a su ventana.

Evidencia de que el ejecutable de verdad trae el selector y arranca en el idioma guardado.
"""
from __future__ import annotations

import ctypes
import json
import os
import subprocess
import time
from ctypes import wintypes

EXE = r"C:/Users/Lukas/p5x-datamining/p5x_studio/P5X Studio.exe"
CONFIG = r"C:/Users/Lukas/p5x-datamining/p5x_studio/config.json"
SALIDA = r"C:/Users/Lukas/p5x-datamining/_dl"

user32 = ctypes.windll.user32
user32.SetProcessDPIAware()


def fijar_idioma(codigo: str) -> None:
    datos = json.loads(open(CONFIG, encoding="utf-8").read())
    datos["idioma"] = codigo
    open(CONFIG, "w", encoding="utf-8").write(json.dumps(datos, ensure_ascii=False, indent=1))


def matar() -> None:
    subprocess.run(["taskkill", "/IM", "P5X Studio.exe", "/F"], capture_output=True)


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
            if "P5X Studio" in buf.value:
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
    time.sleep(13)  # que termine de rellenar la lista de personajes
    user32.ShowWindow(hwnd, 9)          # SW_RESTORE
    user32.SetForegroundWindow(hwnd)
    time.sleep(1.5)
    r = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    from PIL import ImageGrab
    img = ImageGrab.grab(bbox=(r.left, r.top, r.right, r.bottom))
    ruta = os.path.join(SALIDA, "exe_%s.png" % codigo)
    img.save(ruta)
    matar()
    time.sleep(1)
    return {"idioma": codigo, "ruta": ruta,
            "ventana": [r.right - r.left, r.bottom - r.top]}


def main():
    print(json.dumps([foto("es"), foto("en")], ensure_ascii=False, indent=1))
    fijar_idioma("es")
    print("config restaurada a es")


if __name__ == "__main__":
    main()