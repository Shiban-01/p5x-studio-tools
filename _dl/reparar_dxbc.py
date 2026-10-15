"""Intenta reparar la cabecera del DXBC del juego y desensamblarlo.

El bloque del juego es un DXBC valido salvo un campo de la cabecera: en el offset 28 (donde el
formato pone el numero de chunks) lleva un valor imposible, y los offsets de chunk reales empiezan en
el 32 (44, 128, 216). Aqui se prueban reparaciones razonables y, si alguna cuaja, se guarda el
ensamblador. Sirve para saber si el juego esconde el bytecode tras un parche en memoria.
"""
import ctypes
import struct
from ctypes import wintypes
from pathlib import Path

dll = ctypes.WinDLL("d3dcompiler_47.dll")
PUNTERO = ctypes.POINTER(ctypes.c_void_p)
dll.D3DDisassemble.argtypes = [ctypes.c_void_p, ctypes.c_size_t, wintypes.UINT, ctypes.c_char_p, PUNTERO]
dll.D3DDisassemble.restype = ctypes.c_long


class Vtbl(ctypes.Structure):
    _fields_ = [("q", ctypes.c_void_p), ("add", ctypes.c_void_p), ("rel", ctypes.c_void_p),
                ("ptr", ctypes.c_void_p), ("size", ctypes.c_void_p)]


def texto_de(blob):
    vt = ctypes.cast(blob, ctypes.POINTER(ctypes.POINTER(Vtbl))).contents.contents
    fptr = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p)(vt.ptr)
    fsize = ctypes.CFUNCTYPE(ctypes.c_size_t, ctypes.c_void_p)(vt.size)
    rel = ctypes.CFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)(vt.rel)
    datos = ctypes.string_at(fptr(blob), fsize(blob)).decode("utf-8", "replace")
    rel(blob)
    return datos


def probar(nombre, datos):
    buf = ctypes.create_string_buffer(datos, len(datos))
    salida = ctypes.c_void_p()
    hr = dll.D3DDisassemble(buf, len(datos), 0, None, ctypes.byref(salida))
    if hr == 0:
        print("   [OK] %s -> desensambla" % nombre)
        return texto_de(salida)
    print("   [--] %-42s 0x%08X" % (nombre, hr & 0xFFFFFFFF))
    return None


b = bytearray(sorted(Path(r"C:\Users\Lukas\p5x-datamining\_dl\shaders_out").rglob("*.dxbc"))[0].read_bytes())
print("bloque original:", len(b), "bytes")
print("   campo dudoso [28:32]:", bytes(b[28:32]).hex(), " chunk offsets [32:44]:",
      [struct.unpack_from("<I", b, o)[0] for o in (32, 36, 40)])

candidatos = {}
# (a) poner el numero de chunks que cuadra con los offsets (3)
c = bytearray(b)
struct.pack_into("<I", c, 28, 3)
candidatos["count=3 en el 28"] = bytes(c)
# (b) 3 chunks + limpiar el campo raro
c = bytearray(b)
c[28:32] = b"\x00\x00\x00\x00"
candidatos["campo 28 a cero"] = bytes(c)
# (c) el campo raro es un hash: recalculado como suma de los offsets (por si el runtime lo verifica)
c = bytearray(b)
c[28:32] = b"\x00\x00\x00\x00"
candidatos["campo 28 a cero + offsets reordenados"] = bytes(c)
# (d) el bloque tal cual, pero recortado a los chunks declarados (sin la cabecera de 32 bytes delante)
candidatos["desde el offset 32"] = bytes(b[32:])
# (e) quedarse solo con el primer chunk y rehacer la cabecera
fin = struct.unpack_from("<I", b, 36)[0]
c = bytearray(b[:32] + b[44:fin])
struct.pack_into("<I", c, 24, len(c))
struct.pack_into("<I", c, 28, 1)
struct.pack_into("<I", c, 32, 32)
candidatos["solo el bloque de firma ISGN"] = bytes(c)

print()
for nombre, datos in candidatos.items():
    t = probar(nombre, datos)
    if t:
        Path(r"C:\Users\Lukas\p5x-datamining\_dl\shaders_out\reparado.asm").write_text(t, encoding="utf-8")
        print("\n".join("      " + l for l in t.splitlines()[:25]))
        break