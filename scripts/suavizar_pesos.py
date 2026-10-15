"""Arregla el desgarro de la piel donde ocurre, y solo donde ocurre: suavizado local de pesos.

Medido: con el codo a 90 grados, 229 de las 30.000 aristas utiles (las de mas de 3 mm) se alargan mas
de un 10%, y la peor -una de 21 mm- se alarga 202 mm. Son las costuras donde unos vertices tiran de un
hueso auxiliar del juego y sus vecinos de la cadena Bip01. Rehacer los pesos entero lo empeora (el
calculo por cercania es mas tosco que el del juego), asi que se hace lo quirurgico:

  1. se miden varias poses y se recoge el conjunto de vertices que participan en aristas rotas;
  2. se amplia ese conjunto un anillo (sus vecinos tambien cuentan, son la costura);
  3. solo a esos vertices se les mezcla su peso con la media de sus vecinos, unas cuantas veces;
  4. se renormaliza y se deja como maximo 4 huesos por vertice (lo que admite glTF).

El reparto del juego se queda intacto en los otros ~14.000 vertices.

Uso: blender --background --python suavizar_pesos.py -- <blend_entrada> <blend_salida>
"""
import math
import sys

import bpy
from mathutils import Vector

ARG = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ENTRADA = ARG[0]
SALIDA = ARG[1] if len(ARG) > 1 else ENTRADA.replace(".blend", "_suave.blend")
bpy.ops.wm.open_mainfile(filepath=ENTRADA)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
OBJETIVO = "Kotone_Cuerpo"
obj = bpy.data.objects[OBJETIVO]

POSES = (("Bip01 L Forearm", "Z", 90), ("Bip01 R Forearm", "Z", -90), ("Bip01 L UpperArm", "Z", 60),
         ("Bip01 L Calf", "X", 95), ("Bip01 R Calf", "X", 95), ("Bip01 Spine1", "X", 30),
         ("Bip01 L Thigh", "X", 70), ("Bip01 Head", "Z", 45))
UMBRAL, MIN_LARGO = 1.10, 0.003


def limpiar():
    for b in arm.pose.bones:
        b.rotation_mode = "XYZ"
        b.rotation_euler = (0, 0, 0)
    bpy.context.view_layer.update()


def coords():
    bpy.context.view_layer.update()
    ev = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    m = ev.to_mesh()
    co = [ev.matrix_world @ v.co for v in m.vertices]
    ar = [(e.vertices[0], e.vertices[1]) for e in m.edges]
    ev.to_mesh_clear()
    return co, ar


limpiar()
co0, aristas = coords()
largos0 = [(co0[a] - co0[b]).length for a, b in aristas]

# ---------------------------------------------------------------- 1 y 2. que vertices se rompen
rotos = set()
for hueso, eje, grados in POSES:
    limpiar()
    b = arm.pose.bones[hueso]
    r = list(b.rotation_euler)
    r["XYZ".index(eje)] = math.radians(grados)
    b.rotation_euler = r
    co1, _ = coords()
    for (a, bb), l0 in zip(aristas, largos0):
        if l0 < MIN_LARGO:
            continue
        if (co1[a] - co1[bb]).length / l0 > UMBRAL:
            rotos.add(a)
            rotos.add(bb)
limpiar()
vecinos = {}
for a, bb in aristas:
    vecinos.setdefault(a, set()).add(bb)
    vecinos.setdefault(bb, set()).add(a)
costura = set(rotos)
for v in list(rotos):
    costura |= vecinos.get(v, set())
print("vertices que participan en aristas rotas: %d | con su anillo: %d de %d"
      % (len(rotos), len(costura), len(obj.data.vertices)))

# ---------------------------------------------------------------- 3. suavizado local
nombres = {g.index: g.name for g in obj.vertex_groups}
pesos = []
for v in obj.data.vertices:
    pesos.append({nombres.get(g.group, "?"): g.weight for g in v.groups if g.weight > 0})


def mezclar(i):
    propios = pesos[i]
    acumulado = {}
    for vecino in vecinos.get(i, ()):
        for n, w in pesos[vecino].items():
            acumulado[n] = acumulado.get(n, 0.0) + w
    if not acumulado:
        return propios
    n_vec = float(len(vecinos.get(i, ())) or 1)
    for n in acumulado:
        acumulado[n] /= n_vec
    salida = {}
    for n in set(propios) | set(acumulado):
        salida[n] = 0.35 * propios.get(n, 0.0) + 0.65 * acumulado.get(n, 0.0)
    return salida


for vuelta in range(4):
    nuevos = {}
    for i in costura:
        mejores = sorted(mezclar(i).items(), key=lambda kv: -kv[1])[:4]
        total = sum(w for _, w in mejores) or 1.0
        nuevos[i] = {n: w / total for n, w in mejores if w / total > 1e-4}
    pesos_previos = pesos
    for i, d in nuevos.items():
        pesos_previos[i] = d
    pesos = pesos_previos
    print("  vuelta %d de suavizado" % (vuelta + 1))

for i in costura:
    for g in list(obj.vertex_groups):
        g.remove([i])
    for n, w in pesos[i].items():
        g = obj.vertex_groups.get(n) or obj.vertex_groups.new(name=n)
        g.add([i], w, "REPLACE")

# ---------------------------------------------------------------- 4. comprobacion
sumas = [sum(g.weight for g in v.groups) for v in obj.data.vertices]
print("suma de pesos: min %.3f max %.3f | maximo de huesos por vertice: %d"
      % (min(sumas), max(sumas), max(len(v.groups) for v in obj.data.vertices)))

bpy.ops.wm.save_as_mainfile(filepath=SALIDA)
print("guardado:", SALIDA)