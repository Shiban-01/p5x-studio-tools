"""Sonda del rig de Kotone: ejes de giro reales de cada hueso y posiciones de reposo.

En este rig girar "en X" no significa lo mismo en el hombro que en la rodilla. Aqui se mide: para
cada hueso se gira 30 grados en cada eje local y se ve hacia donde se mueve la punta de su cadena.
Tambien se imprimen las posiciones de reposo de las articulaciones que hay que calcar.
"""
import math
import sys

import bpy
from mathutils import Vector

BLEND = r"C:\Users\Lukas\p5x-datamining\media\toon_blender\kotone_toon.blend"
bpy.ops.wm.open_mainfile(filepath=BLEND)

arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
print("armadura: %s  huesos: %d" % (arm.name, len(arm.pose.bones)))
print("mallas: %s" % [o.name for o in bpy.data.objects if o.type == "MESH"])
print("camara en escena: %s" % (bpy.context.scene.camera.name if bpy.context.scene.camera else None))
print("resolucion: %dx%d  motor: %s" % (bpy.context.scene.render.resolution_x,
                                        bpy.context.scene.render.resolution_y,
                                        bpy.context.scene.render.engine))


def limpiar():
    for b in arm.pose.bones:
        b.rotation_mode = "XYZ"
        b.rotation_euler = (0, 0, 0)
    bpy.context.view_layer.update()


def pos(h):
    bpy.context.view_layer.update()
    return arm.matrix_world @ arm.pose.bones[h].head


print("\n=== POSICIONES DE REPOSO (metros, mundo) ===")
for h in ["Bip01 Pelvis", "Bip01 Spine1", "Bip01 Spine2", "Bip01 Neck1", "Bip01 Head",
          "Bip01 L Clavicle", "Bip01 L UpperArm", "Bip01 L Forearm", "Bip01 L Hand",
          "Bip01 R Clavicle", "Bip01 R UpperArm", "Bip01 R Forearm", "Bip01 R Hand",
          "Bip01 L Thigh", "Bip01 L Calf", "Bip01 L Foot", "Bip01 L Toe0",
          "Bip01 R Thigh", "Bip01 R Calf", "Bip01 R Foot", "Bip01 R Toe0"]:
    if h in arm.pose.bones:
        p = pos(h)
        print("   %-20s (%.3f, %.3f, %.3f)" % (h, p.x, p.y, p.z))
    else:
        print("   %-20s NO EXISTE" % h)

print("\n=== EJES: a donde mueve la punta girar 30 grados en cada eje local ===")
pruebas = [("Bip01 Spine1", "Bip01 Head"), ("Bip01 Spine2", "Bip01 Head"),
           ("Bip01 Neck1", "Bip01 Head"), ("Bip01 Head", "Bip01 Head"),
           ("Bip01 L Clavicle", "Bip01 L Hand"), ("Bip01 L UpperArm", "Bip01 L Hand"),
           ("Bip01 L Forearm", "Bip01 L Hand"), ("Bip01 L Hand", "Bip01 L Finger1"),
           ("Bip01 R Clavicle", "Bip01 R Hand"), ("Bip01 R UpperArm", "Bip01 R Hand"),
           ("Bip01 R Forearm", "Bip01 R Hand"), ("Bip01 R Hand", "Bip01 R Finger1"),
           ("Bip01 L Thigh", "Bip01 L Foot"), ("Bip01 L Calf", "Bip01 L Foot"),
           ("Bip01 R Thigh", "Bip01 R Foot"), ("Bip01 R Calf", "Bip01 R Foot"),
           ("Bip01 Pelvis", "Bip01 Head")]
for hueso, punta in pruebas:
    if hueso not in arm.pose.bones or punta not in arm.pose.bones:
        print("   (falta %s o %s)" % (hueso, punta))
        continue
    limpiar()
    origen = pos(punta)
    salida = []
    for eje in "XYZ":
        b = arm.pose.bones[hueso]
        r = list(b.rotation_euler)
        r["XYZ".index(eje)] = math.radians(30)
        b.rotation_euler = r
        d = pos(punta) - origen
        salida.append("%s:(%+.2f,%+.2f,%+.2f)=%.3f" % (eje, d.x, d.y, d.z, d.length))
        limpiar()
    print("   %-20s %s" % (hueso, "  ".join(salida)))
print("\n   convencion: x = derecha del personaje, y = hacia atras, z = arriba. Mira hacia -Y.")
limpiar()