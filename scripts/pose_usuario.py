"""Render final con la pose descrita por el usuario, weapon_05 y expresion facial.

Descripcion (dicha de frente, asi que "izquierda de la imagen" = su derecha):
  - su mano DERECHA, abajo, agarrando el mastil cerca del filo;
  - su mano IZQUIERDA, arriba, agarrando el mastil por detras;
  - su rodilla DERECHA levantada.

El arma se fija a 50 grados (hoja abajo-izquierda de la imagen, pomo arriba-derecha, que es lo
medido en la referencia) y las manos se colocan sobre el asta: la derecha a 25 cm del filo, la
izquierda a 1,15 m. Los angulos de hombro y codo se buscan con limites anatomicos.
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

# --- el arma: 50 grados, con la HOJA abajo a su derecha (izquierda de la imagen)
# medido en el OBJ: la cabeza (0,226 m de ancho) esta en el extremo de Z MAXIMO, o sea que
# el eje +Z local apunta hacia la hoja, no hacia el pomo. De ahi el sentido de giro.
P0 = Vector((-0.62, -0.48, 0.50))            # punta de la hoja, separada del cuerpo
LARGO = 1.995                                # medido en el OBJ
ANG = math.radians(50)
DIR = Vector((math.cos(ANG), 0.0, math.sin(ANG)))   # hacia el mango, subiendo
OBJ_DER = P0 + DIR * 0.40                    # su mano derecha, cerca de la hoja
OBJ_IZQ = P0 + DIR * 1.25                    # su mano izquierda, en el tramo alto del asta

FIJO = [
    ("Bip01 Pelvis",     "Z",  24), ("Bip01 Pelvis",     "Y",   6),
    ("Bip01 Spine1",     "Z", -16), ("Bip01 Spine1",     "Y",   7),
    ("Bip01 Spine2",     "Z", -12), ("Bip01 Spine2",     "Y",   5),
    ("Bip01 L Clavicle", "X",   6), ("Bip01 R Clavicle", "X",  12),
    # la rodilla que sube es la IZQUIERDA (la que sale a la derecha de la imagen); la derecha
    # queda extendida hacia abajo, y como salta, los dos pies van en el aire
    # medido con sonda_rig_kotone: en el muslo el eje que ADELANTA la rodilla es Y, no X
    # (X solo la retuerce). En la pantorrilla, X negativo pliega el pie hacia atras.
    ("Bip01 L Thigh",    "Y",  55),
    ("Bip01 L Calf",     "X", -64),
    ("Bip01 R Thigh",    "Y",  -6),
    ("Bip01 R Calf",     "X", -10),
    ("Bip01 Head",       "Z", -18), ("Bip01 Head",       "X",  10),
]
EXPRESION = {"a": 35}

bpy.ops.wm.open_mainfile(filepath=BLEND)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
for o in list(bpy.data.objects):
    if "esfera" in o.name.lower():
        bpy.data.objects.remove(o, do_unlink=True)


def aplicar(lista):
    for b in arm.pose.bones:
        b.rotation_mode = "XYZ"
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
    """busca (hombro X,Y,Z, codo X,Y) con limites anatomicos, en tres pasadas"""
    hh, hc, hm = ("Bip01 %s UpperArm" % lado, "Bip01 %s Forearm" % lado, "Bip01 %s Hand" % lado)
    mejor = (1e9, None)

    def ev(v):
        aplicar(FIJO + [(hh, "X", v[0]), (hh, "Y", v[1]), (hh, "Z", v[2]),
                        (hc, "X", v[3]), (hc, "Y", v[4])])
        return (mano(hm) - objetivo).length

    # el brazo puede subir (X negativo) o bajar (X positivo); el codo dobla en un sentido
    rej = [range(-60, 121, 30), range(-60, 61, 30), range(-40, 41, 40),
           range(-30, 31, 30), range(-70, 71, 35)]
    for v in itertools.product(*rej):
        d = ev(v)
        if d < mejor[0]:
            mejor = (d, v)
    for paso, radio in ((15, 30), (6, 12), (2, 4)):
        base = mejor[1]
        for v in itertools.product(*[range(b - radio, b + radio + 1, paso) for b in base]):
            d = ev(v)
            if d < mejor[0]:
                mejor = (d, v)
    return mejor


d_der, v_der = busca("R", OBJ_DER)
d_izq, v_izq = busca("L", OBJ_IZQ)
print("=== manos sobre el asta ===")
print("   derecha (abajo, junto al filo): error %.3f m  angulos %s" % (d_der, v_der))
print("   izquierda (arriba, por detras): error %.3f m  angulos %s" % (d_izq, v_izq))

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
print("   objetivos:  der (%+.2f, %+.2f, %+.2f)   izq (%+.2f, %+.2f, %+.2f)" % (*OBJ_DER, *OBJ_IZQ))

# --- expresion
tocadas = 0
for o in bpy.data.objects:
    if o.type == "MESH" and o.data.shape_keys:
        for kb in o.data.shape_keys.key_blocks:
            if kb.name in EXPRESION:
                kb.value = EXPRESION[kb.name]
                tocadas += 1
print("   shape keys de expresion aplicadas: %d" % tocadas)

# --- arma
bpy.ops.wm.obj_import(filepath=ARMA, forward_axis="Y", up_axis="Z")
w = next(o for o in bpy.data.objects if o.name.startswith("weapon_05"))
# el +Z local va hacia la hoja, asi que se gira hacia -DIR y se traslada al extremo opuesto
giro = Vector((0, 0, 1)).rotation_difference(-DIR).to_matrix().to_4x4()
w.matrix_world = Matrix.Translation(P0 + DIR * LARGO) @ giro
bpy.context.view_layer.update()
esq = [w.matrix_world @ Vector(v) for v in w.bound_box]
print("   arma: de (%.2f, %.2f, %.2f) a (%.2f, %.2f, %.2f)"
      % (min(p.x for p in esq), min(p.y for p in esq), min(p.z for p in esq),
         max(p.x for p in esq), max(p.y for p in esq), max(p.z for p in esq)))

# --- camara contrapicada, conjunto entero
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
cam.data.lens = 66.0
objetivo = Vector((centro.x, centro.y, centro.z))
# el encuadre es vertical (704x1020), pero una pierna levantada abre la figura en horizontal:
# si solo se mira el alto, la camara queda demasiado cerca y corta el miembro que sobresale
ancho = mx.x - mn.x
alto_util = max(alto, ancho * 1020.0 / 704.0)
dist = (alto_util / (2 * math.tan(math.radians(38) / 2))) * 1.32
cam.location = (objetivo.x + dist * 0.05, objetivo.y - dist * 0.95, objetivo.z - alto * 0.24)
cam.rotation_euler = (objetivo - Vector(cam.location)).to_track_quat("-Z", "Y").to_euler()
esc.render.resolution_x = 704
esc.render.resolution_y = 1020
esc.render.film_transparent = True
esc.render.filepath = os.path.join(SAL, "pose_usuario.png")
bpy.ops.render.render(write_still=True)
print("   render:", esc.render.filepath)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(SAL, "kotone_pose_usuario.blend"))
print("LISTO")