"""Sujeta el plano de doblez de codo y rodilla con huesos de referencia (pole targets).

Sin referencia, el IK gira el plano de doblez: con el pie atras la rodilla se invertia. El polo fija el
plano, pero su angulo hay que medirlo.

OJO con el criterio, que es donde me equivoque antes: mirar solo el desvio en Y no vale, porque el
plano tambien puede girar HACIA UN LADO (el codo o la rodilla se van de lado). El criterio bueno es que
la articulacion se desvie hacia el MISMO LADO que en reposo, y ademas que el reposo no se mueva.

Uso: blender --background --python polos_ik2.py -- <blend>
"""
import math
import sys

import bpy

from mathutils import Vector

ruta = sys.argv[sys.argv.index("--") + 1]
bpy.ops.wm.open_mainfile(filepath=ruta)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")

POLOS = {"Codo_Izq": ("Antebrazo_Izq", Vector((0, 0.6, 0))),
         "Codo_Der": ("Antebrazo_Der", Vector((0, 0.6, 0))),
         "Rodilla_Izq": ("Pantorrilla_Izq", Vector((0, -0.6, 0))),
         "Rodilla_Der": ("Pantorrilla_Der", Vector((0, -0.6, 0)))}
CADENAS = {"Antebrazo_Izq": "Codo_Izq", "Antebrazo_Der": "Codo_Der",
           "Pantorrilla_Izq": "Rodilla_Izq", "Pantorrilla_Der": "Rodilla_Der"}

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
for hueso, polo in CADENAS.items():
    c = next(c for c in arm.pose.bones[hueso].constraints if c.type == "IK")
    c.pole_target = arm
    c.pole_subtarget = polo
print("   polos puestos: %s" % ", ".join(CADENAS.values()))


def eslabones(extremidad, lado):
    if extremidad == "Mano":
        return ("Brazo_" + lado, "Antebrazo_" + lado, "Mano_" + lado)
    return ("Muslo_" + lado, "Pantorrilla_" + lado, "Pie_" + lado)


def desvio(extremidad, lado):
    """Vector de la articulacion intermedia respecto a la recta que une sus dos vecinas."""
    p0, p1, p2 = (arm.pose.bones[n].head for n in eslabones(extremidad, lado))
    t = (p1 - p0).dot(p2 - p0) / max((p2 - p0).length_squared, 1e-9)
    return p1 - (p0 + t * (p2 - p0))


def desvio_reposo(extremidad, lado):
    p0, p1, p2 = (arm.data.bones[n].head_local for n in eslabones(extremidad, lado))
    t = (p1 - p0).dot(p2 - p0) / max((p2 - p0).length_squared, 1e-9)
    return p1 - (p0 + t * (p2 - p0))


REFERENCIA = {(e, l): desvio_reposo(e, l) for e in ("Mano", "Pie") for l in ("Izq", "Der")}

CASOS = [("IK_Mano_Der", "Mano", "Der", (0.00, -0.18, 0.12)),
         ("IK_Mano_Der", "Mano", "Der", (0.00, -0.10, 0.25)),
         ("IK_Mano_Der", "Mano", "Der", (0.10, 0.05, 0.15)),
         ("IK_Mano_Izq", "Mano", "Izq", (0.00, -0.15, 0.10)),
         ("IK_Mano_Izq", "Mano", "Izq", (-0.08, -0.20, 0.00)),
         ("IK_Pie_Izq", "Pie", "Izq", (0.00, -0.20, 0.05)),
         ("IK_Pie_Izq", "Pie", "Izq", (0.05, 0.18, 0.02)),
         ("IK_Pie_Der", "Pie", "Der", (0.00, 0.15, 0.05)),
         ("IK_Pie_Der", "Pie", "Der", (-0.06, -0.25, 0.04))]


def limpiar():
    for pb in arm.pose.bones:
        pb.location = (0, 0, 0)
    bpy.context.view_layer.update()


def reposo_movido():
    """Cuanto se aparta del sitio el hueso que mas se mueve, con los controles en reposo."""
    peor = 0.0
    for b in arm.data.bones:
        if b.name.startswith(("IK_", "Codo_", "Rodilla_")):
            continue
        peor = max(peor, (arm.pose.bones[b.name].head - b.head_local).length)
    return peor


def faltas(angulo):
    for hueso in CADENAS:
        next(c for c in arm.pose.bones[hueso].constraints if c.type == "IK").pole_angle = angulo
    limpiar()
    movido = reposo_movido()
    malos = []
    for control, extremidad, lado, destino in CASOS:
        limpiar()
        arm.pose.bones[control].location = Vector(destino)
        bpy.context.view_layer.update()
        d = desvio(extremidad, lado)
        ref = REFERENCIA[(extremidad, lado)]
        if d.length < 0.002:                       # recto: no hay articulacion que juzgar
            continue
        if d.normalized().dot(ref.normalized()) < 0.5:
            malos.append("%s%s %s" % (extremidad, lado[0], ["%+.2f" % x for x in d]))
    return movido, malos


print()
print("=== buscando el angulo de polo (mirando el sentido del desvio Y el reposo) ===")
mejor = None
for grados in (-180, -135, -90, -60, -45, -30, 0, 30, 45, 60, 90, 135, 180):
    movido, malos = faltas(math.radians(grados))
    marca = "" if movido < 0.02 else " (reposo desplazado %.3f m)" % movido
    print("   polo %+5d -> %d malos%s %s" % (grados, len(malos), marca, malos[:2]))
    if mejor is None or (len(malos), movido) < (len(mejor[2]), mejor[3]):
        mejor = (grados, math.radians(grados), malos, movido)
print("ELEGIDO: %+d grados (%d malos, reposo desplazado %.4f m)"
      % (mejor[0], len(mejor[2]), mejor[3]))
faltas(mejor[1])
limpiar()
bpy.ops.wm.save_as_mainfile(filepath=ruta)
print("guardado:", ruta)
