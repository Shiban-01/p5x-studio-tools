"""Averigua que HUESOS deforman la malla en reposo dentro de Blender.

Importa el GLB tal cual, compara cada vertice evaluado (con la armadura puesta) con el vertice
original y atribuye el desplazamiento a los grupos de vertices (huesos) del vertice.
Uso: blender --background --python ver_deform_blender.py -- <glb>
"""
import sys
from collections import Counter

import bpy

ruta = sys.argv[sys.argv.index("--") + 1]
bpy.ops.wm.read_factory_settings(use_empty=True)
if ruta.lower().endswith(".fbx"):
    bpy.ops.import_scene.fbx(filepath=ruta)
else:
    bpy.ops.import_scene.gltf(filepath=ruta)
dg = bpy.context.evaluated_depsgraph_get()

grupos = bpy.data.objects[0].vertex_groups if False else None
culpables = Counter()
for o in bpy.data.objects:
    if o.type != "MESH" or o.name.startswith("Icosphere"):
        continue
    ev = o.evaluated_get(dg)
    me = ev.to_mesh()
    org = o.data
    if len(me.vertices) != len(org.vertices):
        print("  %s: recuento distinto" % o.name[:40])
        ev.to_mesh_clear()
        continue
    nombres = {g.index: g.name for g in o.vertex_groups}
    peor = 0.0
    peor_v = None
    for i, v in enumerate(me.vertices):
        d = (v.co - org.vertices[i].co).length
        if d > peor:
            peor, peor_v = d, i
    print("  %-44s peor desplazamiento en reposo: %.4f" % (o.name[-44:], peor))
    if peor > 1e-3 and peor_v is not None:
        vg = [(nombres[g.group], round(g.weight, 3)) for g in org.vertices[peor_v].groups]
        print("      vertice %d grupos: %s" % (peor_v, vg))
        for n, w in vg:
            culpables[n] += 1
    ev.to_mesh_clear()

print("huesos culpables (los que mas veces aparecen en vertices desplazados):")
for n, c in culpables.most_common(12):
    print("   %-34s %d" % (n, c))