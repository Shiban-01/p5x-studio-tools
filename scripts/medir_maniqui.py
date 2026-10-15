"""Mueve un hueso a la vez y mide que trozos de malla responden.

Sirve para cazar piezas mal atadas: si al girar 'Pie_Izq' se mueve algo que no sea el pie, o si al
girar la cabeza se mueve el cuerpo, el refundido de pesos esta mal.
Uso: blender --background --python medir_maniqui.py -- <blend>
"""
import math
import sys

import bpy

bpy.ops.wm.open_mainfile(filepath=sys.argv[sys.argv.index("--") + 1])
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
mallas = [o for o in bpy.data.objects if o.type == "MESH"]


def leer(dg):
    salida = {}
    for ob in mallas:
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        salida[ob.name] = [ob.matrix_world @ v.co for v in me.vertices]
        ev.to_mesh_clear()
    return salida


bpy.context.view_layer.update()
referencia = leer(bpy.context.evaluated_depsgraph_get())

CLAVES = ["Cabeza", "Cuello", "Brazo_Der", "Mano_Der", "Antebrazo_Izq", "Muslo_Izq",
          "Pantorrilla_Der", "Pie_Izq", "Cadera", "Dedo1_Izq"]
print("=== giro de 20 grados en cada hueso: que malla se mueve y en que franja de altura ===")
for hueso in CLAVES:
    pb = arm.pose.bones[hueso]
    pb.rotation_mode = "XYZ"
    pb.rotation_euler = (math.radians(20), 0, 0)
    bpy.context.view_layer.update()
    ahora = leer(bpy.context.evaluated_depsgraph_get())
    pb.rotation_euler = (0, 0, 0)
    bpy.context.view_layer.update()

    trozos = []
    for ob in mallas:
        indices = [i for i, (a, b) in enumerate(zip(referencia[ob.name], ahora[ob.name]))
                   if (a - b).length > 0.002]
        if indices:
            zs = [referencia[ob.name][i].z for i in indices]
            trozos.append("%s %d v (Z %.2f-%.2f)" % (ob.name.replace("Kotone_", ""), len(indices),
                                                     min(zs), max(zs)))
    print("   %-16s %s" % (hueso, " | ".join(trozos) or "NO MUEVE NADA"))

# cada hueso del maniqui debe tener su grupo en las mallas que le tocan
print()
print("=== huesos del maniqui sin ningun vertice asignado ===")
vacios = []
for b in arm.data.bones:
    total = 0
    for ob in mallas:
        g = ob.vertex_groups.get(b.name)
        if g:
            total += sum(1 for v in ob.data.vertices for e in v.groups
                         if e.group == g.index and e.weight > 0)
    if total == 0:
        vacios.append(b.name)
print("   ", ", ".join(vacios) or "ninguno")
