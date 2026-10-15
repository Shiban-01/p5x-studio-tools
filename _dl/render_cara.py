"""Render de primer plano de la cabeza de un GLB, desde los dos lados, para ver la cara.

Uso: blender --background --python render_cara.py -- <glb> <png_frente> <png_reves>
"""
import math
import sys

import bpy
from mathutils import Vector

a = sys.argv[sys.argv.index("--") + 1:]
ruta, salida_a, salida_b = a[0], a[1], a[2]

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=ruta)
esc = bpy.context.scene
dg = bpy.context.evaluated_depsgraph_get()

puntos = []
for o in [x for x in bpy.data.objects if x.type == "MESH"]:
    ev = o.evaluated_get(dg)
    for v in ev.to_mesh().vertices:
        puntos.append(o.matrix_world @ v.co)
    ev.to_mesh_clear()
xs = [p.x for p in puntos]
ys = [p.y for p in puntos]
zs = [p.z for p in puntos]
alto = max(zs) - min(zs)
print("BBOX (%.2f, %.2f, %.2f) (%.2f, %.2f, %.2f) alto %.2f"
      % (min(xs), min(ys), min(zs), max(xs), max(ys), max(zs), alto))
cabeza = Vector(((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, max(zs) - alto * 0.09))

mundo = bpy.data.worlds.new("m")
esc.world = mundo
mundo.use_nodes = True
mundo.node_tree.nodes["Background"].inputs[0].default_value = (0.6, 0.6, 0.62, 1)
mundo.node_tree.nodes["Background"].inputs[1].default_value = 1.6
for loc, e in (((3, -4, 4), 4.0), ((-3, -4, 3), 3.0), ((0, 4, 2), 2.5)):
    ld = bpy.data.lights.new("l", "AREA")
    ld.energy = e * 90
    ld.size = 6
    lo = bpy.data.objects.new("l", ld)
    esc.collection.objects.link(lo)
    lo.location = Vector(loc) + cabeza
    lo.rotation_euler = (cabeza - lo.location).to_track_quat("-Z", "Y").to_euler()

cd = bpy.data.cameras.new("c")
cd.type = "ORTHO"
cd.ortho_scale = alto * 0.34
cam = bpy.data.objects.new("c", cd)
esc.collection.objects.link(cam)
esc.camera = cam

esc.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in \
    [i.identifier for i in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items] else "BLENDER_EEVEE"
esc.render.resolution_x = 900
esc.render.resolution_y = 900
esc.render.film_transparent = False

for ang, salida in ((180, salida_a), (0, salida_b)):
    r = alto * 2.0
    cam.location = (cabeza.x + r * math.sin(math.radians(ang)), cabeza.y + r * math.cos(math.radians(ang)),
                    cabeza.z)
    cam.rotation_euler = (math.radians(90), 0, math.radians(ang))
    esc.render.filepath = salida
    bpy.ops.render.render(write_still=True)
    print("RENDER", salida)