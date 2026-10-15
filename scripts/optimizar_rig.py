"""Crea una copia OPTIMIZADA del paquete de artista, con el rig sin huesos de relleno.

Criterio (medido, no supuesto): se conserva un hueso si
  - lleva algun vertice de la malla (peso > 0 en cualquier objeto, aunque sea minimo), o
  - es ancestro de uno que lleva (sin el, la cadena se rompe), o
  - otro hueso lo referencia (restriccion o driver: son los controles de posado).

Se quitan los que no cumplen nada de eso: el plugin Magica Cloth, los ayudantes de MMD
(h_Motion_*, h_B_*), los duplicados con nombre al estilo MMD ("Bip01 L Thigh"), las gafas de VR,
los props y los objetivos que solo usaba el juego.

El fichero original NO se toca. Uso:
  blender --background --python optimizar_rig.py -- <blend_entrada> <blend_salida> [glb_salida]
"""
import os
import sys
import json

import bpy

entrada = sys.argv[sys.argv.index("--") + 1]
salida = sys.argv[sys.argv.index("--") + 2]
glb = sys.argv[sys.argv.index("--") + 3] if len(sys.argv) > sys.argv.index("--") + 3 else None

bpy.ops.wm.open_mainfile(filepath=entrada)

arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
mallas = [o for o in bpy.data.objects if o.type == "MESH" and o.vertex_groups]
total_antes = len(arm.data.bones)

# ---- 1) que huesos llevan malla (peso > 0, cualquier valor) ----
con_peso, vertices = set(), {}
for ob in mallas:
    nombres = [g.name for g in ob.vertex_groups]
    for v in ob.data.vertices:
        for g in v.groups:
            if g.weight > 0:
                n = nombres[g.group]
                con_peso.add(n)
                vertices[n] = vertices.get(n, 0) + 1

padres = {b.name: (b.parent.name if b.parent else None) for b in arm.data.bones}

# ---- 2) referencias: restricciones y drivers de los huesos ----
referenciados = set()
for pb in arm.pose.bones:
    for c in pb.constraints:
        if c.subtarget and c.subtarget in padres:
            referenciados.add(c.subtarget)
if arm.animation_data:
    for d in arm.animation_data.drivers:
        for objetivo in (d.data_path or "",):
            for nombre in padres:
                if '["%s"]' % nombre in objetivo:
                    referenciados.add(nombre)

# ---- 3) plan ----
conservar = set(con_peso) | referenciados
for n in list(conservar):                     # ancestros: sin ellos la cadena se rompe
    a = padres.get(n)
    while a:
        conservar.add(a)
        a = padres.get(a)
quitar = [b.name for b in arm.data.bones if b.name not in conservar]

def familia(nombre):
    if nombre.startswith("Magica"):
        return "plugin Magica Cloth"
    if nombre.startswith("h_"):
        return "ayudantes de MMD (h_*)"
    if nombre.startswith("t_"):
        return "objetivos de MMD/VR (t_*)"
    if nombre.startswith("CTRL_"):
        return "controles de posado (CTRL_*)"
    if " " in nombre:
        return 'duplicados con nombre de MMD ("Bipii L ...")'
    if nombre.startswith(("peishi_", "qunzi_")):
        return "huesos de tela (peishi_/qunzi_)"
    return "otros sin geometria"

resumen = {}
for n in quitar:
    resumen.setdefault(familia(n), []).append(n)

print("=== ANTES: %d huesos ===" % total_antes)
print("   llevan malla: %d | referenciados por otros huesos: %d | conservados con ancestros: %d"
      % (len(con_peso), len(referenciados), len(conservar)))
print("=== SE QUITAN: %d ===" % len(quitar))
for grupo, lista in sorted(resumen.items()):
    print("   %-42s %3d   %s" % (grupo, len(lista), ", ".join(sorted(lista))[:110]))
print("=== QUEDAN: %d ===" % len(conservar))

# ---- 4) borrar en modo edicion ----
# OJO: los huesos que estan en una coleccion OCULTA no se pueden seleccionar en modo Edicion, asi
# que `armature.delete()` los ignora. Hay que quitar las colecciones ANTES de borrar (de paso el
# artista ya no necesita nada escondido, porque no queda relleno). Con las colecciones puestas se
# borraron 60 de los 82 y el fichero salio con 274 huesos en vez de 252.
for c in list(arm.data.collections):
    arm.data.collections.remove(c)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.armature.select_all(action="DESELECT")
for eb in arm.data.edit_bones:
    if eb.name in set(quitar):
        eb.select = True
        eb.select_head = True
        eb.select_tail = True
bpy.ops.armature.delete()
bpy.ops.object.mode_set(mode="OBJECT")
print("tras borrar: %d huesos (%d de los %d planificados)"
      % (len(arm.data.bones), total_antes - len(arm.data.bones), len(quitar)))
if len(arm.data.bones) != len(conservar):
    print("   AVISO: quedan %d de mas; revisar antes de publicar" % (len(arm.data.bones) - len(conservar)))

# ---- 5) comprobar que no se ha roto nada ----
rotas = []
for pb in arm.pose.bones:
    for c in pb.constraints:
        if c.subtarget and c.subtarget not in arm.data.bones:
            rotas.append("%s -> %s" % (pb.name, c.subtarget))
huerfanos = [g.name for ob in mallas for g in ob.vertex_groups
             if g.name not in arm.data.bones and vertices.get(g.name, 0) > 0]
print("restricciones rotas: %d %s" % (len(rotas), rotas[:4]))
print("grupos de vertices que ahora no tienen hueso (con pesos): %d %s" % (len(huerfanos), huerfanos[:6]))
faltan = [b.name for b in arm.data.bones if b.name in con_peso] if False else []
sin_deform = [b.name for b in arm.data.bones if b.name in con_peso]
print("huesos que deforman y siguen presentes: %d de %d" % (len(sin_deform), len(con_peso)))

# ---- 6) colecciones: quitarlas, ya no hace falta esconder nada ----
for c in list(arm.data.collections):
    arm.data.collections.remove(c)

os.makedirs(os.path.dirname(salida), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=salida)
print("guardado:", salida, os.path.getsize(salida) // 1024, "KB")

if glb:
    bpy.ops.export_scene.gltf(filepath=glb, export_format="GLB", export_apply=False,
                              export_animations=False, export_yup=True)
    print("glb:", glb, os.path.getsize(glb) // 1024, "KB")

json.dump({"antes": total_antes, "despues": len(arm.data.bones), "quitados": sorted(quitar),
           "conservados": sorted(conservar), "con_peso": sorted(con_peso),
           "referenciados": sorted(referenciados), "restricciones_rotas": rotas},
          open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_dl",
                            "rig_optimizado.json"), "w"), indent=1)
