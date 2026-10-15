"""Mide en el PMX reimportado si la rodilla (ひざ) esta a la altura de la rodilla y si el IK dobla ahi.

Imprime las alturas de 足 (muslo), ひざ (rodilla), 足首 (tobillo), y despues mueve 足ＩＫ.L como haria
una coreografia VMD y mide el angulo de doblez y donde queda la rodilla.

Uso: blender --background --python medir_pmx_rodilla.py -- <archivo.pmx>
"""
import math
import sys

import bpy

ARM = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ARM = ARM[0]
bpy.ops.preferences.addon_enable(module="bl_ext.user_default.mmd_tools")
if ARM.endswith(".pmx"):
    bpy.ops.mmd_tools.import_model(filepath=ARM, scale=1.0, types={"MESH", "ARMATURE", "MORPHS", "DISPLAY"},
                                   clean_model=False, rename_bones=False)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
print("armadura:", arm.name, "| huesos:", len(arm.data.bones))
def buscar(*claves, excluir=()):
    for pb in arm.pose.bones:
        if all(k in pb.name for k in claves) and not any(e in pb.name for e in excluir):
            return pb
    return None


print("--- alturas en reposo (unidades MMD; 20 = estatura) ---")
muslo = buscar("足", excluir=("首", "ＩＫ", "つま先", "ひざ"))
pierna = buscar("ひざ")
tobillo = buscar("足首")
ik = buscar("足ＩＫ")
for pb in (muslo, pierna, tobillo, buscar("つま先"), ik, buscar("上半身"), buscar("頭")):
    if pb:
        h = arm.matrix_world @ pb.head
        print("   %-12s z=%.2f   (y=%.2f x=%.2f)" % (pb.name, h.z, h.y, h.x))

if not (ik and pierna and muslo and tobillo):
    raise SystemExit("faltan huesos: muslo=%s rodilla=%s tobillo=%s ik=%s"
                     % (muslo, pierna, tobillo, ik))


def medir(etiqueta, desplazamiento):
    for pb in arm.pose.bones:
        pb.location = (0, 0, 0)
        pb.rotation_mode = "XYZ"
        pb.rotation_euler = (0, 0, 0)
    ik.location = desplazamiento
    bpy.context.view_layer.update()
    # con IK el resultado va a la matriz visual, no a rotation_euler
    p_muslo = (arm.matrix_world @ muslo.matrix).to_translation()
    p_rodilla = (arm.matrix_world @ pierna.matrix).to_translation()
    p_tobillo = (arm.matrix_world @ tobillo.matrix).to_translation()
    v1 = p_rodilla - p_muslo
    v2 = p_tobillo - p_rodilla
    ang = math.degrees(v1.angle(v2))
    print("   %-16s rodilla z=%.2f y=%+.2f | tobillo z=%.2f y=%+.2f | doblez=%5.1f grados"
          % (etiqueta, p_rodilla.z, p_rodilla.y, p_tobillo.z, p_tobillo.y, ang))


print("--- moviendo 足ＩＫ.L como una coreografia ---")
medir("reposo", (0, 0, 0))
medir("pie arriba 2", (0, 0, -2.0))       # adelante-abajo en el eje de MMD
medir("pie atras 2", (0, -2.0, -2.0))
medir("paso", (0, 3.0, -1.0))