"""Busca la esfera suelta (Icosphere) dentro del GLB: nodos con malla, nombres y vertices."""
import json
import os
import struct

GLB = r"C:\Users\Lukas\p5x-datamining\kotone_shiomi\01_model\glb\Kotone_Shiomi_full.glb"
COMP = {5120: "b", 5121: "B", 5122: "h", 5123: "H", 5125: "I", 5126: "f"}


def leer(ruta):
    d = open(ruta, "rb").read()
    off, js, bin_ = 12, None, None
    while off < len(d):
        largo, tipo = struct.unpack("<II", d[off:off + 8])
        if tipo == 0x4E4F534A:
            js = json.loads(d[off + 8:off + 8 + largo].decode("utf-8"))
        elif tipo == 0x004E4942:
            bin_ = d[off + 8:off + 8 + largo]
        off += 8 + largo
    return js, bin_, len(d)


js, bin_, tam = leer(GLB)
print("GLB: %.1f MB   nodos: %d   mallas: %d   escenas: %d"
      % (tam / 1048576, len(js["nodes"]), len(js["meshes"]), len(js["scenes"])))

print("\n=== mallas declaradas ===")
for i, m in enumerate(js["meshes"]):
    n = 0
    for pr in m["primitives"]:
        n += js["accessors"][pr["attributes"]["POSITION"]]["count"]
    print("   [%2d] %-58s %6d v   primitivas: %d"
          % (i, (m.get("name") or "(sin nombre)")[:58], n, len(m["primitives"])))

print("\n=== nodos que llevan malla ===")
for i, n in enumerate(js["nodes"]):
    if "mesh" in n:
        print("   nodo [%3d] %-52s -> malla %d   hijos: %d   skin: %s"
              % (i, (n.get("name") or "(sin nombre)")[:52], n["mesh"],
                 len(n.get("children", [])), n.get("skin")))

print("\n=== raices de la escena ===")
for i in js["scenes"][0]["nodes"]:
    print("   [%3d] %s" % (i, js["nodes"][i].get("name") or "(sin nombre)"))