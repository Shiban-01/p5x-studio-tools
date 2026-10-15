"""Saca el bytecode DXBC de los shaders que interesan y lo desensambla a texto legible.

Los shaders del juego son DXBC (Direct3D 11). Aqui se localizan los bloques dentro del objeto del
shader y se pasan por D3DDisassemble (d3dcompiler_47.dll de Windows) para obtener el ensamblador, que
es lo que se puede leer y comparar con una recreacion. Deja .dxbc y .asm por shader.

Uso:  sacar_shader_asm.py "UI/chouka" "UI/UIMultipleGradient" ...
      (sin argumentos: todos los de interfaz que tengan bytecode)
"""
import ctypes
import json
import re
import struct
import sys
from ctypes import wintypes
from pathlib import Path

import UnityPy

B = r"C:\Users\Lukas\p5x-datamining\game_dump\fileContentOut\Bundles\Windows\106\shaders.bundle"
SALIDA = Path(r"C:\Users\Lukas\p5x-datamining\_dl\shaders_out")

OBJETIVO = sys.argv[1:]

dll = ctypes.WinDLL("d3dcompiler_47.dll")


class Blob(ctypes.Structure):
    _fields_ = [("lpVtbl", ctypes.c_void_p)]


class BlobVtbl(ctypes.Structure):
    _fields_ = [("QueryInterface", ctypes.c_void_p), ("AddRef", ctypes.c_void_p),
                ("Release", ctypes.c_void_p), ("GetBufferPointer", ctypes.c_void_p),
                ("GetBufferSize", ctypes.c_void_p)]


dll.D3DDisassemble.argtypes = [ctypes.c_void_p, ctypes.c_size_t, wintypes.UINT,
                               ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)]
dll.D3DDisassemble.restype = ctypes.c_long


def desensamblar(dxbc: bytes):
    """Devuelve el ensamblador del bloque DXBC, o el motivo del fallo."""
    buf = ctypes.create_string_buffer(dxbc, len(dxbc))
    blob = ctypes.c_void_p()
    hr = dll.D3DDisassemble(buf, len(dxbc), 0, None, ctypes.byref(blob))
    if hr != 0 or not blob:
        return None, "D3DDisassemble devolvio 0x%08X" % (hr & 0xFFFFFFFF)
    vtbl = ctypes.cast(blob, ctypes.POINTER(ctypes.POINTER(BlobVtbl))).contents.contents
    obtener = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p)(vtbl.GetBufferPointer)
    tam = ctypes.CFUNCTYPE(ctypes.c_size_t, ctypes.c_void_p)(vtbl.GetBufferSize)
    ptr, n = obtener(blob), tam(blob)
    texto = ctypes.string_at(ptr, n).decode("utf-8", "replace")
    release = ctypes.CFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)(vtbl.Release)
    release(blob)
    return texto, None


def bloques_dxbc(raw: bytes):
    """Localiza cada bloque DXBC completo (el tamano va en la cabecera, offset 24)."""
    fuera = []
    pos = 0
    while True:
        i = raw.find(b"DXBC", pos)
        if i < 0 or i + 32 > len(raw):
            break
        n = struct.unpack_from("<I", raw, i + 24)[0]
        if 64 < n <= 4_000_000 and i + n <= len(raw):
            fuera.append(raw[i:i + n])
            pos = i + n
        else:
            pos = i + 4
    return fuera


def nombre_de(raw: bytes):
    textos = [s.decode("ascii", "ignore") for s in re.findall(rb"[\x20-\x7e]{4,80}", raw)]
    cand = [t for t in textos if re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_ ]*(/[A-Za-z0-9_][A-Za-z0-9_ ]*)+", t)
            and t not in ("$Globals", "UnityPerDraw", "UnityPerMaterial")]
    return cand


env = UnityPy.load(B)
SALIDA.mkdir(parents=True, exist_ok=True)
entregados = []

for o in env.objects:
    if o.type.name not in ("Shader", "ComputeShader"):
        continue
    raw = o.get_raw_data()
    cands = nombre_de(raw)
    if OBJETIVO:
        elegido = next((c for c in cands if c in OBJETIVO), None)
        if not elegido:
            continue
    else:
        elegido = next((c for c in cands if c.split("/")[0] in ("UI", "UIEffect")), None)
        if not elegido or raw.count(b"DXBC") < 1:
            continue
    dxbcs = bloques_dxbc(raw)
    if not dxbcs:
        continue
    carpeta = SALIDA / elegido.replace("/", "__")
    carpeta.mkdir(parents=True, exist_ok=True)
    asm_ok = 0
    for k, b in enumerate(dxbcs):
        (carpeta / ("bloque%02d.dxbc" % k)).write_bytes(b)
        texto, fallo = desensamblar(b)
        if texto:
            (carpeta / ("bloque%02d.asm" % k)).write_text(texto, encoding="utf-8")
            asm_ok += 1
    info = {"shader": elegido, "candidatos": cands, "bloques": len(dxbcs), "desensamblados": asm_ok,
            "bytes_objeto": len(raw)}
    entregados.append(info)
    print("  %-40s %2d bloques DXBC  %2d desensamblados" % (elegido[:40], len(dxbcs), asm_ok), flush=True)

(SALIDA / "indice.json").write_text(json.dumps(entregados, ensure_ascii=False, indent=1), encoding="utf-8")
print()
print("shaders con bytecode entregados: %d" % len(entregados))
print("salida en", SALIDA)