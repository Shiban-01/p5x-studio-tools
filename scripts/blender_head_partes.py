
"""Renderiza la cabeza aislando mallas, para saber si alguna pieza esta desplazada o rota.

Uso: blender --background --python blender_head_partes.py -- <glb> <carpeta>
"""
import math
import os
import sys

import bpy
from mathutils import Vector

ARG = sys.argv[sys.argv.index("--") + 1:]
GLB, SAL = ARG[0], ARG[1]
os.makedirs(SAL, exist_ok=True)

for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)
bpy.ops.import_scene.gltf(filepath=GLB)
for o in list(bpy.data.objects):
    if not o.name.startswith("PC079"):
        bpy.data.objects.remove(o, do_unlink=True)

mallas = [o for o in bpy.data.objects if o.type == "MESH"]
mn = [1e9] * 3
mx = [-1e9] * 3
for o in mallas:
    for v in o.data.vertices:
        w = o.matrix_world @ v.co
        for i in range(3):
            mn[i] = min(mn[i], w[i]); mx[i] = max(mx[i], w[i])
alto = mx[2] - mn[2]
ancho = mx[0] - mn[0]
centro = [(mn[i] + mx[i]) / 2 for i in range(3)]
print("mallas en el GLB:", len(mallas))
for o in mallas:
    print("   ", o.name)

luz = bpy.data.lights.new("k", type="AREA"); luz.energy = 260; luz.size = 4
ob = bpy.data.objects.new("k", luz); bpy.context.collection.objects.link(ob)
ob.location = (1.6, -3.0, 1.3); ob.rotation_euler = (math.radians(60), 0, math.radians(28))
luz2 = bpy.data.lights.new("f", type="AREA"); luz2.energy = 140; luz2.size = 5
ob2 = bpy.data.objects.new("f", luz2); bpy.context.collection.objects.link(ob2)
ob2.location = (-2.2, -2.6, 0.4); ob2.rotation_euler = (math.radians(78), 0, math.radians(-40))

cam_d = bpy.data.cameras.new("c"); cam = bpy.data.objects.new("c", cam_d)
bpy.context.collection.objects.link(cam)
bpy.context.scene.camera = cam
esc = bpy.context.scene
disponibles = [i.identifier for i in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
esc.render.engine = next((e for e in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE") if e in disponibles),
                         disponibles[0])
esc.render.resolution_x, esc.render.resolution_y = 800, 800
esc.view_settings.view_transform = "Standard"
mundo = bpy.data.worlds.new("w"); esc.world = mundo
mundo.use_nodes = True
for n in mundo.node_tree.nodes:
    if n.type == "BACKGROUND":
        n.inputs[0].default_value = (0.30, 0.32, 0.37, 1)


def encuadrar(objetivo, orto):
    cam_d.type = "ORTHO"
    cam_d.ortho_scale = orto
    cam.location = (objetivo[0], objetivo[1] + ancho * 2.0, objetivo[2])
    d = Vector(objetivo) - cam.location
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    bpy.context.view_layer.update()


def render(nombre):
    esc.render.filepath = os.path.join(SAL, nombre)
    bpy.ops.render.render(write_still=True)
    print("render:", nombre)


def solo(patrones):
    """Deja visibles solo las mallas cuyo nombre contenga alguno de los patrones."""
    for o in mallas:
        visible = any(p in o.name for p in patrones)
        o.hide_render = not visible
        o.hide_viewport = not visible


def name_of(*claves):
    return [o.name for o in mallas if any(c in o.name for c in claves)]


cuerpo = name_of("body_MALLA")
cara = name_of("bs_PC079_01_face_MALLA")
ojo = name_of("bs_PC079_01_eye_MALLA")
parpado = name_of("bs_PC079_01_eyelid_MALLA")
pelo = name_of("hair_MALLA")
z_cab = mx[2] - alto * 0.085
objetivo = (centro[0], centro[1], z_cab)

for etiqueta, patrones in (("todos", [""]),
                           ("cuerpo", ["body_MALLA"]),
                           ("cara_ojos_parpado", ["bs_PC079_01"]),
                           ("pelo", ["hair_MALLA"]),
                           ("sin_pelo", ["body_MALLA", "bs_PC079_01"])):
    solo(patrones)
    encuadrar(objetivo, alto * 0.24)
    render("cabeza_" + etiqueta + ".png")
print("TERMINADO")
