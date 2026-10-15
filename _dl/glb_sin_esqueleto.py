"""Quita el esqueleto de un GLB dejando la geometria intacta (mismo buffer binario).

Sirve para renderizar en Blender: al importar glTF con skin, Blender monta una armadura con su
propia transformada y deforma la malla, asi que el render no se corresponde con los datos.

Uso: python glb_sin_esqueleto.py <entrada.glb> <salida.glb>
"""
import json
import struct
import sys
from pathlib import Path


def leer(ruta):
    b = Path(ruta).read_bytes()
    assert b[:4] == b"glTF", "no es un GLB"
    off, js, bin_ = 12, None, b""
    while off < len(b):
        ln, ty = struct.unpack_from("<II", b, off)
        off += 8
        trozo = b[off:off + ln]
        off += ln
        if ty == 0x4E4F534A:
            js = json.loads(trozo.decode("utf-8"))
        elif ty == 0x004E4942:
            bin_ = trozo
    return js, bin_


def escribir(ruta, js, bin_):
    txt = json.dumps(js, separators=(",", ":")).encode("utf-8")
    txt += b" " * (-len(txt) % 4)
    bin_ += b"\x00" * (-len(bin_) % 4)
    total = 12 + 8 + len(txt) + (8 + len(bin_) if bin_ else 0)
    out = bytearray()
    out += struct.pack("<4sII", b"glTF", 2, total)
    out += struct.pack("<II", len(txt), 0x4E4F534A) + txt
    if bin_:
        out += struct.pack("<II", len(bin_), 0x004E4942) + bin_
    Path(ruta).write_bytes(bytes(out))


js, bin_ = leer(sys.argv[1])
# nodos con malla y sus descendientes se conservan; los huesos y el skin se van
conservar = {i for i, n in enumerate(js["nodes"]) if "mesh" in n}
cambio = True
while cambio:
    cambio = False
    for i, n in enumerate(js["nodes"]):
        if i in conservar:
            continue
        if any(c in conservar for c in n.get("children", [])):
            conservar.add(i)
            cambio = True

mapa = {viejo: nuevo for nuevo, viejo in enumerate(sorted(conservar))}
nodos = []
for viejo in sorted(conservar):
    n = dict(js["nodes"][viejo])
    n.pop("skin", None)
    if "children" in n:
        n["children"] = [mapa[c] for c in n["children"] if c in mapa]
        if not n["children"]:
            n.pop("children")
    nodos.append(n)

for m in js["meshes"]:
    for p in m["primitives"]:
        for k in ("JOINTS_0", "WEIGHTS_0"):
            p["attributes"].pop(k, None)

hijos = set()
for i in conservar:
    hijos.update(c for c in js["nodes"][i].get("children", []) if c in mapa)
raices = [mapa[i] for i in sorted(conservar) if i not in hijos]
js["nodes"] = nodos
js.pop("skins", None)
js["scenes"] = [{"nodes": raices}]
js["scene"] = 0
escribir(sys.argv[2], js, bin_)
print("OK", sys.argv[2], "nodos", len(nodos), "mallas", len(js["meshes"]))