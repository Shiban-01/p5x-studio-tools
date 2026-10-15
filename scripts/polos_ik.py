"""Sujeta el plano de doblez de codo y rodilla con huesos de referencia (pole targets).

Sin referencia, el IK gira el plano de doblez cuando el objetivo cruza cierta zona: con el pie atras, la
rodilla se invertia. El polo fija ese plano. El angulo del polo no se adivina: se prueban los candidatos
y se elige el que hace doblar bien en TODOS los casos.

Uso: blender --background --python polos_ik.py -- <blend>
"""
import math
import sys

import bpy

from mathutils import Vector

ruta = sys.argv[sys.argv.index("--") + 1]
bpy.ops.wm.open_mainfile(filepath=ruta)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")

# 1) huesos de referencia, colocados donde debe apuntar la articulacion
POLOS = {"Codo_Izq": ("Antebrazo_Izq", Vector((0, 0.6, 0))),      # el codo apunta atras
         "Codo_Der": ("Antebrazo_Der", Vector((0, 0.6, 0))),
         "Rodilla_Izq": ("Pantorrilla_Izq", Vector((0, -0.6, 0))),  # la rodilla apunta adelante
         "Rodilla_Der": ("Pantorrilla_Der", Vector((0, -0.6, 0)))}
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode="EDIT")
for nombre, (articulacion, hacia) in POLOS.items():
    if nombre in arm.data.edit_bones:
        arm.data.edit_bones.remove(arm.data.edit_bones[nombre])
    eb = arm.data.edit_bones.new(nombre)
    eb.head = arm.data.edit_bones[articulacion].head.copy()
    eb.tail = eb.head + hacia
    eb.parent = arm.data.edit_bones["Raiz"]
    eb.use_deform = False
    eb.use_connect = False
bpy.ops.object.mode_set(mode="OBJECT")

CADENAS = {"Antebrazo_Izq": "Codo_Izq", "Antebrazo_Der": "Codo_Der",
           "Pantorrilla_Izq": "Rodilla_Izq", "Pantorrilla_Der": "Rodilla_Der"}
for hueso, polo in CADENAS.items():
    c = next(c for c in arm.pose.bones[hueso].constraints if c.type == "IK")
    c.pole_target = arm
    c.pole_subtarget = polo
    print("   %s -> polo %s" % (hueso, polo))

# 2) casos de prueba, todos dentro del alcance
CASOS = [("IK_Mano_Der", "Mano", "Der", (0.00, -0.18, 0.12)),
         ("IK_Mano_Der", "Mano", "Der", (0.00, -0.10, 0.25)),
         ("IK_Mano_Der", "Mano", "Der", (0.10, 0.05, 0.15)),
         ("IK_Mano_Izq", "Mano", "Izq", (0.00, -0.15, 0.10)),
         ("IK_Mano_Izq", "Mano", "Izq", (-0.08, -0.20, 0.00)),
         ("IK_Pie_Izq", "Pie", "Izq", (0.00, -0.20, 0.05)),
         ("IK_Pie_Izq", "Pie", "Izq", (0.05, 0.18, 0.02)),
         ("IK_Pie_Der", "Pie", "Der", (0.00, 0.15, 0.05)),
         ("IK_Pie_Der", "Pie", "Der", (-0.06, -0.25, 0.04))]


def desvio(extremidad, lado):
    if extremidad == "Mano":
        a, m, b = "Brazo_" + lado, "Antebrazo_" + lado, "Mano_" + lado
    else:
        a, m, b = "Muslo_" + lado, "Pantorrilla_" + lado, "Pie_" + lado
    p0, p1, p2 = (arm.pose.bones[n].head for n in (a, m, b))
    t = (p1 - p0).dot(p2 - p0) / max((p2 - p0).length_squared, 1e-9)
    return (p1 - (p0 + t * (p2 - p0))).y


def fallos(angulo):
    """Cuantos casos doblan al reves con este angulo de polo."""
    for hueso in CADENAS:
        next(c for c in arm.pose.bones[hueso].constraints if c.type == "IK").pole_angle = angulo
    n, detalles = 0, []
    for control, extremidad, lado, destino in CASOS:
        for pb in arm.pose.bones:
            pb.location = (0, 0, 0)
        bpy.context.view_layer.update()
        arm.pose.bones[control].location = Vector(destino)
        bpy.context.view_layer.update()
        d = desvio(extremidad, lado)
        bien = d > 0.004 if extremidad == "Mano" else d < -0.004
        recto = abs(d) <= 0.004
        if not bien and not recto:
            n += 1
            detalles.append("%s%s %s->%s" % (extremidad, lado[0], str(destino), "%+.3f" % d))
    return n, detalles


print()
print("=== buscando el angulo de polo que dobla bien en los %d casos ===" % len(CASOS))
mejor, mejor_detalle = None, None
for grados in (-180, -135, -90, -45, 0, 45, 90, 135, 180):
    n, detalle = fallos(math.radians(grados))
    print("   polo %+5d grados -> %d fallos %s" % (grados, n, detalle[:3]))
    if mejor is None or n < mejor[1]:
        mejor, mejor_detalle = (grados, n), detalle
print("ELEGIDO: %+d grados, %d fallos" % (mejor[0], mejor[1]))
fallos(math.radians(mejor[0]))
for pb in arm.pose.bones:
    pb.location = (0, 0, 0)
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=ruta)
print("guardado:", ruta)
