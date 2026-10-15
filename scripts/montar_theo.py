"""Monta el busto de N040 (Theo) en Blender: cara, ojos y pelo con sus texturas, y lo renderiza.

Las mallas vienen de AssetStudioModCLI en OBJ y ya estan todas en el mismo espacio (la cara ocupa
Z 1,54-1,72 m, el pelo por encima, los ojos dentro), asi que no hay que colocar nada: solo importar,
dar material y mirar.

Uso: blender --background --python montar_theo.py -- <carpeta_crudo> <salida.blend> <preview.png>
"""
import math
import os
import sys

import bpy

from mathutils import Vector

crudo, blend, png = sys.argv[sys.argv.index("--") + 1: sys.argv.index("--") + 4]

PIEZAS = [
    ("cara_retrato/N040_face_wholeexport_rig_N040_face.obj", "texturas/N040_body_face_bc.png", "Cara"),
    ("cara_retrato/N040_face_wholeexport_rig_N040_eye.obj", "texturas/N040_body_eye_bc.png", "Ojo"),
    ("cara_retrato/N040_face_wholeexport_rig_N040_eyelid.obj", "texturas/N040_body_eye_bc.png",
     "Parpado"),
    ("pelo/N040_hair_wholeexport_rig_N040_hair.obj", "pelo/N040_body_hair_bc.png", "Pelo"),
]

# escena limpia
bpy.ops.wm.read_factory_settings(use_empty=True)
escena = bpy.context.scene


def material(nombre, textura):
    mat = bpy.data.materials.new(nombre)
    mat.use_nodes = True
    nodos = mat.node_tree.nodes
    nodos.clear()
    salida = nodos.new("ShaderNodeOutputMaterial")
    principled = nodos.new("ShaderNodeBsdfPrincipled")
    principled.inputs["Roughness"].default_value = 0.6
    mat.node_tree.links.new(principled.outputs["BSDF"], salida.inputs["Surface"])
    if os.path.exists(textura):
        tex = nodos.new("ShaderNodeTexImage")
        tex.image = bpy.data.images.load(textura)
        tex.interpolation = "Closest"
        mat.node_tree.links.new(tex.outputs["Color"], principled.inputs["Base Color"])
        # la V va al reves en las texturas del juego
        mapa = nodos.new("ShaderNodeMapping")
        mapa.inputs["Scale"].default_value[1] = -1.0
        coord = nodos.new("ShaderNodeTexCoord")
        mat.node_tree.links.new(coord.outputs["UV"], mapa.inputs["Vector"])
        mat.node_tree.links.new(mapa.outputs["Vector"], tex.inputs["Vector"])
    return mat


totales = {"verts": 0, "caras": 0}
for rel, textura, nombre in PIEZAS:
    ruta = os.path.join(crudo, rel.replace("/", os.sep))
    if not os.path.exists(ruta):
        print("   [!] falta %s" % ruta)
        continue
    antes = set(bpy.data.objects)
    # El OBJ de AssetStudio ya viene Z-arriba (el pelo esta en Z 1,54-1,76). Por defecto el importador
    # asume Y-arriba y tumba el modelo: hay que decirle los ejes del fichero.
    bpy.ops.wm.obj_import(filepath=ruta, forward_axis="Y", up_axis="Z")
    nuevo = [o for o in bpy.data.objects if o not in antes][0]
    nuevo.name = nombre
    nuevo.data.materials.append(material(nombre, os.path.join(crudo, textura.replace("/", os.sep))))
    totales["verts"] += len(nuevo.data.vertices)
    totales["caras"] += len(nuevo.data.polygons)
    print("   %-9s %6d verts %6d caras" % (nombre, len(nuevo.data.vertices), len(nuevo.data.polygons)))

print("   TOTAL     %6d verts %6d caras" % (totales["verts"], totales["caras"]))

# Los OBJ vienen en Y-arriba (convencion de Unity). Se mide donde ha caido la malla y se pone derecha,
# en vez de suponerlo: la primera version puso la camara a Z-arriba y el render salio vacio.
minimos = Vector((1e9, 1e9, 1e9))
maximos = Vector((-1e9, -1e9, -1e9))
for objeto in bpy.data.objects:
    if objeto.type != "MESH":
        continue
    for esquina in objeto.bound_box:
        punto = objeto.matrix_world @ Vector(esquina)
        for i in range(3):
            minimos[i] = min(minimos[i], punto[i])
            maximos[i] = max(maximos[i], punto[i])
extremos = maximos - minimos
print("   limites antes de enderezar: min %s max %s"
      % ([round(v, 3) for v in minimos], [round(v, 3) for v in maximos]))
if extremos.z < extremos.y * 0.5:
    print("   el modelo esta tumbado (Y-arriba): se gira a Z-arriba")
    for objeto in [o for o in bpy.data.objects if o.type == "MESH"]:
        objeto.rotation_euler.x = math.radians(-90)
        objeto.select_set(True)
    bpy.context.view_layer.objects.active = [o for o in bpy.data.objects if o.type == "MESH"][0]
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    for objeto in [o for o in bpy.data.objects if o.type == "MESH"]:
        objeto.select_set(False)
    minimos = Vector((1e9, 1e9, 1e9))
    maximos = Vector((-1e9, -1e9, -1e9))
    for objeto in bpy.data.objects:
        if objeto.type != "MESH":
            continue
        for esquina in objeto.bound_box:
            punto = objeto.matrix_world @ Vector(esquina)
            for i in range(3):
                minimos[i] = min(minimos[i], punto[i])
                maximos[i] = max(maximos[i], punto[i])
    print("   limites ya enderezados:      min %s max %s"
          % ([round(v, 3) for v in minimos], [round(v, 3) for v in maximos]))

# luz y camara
mundo = bpy.data.worlds.new("mundo")
mundo.use_nodes = True
mundo.node_tree.nodes["Background"].inputs[0].default_value = (0.05, 0.05, 0.06, 1)
mundo.node_tree.nodes["Background"].inputs[1].default_value = 0.6
escena.world = mundo
for direccion, energia in (((0.4, -0.8, 0.6), 4.0), ((-0.6, -0.3, 0.2), 1.5), ((0, 1, 0.3), 1.2)):
    luz = bpy.data.objects.new("luz", bpy.data.lights.new("luz", type="SUN"))
    luz.data.energy = energia
    luz.rotation_euler = Vector(direccion).to_track_quat("Z", "Y").to_euler()
    escena.collection.objects.link(luz)

centro = Vector((0.0, 0.02, 1.65))
cam = bpy.data.objects.new("camara", bpy.data.cameras.new("camara"))
escena.collection.objects.link(cam)
escena.camera = cam
escena.render.resolution_x, escena.render.resolution_y = 800, 900
try:
    escena.render.engine = "BLENDER_EEVEE_NEXT"
except TypeError:
    escena.render.engine = "BLENDER_EEVEE"
escena.render.film_transparent = False

for etiqueta, ubicacion, distancia in (("frente", Vector((0.0, -1.0, 0.10)), 0.62),
                                       ("trescuartos", Vector((0.75, -0.85, 0.25)), 0.66)):
    cam.location = centro + ubicacion.normalized() * distancia
    cam.rotation_euler = (centro - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = 70
    escena.render.filepath = png.replace(".png", "_%s.png" % etiqueta)
    bpy.ops.render.render(write_still=True)
    print("   render %-11s -> %s (%d KB)" % (etiqueta, escena.render.filepath,
                                             os.path.getsize(escena.render.filepath) // 1024))

bpy.ops.wm.save_as_mainfile(filepath=blend)
print("   guardado:", blend)
bpy.ops.export_scene.gltf(filepath=blend.replace(".blend", ".glb"), export_format="GLB")
print("   glb:", blend.replace(".blend", ".glb"))