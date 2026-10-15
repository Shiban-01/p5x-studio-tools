"""Encuentra el eje de giro bueno de cada hueso MIDIENDO, y monta una pose de ejemplo coherente.

Un hueso tiene su propio sistema local: girarlo "en X" no significa lo mismo en el hombro que en la
rodilla. En vez de adivinar el eje, se prueban los tres y se mira hacia donde se mueve la extremidad.
"""
import math
import os
import sys

import bpy
from mathutils import Vector

ARG = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
BLEND, SAL = ARG[0], ARG[1]
os.makedirs(SAL, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=BLEND)
esc = bpy.context.scene
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")


def limpiar():
    for b in arm.pose.bones:
        b.rotation_mode = "XYZ"
        b.rotation_euler = (0, 0, 0)
    bpy.context.view_layer.update()


def pos_de(hueso):
    bpy.context.view_layer.update()
    return arm.matrix_world @ arm.pose.bones[hueso].head


def probar(hueso, punta, grados=40):
    """Gira el hueso en cada eje local y mide hacia donde va la punta de la cadena."""
    limpiar()
    origen = pos_de(punta)
    salida = {}
    for eje in "XYZ":
        b = arm.pose.bones[hueso]
        r = list(b.rotation_euler)
        r["XYZ".index(eje)] = math.radians(grados)
        b.rotation_euler = r
        fin = pos_de(punta)
        d = fin - origen
        salida[eje] = (round(d.x, 3), round(d.y, 3), round(d.z, 3), round(d.length, 3))
        limpiar()
    return salida


print("=== A QUE EJE RESPONDE CADA HUESO (desplazamiento de la punta, en metros) ===")
# x = derecha del personaje, y = hacia atras, z = arriba (el modelo mira a -Y)
pruebas = [("Bip01 L UpperArm", "Bip01 L Hand"), ("Bip01 L Forearm", "Bip01 L Hand"),
           ("Bip01 L Thigh", "Bip01 L Foot"), ("Bip01 L Calf", "Bip01 L Foot"),
           ("Bip01 Head", "Bip01 Head"), ("Bip01 Spine1", "Bip01 Head"),
           ("Bip01 L Hand", "Bip01 L Finger1"), ("Bip01 R UpperArm", "Bip01 R Hand")]
elegido = {}
for hueso, punta in pruebas:
    if hueso not in arm.pose.bones or punta not in arm.pose.bones:
        print("  (falta", hueso, "o", punta, ")")
        continue
    r = probar(hueso, punta)
    print("  %-20s -> %s" % (hueso, "  ".join("%s:%s" % (e, r[e]) for e in "XYZ")))
    elegido[hueso] = r

# --- Pose de ejemplo, con los ejes MEDIDOS -------------------------------------------------
# Para cada hueso se busca el eje que mueve la punta hacia donde se quiere (el signo se ajusta aqui,
# a mano, mirando los numeros de arriba).
limpiar()
POSE = [("Bip01 L Thigh", "X", -18), ("Bip01 L Calf", "X", 22), ("Bip01 R Thigh", "X", 8),
        ("Bip01 L UpperArm", "Y", -32), ("Bip01 L Forearm", "Z", 42), ("Bip01 R UpperArm", "Y", 18),
        ("Bip01 R Forearm", "Z", -20), ("Bip01 Spine1", "X", -4), ("Bip01 Head", "Z", 12),
        ("Bip01 L Hand", "Z", 10)]
for hueso, eje, grados in POSE:
    b = arm.pose.bones.get(hueso)
    if not b:
        continue
    r = list(b.rotation_euler)
    r["XYZ".index(eje)] = math.radians(grados)
    b.rotation_euler = r
bpy.context.view_layer.update()

print("=== VERIFICACION DE LA POSE ===")
for hueso, punta in (("Bip01 L UpperArm", "Bip01 L Hand"), ("Bip01 L Thigh", "Bip01 L Foot"),
                     ("Bip01 Head", "Bip01 Head")):
    print("  %s con %s: desplazamiento %.3f m" % (hueso, punta, (pos_de(punta) - Vector((0, 0, 0))).length))

# --- render de la pose --------------------------------------------------------------------
mn = Vector((1e9,) * 3); mx = Vector((-1e9,) * 3)
for o in [x for x in bpy.data.objects if x.type == "MESH" and x.data.vertices]:
    for v in o.data.vertices:
        w = o.matrix_world @ v.co
        for k in range(3):
            mn[k] = min(mn[k], w[k]); mx[k] = max(mx[k], w[k])
centro = (mn + mx) / 2
alto = max(mx[2] - mn[2], 0.1)
cam = bpy.data.objects.get("camara")
if cam is None:
    cam = bpy.data.objects.new("camara", bpy.data.cameras.new("camara"))
    bpy.context.collection.objects.link(cam)
esc.camera = cam
esc.render.resolution_x = 900
esc.render.resolution_y = 1350
for nombre, ang in (("05_pose_eje_correcto", 20), ("06_pose_eje_correcto_frente", 0)):
    dist = (alto / (2 * math.tan(math.radians(28) / 2))) * 1.15
    cam.data.lens = 60.0
    cam.location = (centro.x + dist * math.sin(math.radians(ang)),
                    centro.y - dist * math.cos(math.radians(ang)), centro.z)
    cam.rotation_euler = (centro - Vector(cam.location)).to_track_quat("-Z", "Y").to_euler()
    esc.render.filepath = os.path.join(SAL, nombre + ".png")
    bpy.ops.render.render(write_still=True)
    print("preview:", esc.render.filepath)

# Se guarda una copia con la pose, para que se vea que el fichero viene listo para posar
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(SAL, "Kotone_Shiomi_pose_ejemplo.blend"))
print("LISTO")