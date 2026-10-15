"""Verifica el PMX con el importador de mmd_tools (el consumidor real) y lo renderiza posado con IK."""
import math
import os
import sys

import bpy

ARG = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
PMX = ARG[0]
SAL = ARG[1] if len(ARG) > 1 else os.path.dirname(PMX)
bpy.ops.preferences.addon_enable(module="bl_ext.user_default.mmd_tools")

# escena limpia de verdad
bpy.ops.wm.read_homefile(use_empty=True)
bpy.ops.mmd_tools.import_model(filepath=PMX, scale=1.0, types={"MESH", "ARMATURE", "MORPHS", "DISPLAY"},
                               clean_model=False, rename_bones=True)
print("=== LEIDO POR MMD TOOLS ===")
arm = next((o for o in bpy.data.objects if o.type == "ARMATURE"), None)
mallas = [o for o in bpy.data.objects if o.type == "MESH"]
print("mallas: %d (%s)" % (len(mallas), [o.name for o in mallas][:4]))
print("vertices totales:", sum(len(o.data.vertices) for o in mallas))
if arm:
    nombres = [b.name for b in arm.data.bones]
    print("huesos: %d" % len(nombres))
    estandar = [n for n in ("全ての親", "センター", "上半身", "上半身2", "下半身", "首", "頭",
                            "肩.L", "腕.L", "ひじ.L", "手首.L", "足.L", "ひざ.L", "足首.L", "つま先.L",
                            "足ＩＫ.L", "つま先ＩＫ.L", "親指0.L", "人指1.L", "小指2.L",
                            "肩.R", "腕.R", "ひじ.R", "手首.R", "足.R", "ひざ.R", "足首.R",
                            "足ＩＫ.R", "つま先ＩＫ.R") if n in nombres]
    print("huesos estandar presentes (%d):" % len(estandar), estandar)
    print("faltan:", [n for n in ("全ての親", "センター", "上半身", "下半身", "腕.L", "ひじ.L", "足.L", "ひざ.L",
                                 "足首.L", "足ＩＫ.L", "つま先ＩＫ.L", "腕.R", "足.R", "足ＩＫ.R") if n not in nombres])
    iks = [(b.name, c.subtarget, c.chain_count) for b in arm.pose.bones for c in b.constraints if c.type == "IK"]
    print("restricciones IK (%d): %s" % (len(iks), iks))
morfos = [o for o in mallas if o.data.shape_keys]
if morfos:
    kb = [k.name for k in morfos[0].data.shape_keys.key_blocks]
    print("morphs en %s: %d -> %s" % (morfos[0].name, len(kb), kb[:16]))
zs = [(o.matrix_world @ v.co).z for o in mallas for v in o.data.vertices]
alto_total = max(zs) - min(zs)
print("altura del modelo tal como llega del PMX: %.2f unidades (el Miku oficial mide 20.12 asi)" % alto_total)
print("materiales e imagenes:")
for m in bpy.data.materials:
    if not m.use_nodes:
        print("   %-28s (sin nodos)" % m.name)
        continue
    imgs = [n.image.name for n in m.node_tree.nodes if n.type == "TEX_IMAGE" and n.image]
    faltan = [n.image.filepath for n in m.node_tree.nodes if n.type == "TEX_IMAGE" and n.image
              and not os.path.exists(bpy.path.abspath(n.image.filepath))]
    print("   %-28s imagenes %s%s" % (m.name, imgs or "NINGUNA", " | NO ENCONTRADAS: %s" % faltan if faltan else ""))

# render: en reposo y posado tirando de 足ＩＫ y de la mano si existe
escena = bpy.context.scene
escena.render.engine = "BLENDER_EEVEE"
escena.view_settings.view_transform = "Standard"
escena.render.resolution_x, escena.render.resolution_y = 800, 1100
cam = bpy.data.objects.new("CamMMD", bpy.data.cameras.new("CamMMD"))
escena.collection.objects.link(cam)
cam.data.type = "ORTHO"
# encuadre calculado con la caja real del modelo, para que no se corte la cabeza ni los pies
from mathutils import Vector
puntos = [o.matrix_world @ v.co for o in mallas for v in o.data.vertices]
minimo = Vector((min(p.x for p in puntos), min(p.y for p in puntos), min(p.z for p in puntos)))
maximo = Vector((max(p.x for p in puntos), max(p.y for p in puntos), max(p.z for p in puntos)))
centro = (minimo + maximo) / 2
alto = (maximo - minimo).z
cam.data.ortho_scale = max((maximo - minimo).x, alto, 4.0) * 1.25
cam.location = (centro.x, centro.y - alto * 2.5, centro.z)
cam.rotation_euler = (centro - Vector(cam.location)).to_track_quat("-Z", "Y").to_euler()
luz = bpy.data.objects.new("LuzMMD", bpy.data.lights.new("LuzMMD", "SUN"))
escena.collection.objects.link(luz)
luz.data.energy = 3.0
luz.rotation_euler = (math.radians(50), 0, math.radians(35))
escena.camera = cam
escena.render.filepath = os.path.join(SAL, "mmd_01_reposo.png")
bpy.ops.render.render(write_still=True)
print("render:", escena.render.filepath)

if arm:
    # postura suave, en unidades MMD (el modelo mide 20): un pie adelantado y el otro atras, nada mas.
    def mover(nombre, delta_mundo):
        b = arm.pose.bones.get(nombre)
        if not b:
            return
        local = b.bone.matrix_local.to_3x3().inverted() @ Vector(delta_mundo)
        b.location = tuple(b.location[i] + local[i] for i in range(3))
        print("   %s movido en el mundo %s" % (nombre, delta_mundo))

    mover("足ＩＫ.L", (0.0, -0.9, 0.15))
    mover("足ＩＫ.R", (0.0, 0.7, 0.0))
    bpy.context.view_layer.update()
    escena.render.filepath = os.path.join(SAL, "mmd_02_pose_ik.png")
    bpy.ops.render.render(write_still=True)
    print("render:", escena.render.filepath)
print("LISTO")