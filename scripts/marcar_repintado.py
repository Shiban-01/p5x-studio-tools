"""Marca en un grupo de vertices las zonas de piel que hay que repintar a mano, y las resume por zona.

Para que sirve: medido, los pesos del juego son los mejores disponibles (seis intentos de rehacerlos
salieron peores) y las inversas de bind son identicas entre partes, asi que el estirón que aparece en
posturas forzadas no es un dato corrupto: es el precio de posar en estatico un esqueleto cuyos huesos
auxiliares (torsion de tela, correctores de codo) el juego mueve con animacion y fisica y nosotros no.

El arreglo fino es repintar a mano unos pocos anillos de vertices. Este script los localiza midiendo
(no a ojo) y los deja en el grupo `REPINTAR_piel_a_mano`, para que en el editor de pesos se vean
resaltados. El grupo es una GUIA: no es piel, no lleva pesos, y conviene borrarlo antes de exportar.

Uso: blender --background --python marcar_repintado.py -- <blend_entrada> [<blend_salida>]
"""
import math
import sys
from collections import Counter

import bpy

ARG = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ENTRADA = ARG[0]
SALIDA = ARG[1] if len(ARG) > 1 else ENTRADA
GRUPO = "REPINTAR_piel"
GRUPO_SEVERO = "REPINTAR_piel_GRAVE"
bpy.ops.wm.open_mainfile(filepath=ENTRADA)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
POSES = (("Bip01 L Forearm", "Z", 90), ("Bip01 R Forearm", "Z", -90), ("Bip01 L UpperArm", "Z", 60),
         ("Bip01 R UpperArm", "Z", -60), ("Bip01 L Calf", "X", 95), ("Bip01 R Calf", "X", 95),
         ("Bip01 L Thigh", "X", 70), ("Bip01 R Thigh", "X", -40), ("Bip01 Spine1", "X", 30),
         ("Bip01 Head", "Z", 45))
UMBRAL, MIN_LARGO = 1.10, 0.003


def limpiar():
    for b in arm.pose.bones:
        b.rotation_mode = "XYZ"
        b.rotation_euler = (0, 0, 0)
    bpy.context.view_layer.update()


def forma():
    bpy.context.view_layer.update()
    ev = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    m = ev.to_mesh()
    co = [ev.matrix_world @ v.co for v in m.vertices]
    ar = [(e.vertices[0], e.vertices[1]) for e in m.edges]
    ev.to_mesh_clear()
    return co, ar


for nombre in ("Kotone_Cuerpo", "Kotone_Pelo"):
    obj = bpy.data.objects.get(nombre)
    if obj is None:
        continue
    limpiar()
    co0, aristas = forma()
    largos = [(co0[a] - co0[b]).length for a, b in aristas]
    rotos, severos, vecinos = set(), set(), {}
    for a, b in aristas:
        vecinos.setdefault(a, set()).add(b)
        vecinos.setdefault(b, set()).add(a)
    for hueso, eje, grados in POSES:
        limpiar()
        b = arm.pose.bones[hueso]
        r = list(b.rotation_euler)
        r["XYZ".index(eje)] = math.radians(grados)
        b.rotation_euler = r
        co1, _ = forma()
        for (a, bb), l0 in zip(aristas, largos):
            if l0 < MIN_LARGO:
                continue
            razon = (co1[a] - co1[bb]).length / l0
            if razon > UMBRAL:
                rotos.add(a)
                rotos.add(bb)
            if razon > 1.25:                      # lo que de verdad salta a la vista
                severos.add(a)
                severos.add(bb)
    limpiar()
    costura = set(rotos)
    for v in list(rotos):
        costura |= vecinos.get(v, set())
    # a que hueso pertenece cada zona: para saber donde hay que repintar
    nombres = {g.index: g.name for g in obj.vertex_groups}
    cuenta = Counter()
    for i in costura:
        v = obj.data.vertices[i]
        if not v.groups:
            continue
        dominante = max(v.groups, key=lambda g: g.weight).group
        cuenta[nombres[dominante]] += 1
    viejo = obj.vertex_groups.get(GRUPO)
    if viejo:
        obj.vertex_groups.remove(viejo)
    for nombreg, conjunto in ((GRUPO, costura), (GRUPO_SEVERO, severos)):
        viejo = obj.vertex_groups.get(nombreg)
        if viejo:
            obj.vertex_groups.remove(viejo)
        g = obj.vertex_groups.new(name=nombreg)
        g.add(sorted(conjunto), 0.0, "REPLACE")      # peso 0: marca los vertices sin alterar la piel
    print("%s: %d vertices marcados de %d | de ellos GRAVES (>25%%): %d"
          % (nombre, len(costura), len(obj.data.vertices), len(severos)))
    print("   zonas (hueso dominante -> vertices):", cuenta.most_common(8))
bpy.ops.wm.save_as_mainfile(filepath=SALIDA)
print("guardado:", SALIDA)