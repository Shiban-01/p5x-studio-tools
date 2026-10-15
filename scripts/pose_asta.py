"""Coloca weapon_05 en su diagonal y posa los brazos para que las manos caigan sobre el asta.

Al reves que antes: aqui el arma manda. Se fija su recta (centro y direccion a 50 grados, que es lo
que se mide en la referencia: hoja abajo-izquierda, pomo arriba-derecha) y despues se buscan los
angulos de hombro y codo que llevan cada mano a un punto concreto del asta, separadas 25 cm.
"""
import itertools
import math
import os

import bpy
from mathutils import Vector, Matrix

BLEND = r"C:\Users\Lukas\p5x-datamining\media\toon_blender\kotone_toon.blend"
ARMA = r"C:\Users\Lukas\p5x-datamining\kotone_shiomi\01_model\obj\weapons\weapon_05.obj"
SAL = r"C:\Users\Lukas\p5x-datamining\media\toon_pose"
os.makedirs(SAL, exist_ok=True)

# la recta del asta: 50 grados en el plano x-z, delante del cuerpo
CENTRO = Vector((-0.02, -0.24, 1.02))
ANG = math.radians(50)
DIR = Vector((math.cos(ANG), 0.0, math.sin(ANG)))     # apunta hacia el pomo
# puntos del asta donde agarran las manos (25 cm entre ellas, sobre la recta)
OBJ_DER = CENTRO + DIR * (-0.05)      # su mano derecha, mas abajo sobre el asta
OBJ_IZQ = CENTRO + DIR * (0.20)       # su mano izquierda, mas arriba

FIJO = [
    ("Bip01 Pelvis",     "Z",  26), ("Bip01 Pelvis",     "Y",   5),
    ("Bip01 Spine1",     "Z", -18), ("Bip01 Spine1",     "Y",   7),
    ("Bip01 Spine2",     "Z", -12), ("Bip01 Spine2",     "Y",   5),
    ("Bip01 L Thigh",    "X", -48), ("Bip01 L Thigh",    "Z",  20),
    ("Bip01 L Calf",     "X",  50),
    ("Bip01 R Thigh",    "X",  14), ("Bip01 R Thigh",    "Z", -14),
    ("Bip01 R Calf",     "X",  22),
    ("Bip01 Head",       "Z", -16), ("Bip01 Head",       "X",   6),
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
    for b in arm.pose.bones:
        b.rotation_mode = "XYZ"          # sin esto el euler se ignora si el hueso esta en cuaternion
        b.rotation_euler = (0, 0, 0)
    for hueso, eje, grados in lista:
        b = arm.pose.bones.get(hueso)
        if b:
            r = list(b.rotation_euler)
            r["XYZ".index(eje)] += math.radians(grados)
            b.rotation_euler = r
    bpy.context.view_layer.update()


def mano(n):
    return arm.matrix_world @ arm.pose.bones[n].head


def busca(lado, objetivo):
    """busca (hombro X,Y,Z, codo X,Y) que lleva la mano al objetivo, en dos pasadas"""
    hueso_h, hueso_c, hueso_m = ("Bip01 %s UpperArm" % lado, "Bip01 %s Forearm" % lado,
                                 "Bip01 %s Hand" % lado)
    mejor = (1e9, None)

    def evalua(vals):
        aplicar(FIJO + [(hueso_h, "X", vals[0]), (hueso_h, "Y", vals[1]), (hueso_h, "Z", vals[2]),
                        (hueso_c, "X", vals[3]), (hueso_c, "Y", vals[4])])
        return (mano(hueso_m) - objetivo).length

    # rangos anatomicos: el hombro no pasa de ~120 grados al bajar el brazo y el codo
    # solo dobla en un sentido (el signo depende del lado)
    if lado == "L":
        rejilla = [range(70, 121, 15), range(-40, 31, 20), range(-40, 21, 20),
                   range(-20, 21, 20), range(-80, 1, 20)]
    else:
        rejilla = [range(70, 121, 15), range(-30, 41, 20), range(-20, 41, 20),
                   range(-20, 21, 20), range(0, 81, 20)]
    for v in itertools.product(*rejilla):
        d = evalua(v)
        if d < mejor[0]:
            mejor = (d, v)
    base = mejor[1]
    for v in itertools.product(*[range(b - 20, b + 21, 10) for b in base]):
        d = evalua(v)
        if d < mejor[0]:
            mejor = (d, v)
    base = mejor[1]
    for v in itertools.product(*[range(b - 8, b + 9, 4) for b in base]):
        d = evalua(v)
        if d < mejor[0]:
            mejor = (d, v)
    return mejor


d_der, v_der = busca("R", OBJ_DER)
d_izq, v_izq = busca("L", OBJ_IZQ)
print("=== manos sobre el asta ===")
print("   mano derecha: error %.3f m   angulos %s" % (d_der, v_der))
print("   mano izquierda: error %.3f m   angulos %s" % (d_izq, v_izq))

POSE = FIJO + [("Bip01 R UpperArm", "X", v_der[0]), ("Bip01 R UpperArm", "Y", v_der[1]),
               ("Bip01 R UpperArm", "Z", v_der[2]), ("Bip01 R Forearm", "X", v_der[3]),
               ("Bip01 R Forearm", "Y", v_der[4]),
               ("Bip01 L UpperArm", "X", v_izq[0]), ("Bip01 L UpperArm", "Y", v_izq[1]),
               ("Bip01 L UpperArm", "Z", v_izq[2]), ("Bip01 L Forearm", "X", v_izq[3]),
               ("Bip01 L Forearm", "Y", v_izq[4])]
aplicar(POSE)

print("\n=== articulaciones ===")
for n in ("Bip01 L Hand", "Bip01 R Hand", "Bip01 Head", "Bip01 L Foot", "Bip01 R Foot",
          "Bip01 L Calf", "Bip01 R Calf"):
    p = arm.matrix_world @ arm.pose.bones[n].head
    print("   %-16s (%+.3f, %+.3f, %+.3f)" % (n, p.x, p.y, p.z))
print("   objetivos:    der (%+.3f, %+.3f, %+.3f)   izq (%+.3f, %+.3f, %+.3f)"
      % (*OBJ_DER, *OBJ_IZQ))

# --- arma sobre su recta fija
bpy.ops.wm.obj_import(filepath=ARMA, forward_axis="Y", up_axis="Z")
w = next(o for o in bpy.data.objects if o.name.startswith("weapon_05"))
giro = Vector((0, 0, 1)).rotation_difference(DIR).to_matrix().to_4x4()
# el origen del OBJ esta al final de la hoja; se desplaza a lo largo del asta para que
# el punto de empunadura (unos 55 cm desde la hoja, como en la referencia) caiga en CENTRO
w.matrix_world = Matrix.Translation(CENTRO - DIR * 0.55) @ giro
bpy.context.view_layer.update()
esq = [w.matrix_world @ Vector(v) for v in w.bound_box]
mn_a = Vector((min(p.x for p in esq), min(p.y for p in esq), min(p.z for p in esq)))
mx_a = Vector((max(p.x for p in esq), max(p.y for p in esq), max(p.z for p in esq)))
print("   arma: de (%.2f, %.2f, %.2f) a (%.2f, %.2f, %.2f)   largo %.2f m"
      % (*mn_a, *mx_a, (mx_a - mn_a).length))

# --- camara contrapicada, cuerpo entero
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
print("   conjunto: alto %.2f  de z %.2f a %.2f  centro (%.2f, %.2f, %.2f)"
      % (alto, mn.z, mx.z, centro.x, centro.y, centro.z))

esc = bpy.context.scene
cam = esc.camera or bpy.data.objects.new("camara", bpy.data.cameras.new("camara"))
esc.camera = cam
cam.data.lens = 70.0
objetivo = Vector((centro.x, centro.y, centro.z))
dist = (alto / (2 * math.tan(math.radians(40) / 2))) * 1.32
cam.location = (objetivo.x + dist * 0.05, objetivo.y - dist * 0.95, objetivo.z - alto * 0.22)
cam.rotation_euler = (objetivo - Vector(cam.location)).to_track_quat("-Z", "Y").to_euler()
esc.render.resolution_x = 704
esc.render.resolution_y = 1020
esc.render.film_transparent = True
esc.render.filepath = os.path.join(SAL, "pose_00.png")
bpy.ops.render.render(write_still=True)
print("   render:", esc.render.filepath)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(SAL, "kotone_pose.blend"))
print("LISTO")