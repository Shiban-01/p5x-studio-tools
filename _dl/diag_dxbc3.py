"""Test de ida y vuelta del desensamblador + analisis del payload del shader del juego.

1) Compila un shader trivial y lo desensambla: si eso funciona, la herramienta esta bien y lo raro
   es el bytecode del juego.
2) Mira en hexadecimal el chunk del programa del shader del juego para juzgar si es codigo real o
   datos alterados.
"""
import ctypes
import math
from collections import Counter
from ctypes import wintypes
from pathlib import Path

dll = ctypes.WinDLL("d3dcompiler_47.dll")
PUNTERO = ctypes.POINTER(ctypes.c_void_p)
dll.D3DCompile.argtypes = [ctypes.c_char_p, ctypes.c_size_t, ctypes.c_char_p, PUNTERO, PUNTERO,
                           ctypes.c_char_p, ctypes.c_char_p, wintypes.UINT, wintypes.UINT,
                           ctypes.POINTER(ctypes.c_void_p), PUNTERO]
dll.D3DCompile.restype = ctypes.c_long
dll.D3DDisassemble.argtypes = [ctypes.c_void_p, ctypes.c_size_t, wintypes.UINT, ctypes.c_char_p, PUNTERO]
dll.D3DDisassemble.restype = ctypes.c_long


class Vtbl(ctypes.Structure):
    _fields_ = [("q", ctypes.c_void_p), ("add", ctypes.c_void_p), ("rel", ctypes.c_void_p),
                ("ptr", ctypes.c_void_p), ("size", ctypes.c_void_p)]


def leer_blob(blob):
    vt = ctypes.cast(blob, ctypes.POINTER(ctypes.POINTER(Vtbl))).contents.contents
    fptr = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p)(vt.ptr)
    fsize = ctypes.CFUNCTYPE(ctypes.c_size_t, ctypes.c_void_p)(vt.size)
    rel = ctypes.CFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)(vt.rel)
    datos = ctypes.string_at(fptr(blob), fsize(blob))
    rel(blob)
    return datos


print("=== 1) ida y vuelta del propio desensamblador ===")
fuente = b"float4 main(float4 p : POSITION) : SV_POSITION { return p; }"
codigo, errores = ctypes.c_void_p(), ctypes.c_void_p()
hr = dll.D3DCompile(fuente, len(fuente), b"prueba.hlsl", None, None, b"main", b"vs_5_0", 0, 0,
                    ctypes.byref(codigo), ctypes.byref(errores))
print("   D3DCompile -> 0x%08X" % (hr & 0xFFFFFFFF))
if hr == 0:
    dxbc = leer_blob(codigo)
    print("   bytecode compilado:", len(dxbc), "bytes; cabecera:", dxbc[:4])
    salida = ctypes.c_void_p()
    hr2 = dll.D3DDisassemble(ctypes.create_string_buffer(dxbc, len(dxbc)), len(dxbc), 0, None,
                             ctypes.byref(salida))
    print("   D3DDisassemble del propio bytecode -> 0x%08X  %s"
          % (hr2 & 0xFFFFFFFF, "OK" if hr2 == 0 else "FALLO"))
    if hr2 == 0:
        print("   primeras lineas:")
        for linea in leer_blob(salida).decode("utf-8", "replace").splitlines()[:4]:
            print("      ", linea)

print()
print("=== 2) el bytecode del juego, en hexadecimal ===")
b = sorted(Path(r"C:\Users\Lukas\p5x-datamining\_dl\shaders_out").rglob("*.dxbc"))[0].read_bytes()
print("   tamano:", len(b))
print("   cabecera:", b[:44].hex(" "))
# trozo del programa (SHEX) y su entropia: codigo real ~7-8 bits/byte, cifrado ~8.0 y uniforme
i = b.find(b"SHEX")
if i >= 0:
    cuerpo = b[i + 8:i + 8 + 256]
    print("   SHEX en offset", i, " tamano declarado:", int.from_bytes(b[i + 4:i + 8], "little"))
    print("   primeros 64 del programa:", cuerpo[:64].hex(" "))
    cuenta = Counter(cuerpo)
    entropia = -sum((n / len(cuerpo)) * math.log2(n / len(cuerpo)) for n in cuenta.values())
    print("   entropia de 256 bytes: %.2f bits/byte  (codigo normal ~6-7; cifrado ~7.9-8.0)" % entropia)
    print("   bytes repetidos arriba:", cuenta.most_common(4))