"""Comprueba el sentido del codo y la rodilla con el IK, con objetivos DENTRO del alcance.

Dentro del alcance la cadena tiene que doblarse, y ahi se puede medir de verdad: el codo debe quedar
por detras de la recta hombro->muneca (+Y) y la rodilla por delante (-Y), porque el personaje mira a -Y.
"""
import sys

import bpy

from mathutils import Vector

bpy.ops.wm.open_mainfile(filepath=sys.argv[sys.argv.index("--") + 1])
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")


def desvio(lado, extremidad, etiqueta):
    if etiqueta == "Mano":
        a, m, b = "Brazo_" + lado, "Antebrazo_" + lado, "Mano_" + lado
    else:
        a, m, b = "Muslo_" + lado, "Pantorrilla_" + lado, "Pie_" + lado
    p0, p1, p2 = (arm.pose.bones[n].head for n in (a, m, b))
    t = (p1 - p0).dot(p2 - p0) / max((p2 - p0).length_squared, 1e-9)
    recta = p0 + t * (p2 - p0)
    d = (p1 - recta).y
    largo = (p2 - p0).length
    return d, largo


print("=== objetivos DENTRO del alcance ===")
CASOS = [("IK_Mano_Der", "Der", "Mano", (0.0, -0.18, 0.12)),
         ("IK_Mano_Der", "Der", "Mano", (0.0, -0.10, 0.25)),
         ("IK_Mano_Izq", "Izq", "Mano", (0.0, -0.15, 0.10)),
         ("IK_Pie_Izq", "Izq", "Pie", (0.0, -0.20, 0.05)),
         ("IK_Pie_Der", "Der", "Pie", (0.0, 0.15, 0.05))]
for control, lado, extremidad, destino in CASOS:
    for pb in arm.pose.bones:
        pb.location = (0, 0, 0)
    bpy.context.view_layer.update()
    arm.pose.bones[control].location = Vector(destino)
    bpy.context.view_layer.update()
    d, largo = desvio(lado, extremidad, extremidad)
    if extremidad == "Mano":
        bien = d > 0.004
        texto = "atras, correcto" if bien else ("ADELANTE, MAL" if d < -0.004 else "recto")
    else:
        bien = d < -0.004
        texto = "adelante, correcto" if bien else ("ATRAS, MAL" if d > 0.004 else "recto")
    print("   %-14s %-28s %s: desvio %+.3f (alcance %.3f m)  %s"
          % (control, str(destino), extremidad, d, largo, texto))
