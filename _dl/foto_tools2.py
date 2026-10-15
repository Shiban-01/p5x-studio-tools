"""Foto del ejecutable SIN depender de quien tenga el foco.

`ImageGrab.grab(bbox)` copia la PANTALLA: si el escritorio de Hermes queda encima, la foto sale del
escritorio. Aqui se usa `PrintWindow(..., PW_RENDERFULLCONTENT)`, que le pide a la propia ventana que
se dibuje en un bitmap: funciona aunque este tapada y no roba el foco a nadie.

Salida: _dl/tools_<idioma>.png
"""
from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import json
import os
import subprocess
import time

from PIL import Image

EXE = r"C:/Users/Lukas/p5x-datamining/p5x_studio/P5X Studio Tools.exe"
CONFIG = r"C:/Users/Lukas/p5x-datamining/p5x_studio/config.json"
SALIDA = r"C:/Users/Lukas/p5x-datamining/_dl"

u = ctypes.windll.user32
g = ctypes.windll.gdi32
u.SetProcessDPIAware()


class _CABECERA(ctypes.Structure):
    _fields_ = [("biSize", wt.DWORD), ("biWidth", wt.LONG), ("biHeight", wt.LONG),
                ("biPlanes", wt.WORD), ("biBitCount", wt.WORD), ("biCompression", wt.DWORD),
                ("biSizeImage", wt.DWORD), ("biXPelsPerMeter", wt.LONG),
                ("biYPelsPerMeter", wt.LONG), ("biClrUsed", wt.DWORD),
                ("biClrImportant", wt.DWORD)]


class _INFO(ctypes.Structure):
    _fields_ = [("bmiHeader", _CABECERA), ("bmiColors", wt.DWORD * 3)]


def fijar_idioma(codigo: str) -> None:
    datos = json.loads(open(CONFIG, encoding="utf-8").read())
    datos["idioma"] = codigo
    open(CONFIG, "w", encoding="utf-8").write(json.dumps(datos, ensure_ascii=False, indent=1))


def matar() -> None:
    subprocess.run(["taskkill", "/IM", "P5X Studio Tools.exe", "/F"], capture_output=True)


def buscar_ventana() -> int:
    fuera = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)
    def cb(hwnd, _):
        if user32_visible(hwnd):
            n = u.GetWindowTextLengthW(hwnd)
            if n:
                buf = ctypes.create_unicode_buffer(n + 1)
                u.GetWindowTextW(hwnd, buf, n + 1)
                if "P5X Studio Tools" in buf.value:
                    fuera.append(hwnd)
        return True

    u.EnumWindows(cb, 0)
    return fuera[0] if fuera else 0


def user32_visible(hwnd) -> bool:
    return bool(u.IsWindowVisible(hwnd))


def capturar(hwnd: int, ruta: str) -> tuple:
    """Pide a la ventana que se dibuje en un bitmap (aunque este debajo de otras)."""
    r = wt.RECT()
    u.GetWindowRect(hwnd, ctypes.byref(r))
    ancho, alto = r.right - r.left, r.bottom - r.top
    hdc = u.GetWindowDC(hwnd)
    mem = g.CreateCompatibleDC(hdc)
    bmp = g.CreateCompatibleBitmap(hdc, ancho, alto)
    g.SelectObject(mem, bmp)
    # 2 = PW_RENDERFULLCONTENT (necesario para ventanas compuestas)
    if not u.PrintWindow(hwnd, mem, 2):
        u.PrintWindow(hwnd, mem, 0)
    info = _INFO()
    info.bmiHeader.biSize = ctypes.sizeof(_CABECERA)
    info.bmiHeader.biWidth = ancho
    info.bmiHeader.biHeight = -alto          # negativo = filas de arriba abajo
    info.bmiHeader.biPlanes = 1
    info.bmiHeader.biBitCount = 32
    info.bmiHeader.biCompression = 0         # BI_RGB
    buf = ctypes.create_string_buffer(ancho * alto * 4)
    g.GetDIBits(mem, bmp, 0, alto, buf, ctypes.byref(info), 0)
    g.DeleteObject(bmp)
    g.DeleteDC(mem)
    u.ReleaseDC(hwnd, hdc)
    img = Image.frombuffer("RGB", (ancho, alto), buf, "raw", "BGRX", 0, 1)
    img.save(ruta)
    return ancho, alto


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
    time.sleep(9)                    # que rellene el explorador (16.535 bundles del disco)
    ruta = os.path.join(SALIDA, "tools_%s.png" % codigo)
    ancho, alto = capturar(hwnd, ruta)
    matar()
    time.sleep(1)
    return {"idioma": codigo, "ruta": ruta, "ventana": [ancho, alto]}


def main():
    print(json.dumps([foto("en"), foto("es")], ensure_ascii=False, indent=1))
    fijar_idioma("en")


if __name__ == "__main__":
    main()