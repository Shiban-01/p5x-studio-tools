"""Saca la jerarquia de nodos y la transformada del nodo que lleva cada malla.

Uso: python glb_nodos.py <glb> [subcadena]
"""
import json
import struct
import sys

ruta = sys.argv[1]
filtro = sys.argv[2] if len(sys.argv) > 2 else ""
b = open(ruta, "rb").read()
off = 12
js = None
while off < len(b):
    ln, tipo = struct.unpack_from("<II", b, off)
    if tipo == 0x4E4F534A:
        js = json.loads(b[off + 8: off + 8 + ln])
        break
    off += 8 + ln + ((-ln) % 4)

nodos = js["nodes"]
padres = {}
for i, n in enumerate(nodos):
    for c in n.get("children", []):
        padres[c] = i

meshes = js.get("meshes", [])
for i, n in enumerate(nodos):
    if "mesh" not in n:
        continue
    nombre = n.get("name", "") or meshes[n["mesh"]].get("name", "?")
    mn = meshes[n["mesh"]].get("name", "")
    etq = nombre + " | " + mn
    if filtro and filtro not in etq:
        continue
    cadena = []
    j = i
    while j is not None:
        cadena.append(nodos[j].get("name", "?"))
        j = padres.get(j)
    tr = n.get("translation")
    print("nodo%-4d %-52s tr=%s" % (i, etq[:52], tr))
    print("        ruta: %s" % " < ".join(cadena))