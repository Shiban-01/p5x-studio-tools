"""Lee un GLB y saca, por malla, el centro y tamano de su POSITION (accessor min/max).

Uso: python glb_bbox.py <glb> [subcadena]
"""
import json
import struct
import sys

ruta = sys.argv[1]
filtro = sys.argv[2] if len(sys.argv) > 2 else ""
b = open(ruta, "rb").read()
assert b[:4] == b"glTF", "no es GLB"
off = 12
js = None
while off < len(b):
    ln, tipo = struct.unpack_from("<II", b, off)
    cuerpo = b[off + 8: off + 8 + ln]
    if tipo == 0x4E4F534A:  # JSON
        js = json.loads(cuerpo)
        break
    off += 8 + ln + ((-ln) % 4)

acc = js["accessors"]
for m in js.get("meshes", []):
    for p in m.get("primitives", []):
        ia = p["attributes"].get("POSITION")
        if ia is None:
            continue
        a = acc[ia]
        mn, mx = a.get("min"), a.get("max")
        if not mn:
            continue
        c = [(mn[i] + mx[i]) / 2 for i in range(3)]
        tam = [mx[i] - mn[i] for i in range(3)]
        nom = m.get("name", "?")
        if filtro and filtro not in nom:
            continue
        print("%-58s c=(%7.3f,%7.3f,%7.3f) tam=(%6.3f,%6.3f,%6.3f) v=%d"
              % (nom[:58], c[0], c[1], c[2], tam[0], tam[1], tam[2], a["count"]))