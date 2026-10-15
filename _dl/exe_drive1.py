# -*- coding: utf-8 -*-
"""Lanza el .exe real y localiza su ventana; guarda una captura inicial."""
import ctypes, subprocess, time, sys, os
from ctypes import wintypes
from PIL import ImageGrab

u32 = ctypes.windll.user32
EXE = r"C:/Users/Lukas/p5x-datamining/p5x_studio/P5X Studio.exe"

p = subprocess.Popen([EXE], cwd=r"C:/Users/Lukas/p5x-datamining/p5x_studio")
hwnd = None
for _ in range(60):
    time.sleep(0.5)
    hwnd = u32.FindWindowW(None, "P5X Studio")
    if hwnd:
        break
print("hwnd:", hwnd, "pid:", p.pid)
if not hwnd:
    print("no encontrado"); sys.exit(1)
u32.SetForegroundWindow(hwnd)
time.sleep(1.5)
r = wintypes.RECT()
u32.GetWindowRect(hwnd, ctypes.byref(r))
print("rect:", r.left, r.top, r.right, r.bottom)
img = ImageGrab.grab()
img.save(r"C:/Users/Lukas/p5x-datamining/_dl/exe_paso0.png")
print("captura -> exe_paso0.png")
# guarda hwnd para el siguiente paso
open(r"C:/Users/Lukas/p5x-datamining/_dl/_hwnd.txt", "w").write("%d %d %d %d %d" % (hwnd, r.left, r.top, r.right, r.bottom))