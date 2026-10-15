"""Comprueba en Blender que un GLB esta bien montado: huesos, grupos, shape keys y, sobre todo,
si la PIEL es consistente (con el esqueleto en reposo, la malla deformada debe coincidir con la
malla original; si no, los bind poses no cuadran con la jerarquia).

Uso: blender --background --python blender_verificar_glb.py -- <modelo.glb> [salida.json]
"""
import json
import sys

import bpy

ARG = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
GLB = ARG[0] if ARG else ""
SALIDA = ARG[1] if len(ARG) > 1 else ""

for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)

bpy.ops.import_scene.gltf(filepath=GLB)

sal = {"fichero": GLB, "armaduras": [], "mallas": [], "piel_consistente": None, "peor_desvio_m": None,
       "materiales": {}, "shape_keys": {}}

for o in bpy.data.objects:
    if o.type == "ARMATURE":
        sal["armaduras"].append({
            "nombre": o.name, "huesos": len(o.data.bones),
            "raices": [b.name for b in o.data.bones if b.parent is None][:10],
        })

deps = bpy.context.evaluated_depsgraph_get()
peor = 0.0
peor_malla = None
for o in bpy.data.objects:
    if o.type != "MESH":
        continue
    sk = [k.name for k in o.data.shape_keys.key_blocks] if o.data.shape_keys else []
    tiene_arm = any(m.type == "ARMATURE" for m in o.modifiers)
    eo = o.evaluated_get(deps)
    em = eo.to_mesh()
    n = min(len(em.vertices), len(o.data.vertices))
    d = 0.0
    if n and tiene_arm:
        d = max((em.vertices[i].co - o.data.vertices[i].co).length for i in range(n))
        if d > peor:
            peor, peor_malla = d, o.name
    sal["mallas"].append({
        "nombre": o.name, "vertices": len(o.data.vertices), "grupos": len(o.vertex_groups),
        "uvs": [u.name for u in o.data.uv_layers], "shape_keys": len(sk),
        "modificadores": [m.type for m in o.modifiers],
        "materiales": [m.name for m in o.data.materials if m],
        "desvio_reposo_m": round(d, 6),
    })
    if sk:
        sal["shape_keys"][o.name] = sk
    for m in o.data.materials:
        if m:
            texs = []
            if m.use_nodes:
                for nodo in m.node_tree.nodes:
                    if nodo.type == "TEX_IMAGE" and nodo.image:
                        texs.append(nodo.image.name)
            sal["materiales"][m.name] = texs
    eo.to_mesh_clear()

sal["peor_desvio_m"] = round(peor, 6)
sal["piel_consistente"] = (peor < 0.002)

print("===== RESULTADO GLB =====")
print(json.dumps(sal, indent=1, ensure_ascii=False)[:4000])
if SALIDA:
    with open(SALIDA, "w", encoding="utf-8") as fh:
        json.dump(sal, fh, indent=1, ensure_ascii=False)
    print("escrito: " + SALIDA)