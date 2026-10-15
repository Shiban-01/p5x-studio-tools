"""Diagnostico amplio: cuantos bloques DXBC del bundle se dejan desensamblar y de que tipo son."""
import ctypes
import struct
from collections import Counter
from ctypes import wintypes

import UnityPy

B = r"C:\Users\Lukas\p5x-datamining\game_dump\fileContentOut\Bundles\Windows\106\shaders.bundle"

dll = ctypes.WinDLL("d3dcompiler_47.dll")
dll.D3DDisassemble.argtypes = [ctypes.c_void_p, ctypes.c_size_t, wintypes.UINT,
                               ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)]
dll.D3DDisassemble.restype = ctypes.c_long


def trocear(raw):
    fuera, pos = [], 0
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


def chunks(b):
    n = struct.unpack_from("<I", b, 28)[0]
    tabla = []
    for k in range(n):
        off = 32 + 4 * k
        if off + 4 > len(b):
            break
        c = struct.unpack_from("<I", b, off)[0]
        if c + 8 > len(b):
            break
        tabla.append((b[c:c + 4].decode("ascii", "replace"), struct.unpack_from("<I", b, c + 4)[0]))
    return tabla


env = UnityPy.load(B)
probados = exitos = 0
fourccs = Counter()
hrs = Counter()
muestras = []
for o in env.objects:
    if o.type.name != "Shader":
        continue
    for b in trocear(o.get_raw_data()):
        if probados >= 40:
            break
        probados += 1
        tbl = chunks(b)
        for f, _ in tbl:
            fourccs[f] += 1
        buf = ctypes.create_string_buffer(b, len(b))
        blob = ctypes.c_void_p()
        hr = dll.D3DDisassemble(buf, len(b), 0, None, ctypes.byref(blob))
        hrs["0x%08X" % (hr & 0xFFFFFFFF)] += 1
        if hr == 0:
            exitos += 1
            if len(muestras) < 3:
                muestras.append((o.path_id, len(b), tbl))
    if probados >= 40:
        break

print("bloques probados:", probados, " desensamblados:", exitos)
print("codigos devueltos:", dict(hrs))
print("chunks presentes:", dict(fourccs))
print()
for pid, n, tbl in muestras:
    print("  ejemplo path_id=%s  %d bytes" % (pid, n))
    for f, tam in tbl:
        print("     %-6s %8d" % (f, tam))