"""Sigue un vertice concreto: que dice el glTF, que ha hecho Blender al importar y que da la piel.

Uso: blender --background --python seguir_vertice.py -- <glb> <indice_vertice> [<indice_malla>]
"""
import json
import struct
import sys

import bpy

ruta = sys.argv[sys.argv.index("--") + 1]
objetivo = int(sys.argv[sys.argv.index("--") + 2])
malla_i = int(sys.argv[sys.argv.index("--") + 3]) if len(sys.argv) > 3 else 0


def leer_glb(p):
    b = open(p, "rb").read()
    off, js, bin_ = 12, None, b""
    while off < len(b):
        ln, ty = struct.unpack_from("<II", b, off)
        off += 8
        c = b[off:off + ln]
        off += ln
        if ty == 0x4E4F534A:
            js = json.loads(c.decode("utf-8"))
        elif ty == 0x004E4942:
            bin_ = c
    return js, bin_


js, bin_ = leer_glb(ruta)


def acc(i):
    a = js["accessors"][i]
    bv = js["bufferViews"][a["bufferView"]]
    n = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}[a["type"]]
    ch, tam = {5126: ("f", 4), 5123: ("H", 2), 5125: ("I", 4), 5121: ("B", 1)}[a["componentType"]]
    off = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    return [struct.unpack_from("<" + ch * n, bin_, off + k * tam * n) for k in range(a["count"])]


malla = js["meshes"][malla_i]
pr = malla["primitives"][0]
pos = acc(pr["attributes"]["POSITION"])[objetivo]
ji = acc(pr["attributes"]["JOINTS_0"])[objetivo]
jw = acc(pr["attributes"]["WEIGHTS_0"])[objetivo]
skin = js["skins"][js["nodes"][next(i for i, n in enumerate(js["nodes"]) if n.get("mesh") == malla_i)]["skin"]]
joints = skin["joints"]
print("glTF  malla=%s vert=%d" % (malla["name"][-40:], objetivo))
print("   pos   =", [round(x, 4) for x in pos])
print("   pesos =", [round(x, 4) for x in jw])
for c in range(4):
    if jw[c] > 0:
        print("   joint[%d] = %-30s (nodo %d)" % (c, js["nodes"][joints[ji[c]]].get("name"), joints[ji[c]]))

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=ruta)
dg = bpy.context.evaluated_depsgraph_get()
for o in bpy.data.objects:
    if o.type != "MESH" or o.name.startswith("Icosphere"):
        continue
    if len(o.data.vertices) != len(acc(pr["attributes"]["POSITION"])):
        continue
    v = o.data.vertices[objetivo]
    ev = o.evaluated_get(dg).to_mesh().vertices[objetivo]
    nombres = {g.index: g.name for g in o.vertex_groups}
    print("Blender %s" % o.name[-40:])
    print("   base      =", [round(x, 4) for x in v.co])
    print("   evaluado  =", [round(x, 4) for x in ev.co])
    print("   grupos    =", [(nombres[g.group], round(g.weight, 3)) for g in v.groups])
    break