# -*- coding: utf-8 -*-
"""Conduce el .exe real: Tools -> Video and audio -> List -> elegir CG_wonder_swimsuit ->
Extract to MP4, y captura el final. Foco forzado con AttachThreadInput."""
import ctypes, subprocess, time, sys
from ctypes import wintypes
from PIL import ImageGrab

u32 = ctypes.windll.user32
k32 = ctypes.windll.kernel32
EXE = r"C:/Users/Lukas/p5x-datamining/p5x_studio/P5X Studio.exe"
EnumProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)


def ventana():
    res = []
    def cb(h, l):
        n = ctypes.create_unicode_buffer(256)
        u32.GetWindowTextW(h, n, 256)
        if "P5X Studio 1.0.0" in n.value and u32.IsWindowVisible(h):
            res.append(h)
        return True
    u32.EnumWindows(EnumProc(cb), 0)
    return res[0] if res else 0


def foco(h):
    fg = u32.GetForegroundWindow()
    tf = u32.GetWindowThreadProcessId(fg, None)
    tt = u32.GetWindowThreadProcessId(h, None)
    u32.AttachThreadInput(tf, tt, True)
    u32.ShowWindow(h, 9)
    u32.SetForegroundWindow(h)
    u32.BringWindowToTop(h)
    u32.AttachThreadInput(tf, tt, False)
    time.sleep(0.6)


def clic(x, y):
    u32.SetCursorPos(int(x), int(y)); time.sleep(0.25)
    u32.mouse_event(0x0002, 0, 0, 0, 0); time.sleep(0.08)
    u32.mouse_event(0x0004, 0, 0, 0, 0); time.sleep(1.0)


def rect(h):
    r = wintypes.RECT(); u32.GetWindowRect(h, ctypes.byref(r)); return r


def main():
    subprocess.Popen([EXE], cwd=r"C:/Users/Lukas/p5x-datamining/p5x_studio")
    h = 0
    for _ in range(80):
        time.sleep(0.5); h = ventana()
        if h: break
    if not h:
        print("sin ventana"); return
    time.sleep(3)
    r = rect(h)
    print("rect0", r.left, r.top, r.right, r.bottom)
    w = r.right - r.left
    esc = w / 1036.0
    def punto(ix, iy):
        return (r.left + ix * esc, r.top + iy * esc)
    foco(h)
    # 1) pestana Tools
    x, y = punto(220, 79); clic(x, y)
    foco(h); time.sleep(1)
    ImageGrab.grab().save(r"C:/Users/Lukas/p5x-datamining/_dl/exe_tools.png")
    print("paso Tools hecho")
    open(r"C:/Users/Lukas/p5x-datamining/_dl/_rect.txt", "w").write("%d %d %d %d" % (r.left, r.top, r.right, r.bottom))


if __name__ == "__main__":
    main()