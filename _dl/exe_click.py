# -*- coding: utf-8 -*-
"""Clic en coordenadas de PANTALLA sobre la ventana del exe y captura. Uso: exe_click.py X Y salida.png"""
import ctypes, sys, time
from ctypes import wintypes
from PIL import ImageGrab

u32 = ctypes.windll.user32
EnumProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)


def buscar(titulo):
    out = []
    def cb(h, l):
        n = ctypes.create_unicode_buffer(256)
        u32.GetWindowTextW(h, n, 256)
        if titulo.lower() in n.value.lower() and u32.IsWindowVisible(h):
            out.append(h)
        return True
    u32.EnumWindows(EnumProc(cb), 0)
    return out


def clic(x, y):
    u32.SetCursorPos(int(x), int(y))
    time.sleep(0.25)
    u32.mouse_event(0x0002, 0, 0, 0, 0)  # LEFTDOWN
    time.sleep(0.06)
    u32.mouse_event(0x0004, 0, 0, 0, 0)  # LEFTUP
    time.sleep(0.6)


def main():
    x, y, salida = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
    v = buscar("P5X Studio 1.0.0")
    if not v:
        print("ventana no encontrada"); return
    h = v[0]
    u32.SetForegroundWindow(h)
    time.sleep(0.4)
    clic(x, y)
    time.sleep(1.2)
    ImageGrab.grab().save(salida)
    print("clic en", x, y, "->", salida)


if __name__ == "__main__":
    main()