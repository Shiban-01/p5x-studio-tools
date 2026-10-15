"""Render final: Kotone con el toon shader, pose de estocada diagonal con weapon_05 y expresion.

La pose esta afinada a mano (el buscador automatico daba angulos imposibles): los dos brazos bajan
y van al frente agarrando el asta, la rodilla izquierda sube, la derecha empuja hacia abajo, el
tronco gira. El arma se fija a 50 grados -como se mide en la referencia- y se desplaza para que su
recta pase por el punto medio de las manos. Se aplica tambien la expresion facial con shape keys.
"""
import math
import os

import bpy
from mathutils import Vector, Matrix

BLEND = r"C:\Users\Lukas\p5x-datamining\media\toon_blender\kotone_toon.blend"
ARMA = r"C:\Users\Lukas\p5x-datamining\kotone_shiomi\01_model\obj\weapons\weapon_05.obj"
SAL = r"C:\Users\Lukas\p5x-datamining\media\toon_pose"
os.makedirs(SAL, exist_ok=True)

POSE = [
    ("Bip01 Pelvis",     "Z",  22), ("Bip01 Pelvis",     "Y",   5),
    ("Bip01 Spine1",     "Z", -14), ("Bip01 Spine1",     "Y",   8),
    ("Bip01 Spine2",     "Z", -10), ("Bip01 Spine2",     "Y",   6),
    ("Bip01 L Clavicle", "X",  10), ("Bip01 R Clavicle", "X",   8),
    # los dos brazos bajan (X) y se echan al frente (Y): las manos quedan delante del pecho
    ("Bip01 L UpperArm", "X", 102), ("Bip01 L UpperArm", "Y", -34), ("Bip01 L UpperArm", "Z", -12),
    ("Bip01 L Forearm",  "Y", -44), ("Bip01 L Forearm",  "X",  10),
    ("Bip01 R UpperArm", "X",  98), ("Bip01 R UpperArm", "Y",  30), ("Bip01 R UpperArm", "Z",  10),
    ("Bip01 R Forearm",  "Y",  40), ("Bip01 R Forearm",  "X",  10),
    # rodilla izquierda arriba; la derecha sostiene y empuja hacia abajo
    ("Bip01 L Thigh",    "X", -52), ("Bip01 L Thigh",    "Z",  16), ("Bip01 L Thigh", "Y",  10),
    ("Bip01 L Calf",     "X",  62),
    ("Bip01 R Thigh",    "X",  12), ("Bip01 R Thigh",    "Z", -10),
    ("Bip01 R Calf",     "X",  18),
    # cabeza girada hacia su derecha y algo baja, mirando la accion
    ("Bip01 Head",       "Z", -20), ("Bip01 Head",       "X",   8),
]
EXPRESION = {"a": 35}          # boca entreabierta, como en la referencia

bpy.ops.wm.open_mainfile(filepath=BLEND)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
for o in list(bpy.data.objects):
    if "esfera" in o.name.lower():
        bpy.data.objects.remove(o, do_unlink=True)

# --- pose
for b in arm.pose.bones:
    b.rotation_mode = "XYZ"
    b.rotation_euler = (0, 0, 0)
for hueso, eje, grados in POSE:
    b = arm.pose.bones.get(hueso)
    if not b:
        print("   (falta %s)" % hueso)
        continue
    r = list(b.rotation_euler)
    r["XYZ".index(eje)] += math.radians(grados)
    b.rotation_euler = r
bpy.context.view_layer.update()

# --- expresion facial por shape keys
print("=== expresion ===")
tocadas = 0
for o in bpy.data.objects:
    if o.type != "MESH" or not o.data.shape_keys:
        continue
    for kb in o.data.shape_keys.key_blocks:
        if kb.name in EXPRESION:
            kb.value = EXPRESION[kb.name]
            print("   %-52s %s = %d" % (o.name[:52], kb.name, EXPRESION[kb.name]))
            tocadas += 1
print("   shape keys aplicadas: %d" % tocadas)

mano_l = arm.matrix_world @ arm.pose.bones["Bip01 L Hand"].head
mano_r = arm.matrix_world @ arm.pose.bones["Bip01 R Hand"].head
cabeza = arm.matrix_world @ arm.pose.bones["Bip01 Head"].head
print("\n=== articulaciones ===")
for n in ("Bip01 L Hand", "Bip01 R Hand", "Bip01 Head", "Bip01 L Foot", "Bip01 R Foot"):
    p = arm.matrix_world @ arm.pose.bones[n].head
    print("   %-16s (%+.3f, %+.3f, %+.3f)" % (n, p.x, p.y, p.z))

# --- arma: direccion fija a 50 grados, colocada para que pase por el punto medio de las manos
bpy.ops.wm.obj_import(filepath=ARMA, forward_axis="Y", up_axis="Z")
w = next(o for o in bpy.data.objects if o.name.startswith("weapon_05"))
ANG = math.radians(50)
DIR = Vector((math.cos(ANG), 0.0, math.sin(ANG)))          # hacia el pomo
medio = (mano_l + mano_r) / 2
giro = Vector((0, 0, 1)).rotation_difference(DIR).to_matrix().to_4x4()
# el origen del OBJ esta en la punta de la hoja: 55 cm hasta la empunadura
w.matrix_world = Matrix.Translation(medio - DIR * 0.55) @ giro
bpy.context.view_layer.update()
esq = [w.matrix_world @ Vector(v) for v in w.bound_box]
print("   arma: de (%.2f, %.2f, %.2f) a (%.2f, %.2f, %.2f)"
      % (min(p.x for p in esq), min(p.y for p in esq), min(p.z for p in esq),
         max(p.x for p in esq), max(p.y for p in esq), max(p.z for p in esq)))
print("   distancia de cada mano al asta: izq %.3f m   der %.3f m"
      % ((mano_l - medio).length, (mano_r - medio).length))

# --- camara contrapicada, figura entera
mn = Vector((1e9,) * 3); mx = Vector((-1e9,) * 3)
dg = bpy.context.evaluated_depsgraph_get()
for o in bpy.data.objects:
    if o.type != "MESH" or o.name.endswith("_contorno"):
        continue
    ev = o.evaluated_get(dg)
    for v in ev.data.vertices:
        p = ev.matrix_world @ v.co
        for k in range(3):
            mn[k] = min(mn[k], p[k]); mx[k] = max(mx[k], p[k])
centro = (mn + mx) / 2
alto = max(mx.z - mn.z, 0.5)
print("   conjunto: alto %.2f m  centro (%.2f, %.2f, %.2f)" % (alto, centro.x, centro.y, centro.z))

esc = bpy.context.scene
cam = esc.camera or bpy.data.objects.new("camara", bpy.data.cameras.new("camara"))
esc.camera = cam
cam.data.lens = 68.0
objetivo = Vector((centro.x, centro.y, centro.z))
dist = (alto / (2 * math.tan(math.radians(38) / 2))) * 1.10
cam.location = (objetivo.x + dist * 0.05, objetivo.y - dist * 0.95, objetivo.z - alto * 0.24)
cam.rotation_euler = (objetivo - Vector(cam.location)).to_track_quat("-Z", "Y").to_euler()
esc.render.resolution_x = 704
esc.render.resolution_y = 1020
esc.render.film_transparent = False
esc.render.filepath = os.path.join(SAL, "pose_final.png")
bpy.ops.render.render(write_still=True)
print("   render:", esc.render.filepath)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(SAL, "kotone_pose_final.blend"))
print("LISTO")