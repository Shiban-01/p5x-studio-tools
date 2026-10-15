"""Render decente de un GLB/FBX: camara ortografica de frente, tres luces y fondo claro.

Uso: blender --background --python render_bueno.py -- --mode glb <fichero> <salida.png> [<salida2.png>]
"""
import math
import os
import sys

import bpy
from mathutils import Vector


def _args():
    a = sys.argv[sys.argv.index("--") + 1:]
    modo, ruta, salida, salida2 = "glb", None, None, None
    i = 0
    while i < len(a):
        if a[i] == "--mode":
            i += 1
            modo = a[i]
        elif a[i] == "--out":
            i += 1
            salida = a[i]
        elif a[i] == "--out2":
            i += 1
            salida2 = a[i]
        else:
            ruta = a[i]
        i += 1
    return modo, ruta, salida, salida2


def main():
    modo, ruta, salida, salida2 = _args()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if modo == "glb":
        bpy.ops.import_scene.gltf(filepath=ruta)
        for o in list(bpy.data.objects):
            if any(c.name == "glTF_not_exported" for c in o.users_collection):
                bpy.data.objects.remove(o, do_unlink=True)
    else:
        bpy.ops.import_scene.fbx(filepath=ruta)

    for o in bpy.data.objects:
        if o.type == "MESH":
            if o.data.materials:
                for mat in o.data.materials:
                    if mat and mat.use_nodes:
                        for n in mat.node_tree.nodes:
                            if n.type == "TEX_IMAGE" and n.image:
                                n.image.alpha_mode = "NONE"

    objetos = [o for o in bpy.data.objects if o.type == "MESH"]
    mins = Vector((1e9, 1e9, 1e9))
    maxs = Vector((-1e9, -1e9, -1e9))
    for o in objetos:
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            for i in range(3):
                mins[i] = min(mins[i], w[i])
                maxs[i] = max(maxs[i], w[i])
    centro = (mins + maxs) / 2
    tam = max((maxs - mins)[i] for i in range(3))
    print("BBOX mins=%s maxs=%s tam=%.3f" % (tuple(round(v, 2) for v in mins),
                                             tuple(round(v, 2) for v in maxs), tam))

    esc = bpy.context.scene
    esc.render.engine = "BLENDER_EEVEE"
    esc.render.resolution_x = 900
    esc.render.resolution_y = 1300
    esc.render.film_transparent = False
    esc.view_settings.view_transform = "Standard"

    mundo = bpy.data.worlds.new("w")
    mundo.use_nodes = True
    mundo.node_tree.nodes["Background"].inputs[0].default_value = (0.62, 0.63, 0.66, 1)
    mundo.node_tree.nodes["Background"].inputs[1].default_value = 1.6
    esc.world = mundo

    for nombre, loc, energia in (("key", (2.0, -3.0, 2.4), 260.0),
                                 ("fill", (-2.6, -2.0, 1.0), 120.0),
                                 ("rim", (0.0, 3.0, 2.0), 150.0)):
        d = bpy.data.lights.new(nombre, type="AREA")
        d.energy = energia
        d.size = 4.0
        o = bpy.data.objects.new(nombre, d)
        esc.collection.objects.link(o)
        o.location = Vector(loc) * (tam / 1.8) + Vector((centro.x, centro.y, centro.z))
        direccion = Vector((centro.x, centro.y, centro.z)) - o.location
        o.rotation_euler = direccion.to_track_quat("-Z", "Y").to_euler()

    datos = bpy.data.cameras.new("cam")
    datos.type = "ORTHO"
    datos.ortho_scale = tam * 1.15
    cam = bpy.data.objects.new("cam", datos)
    esc.collection.objects.link(cam)
    esc.camera = cam
    cam.location = (centro.x, centro.y - tam * 3.0, centro.z)
    cam.rotation_euler = (math.radians(90), 0, 0)

    esc.render.filepath = salida
    esc.render.image_settings.file_format = "PNG"
    bpy.ops.render.render(write_still=True)
    print("RENDER=%s" % salida)

    if salida2:
        cam.location = (centro.x + tam * 2.1, centro.y - tam * 2.1, centro.z + tam * 0.15)
        cam.rotation_euler = (math.radians(87), 0, math.radians(45))
        esc.render.filepath = salida2
        bpy.ops.render.render(write_still=True)
        print("RENDER=%s" % salida2)


if __name__ == "__main__":
    main()