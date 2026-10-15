"""Prueba la receta completa: personaje + arma emparentada al hueso de la mano, y comprueba que
el arma sigue a la mano de verdad (no solo que el parent se aplique sin error).
"""
import bpy
import math
from mathutils import Vector

PAQUETE = r"C:\Users\Lukas\p5x-datamining\kotone_shiomi"
FULL = PAQUETE + r"\01_model\glb\Kotone_Shiomi_full.glb"
ARMA = PAQUETE + r"\01_model\obj\weapons\weapon_02.obj"

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=FULL)
bpy.ops.wm.obj_import(filepath=ARMA, forward_axis="Y", up_axis="Z")

arma = next(o for o in bpy.data.objects if o.name.startswith("weapon_02"))
armadura = next(o for o in bpy.data.objects if o.type == "ARMATURE")
mano = armadura.pose.bones["Bip01 R Hand"]
print("arma: %s    armadura: %s    hueso: %s" % (arma.name, armadura.name, mano.name))


def centro(obj):
    return sum((obj.matrix_world @ Vector(v) for v in obj.bound_box), Vector()) / 8


print("\ncentro del arma antes de emparentar: (%.3f, %.3f, %.3f)" % tuple(centro(arma)))

# la receta: seleccionar el arma y luego la armadura, y emparentar al hueso
bpy.ops.object.select_all(action="DESELECT")
arma.select_set(True)
armadura.select_set(True)
bpy.context.view_layer.objects.active = armadura
bpy.ops.object.mode_set(mode="POSE")
armadura.data.bones.active = armadura.data.bones["Bip01 R Hand"]
bpy.ops.object.parent_set(type="BONE", keep_transform=True)
bpy.ops.object.mode_set(mode="OBJECT")

print("emparentada. padre: %s   tipo: %s" % (arma.parent.name if arma.parent else None, arma.parent_type))
print("hueso padre: %s" % (arma.parent_bone or "(ninguno)"))
print("centro del arma tras emparentar: (%.3f, %.3f, %.3f)" % tuple(centro(arma)))

# mover la mano y ver si el arma se mueve con ella
antes = centro(arma)
bpy.context.view_layer.objects.active = armadura
bpy.ops.object.mode_set(mode="POSE")
pb = armadura.pose.bones["Bip01 R Hand"]
pb.rotation_mode = "QUATERNION"
pb.rotation_quaternion = (math.cos(0.5), 0, 0, math.sin(0.5))     # 1 radian
bpy.context.view_layer.update()
bpy.ops.object.mode_set(mode="OBJECT")

despues = centro(arma)
print("centro del arma tras girar la muneca 1 rad: (%.3f, %.3f, %.3f)" % tuple(despues))
print("desplazamiento: %.3f m" % (despues - antes).length)
print("veredicto: %s" % ("sigue a la mano" if (despues - antes).length > 1e-4
                         else "NO se mueve: el parent no ha funcionado"))