"""Saca un preview del PMX con la rodilla doblada, para que se vea que el IK dobla donde debe.

Uso: blender --background --python preview_rodilla_pmx.py -- <pmx> <png_salida>
"""
import math
import sys

import bpy
from mathutils import Vector

ARG = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
PMX, PNG = ARG[0], ARG[1]
bpy.ops.preferences.addon_enable(module="bl_ext.user_default.mmd_tools")
bpy.ops.mmd_tools.import_model(filepath=PMX, scale=1.0, types={"MESH", "ARMATURE", "MORPHS", "DISPLAY"},
                               clean_model=False, rename_bones=False)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
mallas = [o for o in bpy.data.objects if o.type == "MESH"]

# doblar la rodilla con el IK (el personaje mira a +Y en el import de mmd_tools)
ik = next((pb for pb in arm.pose.bones if "足ＩＫ" in pb.name and "右" in pb.name), None)
if ik:
    ik.location = (0.0, -3.4, -2.0)
bpy.context.view_layer.update()

# encuadre a partir de la malla ya posada
dg = bpy.context.evaluated_depsgraph_get()
xs, ys, zs = [], [], []
for o in mallas:
    ev = o.evaluated_get(dg)
    m = ev.to_mesh()
    for v in m.vertices:
        w = ev.matrix_world @ v.co
        xs.append(w.x); ys.append(w.y); zs.append(w.z)
    ev.to_mesh_clear()
centro = Vector(((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, (min(zs) + max(zs)) / 2))
alto = max(zs) - min(zs)
print("modelo: alto %.2f | centro (%.1f, %.1f, %.1f)" % (alto, centro.x, centro.y, centro.z))

cam_data = bpy.data.cameras.new("CamPreview")
cam = bpy.data.objects.new("CamPreview", cam_data)
bpy.context.scene.collection.objects.link(cam)
# vista de tres cuartos desde el lado izquierdo: es donde mejor se ve el doblez de la rodilla
cam.location = (alto * 1.5, -alto * 1.1, centro.z + alto * 0.08)
direccion = centro - cam.location
cam.rotation_euler = direccion.to_track_quat("-Z", "Y").to_euler()

escena = bpy.context.scene
escena.camera = cam
escena.render.resolution_x, escena.render.resolution_y = 640, 900
escena.render.image_settings.file_format = "PNG"
escena.render.filepath = PNG
bpy.ops.render.render(write_still=True)
print("render:", PNG)