"""Monta una capa de CONTROLES (IK + raiz) sobre el esqueleto original y exporta el paquete.

Idea: el esqueleto `Bip01` del juego se queda tal cual (posiciones derivadas de las inversas de bind)
y encima se crean unos huesos de control que NO deforman (`use_deform = False`): un control de raiz,
uno por mano y por pie, y polos de codo y rodilla. Las articulaciones de verdad reciben restricciones
IK de 2 huesos, asi que el artista mueve la mano y el brazo se dobla solo, en el plano correcto: no
hay que adivinar ejes locales.

El GLB y el FBX se exportan ANTES de crear los controles, para que no viajen a otros programas (las
restricciones no se exportan: alli solo estorbaria el hueso suelto).

Uso: blender --background --python rig_control.py -- <blend_entrada> <carpeta_salida>
"""
import math
import os
import sys

import bpy
from mathutils import Vector

ARG = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ENTRADA = ARG[0]
SAL = ARG[1] if len(ARG) > 1 else os.path.dirname(ENTRADA)
bpy.ops.wm.open_mainfile(filepath=ENTRADA)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
bpy.context.view_layer.objects.active = arm

# ---------------------------------------------------------------- 1. exportar sin controles
glb = os.path.join(SAL, "Kotone_Shiomi.glb")
fbx = os.path.join(SAL, "Kotone_Shiomi.fbx")
bpy.ops.export_scene.gltf(filepath=glb, export_format="GLB", export_yup=True, use_selection=False,
                          export_skins=True, export_morph=True, export_animations=False,
                          export_apply=False)
print("glb limpio:", os.path.getsize(glb) // 1024, "KB")
bpy.ops.export_scene.fbx(filepath=fbx, use_selection=False, embed_textures=True, path_mode="COPY",
                         add_leaf_bones=False, bake_anim=False, object_types={"MESH", "ARMATURE"})
print("fbx limpio:", os.path.getsize(fbx) // 1024, "KB")

# ---------------------------------------------------------------- 2. huesos de control
LADOS = (("L", "Izq"), ("R", "Der"))
CONTROLES = []          # (nombre, cabeza, cola, padre, padre_conectado)
def buscar_raiz():
    for cand in ("Bip01 Pelvis", "Bip01"):
        b = arm.data.bones.get(cand)
        if b is not None and b.name:
            return b
    for b in arm.data.bones:
        if b.name.startswith("Bip01") and b.parent is None:
            return b
    for b in arm.data.bones:
        if b.name.startswith("Bip01"):
            return b
    return None


raiz = buscar_raiz()
CONTROLES.append(("CTRL_Raiz", Vector((0, 0, 0.02)), Vector((0, 0, 0.20)), None))
for lado, esp in LADOS:
    hombro = arm.data.bones["Bip01 %s UpperArm" % lado]
    mano = arm.data.bones["Bip01 %s Hand" % lado]
    pie = arm.data.bones["Bip01 %s Foot" % lado]
    codo = arm.data.bones["Bip01 %s Forearm" % lado]
    rodilla = arm.data.bones["Bip01 %s Calf" % lado]
    # el control de mano: donde la mano, un poco hacia adelante
    CONTROLES.append(("CTRL_Mano_%s" % esp, mano.head_local.copy(),
                      mano.head_local + Vector((0, -0.08, 0)), None))
    CONTROLES.append(("CTRL_Pie_%s" % esp, pie.head_local.copy(),
                      pie.head_local + Vector((0, -0.12, 0)), None))
    # Sin polos: medido, si se le da un polo al IK la pierna entera gira para satisfacerlo y la pose
    # sale retorcida incluso en reposo. Sin polo, el IK dobla el miembro en el plano natural del
    # hueso, que en este esqueleto ya es el bueno (el codo hacia atras, la rodilla hacia delante).

bpy.ops.object.mode_set(mode="EDIT")
nuevos = {}
for nombre, cabeza, cola, padre in CONTROLES:
    eb = arm.data.edit_bones.new(nombre)
    eb.head, eb.tail = cabeza, cola
    eb.use_deform = False
    eb.roll = 0.0
    nuevos[nombre] = eb
for nombre, _c, _cola, padre in CONTROLES:
    if padre and padre in nuevos:
        nuevos[nombre].parent = nuevos[padre]
bpy.ops.object.mode_set(mode="OBJECT")

coleccion = arm.data.collections.get("00_Controles") or arm.data.collections.new("00_Controles")
for nombre, *_ in CONTROLES:
    coleccion.assign(arm.data.bones[nombre])
for c in arm.data.collections:
    if c.name != "00_Controles":
        c.is_visible = c.name != "03_Ayudas_del_juego"
coleccion.is_visible = True

# ---------------------------------------------------------------- 3. restricciones


def ik(deform, control, n=2):
    b = arm.pose.bones[deform]
    c = b.constraints.new("IK")
    c.target = arm
    c.subtarget = control
    c.chain_count = n
    c.use_tail = True
    return c


for lado, esp in LADOS:
    ik("Bip01 %s Forearm" % lado, "CTRL_Mano_%s" % esp)
    ik("Bip01 %s Calf" % lado, "CTRL_Pie_%s" % esp)
    # la mano y el pie siguen a su control (el IK solo coloca el hueso, no lo orienta)
    for deform, control in (("Bip01 %s Hand" % lado, "CTRL_Mano_%s" % esp),
                            ("Bip01 %s Foot" % lado, "CTRL_Pie_%s" % esp)):
        cr = arm.pose.bones[deform].constraints.new("COPY_ROTATION")
        cr.target = arm
        cr.subtarget = control
    # OJO: nada de hacer que el polo mire a la articulacion. El IK depende del polo y el polo
    # depende del hueso que mueve el IK -> ciclo de dependencia y Blender desactiva la cadena entera.
    # Los polos se quedan quietos: son el punto hacia el que se abre el codo o la rodilla.

# la raiz manda en la posicion del cuerpo (la rotacion de la pelvis queda libre para el artista)
if raiz is not None and raiz.name:
    print("hueso raiz para el control de posicion:", raiz.name)
    cl = arm.pose.bones[raiz.name].constraints.new("COPY_LOCATION")
    cl.target = arm
    cl.subtarget = "CTRL_Raiz"

for b in arm.pose.bones:
    b.rotation_mode = "XYZ"

# ---------------------------------------------------------------- 4. prueba real: tirar de la mano
def medir_posado():
    obj = bpy.data.objects["Kotone_Cuerpo"]
    dg = bpy.context.evaluated_depsgraph_get()
    co0 = [obj.matrix_world @ v.co for v in obj.data.vertices]
    bpy.context.view_layer.update()
    ev = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    m = ev.to_mesh()
    co1 = [ev.matrix_world @ v.co for v in m.vertices]
    ev.to_mesh_clear()
    return max((a - b).length for a, b in zip(co1, co0))


antes = medir_posado()
ctl = arm.pose.bones["CTRL_Mano_Izq"]
ctl.location = Vector((0.0, 0.0, 0.35))         # subir la mano izquierda 35 cm
cola = arm.pose.bones["Bip01 L Forearm"]
punta = arm.matrix_world @ cola.tail
print("ANTES de tirar del control: desplazamiento maximo %.4f m" % antes)
bpy.context.view_layer.update()
print("DESPUES: desplazamiento maximo de la malla %.4f m" % medir_posado())
print("codo izquierdo: el IK lo ha doblado (punta del antebrazo en %.3f, %.3f, %.3f)" % tuple(punta))
print("rotacion resultante del antebrazo: %.1f grados" % math.degrees(
    max(abs(x) for x in arm.pose.bones["Bip01 L Forearm"].rotation_euler)))
ctl.location = Vector((0, 0, 0))
bpy.context.view_layer.update()

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(SAL, "Kotone_Shiomi.blend"))
print("blend con controles:", os.path.join(SAL, "Kotone_Shiomi.blend"))
print("huesos de control:", [n for n, *_ in CONTROLES])
print("LISTO")