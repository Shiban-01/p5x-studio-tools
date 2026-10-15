"""Arregla la geometria del esqueleto que viene del juego: colas, ejes de flexion y limites de IK.

El problema (medido): los huesos del juego traen colas arbitrarias. El muslo medía 0.118 m y la
pantorrilla 0.510 m con la cola apuntando hacia arriba, y de 109 huesos con un solo hijo NINGUNO tenia
la cola donde empieza el hijo. Como el IK (el de Blender y el de MMD) resuelve la cadena con esas
longitudes y con los ejes locales que salen de la cola y el roll, posar la pierna producia posturas
retorcidas. Ademas la rodilla no tenia limite de angulo, asi que podia doblarse hacia atras.

Que hace:
  1. cola de cada hueso = cabeza de su hijo "principal" (el mas lejano, ignorando ayudantes), y los
     huesos que quedan encadenados se marcan como conectados.
  2. roll de brazos y piernas recalculado para que el eje de flexion sea el X local (predecible).
  3. limite de IK en rodillas y codos, MIDIENDO el signo: se gira +20 grados y se mira si la punta del
     miembro (tobillo/mano) va hacia atras, que es como se doblan de verdad.
     Ese limite es el que MMD usa como "limite del enlace" del IK (ひざ), asi que arreglarlo aqui
     arregla tambien el PMX.

Uso: blender --background --python arreglar_esqueleto.py -- <entrada.blend> <salida.blend>
"""
import math
import sys

import bpy
from mathutils import Vector

ARG = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ENTRADA, SALIDA = ARG[0], ARG[1]

bpy.ops.wm.open_mainfile(filepath=ENTRADA)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
print("=== arreglando el esqueleto de %s (%d huesos) ===" % (arm.name, len(arm.data.bones)))

# nombres de huesos que son ayudantes del juego: no sirven para decidir la forma del hueso
AYUDANTES = ("Capsule Collider", "(mirrored)", "Bone_", "Magica", "toufa", "peishi", "xuzi",
             "qunzi", "xiuzhang", "wq_", "gun_", "Prop")


def es_ayudante(nombre):
    return any(a in nombre for a in AYUDANTES)


# ------------------------------------------------------------------ 1. colas
bpy.context.view_layer.objects.active = arm
arm.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
eb = arm.data.edit_bones
antes = {}
for b in eb:
    antes[b.name] = b.length

cambiados = 0
for b in eb:
    candidatos = [c for c in b.children if not es_ayudante(c.name)]
    if not candidatos:
        continue
    # el hijo "principal" es el que tiene la cabeza mas lejos: ese es la siguiente articulacion
    principal = max(candidatos, key=lambda c: (c.head - b.head).length)
    if (b.tail - principal.head).length > 1e-4:
        b.tail = principal.head
        cambiados += 1
print("colas recolocadas en la articulacion siguiente: %d" % cambiados)

conectados = 0
for b in eb:
    for c in b.children:
        if (b.tail - c.head).length < 1e-5 and not c.use_connect:
            c.use_connect = True
            conectados += 1
print("huesos marcados como conectados al padre: %d" % conectados)

# ------------------------------------------------------------------ 2. roll de brazos y piernas
# El eje de flexion de un codo/rodilla debe ser el X local. Alineando el Z local con el +Y global
# (el personaje mira a -Y), el X local queda horizontal y atravesado: flexionar = girar sobre X.
FLEXION = ("Thigh", "Calf", "Foot", "UpperArm", "Forearm", "Hand", "Clavicle")
alineados = 0
for b in eb:
    if any(f in b.name for f in FLEXION) and b.name.startswith("Bip01"):
        b.align_roll(Vector((0.0, 1.0, 0.0)))
        alineados += 1
print("roll alineado para flexionar sobre X local: %d huesos" % alineados)

bpy.ops.object.mode_set(mode="OBJECT")

# ------------------------------------------------------------------ 3. limites de IK medidos
cuerpo = next((o for o in bpy.data.objects if o.type == "MESH" and len(o.data.vertices) > 10000), None)


def limpiar():
    for pb in arm.pose.bones:
        pb.rotation_mode = "XYZ"
        pb.rotation_euler = (0, 0, 0)
        pb.location = (0, 0, 0)
    bpy.context.view_layer.update()


limpiar()
for etiqueta, hueso, punta, hacia_atras_en in (
        ("rodilla izquierda", "Bip01 L Calf", "Bip01 L Foot", +1),
        ("rodilla derecha", "Bip01 R Calf", "Bip01 R Foot", +1),
        ("codo izquierdo", "Bip01 L Forearm", "Bip01 L Hand", -1),
        ("codo derecho", "Bip01 R Forearm", "Bip01 R Hand", -1)):
    pb = arm.pose.bones.get(hueso)
    if not pb:
        print("   %s: no existe %s" % (etiqueta, hueso))
        continue
    punta_pb = arm.pose.bones.get(punta)
    limpiar()
    y0 = (arm.matrix_world @ punta_pb.head).y if punta_pb else 0.0
    pb.rotation_euler = (math.radians(20), 0, 0)
    bpy.context.view_layer.update()
    y1 = (arm.matrix_world @ punta_pb.head).y if punta_pb else 0.0
    delta = y1 - y0
    # al doblar la rodilla el tobillo va hacia ATRAS (+Y, el personaje mira a -Y); el codo, igual
    signo_positivo_es_natural = (delta * hacia_atras_en) > 0
    limpiar()
    pb.use_ik_limit_x = True
    if signo_positivo_es_natural:
        pb.ik_min_x, pb.ik_max_x = math.radians(0.5), math.radians(179.5)
    else:
        pb.ik_min_x, pb.ik_max_x = math.radians(-179.5), math.radians(-0.5)
    print("   %s (%s): girar +20 grados mueve la punta %.3f m -> limite X en %s"
          % (etiqueta, hueso, delta, "positivo" if signo_positivo_es_natural else "negativo"))

# ------------------------------------------------------------------ informe y guardado
print("=== longitudes antes -> despues ===")
for n in ("Bip01 L Thigh", "Bip01 L Calf", "Bip01 L Foot", "Bip01 L UpperArm", "Bip01 L Forearm"):
    b = arm.data.bones.get(n)
    if b:
        print("   %-18s %.4f -> %.4f m" % (n, antes.get(n, 0.0), b.length))

bpy.ops.wm.save_as_mainfile(filepath=SALIDA)
print("guardado:", SALIDA)
