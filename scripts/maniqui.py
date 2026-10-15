"""Convierte el rig del juego en un MANIQUI de posado: pocos huesos y articulaciones con tope.

Que hace:
  1. Arma un esqueleto nuevo de ~33 huesos (torso, brazos, piernas y un hueso por dedo).
  2. Refunde los pesos de las 9 mallas: cada hueso viejo se suma al del maniqui que le toca, asi el
     pelo se va con la cabeza y la falda con la cadera, y nada se queda colgando de un hueso suelto.
  3. Pone topes de giro: codo y rodilla doblan solo hacia donde doblan de verdad (el eje se calcula,
     no se supone) y el resto de articulaciones tiene un margen humano.
  4. Guarda Kotone_Shiomi_Maniqui.blend y exporta .glb y .fbx.

El fichero optimizado NO se toca. Uso:
  blender --background --python maniqui.py -- <blend_entrada> <blend_salida> [glb] [fbx]
"""
import math
import os
import sys

import bpy

from mathutils import Vector

entrada = sys.argv[sys.argv.index("--") + 1]
salida = sys.argv[sys.argv.index("--") + 2]
resto = sys.argv[sys.argv.index("--") + 3:]
glb = resto[0] if len(resto) > 0 else None
fbx = resto[1] if len(resto) > 1 else None

bpy.ops.wm.open_mainfile(filepath=entrada)
vieja = next(o for o in bpy.data.objects if o.type == "ARMATURE")
mallas = [o for o in bpy.data.objects if o.type == "MESH" and o.vertex_groups]

# ---------------------------------------------------------------------------
# 1) tabla del maniqui: nombre, padre, de donde sale la cabeza, de donde la cola,
#    y que huesos viejos entran (prefijos de nombre; None = solo lo que empareje aparte)
# ---------------------------------------------------------------------------
def dedos(lado):
    filas = []
    for n in range(5):
        filas.append(("Dedo%d_%s" % (n + 1, lado[0]),
                      "Mano_" + lado[0],
                      "Bip01 %s Finger%d" % (lado[1], n),
                      "Bip01 %s Finger%d2" % (lado[1], n),
                      ["Bip01 %s Finger%d" % (lado[1], n)]))
    return filas

def brazo(lado):
    l, L = lado  # l = "Izq"/"Der", L = "L"/"R"
    return [
        ("Hombro_%s" % l,    "Pecho",          "Bip01 %s Clavicle" % L, "Bip01 %s UpperArm" % L,
         ["Bip01 %s Clavicle" % L]),
        ("Brazo_%s" % l,     "Hombro_%s" % l,  "Bip01 %s UpperArm" % L, "Bip01 %s Forearm" % L,
         ["Bip01 %s UpperArm" % L, "UpperArm_%s_" % L, "xiuzhang_"]),
        ("Antebrazo_%s" % l, "Brazo_%s" % l,   "Bip01 %s Forearm" % L,  "Bip01 %s Hand" % L,
         ["Bip01 %s Forearm" % L, "Forearm_%s_" % L, "Bone_zhou_%s" % L]),
        ("Mano_%s" % l,      "Antebrazo_%s" % l, "Bip01 %s Hand" % L,   "Bip01 %s Hand" % L + "|tail",
         ["Bip01 %s Hand" % L, "CTRL_Mano_%s" % ("Der" if L == "R" else "Izq")]),
    ] + dedos((l, L))

def pierna(lado):
    l, L = lado
    return [
        ("Muslo_%s" % l,       "Cadera",           "Bip01 %s Thigh" % L, "Bip01 %s Calf" % L,
         ["Bip01 %s Thigh" % L, "Thigh_%s_" % L]),
        ("Pantorrilla_%s" % l, "Muslo_%s" % l,     "Bip01 %s Calf" % L,  "Bip01 %s Foot" % L,
         ["Bip01 %s Calf" % L, "Calf_%s_" % L, "Bone_xi_%s" % L]),
        ("Pie_%s" % l,         "Pantorrilla_%s" % l, "Bip01 %s Foot" % L, "Bip01 %s Toe0" % L,
         ["Bip01 %s Foot" % L, "CTRL_Pie_%s" % ("Der" if L == "R" else "Izq")]),
        ("DedoPie_%s" % l,     "Pie_%s" % l,      "Bip01 %s Toe0" % L, "Bip01 %s Toe0" % L + "|tail",
         ["Bip01 %s Toe0" % L]),
    ]

MANIQUI = [
    ("Raiz",      None,        "Bip01",            "Bip01",            ["CTRL_Raiz"]),
    ("Cadera",    "Raiz",      "Bip01 Pelvis",     "Bip01 Spine",      ["peishi_", "qunzi_"]),
    ("Columna_1", "Cadera",    "Bip01 Spine",      "Bip01 Spine1",     []),
    ("Columna_2", "Columna_1", "Bip01 Spine1",     "Bip01 Spine2",     []),
    ("Pecho",     "Columna_2", "Bip01 Spine2",     "Bip01 Neck",       ["yiling_", "xuzi_"]),
    ("Cuello",    "Pecho",     "Bip01 Neck",       "Bip01 Head",       []),
    ("Cabeza",    "Cuello",    "Bip01 Head",       "Bip01 Head|tail",  ["BN_", "toufa_", "h_Motion", "h_M_"]),
] + brazo(("Izq", "L")) + brazo(("Der", "R")) + pierna(("Izq", "L")) + pierna(("Der", "R"))

# ---------------------------------------------------------------------------
# 2) a que hueso del maniqui va cada hueso viejo
# ---------------------------------------------------------------------------
MAPEO, sin_mapear = {}, []
for fila in MANIQUI:
    for patron in fila[4]:
        for b in vieja.data.bones:
            if patron in b.name:
                MAPEO[b.name] = fila[0]

# Nombres EXACTOS del tronco y la cabeza: no pueden ir por prefijo, porque "Bip01 Spine" tambien
# casa con "Bip01 Spine1" y se llevaria los tres. Van a mano y despues del bucle, para que manden.
EXACTOS = {"Bip01": "Raiz", "Bip01 Pelvis": "Cadera", "Bip01 Spine": "Columna_1",
           "Bip01 Spine1": "Columna_2", "Bip01 Spine2": "Pecho", "Bip01 Neck": "Cuello",
           "Bip01 Head": "Cabeza"}
EXACTOS.update({"Bip01 %s %s" % (L, n): "Hombro_%s" % ("Izq" if L == "L" else "Der")
                for L in "LR" for n in ("Clavicle",)})
for _n, _d in EXACTOS.items():
    if _n in vieja.data.bones:
        MAPEO[_n] = _d

# Cadenas de accesorios que cuelgan de un hueso concreto: la vaina y la lanza van a la cadera
# (cuelgan del pelvis en el juego) y la pistola a la mano derecha.
PREFIJOS_EXTRA = {"qiangtao_": "Cadera", "gun_": "Mano_Der"}
for _p, _d in PREFIJOS_EXTRA.items():
    for b in vieja.data.bones:
        if b.name.startswith(_p):
            MAPEO[b.name] = _d

for b in vieja.data.bones:
    if b.name not in MAPEO:
        sin_mapear.append(b.name)

# ---------------------------------------------------------------------------
# 3) huesos del maniqui, colocados sobre los del juego
# ---------------------------------------------------------------------------
def punto(expr):
    """'Bip01 X' -> cabeza del hueso; 'Bip01 X|tail' -> su cola."""
    nombre, cola = (expr.split("|") + ["head"])[:2] if "|" in expr else (expr, "head")
    h = vieja.data.bones[nombre]
    return h.tail_local if cola == "tail" else h.head_local

datos = bpy.data.armatures.new("Kotone_Maniqui")
nueva = bpy.data.objects.new("Kotone_Maniqui", datos)
bpy.context.collection.objects.link(nueva)
bpy.context.view_layer.objects.active = nueva
bpy.ops.object.mode_set(mode="EDIT")
creados = {}
for nombre, padre, cab, cola, _ in MANIQUI:
    eb = datos.edit_bones.new(nombre)
    eb.head, eb.tail = punto(cab), punto(cola)
    if eb.tail.length < 0.005:                      # una cola nunca puede ser cero
        eb.tail = eb.head + Vector((0, 0, 0.02))
    if padre:
        eb.parent = creados[padre]
        eb.use_connect = False
    creados[nombre] = eb
bpy.ops.object.mode_set(mode="OBJECT")

# ---------------------------------------------------------------------------
# 4) refundir los pesos: se suman en el hueso nuevo y se renormaliza a 1
# ---------------------------------------------------------------------------
def mas_cercano(v):
    """Ultimo recurso: hueso del maniqui mas cercano al que se quedo sin destino."""
    return min(MANIQUI, key=lambda f: (punto(f[2]) - v).length)[0]


def destino_por_ancestro(hueso):
    """Sube por la cadena del juego hasta el primer hueso que ya tiene destino.

    Por cercania en el espacio no vale: la lanza, que cuelga del pelvis, acababa pegada al muslo, y
    una pieza de la pistola en el pie. La cadena dice de quien depende cada hueso de verdad.
    """
    a = hueso.parent
    while a is not None:
        if a.name in MAPEO:
            return MAPEO[a.name]
        a = a.parent
    return None

reparto = {}                                        # malla -> {nombre nuevo: {vertice: peso}}
for ob in mallas:
    acumulado = {}
    for g in ob.vertex_groups:
        destino = MAPEO.get(g.name)
        for v in ob.data.vertices:
            for e in v.groups:
                if e.group == g.index and e.weight > 0:
                    if destino is None:
                        destino = destino_por_ancestro(vieja.data.bones[g.name])
                        if destino is None:
                            destino = mas_cercano(vieja.data.bones[g.name].head_local)
                            print("   aviso: %s sin ancestro con destino, se va a %s"
                                  % (g.name, destino))
                        MAPEO[g.name] = destino
                    acumulado.setdefault(destino, {}).setdefault(v.index, 0.0)
                    acumulado[destino][v.index] += e.weight
    reparto[ob.name] = acumulado

    for g in list(ob.vertex_groups):
        ob.vertex_groups.remove(g)
    for destino, vertices in acumulado.items():
        grupo = ob.vertex_groups.new(name=destino)
        for vi, peso in vertices.items():
            total = sum(v[vi] for v in acumulado.values() if vi in v)
            grupo.add([vi], peso / total if total else 0.0, "REPLACE")
    for m in ob.modifiers:
        if m.type == "ARMATURE":
            m.object = nueva
    ob.parent = nueva

print("=== mallas: huesos por malla tras refundir ===")
for ob in mallas:
    print("   %-18s %3d huesos" % (ob.name, len(reparto[ob.name])))
print("sin mapear:", len(sin_mapear), sorted(sin_mapear)[:6])
print("huesos viejos con destino: %d" % len(MAPEO))

# ---------------------------------------------------------------------------
# 5) topes de giro
# ---------------------------------------------------------------------------
EJE_EXTRA = []                                      # (hueso, eje local, min, max)
for pb in nueva.pose.bones:
    pb.rotation_mode = "XYZ"


def eje_del_doblez(hijo):
    """Eje (en espacio del hueso hijo) alrededor del cual dobla la articulacion de verdad."""
    a = nueva.data.bones[hijo].parent
    d1 = (a.tail_local - a.head_local).normalized()
    b = nueva.data.bones[hijo]
    d2 = (b.tail_local - b.head_local).normalized()
    eje_mundo = d1.cross(d2)
    if eje_mundo.length < 1e-4:
        return None
    eje_mundo.normalize()
    local = b.matrix_local.to_3x3().inverted() @ eje_mundo
    indice = max(range(3), key=lambda i: abs(local[i]))
    return ("XYZ"[indice], eje_mundo, indice, local[indice])


# codo y rodilla: eje medido; el resto: margen humano.
# El SIGNO tampoco se supone: se suelta la articulacion 10 grados a cada lado y se mira hacia donde
# se mueve la punta de la cadena. Codo: la mano va adelante (-Y). Rodilla: el pie va atras (+Y).
# (Deducirlo del componente local del eje da el signo al reves en las cuatro articulaciones.)
for hueso in ("Antebrazo_Izq", "Antebrazo_Der", "Pantorrilla_Izq", "Pantorrilla_Der"):
    info = eje_del_doblez(hueso)
    if not info:
        print("   %s: no se pudo medir el eje, se deja libre" % hueso)
        continue
    eje, eje_mundo, indice, componente = info
    punta = [f[0] for f in MANIQUI if f[1] == hueso][0]          # Mano_* o Pie_*
    pb_h, pb_p = nueva.pose.bones[hueso], nueva.pose.bones[punta]
    esperado = -1 if hueso.startswith("Antebrazo") else +1
    base = (nueva.matrix_world @ pb_p.tail).copy()
    desvio = {}
    for signo in (1, -1):
        pb_h.rotation_euler = [0, 0, 0]
        pb_h.rotation_euler[indice] = math.radians(10) * signo
        bpy.context.view_layer.update()
        desvio[signo] = ((nueva.matrix_world @ pb_p.tail) - base).y
    pb_h.rotation_euler = [0, 0, 0]
    bpy.context.view_layer.update()
    natural = max(desvio, key=lambda s: desvio[s] * esperado)

    c = pb_h.constraints.new("LIMIT_ROTATION")
    c.owner_space = "LOCAL"
    setattr(c, "use_limit_" + eje.lower(), True)
    tope = math.radians(150)
    if natural > 0:
        setattr(c, "min_" + eje.lower(), 0.0)
        setattr(c, "max_" + eje.lower(), tope)
    else:
        setattr(c, "min_" + eje.lower(), -tope)
        setattr(c, "max_" + eje.lower(), 0.0)
    for otro in "XYZ".replace(eje, ""):
        setattr(c, "use_limit_" + otro.lower(), True)
        setattr(c, "min_" + otro.lower(), math.radians(-25))
        setattr(c, "max_" + otro.lower(), math.radians(25))
    print("   %-16s dobla en %s, sentido %+d (la punta va hacia %s) de 0 a 150 grados"
          % (hueso, eje, natural, "-Y" if desvio[natural] < 0 else "+Y"))

MARGENES = {"Cuello": 50, "Cabeza": 55, "Columna_1": 30, "Columna_2": 30, "Pecho": 30,
            "Cadera": 40, "Mano_Izq": 60, "Mano_Der": 60, "Pie_Izq": 45, "Pie_Der": 45,
            "Brazo_Izq": 110, "Brazo_Der": 110, "Muslo_Izq": 100, "Muslo_Der": 100}
puestos = 0
for hueso, grados in MARGENES.items():
    if not any(c.type == "LIMIT_ROTATION" for c in nueva.pose.bones[hueso].constraints):
        c = nueva.pose.bones[hueso].constraints.new("LIMIT_ROTATION")
        c.owner_space = "LOCAL"
        for eje in "XYZ":
            setattr(c, "use_limit_" + eje.lower(), True)
            setattr(c, "min_" + eje.lower(), math.radians(-grados))
            setattr(c, "max_" + eje.lower(), math.radians(grados))
        puestos += 1
print("topes: %d articulaciones con margen humano + 4 doblando en un solo sentido" % puestos)

datos.display_type = "OCTAHEDRAL"
nueva.show_in_front = True

# ---------------------------------------------------------------------------
# 6) comprobaciones y guardado
# ---------------------------------------------------------------------------
sin_peso = []
for ob in mallas:
    for v in ob.data.vertices:
        if sum(e.weight for e in v.groups) < 0.99:
            sin_peso.append((ob.name, v.index))
            break
print("vertices sin peso completo: %d mallas afectadas %s"
      % (len(sin_peso), sorted({x[0] for x in sin_peso}) or "ninguna"))

os.makedirs(os.path.dirname(salida), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=salida)
print("guardado: %s (%d KB)" % (salida, os.path.getsize(salida) // 1024))
if glb:
    bpy.ops.export_scene.gltf(filepath=glb, export_format="GLB", export_apply=False,
                              export_animations=False, export_yup=True)
    print("glb: %s (%d KB)" % (glb, os.path.getsize(glb) // 1024))
if fbx:
    bpy.ops.export_scene.fbx(filepath=fbx, path_mode="COPY", embed_textures=True,
                             use_selection=False, add_leaf_bones=False, bake_space_transform=False)
    print("fbx: %s (%d KB)" % (fbx, os.path.getsize(fbx) // 1024))
print("HUESOS FINALES: %d" % len(nueva.data.bones))
