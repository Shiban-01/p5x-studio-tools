# -*- coding: utf-8 -*-
"""Lanza el .exe y guarda una captura de pantalla; localiza la ventana por titulo."""
import ctypes, subprocess, time, sys
from ctypes import wintypes
from PIL import ImageGrab

u32 = ctypes.windll.user32
EXE = r"C:/Users/Lukas/p5x-datamining/p5x_studio/P5X Studio.exe"
EnumProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)


def buscar(titulo):
    out = []
    def cb(h, l):
        n = ctypes.create_unicode_buffer(256)
        u32.GetWindowTextW(h, n, 256)
        if titulo.lower() in n.value.lower() and u32.IsWindowVisible(h):
            out.append((h, n.value))
        return True
    u32.EnumWindows(EnumProc(cb), 0)
    return out


subprocess.Popen([EXE], cwd=r"C:/Users/Lukas/p5x-datamining/p5x_studio")
hwnd = 0
for _ in range(80):
    time.sleep(0.5)
    v = buscar("P5X Studio 1.0.0")
    if v:
        hwnd = v[0][0]; break
print("hwnd:", hwnd)
if not hwnd:
    sys.exit(1)
time.sleep(3)
u32.SetForegroundWindow(hwnd)
time.sleep(1)
r = wintypes.RECT(); u32.GetWindowRect(hwnd, ctypes.byref(r))
print("rect:", r.left, r.top, r.right, r.bottom)
ImageGrab.grab().save(r"C:/Users/Lukas/p5x-datamining/_dl/exe_paso0.png")
print("captura -> exe_paso0.png")