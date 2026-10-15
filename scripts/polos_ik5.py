"""Polos de IK: un angulo POR CADENA, buscado midiendo cada una por separado.

Las cuatro cadenas son independientes, asi que buscar su angulo de polo una a una da el optimo exacto.
Hacia falta: con un angulo unico, el brazo derecho salia invertido mientras el izquierdo iba bien (son
espejos), y con un angulo para brazos y otro para piernas quedaban 3 casos malos.

Criterio por cadena: que el doblez vaya al MISMO lado que en reposo, y que el reposo de esa cadena no
se mueva (un polo mal puesto llega a desplazar el maniqui 17 cm).

Uso: blender --background --python polos_ik5.py -- <blend> [png]
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


POLOS = {}
for extremidad, lado in (("Mano", "Izq"), ("Mano", "Der"), ("Pie", "Izq"), ("Pie", "Der")):
    POLOS[("Codo_" if extremidad == "Mano" else "Rodilla_") + lado] = (
        eslabones(extremidad, lado)[1], desvio(extremidad, lado, reposo=True).normalized())

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

CADENAS = [("Antebrazo_Izq", "Codo_Izq", "Mano", "Izq"), ("Antebrazo_Der", "Codo_Der", "Mano", "Der"),
           ("Pantorrilla_Izq", "Rodilla_Izq", "Pie", "Izq"),
           ("Pantorrilla_Der", "Rodilla_Der", "Pie", "Der")]
for hueso, polo, _, _ in CADENAS:
    c = next(c for c in arm.pose.bones[hueso].constraints if c.type == "IK")
    c.pole_target = arm
    c.pole_subtarget = polo
print("   polos puestos en la direccion real del doblez de cada articulacion")


def ik(hueso):
    return next(c for c in arm.pose.bones[hueso].constraints if c.type == "IK")


def mover_a(control, destino):
    """Coloca el control en coordenadas DEL MANIQUI (no en el espacio propio del hueso)."""
    pb = arm.pose.bones[control]
    pb.location = pb.bone.matrix_local.to_3x3().inverted() @ (Vector(destino) - pb.bone.head_local)
    bpy.context.view_layer.update()


def limpiar():
    for pb in arm.pose.bones:
        pb.location = (0, 0, 0)
    bpy.context.view_layer.update()


CABEZAS = {c: arm.data.bones[c].head_local.copy() for c in
           ("IK_Mano_Izq", "IK_Mano_Der", "IK_Pie_Izq", "IK_Pie_Der")}
CENTROS = {"Mano": {l: arm.data.bones["Brazo_" + l].head_local.copy() for l in ("Izq", "Der")},
           "Pie": {l: arm.data.bones["Muslo_" + l].head_local.copy() for l in ("Izq", "Der")}}
CASOS = {}
for _, _, extremidad, lado in CADENAS:
    control = "IK_" + extremidad + "_" + lado
    CASOS[(extremidad, lado)] = [CABEZAS[control].lerp(CENTROS[extremidad][lado], f)
                                 for f in (0.3, 0.55, 0.8)]


def probar_cadena(hueso, polo, extremidad, lado, grados):
    """(Casos que doblan al reves, desplazamiento del reposo de esta cadena) con este angulo."""
    ik(hueso).pole_angle = math.radians(grados)
    limpiar()
    movido = max((arm.pose.bones[n].head - arm.data.bones[n].head_local).length
                 for n in eslabones(extremidad, lado))
    control = "IK_" + extremidad + "_" + lado
    ref = desvio(extremidad, lado, reposo=True)
    malos = 0
    for destino in CASOS[(extremidad, lado)]:
        limpiar()
        mover_a(control, destino)
        d = desvio(extremidad, lado)
        if d.length < 0.02 or d.normalized().dot(ref.normalized()) < 0.5:
            malos += 1
    return malos, movido


print()
print("=== un angulo por cadena (3 posiciones por cadena que obligan a doblar) ===")
ELEGIDOS = {}
for hueso, polo, extremidad, lado in CADENAS:
    resultados = [(probar_cadena(hueso, polo, extremidad, lado, g), g)
                  for g in (-180, -135, -90, -60, -45, -30, 0, 30, 45, 60, 90, 135, 180)]
    resultados.sort(key=lambda r: (r[0][0], r[0][1]))
    (malos, movido), grados = resultados[0]
    ELEGIDOS[hueso] = grados
    print("   %-16s elegido %+5d grados (%d fallos, reposo de la cadena desplazado %.4f m)"
          % (hueso, grados, malos, movido))
    print("        otras opciones: %s"
          % ", ".join("%+d:%d" % (g, m) for (m, _), g in resultados[1:6]))
for hueso, _, _, _ in CADENAS:
    ik(hueso).pole_angle = math.radians(ELEGIDOS[hueso])

print()
print("=== informe final ===")
limpiar()
peor = max((arm.pose.bones[b.name].head - b.head_local).length for b in arm.data.bones
           if not b.name.startswith(("IK_", "Codo_", "Rodilla_")))
print("   reposo: el hueso que mas se aparta %.4f m -> %s"
      % (peor, "intacto" if peor < 0.01 else "*** SE MUEVE ***"))
for _, _, extremidad, lado in CADENAS:
    control = "IK_" + extremidad + "_" + lado
    ref = desvio(extremidad, lado, reposo=True)
    for destino in CASOS[(extremidad, lado)]:
        limpiar()
        mover_a(control, destino)
        d = desvio(extremidad, lado)
        alin = d.normalized().dot(ref.normalized())
        print("   %-14s desvio %.3f m, alineado con el reposo %+.2f -> %s"
              % (control, d.length, alin, "dobla bien" if alin > 0.5 else "MAL"))
limpiar()
for control, pareja in (("IK_Mano_Der", ("Brazo_Der", "Mano_Der")),
                        ("IK_Pie_Izq", ("Muslo_Izq", "Pie_Izq"))):
    base = (arm.pose.bones[pareja[1]].head - arm.pose.bones[pareja[0]].head).length
    mover_a(control, arm.data.bones[pareja[1]].head_local + Vector((0, -3, 0)))
    ahora = (arm.pose.bones[pareja[1]].head - arm.pose.bones[pareja[0]].head).length
    print("   %-12s tirando a 3 m: %.3f m (reposo %.3f) -> %s"
          % (control, ahora, base, "no se estira" if ahora < base * 1.02 else "*** SE ESTIRA ***"))
limpiar()
bpy.ops.wm.save_as_mainfile(filepath=ruta)
print("guardado:", ruta)

if png:
    mover_a("IK_Mano_Der", CABEZAS["IK_Mano_Der"] + Vector((0.08, -0.20, 0.30)))
    mover_a("IK_Mano_Izq", CABEZAS["IK_Mano_Izq"] + Vector((-0.05, -0.02, -0.28)))
    mover_a("IK_Pie_Izq", CABEZAS["IK_Pie_Izq"] + Vector((0.03, -0.18, 0.26)))
    mover_a("IK_Pie_Der", CABEZAS["IK_Pie_Der"] + Vector((0, 0.06, 0.04)))
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
