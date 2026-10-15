"""Posa la pierna con el IK sobre el esqueleto ya arreglado y MIDE si la rodilla dobla donde debe.

Mide tres cosas por cada postura:
  - donde queda la rodilla (debe quedarse a la altura de la rodilla real, z ~0.5, no subir a la cadera)
  - cuanto se dobla la rodilla (angulo entre muslo y pantorrilla)
  - cuanto se estira la piel: aristas de mas de 3 mm que se alargan mas del 10%
y saca un render de cada postura.

Uso: blender --background --python probar_piernas.py -- <blend> <carpeta_salida>
"""
import math
import os
import sys

import bpy
from mathutils import Vector

ARG = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
BLEND, SALIDA = ARG[0], ARG[1]
os.makedirs(SALIDA, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=BLEND)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
cuerpo = next(o for o in bpy.data.objects if o.type == "MESH" and len(o.data.vertices) > 10000)


def limpiar():
    for pb in arm.pose.bones:
        pb.rotation_mode = "XYZ"
        pb.rotation_euler = (0, 0, 0)
        pb.location = (0, 0, 0)
    bpy.context.view_layer.update()


def malla():
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    ev = cuerpo.evaluated_get(dg)
    m = ev.to_mesh()
    v = [ev.matrix_world @ x.co for x in m.vertices]
    e = [(a.vertices[0], a.vertices[1]) for a in m.edges]
    ev.to_mesh_clear()
    return v, e


limpiar()
base_v, aristas = malla()
largos0 = [ (base_v[a]-base_v[b]).length for a, b in aristas ]


def medir(etiqueta):
    v, _ = malla()
    rotas = 0
    peor = 0.0
    for (a, b), l0 in zip(aristas, largos0):
        if l0 < 0.003:
            continue
        l1 = (v[a]-v[b]).length
        if l1 > l0 * 1.10:
            rotas += 1
            peor = max(peor, l1 - l0)
    muslo = arm.pose.bones["Bip01 L Thigh"]
    pant = arm.pose.bones["Bip01 L Calf"]
    rodilla = arm.matrix_world @ pant.head
    tobillo = arm.matrix_world @ arm.pose.bones["Bip01 L Foot"].head
    v1 = (arm.matrix_world @ muslo.tail) - (arm.matrix_world @ muslo.head)
    v2 = (arm.matrix_world @ pant.tail) - (arm.matrix_world @ pant.head)
    ang = math.degrees(v1.angle(v2))
    print("   %-22s rodilla z=%.3f (y=%+.3f)  tobillo z=%.3f  doblez=%.1f grados  aristas rotas=%d/%d peor=%.1f mm"
          % (etiqueta, rodilla.z, rodilla.y, tobillo.z, ang, rotas, sum(1 for l in largos0 if l > 0.003), peor*1000))
    return ang


print("=== mediciones (pierna izquierda) ===")
limpiar()
medir("reposo")

# postura 1: pie adelante y arriba (paso)
limpiar()
pb = arm.pose.bones.get("CTRL_Pie_Izq") or arm.pose.bones.get("足ＩＫ.L")
if pb:
    pb.location = (0.0, -0.35, 0.18) if pb.name.startswith("CTRL") else pb.location
    medir("paso (pie adelante)")
else:
    print("   (no hay control de pie)")

# postura 2: pie atras y arriba (rodilla doblada)
limpiar()
if pb:
    pb.location = (0.0, 0.25, 0.30) if pb.name.startswith("CTRL") else pb.location
    medir("rodilla doblada")
limpiar()

# render de las dos posturas
escena = bpy.context.scene
escena.render.resolution_x = 700
escena.render.resolution_y = 900
escena.render.image_settings.file_format = "PNG"
cam = next((o for o in bpy.data.objects if o.type == "CAMERA"), None)
if cam:
    escena.camera = cam
for nombre, loc in (("paso", (0.0, -0.35, 0.18)), ("doblada", (0.0, 0.25, 0.30))):
    limpiar()
    if pb:
        pb.location = loc
        bpy.context.view_layer.update()
    escena.render.filepath = os.path.join(SALIDA, "pierna_%s.png" % nombre)
    bpy.ops.render.render(write_still=True)
    print("   render:", escena.render.filepath)
limpiar()