"""Imprime, por malla, el centro y tamano de su caja envolvente EN MUNDO (con transform de nodo).

Uso: blender --background --python bbox_mundo.py -- <glb> [subcadena]
"""
import json
import sys

import bpy
from mathutils import Vector

a = sys.argv[sys.argv.index("--") + 1:]
entrada = a[0]
filtro = a[1] if len(a) > 1 else ""
salida = a[2] if len(a) > 2 else None

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=entrada)
for o in list(bpy.data.objects):
    if any(c.name == "glTF_not_exported" for c in o.users_collection):
        bpy.data.objects.remove(o, do_unlink=True)

filas = []
for o in bpy.data.objects:
    if o.type != "MESH" or (filtro and filtro not in o.name):
        continue
    mn = Vector((1e18,) * 3)
    mx = Vector((-1e18,) * 3)
    for c in o.bound_box:
        w = o.matrix_world @ Vector(c)
        for i in range(3):
            mn[i] = min(mn[i], w[i])
            mx[i] = max(mx[i], w[i])
    c = (mn + mx) / 2
    tam = mx - mn
    filas.append((o.name, c, tam))

filas.sort()
out = []
for nom, c, tam in filas:
    linea = "%-58s c=(%7.3f,%7.3f,%7.3f) tam=(%6.3f,%6.3f,%6.3f)" % (
        nom[:58], c.x, c.y, c.z, tam.x, tam.y, tam.z)
    print(linea)
    out.append({"nombre": nom, "c": [round(v, 4) for v in c], "tam": [round(v, 4) for v in tam]})
if salida:
    with open(salida, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("JSON=%s" % salida)