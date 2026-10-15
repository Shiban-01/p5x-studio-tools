"""Render 3/4 de un GLB, encuadrado, para ver si el modelo se ve bien montado."""
import math
import sys

import bpy
from mathutils import Vector

a = sys.argv[sys.argv.index("--") + 1:]
entrada, salida = a[0], a[1]
giro = float(a[2]) if len(a) > 2 else 35.0

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=entrada)
for o in list(bpy.data.objects):
    if any(c.name == "glTF_not_exported" for c in o.users_collection):
        bpy.data.objects.remove(o, do_unlink=True)

objs = [o for o in bpy.data.objects if o.type == "MESH"]
mins = Vector((1e9,) * 3)
maxs = Vector((-1e9,) * 3)
for o in objs:
    for c in o.bound_box:
        w = o.matrix_world @ Vector(c)
        for i in range(3):
            mins[i] = min(mins[i], w[i])
            maxs[i] = max(maxs[i], w[i])
centro = (mins + maxs) / 2
tam = max(maxs - mins)

cam_data = bpy.data.cameras.new("cam")
cam = bpy.data.objects.new("cam", cam_data)
bpy.context.scene.collection.objects.link(cam)
ang = math.radians(giro)
d = tam * 1.7
cam.location = (centro.x + d * math.sin(ang), centro.y - d * math.cos(ang), centro.z + tam * 0.1)
direc = centro - cam.location
cam.rotation_euler = direc.to_track_quat("-Z", "Y").to_euler()
cam_data.lens = 60
bpy.context.scene.camera = cam

for (rx, ry, rz), e in (((55, 0, 35), 3.0), ((60, 0, -120), 1.5)):
    luz = bpy.data.lights.new("l", type="SUN")
    luz.energy = e
    lo = bpy.data.objects.new("l", luz)
    bpy.context.scene.collection.objects.link(lo)
    lo.rotation_euler = (math.radians(rx), math.radians(ry), math.radians(rz))

esc = bpy.context.scene
for motor in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
    try:
        esc.render.engine = motor
        break
    except Exception:
        continue
esc.render.resolution_x = 800
esc.render.resolution_y = 1000
esc.render.film_transparent = False
esc.render.filepath = salida
esc.render.image_settings.file_format = "PNG"
esc.world = bpy.data.worlds.new("w")
esc.world.use_nodes = True
esc.world.node_tree.nodes["Background"].inputs[0].default_value = (0.12, 0.12, 0.15, 1)
bpy.ops.render.render(write_still=True)
print("RENDER=%s" % salida)