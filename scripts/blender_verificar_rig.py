"""Verifica con Blender que un GLB riggeado se abre y trae armadura y pesos de piel.

No se fia del parser propio: importa el fichero de verdad con el importador de glTF de Blender y
cuenta lo que Blender ve (armaduras, huesos, mallas, grupos de vertices con peso).

Uso: blender --background --python blender_verificar_rig.py -- <fichero.glb>
"""
import sys

import bpy

ruta = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else None
if not ruta:
    raise SystemExit("falta la ruta del GLB")

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=ruta)

armaduras = [o for o in bpy.data.objects if o.type == "ARMATURE"]
# El importador de glTF de Blender mete sus objetos auxiliares en la coleccion "glTF_not_exported"
# (p. ej. una esfera de ayuda). No son del fichero y no deben contarse.
def _es_del_fichero(o):
    return all(c.name != "glTF_not_exported" for c in o.users_collection)

mallas = [o for o in bpy.data.objects if o.type == "MESH" and _es_del_fichero(o)]

print("=== Blender: %s ===" % ruta)
print("armaduras: %d" % len(armaduras))
for a in armaduras:
    print("  armadura %s: %d huesos" % (a.name, len(a.data.bones)))
print("mallas: %d" % len(mallas))
con_grupos = 0
total_grupos = 0
for m in mallas:
    grupos = len(m.vertex_groups)
    verts_con_peso = 0
    for v in m.data.vertices:
        if any(g.weight > 0.001 for g in v.groups):
            verts_con_peso += 1
    if grupos > 0 and verts_con_peso > 0:
        con_grupos += 1
    total_grupos += grupos
    print("  malla %-46s verts %6d  grupos %3d  verts con peso %6d"
          % (m.name[-46:], len(m.data.vertices), grupos, verts_con_peso))
print("mallas con grupos de vertices: %d de %d" % (con_grupos, len(mallas)))
print("RESUMEN armaduras=%d huesos=%s mallas=%d mallas_con_grupos=%d"
      % (len(armaduras), [len(a.data.bones) for a in armaduras], len(mallas), con_grupos))