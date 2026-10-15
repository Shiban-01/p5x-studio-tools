"""Renderiza a Kotone con el toon shader calcando la pose de la referencia, con weapon_05.

Parte de media/toon_blender/kotone_toon.blend, que ya trae los materiales P5X_Toon y Freestyle.
Aplica la pose (tabla editable abajo), coloca weapon_05 de modo que su asta pase por las dos manos
(que es lo que hace la referencia), encuadra con camara baja y guarda el render y su silueta.
"""
import math
import os
import sys

import bpy
from mathutils import Vector, Matrix

BLEND = r"C:\Users\Lukas\p5x-datamining\media\toon_blender\kotone_toon.blend"
ARMA = r"C:\Users\Lukas\p5x-datamining\kotone_shiomi\01_model\obj\weapons\weapon_05.obj"
SAL = r"C:\Users\Lukas\p5x-datamining\media\toon_pose"
os.makedirs(SAL, exist_ok=True)

# ---------------------------------------------------------------- pose (grados, ejes medidos)
POSE = [
    # tronco: giro suave y algo de inclinacion, sin abrir el cuerpo
    ("Bip01 Pelvis",     "Z",  14), ("Bip01 Pelvis",     "Y",   4),
    ("Bip01 Spine1",     "Z",  -8), ("Bip01 Spine1",     "Y",   6),
    ("Bip01 Spine2",     "Z",  -6), ("Bip01 Spine2",     "Y",   4),
    ("Bip01 L Clavicle", "X",   8),
    ("Bip01 R Clavicle", "X",   8),
    # los dos brazos bajan (X) y van al frente (Y), quedando juntos: agarran el asta
    ("Bip01 L UpperArm", "X",  95), ("Bip01 L UpperArm", "Y", -42),
    ("Bip01 L Forearm",  "Y", -48), ("Bip01 L Forearm",  "Z", -12),
    ("Bip01 R UpperArm", "X",  92), ("Bip01 R UpperArm", "Y",  38),
    ("Bip01 R Forearm",  "Y",  52), ("Bip01 R Forearm",  "Z",  10),
    # pierna izquierda: rodilla arriba, espinilla colgando
    ("Bip01 L Thigh",    "X", -70), ("Bip01 L Thigh",    "Y",   8),
    ("Bip01 L Calf",     "X",  60),
    # pierna derecha: hacia abajo, algo atras
    ("Bip01 R Thigh",    "X",  14), ("Bip01 R Calf",     "X",  16),
    # cabeza girada y algo inclinada
    ("Bip01 Head",       "Z", -22), ("Bip01 Head",       "X",  10),
]

bpy.ops.wm.open_mainfile(filepath=BLEND)
esc = bpy.context.scene
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")

# fuera la esfera suelta que arrastra el importador
for o in list(bpy.data.objects):
    if "esfera" in o.name.lower() or "sphere" in o.name.lower() or "icosphere" in o.name.lower():
        print("quitando objeto suelto:", o.name)
        bpy.data.objects.remove(o, do_unlink=True)

for b in arm.pose.bones:
    b.rotation_mode = "XYZ"
    b.rotation_euler = (0, 0, 0)
for hueso, eje, grados in POSE:
    b = arm.pose.bones.get(hueso)
    if not b:
        print("   (falta el hueso %s)" % hueso)
        continue
    r = list(b.rotation_euler)
    r["XYZ".index(eje)] += math.radians(grados)
    b.rotation_euler = r
bpy.context.view_layer.update()


def mundo(h):
    return arm.matrix_world @ arm.pose.bones[h].head


mano_l, mano_r = mundo("Bip01 L Hand"), mundo("Bip01 R Hand")
codo_l, codo_r = mundo("Bip01 L Forearm"), mundo("Bip01 R Forearm")
cabeza, pelvis = mundo("Bip01 Head"), mundo("Bip01 Pelvis")
pie_l, pie_r = mundo("Bip01 L Foot"), mundo("Bip01 R Foot")
print("\n=== pose aplicada ===")
for n, p in (("mano izq", mano_l), ("mano der", mano_r), ("codo izq", codo_l), ("codo der", codo_r),
             ("cabeza", cabeza), ("pelvis", pelvis), ("pie izq", pie_l), ("pie der", pie_r)):
    print("   %-10s (%+.3f, %+.3f, %+.3f)" % (n, p.x, p.y, p.z))

# ---------------------------------------------------------------- weapon_05 en las manos
bpy.ops.wm.obj_import(filepath=ARMA, forward_axis="Y", up_axis="Z")
arma_obj = next(o for o in bpy.data.objects if o.name.startswith("weapon_05"))
print("\narma importada: %s   vertices: %d" % (arma_obj.name, len(arma_obj.data.vertices)))

# el asta corre por el eje Z local: se orienta para que pase por las dos manos
# el filo va al extremo -Z local, asi que +Z tiene que apuntar hacia la mano izquierda
# para que la hoja quede abajo y a la izquierda, como en la referencia
direccion = (mano_l - mano_r)
if direccion.length < 1e-4:
    direccion = Vector((0, 0, 1))
direccion.normalize()
giro = Vector((0, 0, 1)).rotation_difference(direccion).to_matrix().to_4x4()
# el punto medio de las manos sera el punto del asta que queda entre ellas
medio = (mano_l + mano_r) / 2
arma_obj.matrix_world = Matrix.Translation(medio) @ giro
bpy.context.view_layer.update()
print("arma: centro en (%+.3f, %+.3f, %+.3f), direccion (%+.2f, %+.2f, %+.2f)"
      % (medio.x, medio.y, medio.z, direccion.x, direccion.y, direccion.z))

# ---------------------------------------------------------------- camara: contrapicado, cuerpo entero
mn = Vector((1e9,) * 3)
mx = Vector((-1e9,) * 3)
dg = bpy.context.evaluated_depsgraph_get()
for o in bpy.data.objects:
    if o.type != "MESH" or o.name.endswith("_contorno") or o is arma_obj:
        continue
    ev = o.evaluated_get(dg)
    for v in ev.data.vertices:
        w = ev.matrix_world @ v.co
        for k in range(3):
            mn[k] = min(mn[k], w[k])
            mx[k] = max(mx[k], w[k])
centro = (mn + mx) / 2
alto = max(mx.z - mn.z, 0.5)
ancho = max(mx.x - mn.x, 0.5)
print("\nfigura: alto %.2f m  ancho %.2f m  centro (%.2f, %.2f, %.2f)" % (alto, ancho, centro.x, centro.y, centro.z))

cam = esc.camera or bpy.data.objects.new("camara", bpy.data.cameras.new("camara"))
esc.camera = cam
cam.data.lens = 60.0
objetivo = Vector((centro.x, centro.y, centro.z + alto * 0.05))
dist = (alto / (2 * math.tan(math.radians(40) / 2))) * 1.25
# contrapicado: camara por debajo del centro, mirando hacia arriba
cam.location = (objetivo.x + dist * 0.10, objetivo.y - dist * 0.95, objetivo.z - alto * 0.35)
cam.rotation_euler = (objetivo - Vector(cam.location)).to_track_quat("-Z", "Y").to_euler()

esc.render.resolution_x = 704
esc.render.resolution_y = 1020
esc.render.film_transparent = True
esc.render.filepath = os.path.join(SAL, "pose_00.png")
bpy.ops.render.render(write_still=True)
print("render:", esc.render.filepath)

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(SAL, "kotone_pose.blend"))
print("LISTO")