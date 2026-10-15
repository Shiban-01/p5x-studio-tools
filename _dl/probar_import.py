"""Prueba varias opciones de importacion glTF de Blender y mide el bbox EVALUADO (con la piel puesta).

Si el bbox evaluado coincide con el de la geometria cruda, Blender reproduce bien la piel.
Uso: blender --background --python probar_import.py -- <glb>
"""
import sys

import bpy
from mathutils import Vector

ruta = sys.argv[sys.argv.index("--") + 1]

COMBOS = [
    ("por defecto", {}),
    ("guess_bind_pose=False", {"guess_original_bind_pose": False}),
    ("TEMPERANCE", {"bone_heuristic": "TEMPERANCE"}),
    ("TEMPERANCE+guess=False", {"bone_heuristic": "TEMPERANCE", "guess_original_bind_pose": False}),
    ("BLENDER", {"bone_heuristic": "BLENDER"}),
]


def caja():
    dg = bpy.context.evaluated_depsgraph_get()
    mn = Vector((1e9,) * 3)
    mx = Vector((-1e9,) * 3)
    for o in bpy.data.objects:
        if o.type != "MESH" or o.name.startswith("Icosphere"):
            continue
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        for v in me.vertices:
            w = o.matrix_world @ v.co
            for i in range(3):
                mn[i] = min(mn[i], w[i])
                mx[i] = max(mx[i], w[i])
        ev.to_mesh_clear()
    return mn, mx


for nombre, kw in COMBOS:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    try:
        bpy.ops.import_scene.gltf(filepath=ruta, **kw)
    except Exception as e:
        print("%-24s NO SE PUDO IMPORTAR: %s" % (nombre, e))
        continue
    mn, mx = caja()
    print("%-24s x[%6.2f %6.2f] y[%6.2f %6.2f] z[%6.2f %6.2f]  ancho=%.2f alto=%.2f"
          % (nombre, mn.x, mx.x, mn.y, mx.y, mn.z, mx.z, mx.x - mn.x, mx.z - mn.z))