"""Diagnostico del modelo de cara a publicarlo: jerarquia, pesos, materiales, texturas y expresiones.

No cambia nada: solo mide. Responde a "¿esto lo puede coger otro artista y ponerse a posar?".
"""
import sys

import bpy

ARG = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
GLB = ARG[0]

for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)
bpy.ops.import_scene.gltf(filepath=GLB)

arm = next((o for o in bpy.data.objects if o.type == "ARMATURE"), None)
print("=== ESQUELETO ===")
print("armadura:", arm.name if arm else "NINGUNA", "| huesos:", len(arm.data.bones) if arm else 0)
print("escala:", tuple(round(v, 4) for v in arm.matrix_world.to_scale()) if arm else None)

padres = {}
prof = {}
for b in arm.data.bones:
    padres.setdefault(b.parent.name if b.parent else "(raiz)", []).append(b.name)
    n, p = 1, b.parent
    while p:
        n += 1
        p = p.parent
    prof[b.name] = n
print("raices:", sorted(padres.get("(raiz)", [])))
print("hijos por hueso (los 6 con mas):",
      sorted(((k, len(v)) for k, v in padres.items()), key=lambda x: -x[1])[:6])
print("profundidad maxima:", max(prof.values()) if prof else 0)

# Nombres: cuantos siguen la convencion del juego y cuantos son "huesos sueltos"
import re
patron = re.compile(r"^(Bip01|Bip|xiuzhang|wq_|PC079|_dummy|Q_|B_|E_|H_|S_)", re.I)
raros = [b.name for b in arm.data.bones if not patron.match(b.name)]
print("huesos con nombre no convencional:", len(raros), "ej:", raros[:8])

print()
print("=== MALLAS Y ASIGNACION ===")
sin_armadura = []
for o in [x for x in bpy.data.objects if x.type == "MESH"]:
    grupos = len(o.vertex_groups)
    verts_sin_peso = sum(1 for v in o.data.vertices if not v.groups or sum(g.weight for g in v.groups) < 1e-6)
    mods = [m.type for m in o.modifiers]
    mats = [m.name if m else "NULL" for m in o.data.materials]
    morf = len(o.data.shape_keys.key_blocks) - 1 if o.data.shape_keys else 0
    if "ARMATURE" not in mods:
        sin_armadura.append(o.name)
    print("%-46s v=%6d grupos=%3d sin_peso=%4d mods=%s mats=%s morf=%d" %
          (o.name[:46], len(o.data.vertices), grupos, verts_sin_peso, mods, mats, morf))
print("mallas SIN modificador de armadura:", sin_armadura or "ninguna")

print()
print("=== MATERIALES Y TEXTURAS ===")
for m in bpy.data.materials:
    imgs = [n.image for n in m.node_tree.nodes if n.type == "TEX_IMAGE" and n.image] if m.use_nodes else []
    print("%-30s nodos=%-4d imagenes=%d %s" % (m.name[:30], len(m.node_tree.nodes) if m.use_nodes else 0,
                                               len(imgs), [i.name for i in imgs]))
sueltas = [i.name for i in bpy.data.images if not i.packed_file and i.source == "FILE"]
print("imagenes sin empaquetar:", len(sueltas), sueltas[:6])

print()
print("=== EXPRESIONES (morph targets) ===")
for o in [x for x in bpy.data.objects if x.type == "MESH" and x.data.shape_keys]:
    kb = [k.name for k in o.data.shape_keys.key_blocks]
    print(o.name, "->", len(kb) - 1, "claves:", kb[:26])

print()
print("=== FORMAS PERSONALIZADAS DE HUESO (las 'esferas' del importador) ===")
con_forma = [b.name for b in arm.pose.bones if b.custom_shape]
print("huesos con forma personalizada:", len(con_forma))
print("objetos en la coleccion glTF_not_exported:",
      [o.name for o in bpy.data.objects if o.name.startswith(("Icosphere", "Esfera"))][:4])