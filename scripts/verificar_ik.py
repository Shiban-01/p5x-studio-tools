"""Verificacion del IK del maniqui: reposo intacto, doblez correcto en 9 casos, sin estiramiento.

Uso: blender --background --python verificar_ik.py -- <blend>
"""
import math
import sys

import bpy

from mathutils import Vector

bpy.ops.wm.open_mainfile(filepath=sys.argv[sys.argv.index("--") + 1])
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
mallas = [o for o in bpy.data.objects if o.type == "MESH"]

# ---------------------------------------------------------------- reposo intacto
desplazado = 0.0
for b in arm.data.bones:
    pb = arm.pose.bones[b.name]
    desplazado = max(desplazado, (pb.head - b.head_local).length, (pb.tail - b.tail_local).length)
print("=== reposo ===")
print("   el hueso que mas se aparta de su sitio: %.4f m -> %s"
      % (desplazado, "el IK no mueve nada en reposo" if desplazado < 0.002 else "*** SE MUEVE ***"))

# ---------------------------------------------------------------- doblez
def desvio(extremidad, lado):
    a, m, b = (("Brazo_", "Antebrazo_", "Mano_") if extremidad == "Mano"
               else ("Muslo_", "Pantorrilla_", "Pie_"))
    p0, p1, p2 = (arm.pose.bones[n + lado].head for n in (a, m, b))
    t = (p1 - p0).dot(p2 - p0) / max((p2 - p0).length_squared, 1e-9)
    return (p1 - (p0 + t * (p2 - p0))).y


CASOS = [("IK_Mano_Der", "Mano", "Der", (0.00, -0.18, 0.12)),
         ("IK_Mano_Der", "Mano", "Der", (0.00, -0.10, 0.25)),
         ("IK_Mano_Der", "Mano", "Der", (0.10, 0.05, 0.15)),
         ("IK_Mano_Izq", "Mano", "Izq", (0.00, -0.15, 0.10)),
         ("IK_Mano_Izq", "Mano", "Izq", (-0.08, -0.20, 0.00)),
         ("IK_Pie_Izq", "Pie", "Izq", (0.00, -0.20, 0.05)),
         ("IK_Pie_Izq", "Pie", "Izq", (0.05, 0.18, 0.02)),
         ("IK_Pie_Der", "Pie", "Der", (0.00, 0.15, 0.05)),
         ("IK_Pie_Der", "Pie", "Der", (-0.06, -0.25, 0.04))]
print()
print("=== 9 posiciones del control: el codo debe ir atras y la rodilla adelante ===")
malos = 0
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
        malos += 1
    print("   %-14s %-24s desvio %+.3f  %s" % (control, str(destino), d,
                                               "correcto" if bien else ("recto" if recto else "MAL")))
print("   doblan al reves: %d de %d" % (malos, len(CASOS)))

# ---------------------------------------------------------------- no se estira
print()
print("=== alcance: tirar del control lejos no debe alargar la extremidad ===")
for pb in arm.pose.bones:
    pb.location = (0, 0, 0)
bpy.context.view_layer.update()
for control, lado, pareja in (("IK_Mano_Der", "Der", ("Brazo_Der", "Mano_Der")),
                              ("IK_Pie_Izq", "Izq", ("Muslo_Izq", "Pie_Izq"))):
    base = (arm.pose.bones[pareja[1]].head - arm.pose.bones[pareja[0]].head).length
    arm.pose.bones[control].location = (0, -3.0, 0)
    bpy.context.view_layer.update()
    ahora = (arm.pose.bones[pareja[1]].head - arm.pose.bones[pareja[0]].head).length
    arm.pose.bones[control].location = (0, 0, 0)
    bpy.context.view_layer.update()
    print("   %-12s en reposo %.3f m, tirando a 3 m %.3f m -> %s"
          % (control, base, ahora, "no se estira" if ahora < base * 1.02 else "*** SE ESTIRA ***"))

# ---------------------------------------------------------------- topes de giro siguen
print()
print("=== los topes de giro siguen puestos (y el IK tambien los respeta) ===")
for hueso in ("Antebrazo_Der", "Pantorrilla_Izq", "Crujiente"):
    if hueso not in arm.pose.bones:
        continue
    pb = arm.pose.bones[hueso]
    limite = next((c for c in pb.constraints if c.type == "LIMIT_ROTATION"), None)
    ik = next((c for c in pb.constraints if c.type == "IK"), None)
    print("   %-16s tope %s | IK %s | limite de IK X %s (%d a %d grados)"
          % (hueso,
             "si" if limite else "NO",
             "si" if ik else "NO",
             "si" if pb.use_ik_limit_x else "NO",
             round(math.degrees(pb.ik_min_x)), round(math.degrees(pb.ik_max_x))))
print()
print("huesos: %d" % len(arm.data.bones))
print("controles: %s" % ", ".join(b.name for b in arm.data.bones if b.name.startswith("IK_")
                                  or b.name.startswith(("Codo_", "Rodilla_"))))
