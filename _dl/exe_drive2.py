# -*- coding: utf-8 -*-
"""Lanza el .exe real, espera su ventana por PID, y guarda una captura inicial."""
import ctypes, subprocess, time, sys
from ctypes import wintypes
from PIL import ImageGrab

u32 = ctypes.windll.user32
EXE = r"C:/Users/Lukas/p5x-datamining/p5x_studio/P5X Studio.exe"
EnumProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)


def ventanas(pid):
    out = []
    def cb(h, l):
        p = wintypes.DWORD()
        u32.GetWindowThreadProcessId(h, ctypes.byref(p))
        if p.value == pid and u32.IsWindowVisible(h):
            n = ctypes.create_unicode_buffer(256)
            u32.GetWindowTextW(h, n, 256)
            out.append((h, n.value))
        return True
    u32.EnumWindows(EnumProc(cb), 0)
    return out


p = subprocess.Popen([EXE], cwd=r"C:/Users/Lukas/p5x-datamining/p5x_studio")
hwnd, titulo = 0, ""
for _ in range(80):
    time.sleep(0.5)
    vs = ventanas(p.pid)
    if vs:
        hwnd, titulo = vs[0]
        break
print("pid:", p.pid, "hwnd:", hwnd, "titulo:", repr(titulo))
if not hwnd:
    print("no encontrado"); sys.exit(1)
time.sleep(2)
u32.SetForegroundWindow(hwnd)
time.sleep(1)
r = wintypes.RECT(); u32.GetWindowRect(hwnd, ctypes.byref(r))
print("rect:", r.left, r.top, r.right, r.bottom)
ImageGrab.grab().save(r"C:/Users/Lukas/p5x-datamining/_dl/exe_paso0.png")
print("captura -> exe_paso0.png")
open(r"C:/Users/Lukas/p5x-datamining/_dl/_hwnd.txt", "w").write("%d %d %d %d %d" % (hwnd, r.left, r.top, r.right, r.bottom))