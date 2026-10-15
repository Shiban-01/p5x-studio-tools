"""Mide la CALIDAD de la piel: normalizacion de pesos, huesos por vertice y cuanto se deforma al girar.

Sospechoso principal: si los pesos de un vertice no suman 1, la mezcla lineal encoge y estira la malla
al girar (se ve como "movio el personaje pero lo deformo"). Segundo sospechoso: la mezcla lineal de
matrices (LBS) aplasta las articulaciones; Blender puede usar cuaterniones dobles ("Preserve Volume"),
que en una malla con pesos de juego suele verse bastante mejor.
"""
import math
import sys

import bpy
from mathutils import Vector

ARG = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
BLEND = ARG[0]
bpy.ops.wm.open_mainfile(filepath=BLEND)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
mallas = [o for o in bpy.data.objects if o.type == "MESH" and o.data.vertices]

print("=== PESOS ===")
for o in mallas:
    sumas = []
    cuenta = []
    for v in o.data.vertices:
        s = sum(g.weight for g in v.groups)
        sumas.append(s)
        cuenta.append(len(v.groups))
    malos = sum(1 for s in sumas if abs(s - 1.0) > 0.01)
    print("%-18s verts %6d | suma pesos: min %.3f medio %.3f max %.3f | fuera de 1 (%.0f%%) %d | huesos/vert: max %d medio %.1f"
          % (o.name, len(sumas), min(sumas), sum(sumas) / len(sumas), max(sumas),
             100.0 * malos / len(sumas), malos, max(cuenta), sum(cuenta) / len(cuenta)))


def aristas(obj, evaluado):
    """Longitudes de arista de una malla (evaluada o no)."""
    dg = bpy.context.evaluated_depsgraph_get()
    if evaluado:
        ob = obj.evaluated_get(dg)
        m = ob.to_mesh()
        co = [ob.matrix_world @ v.co for v in m.vertices]
        ar = [(e.vertices[0], e.vertices[1]) for e in m.edges]
        ob.to_mesh_clear()
        return co, ar
    return [obj.matrix_world @ v.co for v in obj.data.vertices], [(e.vertices[0], e.vertices[1]) for e in obj.data.edges]


def limpiar():
    for b in arm.pose.bones:
        b.rotation_mode = "XYZ"
        b.rotation_euler = (0, 0, 0)
    bpy.context.view_layer.update()


def medir(cuerpo_nombre, hueso, grados, eje="Z", conserva_volumen=False):
    obj = bpy.data.objects[cuerpo_nombre]
    for o in mallas:
        for m in o.modifiers:
            if m.type == "ARMATURE":
                m.use_deform_preserve_volume = conserva_volumen
    limpiar()
    co0, ar = aristas(obj, False)
    b = arm.pose.bones[hueso]
    r = list(b.rotation_euler)
    r["XYZ".index(eje)] = math.radians(grados)
    b.rotation_euler = r
    bpy.context.view_layer.update()
    co1, _ = aristas(obj, True)
    # zona de la articulacion: cerca del hueso que gira
    punta = arm.matrix_world @ arm.pose.bones[hueso].head
    cerca, lejos = [], []
    for a, bb in ar:
        p = (co0[a] + co0[bb]) / 2
        l0 = (co0[a] - co0[bb]).length
        l1 = (co1[a] - co1[bb]).length
        if l0 < 1e-6:
            continue
        ratio = l1 / l0
        (cerca if (p - punta).length < 0.12 else lejos).append(ratio)
    limpiar()
    media = lambda x: (sum(x) / len(x)) if x else 0.0           # noqa: E731
    peor = max((abs(r - 1.0) for r in cerca), default=0.0)
    return (media(cerca), media(lejos), peor, sum(1 for r in cerca if abs(r - 1) > 0.10), len(cerca))


print()
print("=== DEFORMACION AL GIRAR (razon de longitud de arista: 1.0 = intacta) ===")
for etiqueta, hv, gr, eje in (("codo 90 grados", "Bip01 L Forearm", 90, "Z"),
                              ("hombro 60 grados", "Bip01 L UpperArm", 60, "Z"),
                              ("rodilla 90 grados", "Bip01 L Calf", 90, "X")):
    for cv in (False, True):
        mc, ml, peor, malas, n = medir("Kotone_Cuerpo", hv, gr, eje, cv)
        print("  %-18s %-16s codo %.3f | resto %.3f | aristas del codo movidas >10%%: %d/%d | peor %.2f"
              % (etiqueta, "con volumen" if cv else "lineal    ", mc, ml, malas, n, peor))
print("(cuanto mas cerca de 1.000 en 'codo', menos se aplasta la articulacion)")