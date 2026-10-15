"""Prueba automatica en el MMD de verdad: lanza MMD, le suelta un modelo por WM_DROPFILES y mira si vive.

MMD no lee la linea de comandos (no importa GetCommandLine), asi que la unica forma de cargar un
modelo sin tocar el raton es simular el arrastrar y soltar: se reserva memoria DENTRO del proceso de
MMD con una estructura DROPFILES y se le manda el mensaje WM_DROPFILES.

Uso:  python probar_mmd.py <modelo.pmx> [segundos_de_espera]
Salida: VIVE (cargo bien) o CRASHEO (codigo de salida), y el desplazamiento del fallo si lo hay.
"""
import ctypes
import subprocess
import sys
import time
from ctypes import wintypes

EXE = r"C:\Users\Lukas\Desktop\MMD\MikuMikuDance.exe"

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
u32 = ctypes.WinDLL("user32", use_last_error=True)

WM_DROPFILES = 0x0233
PROCESS_ALL_ACCESS = 0x1F0FFF
MEM_COMMIT_RESERVE = 0x3000
PAGE_READWRITE = 0x04
MEM_RELEASE = 0x8000


class DROPFILES(ctypes.Structure):
    _fields_ = [("pFiles", wintypes.DWORD), ("pt", wintypes.POINT),
                ("fNC", wintypes.BOOL), ("fWide", wintypes.BOOL)]


# Sin los prototipos, ctypes devuelve int (32 bits) y TRUNCA los punteros de 64 bits: el mensaje
# fallaba al enviarse y la memoria se reservaba en una direccion falsa.
k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
k32.OpenProcess.restype = wintypes.HANDLE
k32.VirtualAllocEx.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD, wintypes.DWORD]
k32.VirtualAllocEx.restype = ctypes.c_void_p
k32.VirtualFreeEx.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD]
k32.WriteProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t,
                                   ctypes.POINTER(ctypes.c_size_t)]
k32.CloseHandle.argtypes = [wintypes.HANDLE]
u32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
u32.PostMessageW.restype = wintypes.BOOL
u32.EnumWindows.argtypes = [ctypes.c_void_p, wintypes.LPARAM]
u32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
u32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
u32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
u32.IsWindowVisible.argtypes = [wintypes.HWND]


def datos_ventana(h):
    p = wintypes.DWORD()
    u32.GetWindowThreadProcessId(h, ctypes.byref(p))
    largo = u32.GetWindowTextLengthW(h)
    t = ctypes.create_unicode_buffer(largo + 1)
    u32.GetWindowTextW(h, t, largo + 1)
    c = ctypes.create_unicode_buffer(256)
    u32.GetClassNameW(h, c, 256)
    return p.value, c.value, t.value


def ventanas_de(pid, solo_visibles=True, principal=True):
    """Devuelve las ventanas del proceso. Ojo: MMD tiene decenas de ventanas internas (tooltips,
    desplegables); la que acepta el soltado es la principal, la que tiene titulo propio."""
    todas = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def cb(hwnd, _):
        pi, cl, t = datos_ventana(hwnd)
        if pi == pid and (not solo_visibles or u32.IsWindowVisible(hwnd)):
            todas.append((hwnd, cl, t))
        return True

    u32.EnumWindows(cb, 0)
    if principal:
        basura = ("tooltips_class32", "Auto-Suggest Dropdown", "_SearchEditBoxFakeWindow",
                  "ComboLBox", "ScrollBar", "#32768", "SysListView32", "SysHeader32")
        con_titulo = [v for v in todas if v[2] and v[1] not in basura]
        return con_titulo or [v for v in todas if v[1] not in basura]
    return todas


def soltar(hwnd, pid, ruta):
    h = k32.OpenProcess(PROCESS_ALL_ACCESS, False, pid)
    if not h:
        raise OSError("no se pudo abrir el proceso: %d" % ctypes.get_last_error())
    texto = (ruta + "\0\0").encode("utf-16-le")
    df = DROPFILES()
    df.pFiles = ctypes.sizeof(DROPFILES)
    df.pt = wintypes.POINT(0, 0)
    df.fNC = False
    df.fWide = True
    datos = bytes(df) + texto
    mem = k32.VirtualAllocEx(h, None, len(datos), MEM_COMMIT_RESERVE, PAGE_READWRITE)
    if not mem:
        raise OSError("no se pudo reservar memoria en MMD")
    escrito = ctypes.c_size_t(0)
    k32.WriteProcessMemory(h, mem, datos, len(datos), ctypes.byref(escrito))
    print("  memoria reservada en MMD: 0x%X (%d bytes)" % (mem or 0, len(datos)))
    ok = u32.PostMessageW(hwnd, WM_DROPFILES, mem, 0)
    err = ctypes.get_last_error()
    print("  PostMessage -> %s (error %d)" % (ok, err))
    if not ok:
        # SendMessage es sincrono: el mensaje se procesa antes de volver, asi que si el modelo es el
        # problema lo veremos aqui directamente.
        print("  probando con SendMessage (sincrono)...")
        u32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        u32.SendMessageW.restype = wintypes.LPARAM
        r = u32.SendMessageW(hwnd, WM_DROPFILES, mem, 0)
        print("  SendMessage -> %s (error %d)" % (r, ctypes.get_last_error()))
    return h, mem


def main():
    modelo = sys.argv[1]
    espera = int(sys.argv[2]) if len(sys.argv) > 2 else 12
    p = subprocess.Popen([EXE])
    print("MMD lanzado (pid %d), esperando a que aparezca la ventana..." % p.pid)
    hwnd = None
    limite = time.time() + 40
    while time.time() < limite:
        if p.poll() is not None:
            print("MMD se cerro solo antes de poder soltar el modelo (codigo %s)" % p.returncode)
            return
        ventanas = ventanas_de(p.pid)
        if ventanas:
            hwnd, clase, titulo = ventanas[0]
            print("ventana principal: %r clase %r (hwnd %d)" % (titulo, clase, hwnd))
            break
        time.sleep(0.5)
    if not hwnd:
        print("no aparecio ninguna ventana de MMD")
        p.kill()
        return
    time.sleep(2.0)
    print("soltando %s" % modelo)
    h, mem = soltar(hwnd, p.pid, modelo)
    t0 = time.time()
    caido = None
    while time.time() - t0 < espera:
        r = p.poll()
        if r is not None:
            caido = r
            break
        time.sleep(0.4)
    # los dialogs de error de MMD (clase #32770) dan el mensaje exacto del fallo
    dialogos = [v for v in ventanas_de(p.pid, solo_visibles=True, principal=False) if v[1] == "#32770"]
    if caido is None:
        print("RESULTADO: VIVE  (MMD sigue abierto %.0f s despues de soltar el modelo -> lo cargo)" % espera)
        titulos = ventanas_de(p.pid)
        print("  titulo de la ventana ahora: %r" % (titulos[0][2] if titulos else None))
        for hh, cc, tt in dialogos:
            print("  AVISO: hay un dialogo abierto: %r" % tt)
            for hijo, c2, t2 in ventanas_de(p.pid, solo_visibles=False, principal=False):
                pass
        p.terminate()
        time.sleep(1.5)
        if p.poll() is None:
            p.kill()
    else:
        codigo = caido & 0xFFFFFFFF
        print("RESULTADO: CRASHEO  (codigo de salida 0x%08X%s)" % (codigo, ", violacion de acceso" if codigo == 0xC0000005 else ""))
    for hh, cc, tt in dialogos:
        print("  dialogo de MMD: clase %r titulo %r" % (cc, tt))
    k32.VirtualFreeEx(h, mem, 0, MEM_RELEASE)
    k32.CloseHandle(h)


if __name__ == "__main__":
    main()
