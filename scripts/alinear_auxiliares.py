
"""Alinea el reposo de los huesos auxiliares con el de su padre. No toca ni un peso.

Diagnostico medido: la peor arista al girar el codo (202 mm de alargamiento en una arista de 21 mm)
une dos vertices que pesan sobre `Bone_zhou_L`, `Forearm_L_01` y `UpperArm_L_02` - auxiliares del juego
cuyas posiciones de reposo estan mal derivadas (el vertice esta en x=-0.315 y sus huesos en x=+0.30).
Al girar el padre, esos huesos barren distinto que el Bip01 del que cuelgan y arrastran sus vertices.

Como la deformacion de un hueso es `pose * reposo^-1`, si se le da a un auxiliar el MISMO reposo que a
su padre, entonces se mueve exactamente como el padre: los pesos se quedan como el juego los dejo y el
desgarro desaparece. En reposo no cambia nada (el factor sigue siendo la identidad).

Uso: blender --background --python alinear_auxiliares.py -- <blend_entrada> <blend_salida>
"""
import sys

import bpy

ARG = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
bpy.ops.wm.open_mainfile(filepath=ARG[0])
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
INTOCABLES = ("Bip01", "BN_")

bpy.ops.object.mode_set(mode="EDIT")
alineados, sin_padre = 0, []
for eb in arm.data.edit_bones:
    if eb.name.startswith(INTOCABLES):
        continue
    padre = eb.parent
    if padre is None:
        sin_padre.append(eb.name)
        continue
    # el auxiliar pasa a tener la misma posicion, direccion y giro que su padre
    eb.head = padre.head.copy()
    eb.tail = padre.head + (padre.tail - padre.head).normalized() * 0.02
    eb.roll = padre.roll
    alineados += 1
bpy.ops.object.mode_set(mode="OBJECT")
print("huesos auxiliares alineados con su padre:", alineados)
print("huesos auxiliares sin padre (no se tocan):", len(sin_padre), sin_padre[:6])
print("huesos que deforman:", sum(1 for b in arm.data.bones if b.use_deform))
bpy.ops.wm.save_as_mainfile(filepath=ARG[1])
print("guardado:", ARG[1])
