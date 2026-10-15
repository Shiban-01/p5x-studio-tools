"""Compara la tabla de huesos de varios .mdl de Source.

Para que $includemodel funcione, el modelo que incluye y el incluido tienen que compartir el
esqueleto: mismos huesos, en el mismo orden y con la misma jerarquia. Si no, las secuencias de
animacion apuntan a huesos que no existen y el motor puede caerse al cargar el modelo.

Uso:  python comparar_huesos.py <a.mdl> <b.mdl> [c.mdl ...]
"""
import struct
import sys


def huesos(ruta):
    d = open(ruta, "rb").read()
    ident = d[:4]
    version, checksum = struct.unpack("<ii", d[4:12])
    numbones, boneindex = struct.unpack("<ii", d[156:164])
    fuera = []
    for i in range(numbones):
        b = boneindex + i * 216
        szname = struct.unpack("<i", d[b:b + 4])[0]
        padre = struct.unpack("<i", d[b + 4:b + 8])[0]
        fin = d.index(b"\x00", b + szname)
        nombre = d[b + szname:fin].decode("ascii", "replace")
        fuera.append((nombre, padre))
    return ident, version, checksum, fuera


tablas = {}
for ruta in sys.argv[1:]:
    ident, version, checksum, h = huesos(ruta)
    tablas[ruta] = h
    print("%s" % ruta)
    print("   cabecera %s  version %d  checksum 0x%08X  %d huesos"
          % (ident.decode("ascii", "replace"), version, checksum & 0xFFFFFFFF, len(h)))
print()

nombres = {r: [n for n, _ in h] for r, h in tablas.items()}
rutas = list(tablas)
base = rutas[0]
for otra in rutas[1:]:
    a, b = set(nombres[base]), set(nombres[otra])
    print("=== %s  contra  %s ===" % (base, otra))
    print("   solo en el primero: %s" % (sorted(a - b) or "ninguno"))
    print("   solo en el segundo: %s" % (sorted(b - a) or "ninguno"))
    iguales = sum(1 for x, y in zip(nombres[base], nombres[otra]) if x == y)
    print("   %d de %d coinciden en el MISMO orden" % (iguales, max(len(a), len(b))))
    # jerarquia: para los huesos comunes, su padre tambien coincide?
    pa = dict(tablas[base]); pb = dict(tablas[otra])
    desf = []
    for n in sorted(a & b):
        p1, p2 = pa[n], pb[n]
        n1 = nombres[base][p1] if p1 >= 0 else "-"
        n2 = nombres[otra][p2] if p2 >= 0 else "-"
        if n1 != n2:
            desf.append("%s: padre %s vs %s" % (n, n1, n2))
    print("   huesos con PADRE distinto: %d %s" % (len(desf), desf[:6] if desf else ""))
    print()