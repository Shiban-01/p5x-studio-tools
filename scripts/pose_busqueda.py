"""Coloca los brazos por busqueda: encuentra los angulos que llevan cada mano a su punto objetivo.

Los objetivos salen de medir la referencia (manos a ~25 cm una de otra, sobre una linea a ~53
grados, las dos hacia el lado derecho de ella, con las piernas al lado contrario). Se prueban
angulos de hombro y codo y se elige la combinacion que minimiza el error, sin renderizar: solo
cinematica directa, asi que es rapido.
"""
import itertools
import math
import os
import sys

import bpy
from mathutils import Vector

BLEND = r"C:\Users\Lukas\p5x-datamining\media\toon_blender\kotone_toon.blend"
SAL = r"C:\Users\Lukas\p5x-datamining\media\toon_pose"
os.makedirs(SAL, exist_ok=True)

# objetivo de cada mano en metros, en el espacio del modelo (x+ = su izquierda, y- = delante, z = arriba)
OBJ_L = Vector((-0.05, -0.30, 1.25))     # mano alta, cruzando al lado derecho
OBJ_R = Vector((-0.20, -0.30, 1.05))     # mano baja

# tronco y piernas: fijos, la busqueda solo toca los brazos
FIJO = [
    ("Bip01 Pelvis",     "Z",  30), ("Bip01 Pelvis",     "Y",   6),
    ("Bip01 Spine1",     "Z", -22), ("Bip01 Spine1",     "Y",   8),
    ("Bip01 Spine2",     "Z", -16), ("Bip01 Spine2",     "Y",   6),
    ("Bip01 L Thigh",    "X", -55), ("Bip01 L Thigh",    "Z",  18),
    ("Bip01 L Calf",     "X",  55),
    ("Bip01 R Thigh",    "X",  10), ("Bip01 R Thigh",    "Z", -12),
    ("Bip01 R Calf",     "X",  20),
    ("Bip01 Head",       "Z", -18), ("Bip01 Head",       "X",   8),
]

bpy.ops.wm.open_mainfile(filepath=BLEND)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
for o in list(bpy.data.objects):
    if "esfera" in o.name.lower():
        bpy.data.objects.remove(o, do_unlink=True)


def limpiar():
    for b in arm.pose.bones:
        b.rotation_mode = "XYZ"
        b.rotation_euler = (0, 0, 0)
    bpy.context.view_layer.update()


def aplicar(lista):
    limpiar()
    for hueso, eje, grados in lista:
        b = arm.pose.bones.get(hueso)
        if not b:
            continue
        r = list(b.rotation_euler)
        r["XYZ".index(eje)] += math.radians(grados)
        b.rotation_euler = r
    bpy.context.view_layer.update()


def mano(nombre):
    return arm.matrix_world @ arm.pose.bones[nombre].head


# --- busqueda del brazo izquierdo
mejor_l = (1e9, None)
for sx, sy, sz in itertools.product(range(70, 141, 10), range(-70, 11, 10), range(-40, 31, 10)):
    for fx, fy in itertools.product(range(-70, 11, 15), range(-60, 31, 15)):
        aplicar(FIJO + [("Bip01 L UpperArm", "X", sx), ("Bip01 L UpperArm", "Y", sy),
                        ("Bip01 L UpperArm", "Z", sz),
                        ("Bip01 L Forearm", "X", fx), ("Bip01 L Forearm", "Y", fy)])
        d = (mano("Bip01 L Hand") - OBJ_L).length
        if d < mejor_l[0]:
            mejor_l = (d, (sx, sy, sz, fx, fy))

mejor_r = (1e9, None)
for sx, sy, sz in itertools.product(range(70, 141, 10), range(-10, 71, 10), range(-30, 41, 10)):
    for fx, fy in itertools.product(range(-70, 11, 15), range(-30, 61, 15)):
        aplicar(FIJO + [("Bip01 R UpperArm", "X", sx), ("Bip01 R UpperArm", "Y", sy),
                        ("Bip01 R UpperArm", "Z", sz),
                        ("Bip01 R Forearm", "X", fx), ("Bip01 R Forearm", "Y", fy)])
        d = (mano("Bip01 R Hand") - OBJ_R).length
        if d < mejor_r[0]:
            mejor_r = (d, (sx, sy, sz, fx, fy))

print("=== resultado de la busqueda ===")
print("   brazo izq: error %.3f m  angulos hombro(X,Y,Z)=%d,%d,%d  codo(X,Y)=%d,%d"
      % (mejor_l[0], *mejor_l[1]))
print("   brazo der: error %.3f m  angulos hombro(X,Y,Z)=%d,%d,%d  codo(X,Y)=%d,%d"
      % (mejor_r[0], *mejor_r[1]))

sx, sy, sz, fx, fy = mejor_l[1]
BRAZO_L = [("Bip01 L UpperArm", "X", sx), ("Bip01 L UpperArm", "Y", sy), ("Bip01 L UpperArm", "Z", sz),
           ("Bip01 L Forearm", "X", fx), ("Bip01 L Forearm", "Y", fy)]
sx, sy, sz, fx, fy = mejor_r[1]
BRAZO_R = [("Bip01 R UpperArm", "X", sx), ("Bip01 R UpperArm", "Y", sy), ("Bip01 R UpperArm", "Z", sz),
           ("Bip01 R Forearm", "X", fx), ("Bip01 R Forearm", "Y", fy)]
POSE = FIJO + BRAZO_L + BRAZO_R
aplicar(POSE)

print("\n=== pose final ===")
for n in ("Bip01 L Hand", "Bip01 R Hand", "Bip01 Head", "Bip01 L Foot", "Bip01 R Foot",
          "Bip01 L Calf", "Bip01 R Calf", "Bip01 Pelvis"):
    p = arm.matrix_world @ arm.pose.bones[n].head
    print("   %-16s (%+.3f, %+.3f, %+.3f)" % (n, p.x, p.y, p.z))

# --- weapon_05: el asta pasa por las dos manos; la hoja al extremo -Z
bpy.ops.wm.obj_import(filepath=r"C:\Users\Lukas\p5x-datamining\kotone_shiomi\01_model\obj\weapons\weapon_05.obj",
                      forward_axis="Y", up_axis="Z")
w = next(o for o in bpy.data.objects if o.name.startswith("weapon_05"))
ml, mr = mano("Bip01 L Hand"), mano("Bip01 R Hand")
dirv = (mr - ml)
dirv.normalize()
giro = Vector((0, 0, 1)).rotation_difference(dirv).to_matrix().to_4x4()
from mathutils import Matrix
w.matrix_world = Matrix.Translation((ml + mr) / 2) @ giro
bpy.context.view_layer.update()
print("   arma: centro (%+.2f,%+.2f,%+.2f) direccion (%+.2f,%+.2f,%+.2f)"
      % (*((ml + mr) / 2), *dirv))

# --- camara contrapicada, cuerpo entero
mn = Vector((1e9,) * 3); mx = Vector((-1e9,) * 3)
dg = bpy.context.evaluated_depsgraph_get()
for o in bpy.data.objects:
    if o.type != "MESH" or o.name.endswith("_contorno") or o is w:
        continue
    ev = o.evaluated_get(dg)
    for v in ev.data.vertices:
        p = ev.matrix_world @ v.co
        for k in range(3):
            mn[k] = min(mn[k], p[k]); mx[k] = max(mx[k], p[k])
centro = (mn + mx) / 2
alto = max(mx.z - mn.z, 0.5)
print("   figura: alto %.2f  centro (%.2f, %.2f, %.2f)" % (alto, centro.x, centro.y, centro.z))

esc = bpy.context.scene
cam = esc.camera or bpy.data.objects.new("camara", bpy.data.cameras.new("camara"))
esc.camera = cam
cam.data.lens = 70.0
objetivo = Vector((centro.x, centro.y, centro.z + alto * 0.02))
dist = (alto / (2 * math.tan(math.radians(38) / 2))) * 1.20
cam.location = (objetivo.x + dist * 0.06, objetivo.y - dist * 0.94, objetivo.z - alto * 0.30)
cam.rotation_euler = (objetivo - Vector(cam.location)).to_track_quat("-Z", "Y").to_euler()
esc.render.resolution_x = 704
esc.render.resolution_y = 1020
esc.render.film_transparent = True
esc.render.filepath = os.path.join(SAL, "pose_00.png")
bpy.ops.render.render(write_still=True)
print("   render:", esc.render.filepath)

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(SAL, "kotone_pose.blend"))
print("LISTO")