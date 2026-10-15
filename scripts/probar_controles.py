"""Posa el modelo con los CONTROLES reales del rig de artistas y mide + renderiza.

Igual que posaria una persona: se mueve CTRL_Pie_Izq (pie) y CTRL_Mano_Izq (mano), y se comprueba que
la rodilla dobla a la altura de la rodilla, que el codo acompana y que la piel no se rasga.

Uso: blender --background --python probar_controles.py -- <blend> <carpeta_salida>
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


def malla():
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    ev = cuerpo.evaluated_get(dg)
    m = ev.to_mesh()
    v = [ev.matrix_world @ x.co for x in m.vertices]
    e = [(a.vertices[0], a.vertices[1]) for a in m.edges]
    ev.to_mesh_clear()
    return v, e


def limpiar():
    for pb in arm.pose.bones:
        pb.rotation_mode = "XYZ"
        pb.rotation_euler = (0, 0, 0)
        pb.location = (0, 0, 0)
    bpy.context.view_layer.update()


limpiar()
base_v, aristas = malla()
largos0 = [(base_v[a] - base_v[b]).length for a, b in aristas]


def medir(etiqueta):
    v, _ = malla()
    rotas, peor = 0, 0.0
    for (a, b), l0 in zip(aristas, largos0):
        if l0 < 0.003:
            continue
        l1 = (v[a] - v[b]).length
        if l1 > l0 * 1.10:
            rotas += 1
            peor = max(peor, l1 - l0)
    tot = sum(1 for l in largos0 if l > 0.003)
    def p(n):
        pb = arm.pose.bones[n]
        return arm.matrix_world @ pb.head
    rodilla = p("Bip01 L Calf")
    tobillo = p("Bip01 L Foot")
    muneca = p("Bip01 L Hand")
    print("   %-18s rodilla z=%.3f | tobillo z=%.3f y=%+.3f | muneca z=%.3f | piel rota=%d/%d peor=%.1f mm"
          % (etiqueta, rodilla.z, tobillo.z, tobillo.y, muneca.z, rotas, tot, peor * 1000))


print("=== posturas con los controles reales ===")
limpiar()
medir("reposo")

cam = next((o for o in bpy.data.objects if o.type == "CAMERA"), None)
centro = sum(base_v, Vector()) / len(base_v)

posturas = [
    ("pierna_doblada", {"CTRL_Pie_Izq": (0.0, 0.10, 0.35)}, "de frente"),
    ("paso", {"CTRL_Pie_Izq": (0.0, -0.28, 0.12)}, "de frente"),
    ("brazo_arriba", {"CTRL_Mano_Izq": (0.0, 0.0, 0.45)}, "de frente"),
]
for nombre, cambios, vista in posturas:
    limpiar()
    for control, desplazamiento in cambios.items():
        if control in arm.pose.bones:
            arm.pose.bones[control].location = desplazamiento
        else:
            print("   (falta el control %s)" % control)
    bpy.context.view_layer.update()
    medir(nombre)
    if nombre in ("pierna_doblada", "paso") and cam:
        cam.location = (0.0, -2.6, centro.z)
        cam.rotation_euler = (math.radians(90), 0, 0)
        bpy.context.scene.camera = cam
        bpy.context.scene.render.resolution_x = 700
        bpy.context.scene.render.resolution_y = 900
        bpy.context.scene.render.image_settings.file_format = "PNG"
        bpy.context.scene.render.filepath = os.path.join(SALIDA, "control_%s.png" % nombre)
        bpy.ops.render.render(write_still=True)
limpiar()
print("renders en:", SALIDA)