"""Render FIABLE de un GLB: usa la geometria tal cual (sin el esqueleto de Blender, que al importar
glTF mete una armadura con su propia transformada y deforma la malla). Convierte Y-arriba a Z-arriba.

Uso: blender --background --python render_estatico.py -- <glb> <salida.png> [<salida2.png>]
"""
import math
import sys

import bpy
from mathutils import Matrix, Vector

a = sys.argv[sys.argv.index("--") + 1:]
ruta, salida = a[0], a[1]
salida2 = a[2] if len(a) > 2 else None

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=ruta)

objs = [o for o in bpy.data.objects if o.type == "MESH" and not o.name.startswith("Icosphere")]

# 1) hornear la transformada de cada malla en sus vertices y soltar el esqueleto: al importar glTF
#    Blender mete una armadura con su propia transformada y deforma la malla
# la piel ya es correcta (error en reposo 0.0000 medido), asi que se deja la armadura puesta
# for o in objs:
#     for m in list(o.modifiers):
#         o.modifiers.remove(m)
pass


def caja():
    mn = Vector((1e9,) * 3)
    mx = Vector((-1e9,) * 3)
    for o in objs:
        for v in o.data.vertices:
            w = o.matrix_world @ v.co
            for i in range(3):
                mn[i] = min(mn[i], w[i])
                mx[i] = max(mx[i], w[i])
    return mn, mx


mins, maxs = caja()
# el GLB viene Y-arriba: si el modelo esta tumbado, girarlo a Z-arriba
if (maxs - mins).y > (maxs - mins).z * 1.2:
    rot = Matrix.Rotation(math.radians(90), 4, "X")
    for o in objs:
        o.data.transform(rot)
    mins, maxs = caja()

centro = (mins + maxs) / 2
tam = max((maxs - mins)[i] for i in range(3))
print("BBOX", tuple(round(v, 2) for v in mins), tuple(round(v, 2) for v in maxs), "tam", round(tam, 2))

esc = bpy.context.scene
esc.render.engine = "BLENDER_EEVEE"
esc.render.resolution_x = 900
esc.render.resolution_y = 900
esc.view_settings.view_transform = "AgX"
esc.view_settings.look = "AgX - Medium High Contrast"
w = bpy.data.worlds.new("w")
w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.62, 0.63, 0.66, 1)
w.node_tree.nodes["Background"].inputs[1].default_value = 0.75
esc.world = w
for nombre, loc, en in (("key", (2, -3, 2.4), 120.0), ("fill", (-2.6, -2, 1), 55.0),
                        ("rim", (0, 3, 2), 70.0)):
    d = bpy.data.lights.new(nombre, type="AREA")
    d.energy, d.size = en, 4.0
    o = bpy.data.objects.new(nombre, d)
    esc.collection.objects.link(o)
    o.location = Vector(loc) * (tam / 1.8) + centro
    o.rotation_euler = (centro - o.location).to_track_quat("-Z", "Y").to_euler()

cd = bpy.data.cameras.new("cam")
cd.type = "ORTHO"
cd.ortho_scale = tam * 0.30
cam = bpy.data.objects.new("cam", cd)
esc.collection.objects.link(cam)
esc.camera = cam
cam.location = (centro.x, centro.y - tam * 2.0, maxs.z - tam * 0.10)
cam.rotation_euler = (math.radians(90), 0, 0)
esc.render.filepath = salida
esc.render.image_settings.file_format = "PNG"
bpy.ops.render.render(write_still=True)
print("RENDER", salida)

if salida2:
    cam.location = (centro.x, centro.y + tam * 2.0, maxs.z - tam * 0.10)
    cam.rotation_euler = (math.radians(90), 0, math.radians(180))
    esc.render.filepath = salida2
    bpy.ops.render.render(write_still=True)
    print("RENDER", salida2)