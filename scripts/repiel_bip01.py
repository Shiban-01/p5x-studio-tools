"""Version buena de la repiel: conserva los pesos del juego y quita de en medio los auxiliares.

Regla por vertice:
  - si ya tiene peso en huesos `Bip01`, se queda con ESOS pesos (los del juego, que son los buenos) y
    se renormaliza;
  - si todo su peso vive en huesos auxiliares (pelo a `toufa_*`, accesorios a `peishi_*`, mangas a
    `UpperArm_L_*`), se le asigna el hueso Bip01 mas cercano con un reparto suave entre los dos
    candidatos de al lado.

Asi el reparto del juego se respeta donde existe y desaparece justo lo que desgarraba la malla.
Los accesorios rigidos van al 100% a un hueso anatomico y la cara/ojos/parpados no se tocan.
"""
import sys

import bpy
from mathutils import Vector

ARG = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ENTRADA = ARG[0]
SALIDA = ARG[1] if len(ARG) > 1 else ENTRADA.replace(".blend", "_repiel2.blend")
bpy.ops.wm.open_mainfile(filepath=ENTRADA)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
mallas = {o.name: o for o in bpy.data.objects if o.type == "MESH" and o.data.vertices}

RIGIDOS = {"Kotone_Brazalete": "Bip01 L UpperArm", "Kotone_Pistola": "Bip01 R Hand",
           "Kotone_Lanza": "Bip01 Spine", "Kotone_Vaina": "Bip01 Spine"}
INTOCABLES = ("Kotone_Cara", "Kotone_Ojos", "Kotone_Parpados")

# candidatos: los huesos Bip01 de deformacion, con su segmento en el mundo
CAND = []
for b in arm.data.bones:
    if b.name.startswith("Bip01") and b.use_deform:
        CAND.append((b.name, arm.matrix_world @ b.head_local, arm.matrix_world @ b.tail_local))


def distancia(p, a, bb):
    ab = bb - a
    t = 0.0 if ab.length_squared == 0 else max(0.0, min(1.0, (p - a).dot(ab) / ab.length_squared))
    return (p - (a + ab * t)).length


def por_proximidad(p, cuantos=2, potencia=6.0):
    ds = sorted(((distancia(p, a, bb), n) for n, a, bb in CAND))[:cuantos]
    pesos = [(n, 1.0 / max(d, 1e-4) ** potencia) for d, n in ds]
    total = sum(w for _, w in pesos) or 1.0
    return [(n, w / total) for n, w in pesos]


def limpiar_y_poner(o, v, tuplas):
    for g in list(o.vertex_groups):
        g.remove([v.index])
    for nombre, w in tuplas:
        g = o.vertex_groups.get(nombre) or o.vertex_groups.new(name=nombre)
        g.add([v.index], w, "REPLACE")


for nombre, o in mallas.items():
    if nombre in RIGIDOS:
        for g in list(o.vertex_groups):
            o.vertex_groups.remove(g)
        g = o.vertex_groups.new(name=RIGIDOS[nombre])
        g.add([v.index for v in o.data.vertices], 1.0, "REPLACE")
        print("  %-18s rigido al 100%% en %s" % (nombre, RIGIDOS[nombre]))
        continue
    if nombre in INTOCABLES:
        print("  %-18s sin tocar (pesos del juego para los visemas)" % nombre)
        continue
    indices = {g.index: g.name for g in o.vertex_groups}
    del_juego, rellenos = 0, 0
    for v in o.data.vertices:
        p = o.matrix_world @ v.co
        propios = [(indices.get(g.group, "?"), g.weight) for g in v.groups if g.weight > 0]
        bip = [(n, w) for n, w in propios if n.startswith("Bip01")]
        if sum(w for _, w in bip) > 0.05:
            total = sum(w for _, w in bip)
            mejores = sorted(bip, key=lambda kv: -kv[1])[:4]
            limpiar_y_poner(o, v, [(n, w / total) for n, w in mejores])
            del_juego += 1
        else:
            limpiar_y_poner(o, v, por_proximidad(p))
            rellenos += 1
    print("  %-18s pesos del juego conservados: %6d | rellenos por cercania: %5d" % (nombre, del_juego, rellenos))

# los huesos auxiliares ya no deforman nada: se apagan para que no ensucien el esquema
apagados = 0
for b in arm.data.bones:
    if not b.name.startswith(("Bip01", "BN_")) and b.use_deform:
        b.use_deform = False
        apagados += 1
print("huesos auxiliares apagados (ya no deforman):", apagados)
print("huesos que deforman:", sum(1 for b in arm.data.bones if b.use_deform))
bpy.ops.wm.save_as_mainfile(filepath=SALIDA)
print("guardado:", SALIDA)