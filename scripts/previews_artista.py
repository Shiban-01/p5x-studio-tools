"""Regenera los previews del paquete de artistas con el material ya corregido (sin doblar la textura).

Dos posturas x dos vistas, con los CONTROLES reales del rig (CTRL_Pie_Izq, CTRL_Mano_Izq), igual que
los generaba render_ik.py, y con las mismas medidas de desgarro de piel.

Uso: blender --background --python previews_artista.py -- <blend> <carpeta>
"""
import math
import os
import sys

import bpy
from mathutils import Vector

ARG = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
BLEND, SAL = ARG[0], ARG[1]
os.makedirs(SAL, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=BLEND)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
obj = bpy.data.objects["Kotone_Cuerpo"]


def evaluado():
    bpy.context.view_layer.update()
    ev = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    m = ev.to_mesh()
    co = [ev.matrix_world @ v.co for v in m.vertices]
    ar = [(e.vertices[0], e.vertices[1]) for e in m.edges]
    ev.to_mesh_clear()
    return co, ar


def limpiar():
    for pb in arm.pose.bones:
        pb.rotation_mode = "XYZ"
        pb.rotation_euler = (0, 0, 0)
        pb.location = (0, 0, 0)
    bpy.context.view_layer.update()


limpiar()
co0, aristas = evaluado()
largos0 = [(co0[a] - co0[b]).length for a, b in aristas]
alto = max(v.z for v in co0) - min(v.z for v in co0)
centro = sum(co0, Vector()) / len(co0)


def desgarro():
    co, _ = evaluado()
    rotas, peor = 0, 0.0
    for (a, b), l0 in zip(aristas, largos0):
        if l0 < 0.003:
            continue
        l1 = (co[a] - co[b]).length
        if l1 > l0 * 1.10:
            rotas += 1
            peor = max(peor, l1 - l0)
    return rotas, sum(1 for l in largos0 if l > 0.003), peor


cam = next((o for o in bpy.data.objects if o.type == "CAMERA"), None)
if cam is None:
    cd = bpy.data.cameras.new("CamPreview")
    cam = bpy.data.objects.new("CamPreview", cd)
    bpy.context.scene.collection.objects.link(cam)
escena = bpy.context.scene
escena.camera = cam
escena.render.resolution_x, escena.render.resolution_y = 620, 900
escena.render.image_settings.file_format = "PNG"


def encuadrar(tres_cuartos):
    if tres_cuartos:
        cam.location = (alto * 1.05, -alto * 1.55, centro.z + alto * 0.10)
    else:
        cam.location = (0.0, -alto * 1.75, centro.z + alto * 0.03)
    cam.rotation_euler = (centro - cam.location).to_track_quat("-Z", "Y").to_euler()


def render(nombre, anotar):
    desgarro_piel = desgarro()
    print("   %-28s aristas danadas %d/%d (peor %.1f mm)"
          % (nombre, desgarro_piel[0], desgarro_piel[1], desgarro_piel[2] * 1000))
    escena.render.filepath = os.path.join(SAL, nombre)
    bpy.ops.render.render(write_still=True)


print("=== previews con el material corregido ===")
limpiar()
for nombre, tc in (("01_reposo_frente.png", False), ("02_reposo_trescuartos.png", True)):
    limpiar()
    encuadrar(tc)
    render(nombre, False)

# la misma pose que usaba render_ik.py: pie arriba/adelante y mano arriba
limpiar()
if "CTRL_Pie_Izq" in arm.pose.bones:
    arm.pose.bones["CTRL_Pie_Izq"].location = (0.06, -0.16, 0.34)
if "CTRL_Mano_Izq" in arm.pose.bones:
    arm.pose.bones["CTRL_Mano_Izq"].location = (-0.22, 0.0, 0.30)
bpy.context.view_layer.update()
for nombre, tc in (("03_pose_ik_frente.png", False), ("04_pose_ik_trescuartos.png", True)):
    encuadrar(tc)
    render(nombre, True)
limpiar()
print("listo:", SAL)