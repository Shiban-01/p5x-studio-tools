"""Prueba de posado: gira huesos y MIDE como se mueve la malla. No opina, mide.

Si el esqueleto derivado de las inversas de bind es un buen rig, al girar el hombro los vertices de
la mano se tienen que mover mucho, los de la cabeza casi nada y los del torso un poco. Si los pesos o
la jerarquia estan mal, sale un desparrame (se mueve todo) o no se mueve nada.
"""
import math
import sys

import bpy
from mathutils import Vector

ARG = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
GLB = ARG[0]

for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)
bpy.ops.import_scene.gltf(filepath=GLB)


def reposo():
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    salida = {}
    for o in bpy.data.objects:
        if o.type != "MESH" or not o.data.vertices:
            continue
        ev = o.evaluated_get(dg)
        malla = ev.to_mesh()
        salida[o.name] = [ev.matrix_world @ v.co for v in malla.vertices]
        ev.to_mesh_clear()
    return salida


def mover(cuerpo, hueso, grados, eje="X"):
    for b in cuerpo.pose.bones:
        b.rotation_mode = "XYZ"
        b.rotation_euler = (0, 0, 0)
    b = cuerpo.pose.bones[hueso]
    i = "XYZ".index(eje)
    r = list(b.rotation_euler)
    r[i] = math.radians(grados)
    b.rotation_euler = r


def desplazamiento(nombre_malla, antes, despues, grupo=None, umbral=0.5):
    """Distancia media de los vertices (los de un grupo de pesos, si se pide)."""
    cuerpo = bpy.data.objects[nombre_malla]
    idx = None
    if grupo:
        vg = cuerpo.vertex_groups.get(grupo)
        if vg is None:
            return None, 0
        idx = vg.index
    suma, n = 0.0, 0
    for i, (a, d) in enumerate(zip(antes[nombre_malla], despues[nombre_malla])):
        if idx is not None:
            peso = 0.0
            for g in cuerpo.data.vertices[i].groups:
                if g.group == idx:
                    peso = g.weight
            if peso < umbral:
                continue
        suma += (a - d).length
        n += 1
    return (suma / n if n else 0.0), n


cuerpo = next(o for o in bpy.data.objects if o.type == "ARMATURE")
malla_cuerpo = next(o.name for o in bpy.data.objects if o.type == "MESH" and "body" in o.name)
malla_cara = next((o.name for o in bpy.data.objects if o.type == "MESH" and "face" in o.name and "eye" not in o.name), None)

base = reposo()
print("=== PRUEBA DE POSADO (desplazamiento medio en metros) ===")
pruebas = [("Bip01 L UpperArm", 45, "hombro izq. 45 grados", "Bip01 L Hand"),
           ("Bip01 L UpperArm", 45, "hombro izq. 45 grados", "Bip01 Head"),
           ("Bip01 L UpperArm", 45, "hombro izq. 45 grados", "Bip01 Spine1"),
           ("Bip01 L Forearm", 60, "codo izq. 60 grados", "Bip01 L Hand"),
           ("Bip01 L Thigh", 40, "muslo izq. 40 grados", "Bip01 L Foot"),
           ("Bip01 Head", 30, "cuello/cabeza 30 grados", "Bip01 Head")]
for hueso, grados, etiqueta, grupo in pruebas:
    mover(cuerpo, hueso, grados)
    desp = reposo()
    d, n = desplazamiento(malla_cuerpo, base, desp, grupo)
    print("  %-32s -> verts de '%-18s' %4d, se mueven %.4f m" % (etiqueta, grupo, n, d or 0.0))

mover(cuerpo, "Bip01 L UpperArm", 0)

# Las expresiones tambien tienen que funcionar
if malla_cara:
    klaves = bpy.data.objects[malla_cara].data.shape_keys.key_blocks
    base_cara = reposo()
    movidos = []
    for k in klaves[1:4]:
        for kk in klaves:
            kk.value = 0.0
        k.value = 1.0
        desp = reposo()
        d, n = desplazamiento(malla_cara, base_cara, desp)
        movidos.append((k.name, d, n))
    for kk in klaves:
        kk.value = 0.0
    print("=== EXPRESIONES ===")
    print("  cara:", ", ".join("%s %.4f m (%d verts)" % (n, d or 0, c) for n, d, c in movidos))

# Y la forma en reposo debe coincidir con la malla original (pesos y bind coherentes)
print("=== CONSISTENCIA EN REPOSO ===")
maxdev = 0.0
dg = bpy.context.evaluated_depsgraph_get()
for o in bpy.data.objects:
    if o.type != "MESH" or not o.data.vertices or "ARMATURE" not in [m.type for m in o.modifiers]:
        continue
    ev = o.evaluated_get(dg)
    m = ev.to_mesh()
    for i, v in enumerate(m.vertices):
        maxdev = max(maxdev, ((ev.matrix_world @ v.co) - (o.matrix_world @ o.data.vertices[i].co)).length)
    ev.to_mesh_clear()
print("  desvio maximo reposo (malla con armadura vs original): %.6f m" % maxdev)