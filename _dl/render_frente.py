"""Render frontal (o por angulo) de un GLB, cuerpo entero o primer plano de la cara.

Uso:
  blender --background --python render_frente.py -- <glb> <png> [cuerpo|cara] [yaw_grados]

El frente de estos modelos, tras el importador glTF de Blender, mira a +Y: el yaw=180 pone la
camara delante. El primer plano de cara encuadra la franja superior de la caja envolvente.
"""
import math
import sys

import bpy
from mathutils import Vector

a = sys.argv[sys.argv.index("--") + 1:]
entrada, salida = a[0], a[1]
modo = a[2] if len(a) > 2 else "cuerpo"
yaw = float(a[3]) if len(a) > 3 else 180.0

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

if modo == "cara":
    # franja superior ~14% de la altura: la cabeza
    objetivo = Vector((centro.x, centro.y, maxs.z - tam * 0.075))
    d = tam * 0.42
    lens = 65
else:
    objetivo = centro
    d = tam * 1.75
    lens = 55

ang = math.radians(yaw)
cam_data = bpy.data.cameras.new("cam")
cam = bpy.data.objects.new("cam", cam_data)
bpy.context.scene.collection.objects.link(cam)
cam.location = (objetivo.x + d * math.sin(ang), objetivo.y - d * math.cos(ang), objetivo.z + tam * 0.03)
direc = objetivo - cam.location
cam.rotation_euler = direc.to_track_quat("-Z", "Y").to_euler()
cam_data.lens = lens
bpy.context.scene.camera = cam

# luz frontal (desde la camara) + relleno
for (rx, ry, rz), e in (((60, 0, yaw + 30), 3.5), ((65, 0, yaw - 130), 1.6)):
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
esc.render.resolution_x = 900
esc.render.resolution_y = 1100 if modo == "cuerpo" else 900
esc.render.film_transparent = False
esc.render.filepath = salida
esc.render.image_settings.file_format = "PNG"
esc.world = bpy.data.worlds.new("w")
esc.world.use_nodes = True
esc.world.node_tree.nodes["Background"].inputs[0].default_value = (0.12, 0.12, 0.15, 1)
bpy.ops.render.render(write_still=True)
print("RENDER=%s" % salida)