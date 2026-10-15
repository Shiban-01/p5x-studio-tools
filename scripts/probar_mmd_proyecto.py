"""Prueba REAL en MMD, automatica: parchea un proyecto de ejemplo para que cargue un modelo nuestro,
hace que MMD lo abra (menu file > open) y mira si sobrevive.

Por que asi: MMD no lee la linea de comandos, no tiene opcion de "cargar modelo" en los menus y el
arrastrar-y-soltar no se puede simular entre procesos (el sistema valida el handle del soltado en el
proceso que lo envia). Pero el menu "open" (id 205) si abre un cuadro de dialogo estandar, y a ese
dialogo se le puede escribir el fichero y darle a aceptar por mensajes. El proyecto .pmm guarda las
rutas de modelo en campos de tamaño fijo, asi que basta con sobrescribir una.

Uso:  python probar_mmd_proyecto.py <modelo.pmx> [segundos]
"""
import ctypes
import os
import shutil
import subprocess
import sys
import time
from ctypes import wintypes

EXE = r"C:\Users\Lukas\Desktop\MMD\MikuMikuDance.exe"
PLANTILLA = r"C:\Users\Lukas\Desktop\MMD\UserFile\sample.pmm"
SALIDA = r"C:\Users\Lukas\p5x-datamining\_dl\prueba_mmd.pmm"
CMS = 0x0205          # menu file > open
WM_COMMAND = 0x0111
WM_SETTEXT = 0x000C
IDOK = 1

u32 = ctypes.WinDLL("user32", use_last_error=True)
u32.EnumWindows.argtypes = [ctypes.c_void_p, wintypes.LPARAM]
u32.EnumChildWindows.argtypes = [wintypes.HWND, ctypes.c_void_p, wintypes.LPARAM]
u32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
u32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
u32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
u32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
u32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
u32.SendMessageW.restype = wintypes.LPARAM
u32.IsWindowVisible.argtypes = [wintypes.HWND]


def ventanas(pid, clase=None, visibles=True):
    salida = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def cb(hwnd, _):
        p = wintypes.DWORD()
        u32.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
        if p.value == pid:
            c = ctypes.create_unicode_buffer(256)
            u32.GetClassNameW(hwnd, c, 256)
            if clase and c.value != clase:
                return True
            if visibles and not u32.IsWindowVisible(hwnd):
                return True
            l = u32.GetWindowTextLengthW(hwnd)
            t = ctypes.create_unicode_buffer(l + 1)
            u32.GetWindowTextW(hwnd, t, l + 1)
            salida.append((hwnd, c.value, t.value))
        return True

    u32.EnumWindows(cb, 0)
    return salida


def hijos(hwnd):
    salida = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def cb(h, _):
        c = ctypes.create_unicode_buffer(256)
        u32.GetClassNameW(h, c, 256)
        l = u32.GetWindowTextLengthW(h)
        t = ctypes.create_unicode_buffer(l + 1)
        u32.GetWindowTextW(h, t, l + 1)
        salida.append((h, c.value, t.value))
        return True

    u32.EnumChildWindows(hwnd, cb, 0)
    return salida


def parchear_proyecto(modelo):
    """Sobrescribe en el .pmm las rutas del modelo de ejemplo por la nuestra (campo de texto fijo)."""
    d = bytearray(open(PLANTILLA, "rb").read())
    aguja = b"HB\\DownLoad\\MikuMikuDanceE_v708a\\UserFile\\Model\\Dammy_Bone.pmd"
    nueva = modelo.encode("cp932", "replace")
    tocadas = 0
    pos = d.find(aguja)
    while pos >= 0 and len(nueva) <= len(aguja):
        d[pos:pos + len(nueva)] = nueva
        d[pos + len(nueva)] = 0                      # termina la cadena
        tocadas += 1
        pos = d.find(aguja, pos + len(nueva))
    open(SALIDA, "wb").write(bytes(d))
    print("proyecto parcheado: %s (%d referencias al modelo)" % (SALIDA, tocadas))
    return tocadas


def main():
    modelo = sys.argv[1]
    espera = int(sys.argv[2]) if len(sys.argv) > 2 else 15
    parchear_proyecto(os.path.abspath(modelo))
    p = subprocess.Popen([EXE])
    hwnd = None
    limite = time.time() + 40
    while time.time() < limite:
        for h, c, t in ventanas(p.pid):
            if c == "Polygon Movie Maker":
                hwnd = h
                break
        if hwnd:
            break
        time.sleep(0.5)
    if not hwnd:
        print("no aparecio la ventana de MMD")
        p.kill()
        return
    time.sleep(2)
    print("abriendo el proyecto por el menu (WM_COMMAND %d)..." % CMS)
    u32.SendMessageW(hwnd, WM_COMMAND, CMS, 0)
    # esperar el cuadro de dialogo
    dlg = None
    limite = time.time() + 15
    while time.time() < limite and dlg is None:
        for h, c, t in ventanas(p.pid):
            if c == "#32770":
                dlg = h
                break
        time.sleep(0.3)
    if dlg is None:
        print("no aparecio el cuadro de dialogo de abrir fichero")
        p.terminate()
        return
    print("cuadro de dialogo encontrado")
    controles = hijos(dlg)
    edit = None
    for h, c, t in controles:
        if c == "Edit":
            edit = h
            break
    if edit is None:
        print("no encontre el campo de texto; controles:", [c for _, c, _ in controles][:15])
        p.terminate()
        return
    u32.SendMessageW(edit, WM_SETTEXT, 0, ctypes.c_wchar_p(os.path.abspath(SALIDA)))
    print("ruta escrita en el dialogo:", SALIDA)
    u32.SendMessageW(dlg, WM_COMMAND, IDOK, 0)
    t0 = time.time()
    caido = None
    while time.time() - t0 < espera:
        r = p.poll()
        if r is not None:
            caido = r
            break
        # ¿dialogos de MMD avisando de algo?
        for h, c, t in ventanas(p.pid):
            if c == "#32770":
                textos = [tt for _, cc, tt in hijos(h) if tt]
                print("  MMD dice: %r" % textos)
                u32.SendMessageW(h, WM_COMMAND, IDOK, 0)      # aceptar y seguir
        time.sleep(0.5)
    if caido is None:
        print("RESULTADO: VIVE  (MMD sigue en pie %.0f s despues de abrir el proyecto)" % espera)
        titulos = [t for _, c, t in ventanas(p.pid) if c == "Polygon Movie Maker"]
        print("  titulo de la ventana:", titulos)
        p.terminate()
        time.sleep(1.5)
        if p.poll() is None:
            p.kill()
    else:
        cod = caido & 0xFFFFFFFF
        print("RESULTADO: CRASHEO (codigo 0x%08X%s)" % (cod, ", violacion de acceso" if cod == 0xC0000005 else ""))
        for h, c, t in ventanas(p.pid):
            print("  ventana:", c, repr(t))


if __name__ == "__main__":
    main()
