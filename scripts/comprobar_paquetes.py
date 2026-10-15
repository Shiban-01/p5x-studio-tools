
"""Comprueba los dos paquetes: el VPK de L4D2 y el GMA de Garry's Mod."""
import struct, sys, zlib

vpk, gma = sys.argv[1], sys.argv[2]

print("=== VPK de L4D2 ===")
d = open(vpk, "rb").read()
magic, version, tree = struct.unpack("<III", d[:12])
print("  cabecera: magic 0x%08X (valido: %s) version %d, arbol de %d bytes" %
      (magic, magic == 0x55AA1234, version, tree))
i, ext_n = 12, 0
exts = set()
arbol = d[12:12 + tree]
p, n = 0, 0
def cadena(buf, pos):
    fin = buf.index(b"\x00", pos); return buf[pos:fin].decode("utf-8", "replace"), fin + 1
while p < len(arbol):
    e, p = cadena(arbol, p)
    if e == "": break
    exts.add(e)
    while p < len(arbol):
        c, p = cadena(arbol, p)
        if c == "": break
        while p < len(arbol):
            nom, p = cadena(arbol, p)
            if nom == "": break
            crc, prec, trozo, off, largo, term = struct.unpack("<IHHIIH", arbol[p:p+18]); p += 18
            p += prec
            n += 1
print("  ficheros en el VPK: %d  (extensiones: %s)" % (n, ",".join(sorted(exts))))

print("=== GMA de Garry's Mod ===")
d = open(gma, "rb").read()
print("  magic: %s  version %d  tamano %.1f MB" % (d[:4].decode("ascii", "replace"), d[4], len(d)/1e6))
p = 5 + 8 + 8 + 1
def leer(pos):
    fin = d.index(b"\x00", pos); return d[pos:fin].decode("utf-8", "replace"), fin + 1
nombre, p = leer(p); desc, p = leer(p); autor, p = leer(p)
version, = struct.unpack("<I", d[p:p+4]); p += 4
print("  nombre: %r | autor: %r | version %d" % (nombre, autor, version))
ficheros, total = 0, 0
while True:
    ident, = struct.unpack("<I", d[p:p+4]); p += 4
    if ident == 0: break
    ruta, p = leer(p)
    tam, = struct.unpack("<Q", d[p:p+8]); crc, = struct.unpack("<I", d[p+8:p+12]); p += 12
    ficheros += 1; total += tam
print("  %d ficheros declarados, %.1f MB de datos" % (ficheros, total/1e6))
crc_final, = struct.unpack("<I", d[-4:])
crc_real = zlib.crc32(d[:-4]) & 0xFFFFFFFF
print("  crc final: %s (declarado 0x%08X, calculado 0x%08X)" %
      ("COINCIDE" if crc_final == crc_real else "NO COINCIDE", crc_final, crc_real))
