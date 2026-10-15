"""Deja la piel lista para posar: reencamina el peso de los huesos auxiliares del juego a los Bip01.

El problema medido: al girar el codo 90 grados habia aristas que se estiraban 22 veces. La causa no
son los pesos (suman 1.000 exacto en todos los vertices) sino SU REPARTO: parte del peso vive en
huesos auxiliares del juego (pelo `toufa_*`, accesorios `peishi_*`, y duplicados de la cadena de
brazo/pierna `Forearm_L_01/02`, `UpperArm_L_*`, `Calf_L_*`) que cuelgan a medias de la cadena Bip01.
Al girar una articulacion, unos vertices siguen al hueso auxiliar y sus vecinos al Bip01, y la malla
se desgarra.

El esqueleto NO se toca: los 54 huesos `Bip01` estan donde los puso el juego (derivados de las
inversas de bind). Lo unico que cambia es a que hueso apunta cada peso: el auxiliar se fusiona con su
equivalente anatomico. Es la version "creado a partir del original y lo mas parecido posible".

Uso: blender --background --python limpiar_pesos.py -- <blend_entrada> <blend_salida>
"""
import os
import sys

import bpy

ARG = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ENTRADA = ARG[0]
SALIDA = ARG[1] if len(ARG) > 1 else ENTRADA.replace(".blend", "_pesos_limpios.blend")

bpy.ops.wm.open_mainfile(filepath=ENTRADA)
arm = next((o for o in bpy.data.objects if o.type == "ARMATURE"), None)
if arm is None:
    sys.exit("no hay armadura")

# ---------------------------------------------------------------- mapa auxiliar -> anatomico
# Los nombres del juego son descriptivos: `toufa` = pelo, `peishi` = accesorio/adorno, `qiangtao` =
# vaina de la lanza, `gun` = pistola, `zhou` = codo. Los duplicados `_01/_02` de brazo y pierna son
# huesos de fisica del tejido; el equivalente anatomico es el Bip01 del mismo segmento.
FAMILIAS = (
    ("toufa_", "Bip01 Head"),            # pelo: que siga a la cabeza
    ("qiangtao_", "Bip01 Spine"),        # la vaina va a la espalda
    ("gun_", "Bip01 R Hand"),            # la pistola, en la mano
    ("_zhou_", None),                    # codo: al hueso de brazo mas cercano (se resuelve abajo)
)
SEGMENTOS = ("UpperArm", "Forearm", "Hand", "Thigh", "Calf", "Foot", "Toe0", "Clavicle", "Spine",
             "Spine1", "Spine2", "Neck", "Head", "Pelvis")


def destino_de(nombre, pos):
    """A que hueso Bip01 debe ir a parar el peso de este hueso auxiliar."""
    if nombre.startswith("Bip01"):
        return None                                   # ya es anatomico: no se toca
    for prefijo, fijo in FAMILIAS:
        if prefijo in nombre.lower():
            if fijo:
                return fijo
            return mas_cercano(nombre, pos)
    # Duplicados de la cadena: el sufijo _L/_R y el segmento del nombre dan el Bip01 exacto.
    lado = "L" if "_L" in nombre or nombre.endswith("L") else ("R" if "_R" in nombre else None)
    for seg in SEGMENTOS:
        if seg in nombre:
            if lado:
                cand = "Bip01 %s %s" % (lado, seg)
                if cand in arm.data.bones:
                    return cand
            return mas_cercano(nombre, pos)
    if nombre.startswith("BN_"):
        return None                                   # cara: cuelga bien de BN_head, se deja
    if nombre.startswith(("peishi_", "Bone_xi", "Magica")):
        return mas_cercano(nombre, pos)
    return mas_cercano(nombre, pos)


CACHE = {}


def mas_cercano(nombre, pos):
    """El Bip01 cuyo hueso pasa mas cerca de esta posicion."""
    if nombre in CACHE:
        return CACHE[nombre]
    hueso = arm.data.bones.get(nombre)
    p = hueso.head_local if hueso else pos
    mejor, md = None, 1e9
    for b in arm.data.bones:
        if not b.name.startswith("Bip01"):
            continue
        ab = b.tail_local - b.head_local
        t = 0.0 if ab.length_squared == 0 else max(0.0, min(1.0, (p - b.head_local).dot(ab) / ab.length_squared))
        d = (p - (b.head_local + ab * t)).length
        if d < md:
            mejor, md = b.name, d
    CACHE[nombre] = mejor
    return mejor


# ---------------------------------------------------------------- fusion de pesos
resumen = {}
objetos_usados = {}      # objeto -> nombres de grupo que si llevan peso tras la fusion
import collections
for o in [x for x in bpy.data.objects if x.type == "MESH" and x.data.vertices]:
    grupos = {g.index: g.name for g in o.vertex_groups}
    nuevos, tocados = {}, 0
    usados_objeto = set()
    for v in o.data.vertices:
        pesos = {}
        for g in v.groups:
            nombre = grupos.get(g.group, "?")
            if g.weight <= 0:
                continue
            hueso = arm.data.bones.get(nombre)
            destino = destino_de(nombre, hueso.head_local if hueso else (0, 0, 0))
            if destino is None:
                destino = nombre
            pesos[destino] = pesos.get(destino, 0.0) + g.weight
            if destino != nombre:
                resumen[(nombre, destino)] = resumen.get((nombre, destino), 0) + 1
                tocados += 1
        # glTF admite 4 influencias por vertice: se conservan las 4 mayores y se renormaliza
        mejores = sorted(pesos.items(), key=lambda kv: -kv[1])[:4]
        suma = sum(w for _, w in mejores) or 1.0
        for nombre in set(grupos.values()):
            g = o.vertex_groups.get(nombre)
            if g:
                g.remove([v.index])
        for nombre, w in mejores:
            g = o.vertex_groups.get(nombre) or o.vertex_groups.new(name=nombre)
            g.add([v.index], w / suma, "REPLACE")
            usados_objeto.add(nombre)
        nuevos[o.name] = nuevos.get(o.name, 0) + tocados
    objetos_usados[o] = usados_objeto
    print("  %-18s pesos reencaminados: %6d | grupos que llevan peso: %d de %d"
          % (o.name, nuevos.get(o.name, 0), len(usados_objeto), len(o.vertex_groups)))

print()
print("=== AUXILIAR -> ANATOMICO (vertices afectados) ===")
for (origen, destino), n in sorted(resumen.items(), key=lambda kv: -kv[1]):
    print("  %-28s -> %-20s %5d" % (origen[:28], destino, n))
print("familias reencaminadas:", len(resumen))

# Grupos que de verdad se han quedado sin peso: se quitan mirando los pesos REESCRITOS.
# (Trampa que ya me costo una malla entera sin piel: leer `v.groups` tras reescribir da datos
#  viejos, y borrar un grupo se lleva sus pesos. Por eso se cuenta con lo que hay en memoria.)
quitados = 0
for o, usados in objetos_usados.items():
    for g in list(o.vertex_groups):
        if g.name not in usados:
            o.vertex_groups.remove(g)
            quitados += 1
print("grupos de vertices vacios quitados:", quitados)

bpy.ops.wm.save_as_mainfile(filepath=SALIDA)
print("guardado:", SALIDA)