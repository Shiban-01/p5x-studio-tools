"""Posar con los CONTROLES (no girando huesos a mano), medirlo y renderizarlo.

Verificacion honesta: se mide el desplazamiento de la malla en el MISMO espacio (mundo) antes y
despues de mover los controles, y se comprueba el angulo que se dobla el codo. Se mide tambien el
desgarro de la piel en esa pose, para no vender humo.

Uso: blender --background --python render_ik.py -- <blend> <carpeta_salida>
"""
import math
import os
import sys

import bpy
from mathutils import Vector

ARG = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
BLEND = ARG[0]
SAL = ARG[1] if len(ARG) > 1 else os.path.dirname(BLEND)
bpy.ops.wm.open_mainfile(filepath=BLEND)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
obj = bpy.data.objects["Kotone_Cuerpo"]


def evaluado():
    bpy.context.view_layer.update()
    ev = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    m = ev.to_mesh()
    co = [ev.matrix_world @ v.co for v in m.vertices]
    ar = [(e.vertices[0], e.vertices[1]) for e in m.edges]
    ev.to_mesh_clear()
    return co, ar


def angulo_entre(a, b):
    na, nb = a.normalized(), b.normalized()
    return math.degrees(math.acos(max(-1.0, min(1.0, na.dot(nb)))))


co0, aristas = evaluado()
largos0 = [(co0[a] - co0[b]).length for a, b in aristas]

# --- la pose se hace SOLO con los controles ---
# OJO: `location` de un hueso va en los ejes LOCALES del hueso. Para mover el control "10 cm hacia
# arriba" en el mundo hay que pasar el vector por la matriz de reposo del hueso, no asignarlo directo.
def mover_control(nombre, delta_mundo):
    c = arm.pose.bones[nombre]
    local = c.bone.matrix_local.to_3x3().inverted() @ Vector(delta_mundo)
    c.location = c.location + local
    return Vector(delta_mundo).length


movimientos = {"CTRL_Mano_Izq": (0.06, -0.06, 0.10), "CTRL_Mano_Der": (-0.04, 0.0, 0.05),
               "CTRL_Pie_Der": (0.0, -0.12, 0.0)}
for nombre, delta in movimientos.items():
    print("control %s movido %.2f m (en el mundo)" % (nombre, mover_control(nombre, delta)))

co1, _ = evaluado()
desp = max((a - b).length for a, b in zip(co1, co0))
hombro = arm.matrix_world @ arm.pose.bones["Bip01 L UpperArm"].head
mano_v = [(co1[i] - co0[i]).length for i, p in enumerate(co0) if (p - hombro).length > 0.45]
print("desplazamiento maximo de la malla: %.3f m" % desp)
print("codo izquierdo: %.1f grados" % angulo_entre(
    arm.pose.bones["Bip01 L UpperArm"].tail - arm.pose.bones["Bip01 L UpperArm"].head,
    arm.pose.bones["Bip01 L Forearm"].tail - arm.pose.bones["Bip01 L Forearm"].head))
rotas = sum(1 for (a, b), l0 in zip(aristas, largos0)
            if l0 > 0.003 and (co1[a] - co1[b]).length / l0 > 1.10)
print("aristas >3mm estiradas >10%% con esta pose: %d de %d" % (rotas, sum(1 for l in largos0 if l > 0.003)))

# --- render ---
escena = bpy.context.scene
escena.render.engine = "BLENDER_EEVEE"      # en esta version el motor se llama asi, no EEVEE_NEXT
escena.view_settings.view_transform = "Standard"
escena.render.resolution_x, escena.render.resolution_y = 900, 1200
escena.render.film_transparent = False
cam = bpy.data.objects.get("CamaraIK") or bpy.data.objects.new("CamaraIK", bpy.data.cameras.new("CamaraIK"))
escena.collection.objects.link(cam)
cam.data.type = "ORTHO"
cam.data.ortho_scale = 2.1
escena.camera = cam
luz = bpy.data.objects.get("LuzIK") or bpy.data.objects.new("LuzIK", bpy.data.lights.new("LuzIK", "SUN"))
escena.collection.objects.link(luz)
luz.data.energy = 2.0
luz.rotation_euler = (math.radians(55), 0, math.radians(30))

for nombre, pos, destino in (("05_pose_ik_frente", (0.0, -4.0, 1.0), (0.0, 0.0, 1.0)),
                             ("06_pose_ik_trescuartos", (2.6, -2.8, 1.3), (0.0, 0.0, 1.0))):
    cam.location = pos
    direccion = Vector(destino) - Vector(pos)
    cam.rotation_euler = direccion.to_track_quat("-Z", "Y").to_euler()
    escena.render.filepath = os.path.join(SAL, nombre + ".png")
    bpy.ops.render.render(write_still=True)
    print("render:", escena.render.filepath)
print("LISTO")