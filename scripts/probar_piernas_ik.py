"""Posa la pierna con un IK temporal sobre el esqueleto ya arreglado y MIDE si la rodilla dobla donde debe.

Mide por postura:
  - donde queda la rodilla (debe quedarse a la altura real, z ~0.5, no subir a la cadera)
  - cuanto se dobla la rodilla (angulo entre muslo y pantorrilla)
  - cuanto se estira la piel: aristas de mas de 3 mm que se alargan mas del 10%
y saca un render de la postura de paso.

Uso: blender --background --python probar_piernas_ik.py -- <blend> <carpeta_salida>
"""
import math
import os
import sys

import bpy
from mathutils import Vector

ARG = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
BLEND, SALIDA = ARG[0], ARG[1]
os.makedirs(SALIDA, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=BLEND)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
cuerpo = next(o for o in bpy.data.objects if o.type == "MESH" and len(o.data.vertices) > 10000)

# IK temporal sobre la rodilla izquierda, con el limite que ya trae el hueso
objetivo = bpy.data.objects.new("TMP_IK", None)
bpy.context.scene.collection.objects.link(objetivo)
objetivo.location = arm.matrix_world @ arm.pose.bones["Bip01 L Foot"].head
pierna = arm.pose.bones["Bip01 L Calf"]
con = pierna.constraints.new(type="IK")
con.target = objetivo
con.chain_count = 2
con.use_tail = True
print("limite de la rodilla: activo=%s [%.0f, %.0f] grados" % (pierna.use_ik_limit_x,
      math.degrees(pierna.ik_min_x), math.degrees(pierna.ik_max_x)))


def limpiar():
    for pb in arm.pose.bones:
        pb.rotation_mode = "XYZ"
        pb.rotation_euler = (0, 0, 0)
        pb.location = (0, 0, 0)
    bpy.context.view_layer.update()


def malla():
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    ev = cuerpo.evaluated_get(dg)
    m = ev.to_mesh()
    v = [ev.matrix_world @ x.co for x in m.vertices]
    e = [(a.vertices[0], a.vertices[1]) for a in m.edges]
    ev.to_mesh_clear()
    return v, e


limpiar()
base_v, aristas = malla()
largos0 = [(base_v[a] - base_v[b]).length for a, b in aristas]
algunas = [l for l in largos0 if l > 0.003]


def medir(etiqueta):
    v, _ = malla()
    rotas = 0
    peor = 0.0
    for (a, b), l0 in zip(aristas, largos0):
        if l0 < 0.003:
            continue
        l1 = (v[a] - v[b]).length
        if l1 > l0 * 1.10:
            rotas += 1
            peor = max(peor, l1 - l0)
    pant = arm.pose.bones["Bip01 L Calf"]
    muslo = arm.pose.bones["Bip01 L Thigh"]
    rodilla = arm.matrix_world @ pant.head
    tobillo = arm.matrix_world @ arm.pose.bones["Bip01 L Foot"].head
    v1 = (arm.matrix_world @ muslo.tail) - (arm.matrix_world @ muslo.head)
    v2 = (arm.matrix_world @ pant.tail) - (arm.matrix_world @ pant.head)
    print("   %-16s rodilla z=%.3f y=%+.3f | tobillo z=%.3f y=%+.3f | doblez=%5.1f grados | piel rota=%d/%d peor=%.1f mm"
          % (etiqueta, rodilla.z, rodilla.y, tobillo.z, tobillo.y, math.degrees(v1.angle(v2)),
             rotas, len(algunas), peor * 1000))


print("=== mediciones (pierna izquierda) ===")
limpiar()
medir("reposo")

centro = sum(base_v, Vector()) / len(base_v)
cam = next((o for o in bpy.data.objects if o.type == "CAMERA"), None)
if cam is None:
    cd = bpy.data.cameras.new("CamPrueba")
    cam = bpy.data.objects.new("CamPrueba", cd)
    bpy.context.scene.collection.objects.link(cam)
cam.location = (0.0, -2.6, centro.z + 0.05)
cam.rotation_euler = (math.radians(90), 0, 0)
bpy.context.view_layer.update()
escena = bpy.context.scene
escena.camera = cam
escena.render.resolution_x, escena.render.resolution_y = 700, 900
escena.render.image_settings.file_format = "PNG"

for nombre, desplazamiento in (("paso_adelante", (0.0, -0.30, 0.20)),
                               ("rodilla_doblada", (0.0, 0.22, 0.32)),
                               ("pierna_estirada", (0.0, -0.55, 0.0))):
    limpiar()
    objetivo.location = (arm.matrix_world @ arm.pose.bones["Bip01 L Foot"].head) + Vector(desplazamiento)
    bpy.context.view_layer.update()
    medir(nombre)
    if nombre == "paso_adelante":
        escena.render.filepath = os.path.join(SALIDA, "pierna_%s.png" % nombre)
        bpy.ops.render.render(write_still=True)
limpiar()
print("render:", os.path.join(SALIDA, "pierna_paso_adelante.png"))