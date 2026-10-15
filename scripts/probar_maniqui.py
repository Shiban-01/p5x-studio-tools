"""Pone una pose al maniqui y la renderiza, para comprobar que la malla le sigue bien.

Uso: blender --background --python probar_maniqui.py -- <blend> <png_salida>
"""
import math
import os
import sys

import bpy

from mathutils import Vector

bpy.ops.wm.open_mainfile(filepath=sys.argv[sys.argv.index("--") + 1])
salida = sys.argv[sys.argv.index("--") + 2]
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
mallas = [o for o in bpy.data.objects if o.type == "MESH"]

# ---------------------------------------------------------------- pose de prueba
G = math.radians
POSE = {
    "Columna_1":  (G(8), 0, G(-6)),
    "Columna_2":  (G(6), 0, G(-4)),
    "Pecho":      (G(4), 0, G(-3)),
    "Cabeza":     (G(-6), G(18), G(4)),
    "Cuello":     (G(4), G(8), 0),
    "Hombro_Der": (0, 0, G(-10)),
    "Brazo_Der":  (G(-70), 0, G(-20)),        # brazo arriba y adelante: apuntando
    "Antebrazo_Der": (G(-70), 0, 0),
    "Mano_Der":   (0, G(-15), 0),
    "Hombro_Izq": (0, 0, G(8)),
    "Brazo_Izq":  (G(35), 0, G(25)),          # el otro brazo hacia atras
    "Antebrazo_Izq": (G(-40), 0, 0),
    "Muslo_Izq":  (G(-35), 0, 0),             # pierna adelantada
    "Pantorrilla_Izq": (G(45), 0, 0),
    "Pie_Izq":    (G(-20), 0, 0),
    "Muslo_Der":  (G(12), 0, 0),              # la otra de apoyo
    "Pantorrilla_Der": (G(15), 0, 0),
}
for hueso in [b.name for b in arm.data.bones if b.name.startswith("Dedo")]:
    POSE[hueso] = (G(35), 0, 0)               # puño flojo
for nombre, (rx, ry, rz) in POSE.items():
    if nombre in arm.pose.bones:
        arm.pose.bones[nombre].rotation_mode = "XYZ"
        arm.pose.bones[nombre].rotation_euler = (rx, ry, rz)
bpy.context.view_layer.update()

# cuanto ha viajado cada malla respecto al reposo: si el pelo va con la cabeza y la falda con la
# cadera, se mueven; si algo se quedara clavado, el desplazamiento seria cero
print("=== desplazamiento de cada malla al posar ===")
for ob in mallas:
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    m = ev.to_mesh()
    centro = sum((ob.matrix_world @ v.co for v in m.vertices), Vector()) / max(len(m.vertices), 1)
    ev.to_mesh_clear()
    print("   %-18s centro %s" % (ob.name, ["%+.2f" % c for c in centro]))

# ---------------------------------------------------------------- camara y luz
todo = [Vector(c) for ob in mallas for c in ob.bound_box]
minx = min(c.x for c in todo); maxx = max(c.x for c in todo)
miny = min(c.y for c in todo); maxy = max(c.y for c in todo)
minz = min(c.z for c in todo); maxz = max(c.z for c in todo)
alto = maxz - minz
centro = Vector(((minx + maxx) / 2, (miny + maxy) / 2, (minz + maxz) / 2))
cam = bpy.data.objects.get("camara")
if cam is None:                                    # ya esta en la escena: no hay que vincularla
    cam = bpy.data.objects.new("camara", bpy.data.cameras.new("camara"))
    bpy.context.collection.objects.link(cam)
cam.location = centro + Vector((alto * 0.9, -alto * 1.7, alto * 0.25))
direccion = centro - cam.location
cam.rotation_euler = direccion.to_track_quat("-Z", "Y").to_euler()
bpy.context.scene.camera = cam

esc = bpy.context.scene
esc.render.resolution_x, esc.render.resolution_y, esc.render.resolution_percentage = 800, 1100, 100
esc.render.film_transparent = False
try:
    esc.render.engine = "BLENDER_EEVEE_NEXT"
except TypeError:
    esc.render.engine = "BLENDER_EEVEE"
esc.render.image_settings.file_format = "PNG"
esc.render.filepath = salida
os.makedirs(os.path.dirname(salida), exist_ok=True)
bpy.ops.render.render(write_still=True)
print("render:", salida, os.path.getsize(salida) // 1024, "KB")
