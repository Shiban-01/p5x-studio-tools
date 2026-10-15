"""Diagnostico: por que falla el desensamblado de los bloques DXBC."""
import ctypes
import struct
from ctypes import wintypes
from pathlib import Path

dll = ctypes.WinDLL("d3dcompiler_47.dll")
dll.D3DDisassemble.argtypes = [ctypes.c_void_p, ctypes.c_size_t, wintypes.UINT,
                               ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)]
dll.D3DDisassemble.restype = ctypes.c_long

carpeta = Path(r"C:\Users\Lukas\p5x-datamining\_dl\shaders_out")
bloques = sorted(carpeta.rglob("*.dxbc"))
print("bloques extraidos:", len(bloques))
if not bloques:
    raise SystemExit("nada que diagnosticar")

b = bloques[0].read_bytes()
print("bloque:", bloques[0].name, len(b), "bytes")
print("primeros 40 bytes:", b[:40])
print("fourcc en la cabecera:", [b[o:o + 4] for o in (0, 4, 20, 28, 32, 36)])
print("tamano declarado en +24:", struct.unpack_from("<I", b, 24)[0])

buf = ctypes.create_string_buffer(b, len(b))
blob = ctypes.c_void_p()
for flags in (0, 1, 2):  # 2 = D3D_DISASM_ENABLE_INSTRUCTION_NUMBERING
    hr = dll.D3DDisassemble(buf, len(b), flags, None, ctypes.byref(blob))
    print("   D3DDisassemble(flags=%d) -> 0x%08X  blob=%s" % (flags, hr & 0xFFFFFFFF, bool(blob)))

# ¿es DXBC valido o es otra cosa? mirar si tiene chunks conocidos
for chunk in (b"RDEF", b"ISGN", b"OSGN", b"SHEX", b"SHDR", b"SPDB", b"STAT"):
    print("   chunk %-4s -> offset %s" % (chunk.decode(), b.find(chunk) if chunk in b else "no"))