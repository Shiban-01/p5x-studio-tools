"""Sujeta el plano de doblez del IK con polos colocados DONDE DOBLA EL MANIQUI, y lo verifica.

Lo que estaba mal en los dos intentos anteriores:
  - El polo se colocaba "detras del codo / delante de la rodilla" a ojo, en (0, +-0.6, 0). Como el polo
    obliga al plano de doblez a pasar por el, si esa direccion no es la del reposo, el IK MUEVE el
    maniqui en reposo (hasta 17 cm medidos). Hay que ponerlo en la direccion real del desvio en reposo.
  - Los objetivos se movian con pose_bone.location, que va en el espacio LOCAL del hueso de control, no
    en el del maniqui. Los desplazamientos acababan en sitios raros y las extremidades salian rectas.

Y la verificacion, con el criterio que de verdad importa: la articulacion debe desviarse hacia el mismo
lado que en reposo (no vale mirar solo la Y: el plano tambien gira hacia los lados).

Uso: blender --background --python polos_ik3.py -- <blend> [png]
"""
import math
import os
import sys

import bpy

from mathutils import Vector

ruta = sys.argv[sys.argv.index("--") + 1]
png = sys.argv[sys.argv.index("--") + 2] if len(sys.argv) > sys.argv.index("--") + 2 else None

bpy.ops.wm.open_mainfile(filepath=ruta)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
mallas = [o for o in bpy.data.objects if o.type == "MESH"]


def eslabones(extremidad, lado):
    if extremidad == "Mano":
        return ("Brazo_" + lado, "Antebrazo_" + lado, "Mano_" + lado)
    return ("Muslo_" + lado, "Pantorrilla_" + lado, "Pie_" + lado)


def desvio(extremidad, lado, reposo=False):
    if reposo:
        p0, p1, p2 = (arm.data.bones[n].head_local for n in eslabones(extremidad, lado))
    else:
        p0, p1, p2 = (arm.pose.bones[n].head for n in eslabones(extremidad, lado))
    t = (p1 - p0).dot(p2 - p0) / max((p2 - p0).length_squared, 1e-9)
    return p1 - (p0 + t * (p2 - p0))


# ---------------------------------------------------------------- 1. polos donde dobla el maniqui
POLOS = {}
for extremidad, lado in (("Mano", "Izq"), ("Mano", "Der"), ("Pie", "Izq"), ("Pie", "Der")):
    hueso_medio = eslabones(extremidad, lado)[1]
    direccion = desvio(extremidad, lado, reposo=True).normalized()
    POLOS[("Codo_" if extremidad == "Mano" else "Rodilla_") + lado] = (hueso_medio, direccion)

bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode="EDIT")
for nombre, (articulacion, direccion) in POLOS.items():
    if nombre in arm.data.edit_bones:
        arm.data.edit_bones.remove(arm.data.edit_bones[nombre])
    eb = arm.data.edit_bones.new(nombre)
    eb.head = arm.data.edit_bones[articulacion].head.copy()
    eb.tail = eb.head + direccion * 0.4
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
print("   polos en la direccion real del doblez: %s"
      % ", ".join("%s(%s)" % (n, ["%+.2f" % x for x in d]) for n, (_, d) in POLOS.items()))


# ---------------------------------------------------------------- 2. mover en coordenadas del maniqui
def mover_a(control, destino):
    """Coloca el control en una posicion DEL MANIQUI (no en el espacio del propio hueso)."""
    pb = arm.pose.bones[control]
    pb.location = pb.bone.matrix_local.to_3x3().inverted() @ (Vector(destino) - pb.bone.head_local)
    bpy.context.view_layer.update()


def limpiar():
    for pb in arm.pose.bones:
        pb.location = (0, 0, 0)
    bpy.context.view_layer.update()


def reposo_movido():
    peor = 0.0
    for b in arm.data.bones:
        if b.name.startswith(("IK_", "Codo_", "Rodilla_")):
            continue
        peor = max(peor, (arm.pose.bones[b.name].head - b.head_local).length)
    return peor


CABEZAS = {c: arm.data.bones[c].head_local.copy() for c in
           ("IK_Mano_Izq", "IK_Mano_Der", "IK_Pie_Izq", "IK_Pie_Der")}
HOMBROS = {l: arm.data.bones["Brazo_" + l].head_local.copy() for l in ("Izq", "Der")}
CADERAS = {l: arm.data.bones["Muslo_" + l].head_local.copy() for l in ("Izq", "Der")}


def casos():
    """Objetivos que obligan a doblar: acercar la mano al hombro o el pie a la cadera."""
    salida = []
    for lado in ("Izq", "Der"):
        for fraccion in (0.35, 0.6, 0.75):
            salida.append(("IK_Mano_" + lado, "Mano", lado,
                           CABEZAS["IK_Mano_" + lado].lerp(HOMBROS[lado], fraccion)))
            salida.append(("IK_Pie_" + lado, "Pie", lado,
                           CABEZAS["IK_Pie_" + lado].lerp(CADERAS[lado], fraccion)))
    return salida


CASOS = casos()


def faltas(angulo):
    for hueso in CADENAS:
        next(c for c in arm.pose.bones[hueso].constraints if c.type == "IK").pole_angle = angulo
    limpiar()
    movido = reposo_movido()
    malos = []
    for control, extremidad, lado, destino in CASOS:
        limpiar()
        mover_a(control, destino)
        d = desvio(extremidad, lado)
        ref = desvio(extremidad, lado, reposo=True)
        if d.length < 0.01:
            malos.append("%s%s RECTA" % (extremidad, lado[0]))
        elif d.normalized().dot(ref.normalized()) < 0.5:
            malos.append("%s%s girada %s" % (extremidad, lado[0], ["%+.2f" % x for x in d]))
    return movido, malos


print()
print("=== angulo de polo: se exige que el reposo no se mueva y que el doblez vaya al mismo lado ===")
mejor = None
for grados in (-180, -135, -90, -45, 0, 45, 90, 135, 180):
    movido, malos = faltas(math.radians(grados))
    print("   polo %+5d -> %2d fallos de %d, reposo desplazado %.4f m  %s"
          % (grados, len(malos), len(CASOS), movido, malos[:2]))
    if mejor is None or (len(malos), movido) < (len(mejor[2]), mejor[3]):
        mejor = (grados, math.radians(grados), malos, movido)
print("ELEGIDO: %+d grados (%d fallos, reposo desplazado %.4f m)" % (mejor[0], len(mejor[2]), mejor[3]))
faltas(mejor[1])

# ---------------------------------------------------------------- 3. informe final
print()
print("=== informe ===")
limpiar()
print("   reposo: el hueso que mas se aparta %.4f m -> %s"
      % (reposo_movido(), "intacto" if reposo_movido() < 0.005 else "*** SE MUEVE ***"))
for control, extremidad, lado, destino in CASOS[:4]:
    limpiar()
    mover_a(control, destino)
    d = desvio(extremidad, lado)
    ref = desvio(extremidad, lado, reposo=True)
    alineacion = d.normalized().dot(ref.normalized()) if d.length > 0.01 else 0.0
    print("   %-14s mano/pie al %d%% del camino al hombro/cadera: articulacion desviada %.3f m, "
          "alineada con el reposo %+.2f"
          % (control, round(100 * (1 - 0.35)), d.length, alineacion))
limpiar()
for control, pareja in (("IK_Mano_Der", ("Brazo_Der", "Mano_Der")),
                        ("IK_Pie_Izq", ("Muslo_Izq", "Pie_Izq"))):
    base = (arm.pose.bones[pareja[1]].head - arm.pose.bones[pareja[0]].head).length
    mover_a(control, arm.data.bones[pareja[1]].head_local + Vector((0, -3, 0)))
    ahora = (arm.pose.bones[pareja[1]].head - arm.pose.bones[pareja[0]].head).length
    print("   %-12s tirando a 3 m: %.3f m (en reposo %.3f) -> %s"
          % (control, ahora, base, "no se estira" if ahora < base * 1.02 else "*** SE ESTIRA ***"))
limpiar()
bpy.ops.wm.save_as_mainfile(filepath=ruta)
print("guardado:", ruta)

if png:
    mover_a("IK_Mano_Der", CABEZAS["IK_Mano_Der"] + Vector((0.10, -0.16, 0.34)))
    mover_a("IK_Mano_Izq", CABEZAS["IK_Mano_Izq"] + Vector((-0.06, -0.05, -0.30)))
    mover_a("IK_Pie_Izq", CABEZAS["IK_Pie_Izq"] + Vector((0.04, -0.16, 0.30)))
    mover_a("IK_Pie_Der", CABEZAS["IK_Pie_Der"] + Vector((0, 0.05, 0.05)))
    arm.pose.bones["Cabeza"].rotation_mode = "XYZ"
    arm.pose.bones["Cabeza"].rotation_euler = (0, math.radians(18), 0)
    bpy.context.view_layer.update()
    todo = [Vector(c) for ob in mallas for c in ob.bound_box]
    alto = max(c.z for c in todo) - min(c.z for c in todo)
    centro = Vector(((min(c.x for c in todo) + max(c.x for c in todo)) / 2,
                     (min(c.y for c in todo) + max(c.y for c in todo)) / 2,
                     (min(c.z for c in todo) + max(c.z for c in todo)) / 2))
    cam = bpy.data.objects.get("camara")
    cam.location = centro + Vector((alto * 1.2, -alto * 1.8, alto * 0.30))
    cam.rotation_euler = (centro - cam.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = cam
    esc = bpy.context.scene
    esc.render.resolution_x, esc.render.resolution_y = 800, 1100
    try:
        esc.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        esc.render.engine = "BLENDER_EEVEE"
    esc.render.filepath = png
    os.makedirs(os.path.dirname(png), exist_ok=True)
    bpy.ops.render.render(write_still=True)
    print("render:", png, os.path.getsize(png) // 1024, "KB")
print("HUESOS: %d" % len(arm.data.bones))
