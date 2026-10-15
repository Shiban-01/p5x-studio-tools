"""Arregla la cadena de las PIERNAS para que el IK doble en la rodilla de verdad.

Diagnostico medido en el modelo tal como viene del juego:

    hueso            cabeza (z)          largo    vertices con peso
    Bip01 L Thigh    1.296  (pecho)      0.118    0
    Bip01 L Calf     0.911  (CADERA)     0.510    0
    Bip01 L Foot     0.102  (tobillo)    0.134    482
    Thigh_L_01       0.941  (cadera OK)  0.118    si
    Bone_xi_L        0.504  (rodilla OK) 0.118    si
    Calf_L_01/02     0.504 / 0.309       0.510    si

El juego usa los Bip01 como huesos gruesos de control y la piel la llevan los auxiliares, cuyas cabezas
SI son las articulaciones reales. Resultado: el IK de la pierna resuelve con un alcance de 0.118+0.510 =
0.63 m cuando la pierna mide 1.20 m, y dobla en un punto que esta a la altura de la cadera. Los brazos
no tienen este problema (su cadena mide 0.59 m y la real ~0.55).

Que hace:
  1. cabeza de Bip01 * Thigh = cabeza del auxiliar de cadera (Thigh_*_01)
  2. cabeza de Bip01 * Calf  = cabeza del auxiliar de rodilla (Bone_xi_*)
  3. el muslo pasa a colgar de Bip01 Pelvis en vez de Bip01 Spine
  4. colas encadenadas: muslo->rodilla, pantorrilla->tobillo, pie->punta
  5. roll alineado para que flexionar sea girar sobre el X local
  6. limite de IK en las rodillas, con el signo MEDIDO (se gira +20 grados y se mira si el tobillo va
     hacia atras, que es como se dobla una rodilla). Ese limite es el que MMD exporta como limite del
     enlace ひざ, asi que arreglarlo aqui arregla tambien el PMX.

At rest nothing changes (the deform is the identity), so this is safe for the already verified skin.

Uso: blender --background --python arreglar_piernas.py -- <entrada.blend> <salida.blend>
"""
import math
import sys

import bpy
from mathutils import Vector

ARG = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ENTRADA, SALIDA = ARG[0], ARG[1]

bpy.ops.wm.open_mainfile(filepath=ENTRADA)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
cuerpo = next((o for o in bpy.data.objects if o.type == "MESH" and len(o.data.vertices) > 10000), None)
print("=== %s: %d huesos ===" % (arm.name, len(arm.data.bones)))

# El blend de artistas puede traer colecciones ocultas/excluidas y con restricciones activas.
# Hay que desocultar todo para poder editar el esqueleto, y APAGAR las restricciones mientras se
# mide: un IK en vuelo anula cualquier rotacion manual y da mediciones falsas.
for lc in [bpy.context.view_layer.layer_collection] + list(bpy.context.view_layer.layer_collection.children):
    lc.exclude = False
    lc.hide_viewport = False
    lc.collection.hide_viewport = False
for o in bpy.data.objects:
    o.hide_viewport = False
    o.hide_set(False)
apagadas = []
for pb in arm.pose.bones:
    for c in pb.constraints:
        if not c.mute:
            apagadas.append(c)
            c.mute = True
print("restricciones apagadas mientras se mide: %d" % len(apagadas))


def punta_de(nombre):
    """Cabeza del hueso, en coordenadas de la armadura."""
    b = arm.data.bones.get(nombre)
    return b.head_local.copy() if b else None


# la malla tal como esta, para comprobar despues que en reposo no se movio ni un milimetro
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
ev = cuerpo.evaluated_get(dg)
malla = ev.to_mesh()
referencia = [ev.matrix_world @ v.co for v in malla.vertices]
ev.to_mesh_clear()

bpy.context.view_layer.objects.active = arm
arm.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
eb = arm.data.edit_bones
if not eb:
    raise SystemExit("ERROR: no se pudo entrar en modo edicion en %s" % arm.name)
print("huesos editables: %d" % len(eb))

print("--- antes ---")
for n in ("Bip01 L Thigh", "Bip01 L Calf", "Bip01 L Foot"):
    b = eb.get(n)
    if b:
        print("   %-16s cabeza z=%.3f  largo=%.3f" % (n, b.head.z, b.length))

for lado in ("L", "R"):
    muslo = eb.get("Bip01 %s Thigh" % lado)
    pantorrilla = eb.get("Bip01 %s Calf" % lado)
    pie = eb.get("Bip01 %s Foot" % lado)
    punta = eb.get("Bip01 %s Toe0" % lado)
    cadera_aux = eb.get("Thigh_%s_01" % lado)
    rodilla_aux = eb.get("Bone_xi_%s" % lado)
    pelvis = eb.get("Bip01 Pelvis")
    if not (muslo and pantorrilla and pie and cadera_aux and rodilla_aux):
        print("   lado %s: faltan huesos, se salta" % lado)
        continue
    # 1 y 2: las cabezas van a las articulaciones reales que marcan los auxiliares
    muslo.head = cadera_aux.head.copy()
    pantorrilla.head = rodilla_aux.head.copy()
    hombro_aux = eb.get("UpperArm_%s_01" % lado)
    codo_aux = eb.get("Bone_zhou_%s" % lado)
    if hombro_aux and eb.get("Bip01 %s UpperArm" % lado):
        eb["Bip01 %s UpperArm" % lado].head = hombro_aux.head.copy()
    if codo_aux and eb.get("Bip01 %s Forearm" % lado):
        eb["Bip01 %s Forearm" % lado].head = codo_aux.head.copy()
    # 3: la pierna cuelga de la pelvis, no de la columna
    if pelvis and muslo.parent != pelvis:
        muslo.parent = pelvis
        muslo.use_connect = False
# 4: colas encadenadas — cada cola cae en la cabeza del hijo, que es donde el IK apunta de verdad
for lado in ("L", "R"):
    for padre, hijo in (("Bip01 %s UpperArm" % lado, "Bip01 %s Forearm" % lado),
                        ("Bip01 %s Forearm" % lado, "Bip01 %s Hand" % lado),
                        ("Bip01 %s Hand" % lado, "Bip01 %s Finger0" % lado)):
        b, c = eb.get(padre), eb.get(hijo)
        if b and c:
            b.tail = c.head.copy()
    muslo, pantorrilla = eb.get("Bip01 %s Thigh" % lado), eb.get("Bip01 %s Calf" % lado)
    pie, punta = eb.get("Bip01 %s Foot" % lado), eb.get("Bip01 %s Toe0" % lado)
    if muslo and pantorrilla:
        muslo.tail = pantorrilla.head.copy()
    if pantorrilla and pie:
        pantorrilla.tail = pie.head.copy()
    if pie and punta:
        pie.tail = punta.head.copy()

# 5: roll para que la flexion sea sobre el X local (el personaje mira a -Y)
for b in eb:
    if b.name.startswith("Bip01") and any(f in b.name for f in ("Thigh", "Calf", "Foot")):
        b.align_roll(Vector((0.0, 1.0, 0.0)))

# 7: los controles de IK tienen que estar exactamente en la punta de su cadena. El IK apunta la COLA
# del hueso al control: si el control esta en otro sitio, al abrir el archivo el IK tuerce el miembro
# (medido: 0.79 m en los brazos, 0.35 m en los pies).
movidos = 0
for pb in arm.pose.bones:
    for c in pb.constraints:
        if c.type == "IK" and c.subtarget:
            ctrl = eb.get(c.subtarget)
            hueso_edit = eb.get(pb.name)
            if not (ctrl and hueso_edit):
                continue
            punta = hueso_edit.tail
            if (ctrl.head - punta).length > 1e-4:
                delta = punta - ctrl.head
                ctrl.head = ctrl.head + delta
                ctrl.tail = ctrl.tail + delta
                movidos += 1
                print("   control %-22s reubicado en la punta de %s (+%.3f m)" % (ctrl.name, pb.name, delta.length))
print("controles de IK reubicados: %d" % movidos)

# 8: las copias de posicion y de ROTACION tienen que ser RELATIVAS. En absoluto, un control raiz en el
# origen arrastra la pelvis al suelo (1.38 m medidos) y una copia de rotacion impone la orientacion del
# control, torciendo el pie (0.35 m). En relativo el reposo se conserva siempre: el control mueve desde
# donde esta.
arregladas = 0
for pb in arm.pose.bones:
    for c in pb.constraints:
        if c.type in ("COPY_LOCATION", "COPY_ROTATION") and not c.use_offset:
            c.use_offset = True
            arregladas += 1
            print("   %-14s de %-16s marcada como relativa (objetivo %s)"
                  % (c.type, pb.name, c.subtarget or (c.target.name if c.target else "?")))
        if c.type == "COPY_LOCATION" and (c.target_space != "LOCAL" or c.owner_space != "LOCAL"):
            print("   COPY_LOCATION de %-16s: espacios %s/%s -> LOCAL/LOCAL"
                  % (pb.name, c.target_space, c.owner_space))
            c.target_space = "LOCAL"
            c.owner_space = "LOCAL"
            arregladas += 1
        if c.type == "COPY_ROTATION" and (c.target_space != "LOCAL" or c.owner_space != "LOCAL"):
            # en espacio mundo el "relativo" mezcla el reposo del control con el del hueso y el pie
            # sale girado 0.26 m. En local la copia es respecto al propio hueso: en reposo, cero.
            print("   COPY_ROTATION de %-16s: espacios %s/%s -> LOCAL/LOCAL"
                  % (pb.name, c.target_space, c.owner_space))
            c.target_space = "LOCAL"
            c.owner_space = "LOCAL"
            arregladas += 1
print("restricciones de copia corregidas: %d" % arregladas)

print("--- despues ---")
for n in ("Bip01 L Thigh", "Bip01 L Calf", "Bip01 L Foot"):
    b = eb.get(n)
    if b:
        print("   %-16s cabeza z=%.3f  largo=%.3f" % (n, b.head.z, b.length))

bpy.ops.object.mode_set(mode="OBJECT")


# 6: limite de IK medido
def limpiar():
    for pb in arm.pose.bones:
        pb.rotation_mode = "XYZ"
        pb.rotation_euler = (0, 0, 0)
        pb.location = (0, 0, 0)
    bpy.context.view_layer.update()


for lado in ("L", "R"):
    pb = arm.pose.bones.get("Bip01 %s Calf" % lado)
    tobillo = arm.pose.bones.get("Bip01 %s Foot" % lado)
    if not (pb and tobillo):
        continue
    limpiar()
    y0 = (arm.matrix_world @ tobillo.head).y
    pb.rotation_euler = (math.radians(20), 0, 0)
    bpy.context.view_layer.update()
    y1 = (arm.matrix_world @ tobillo.head).y
    delta = y1 - y0
    limpiar()
    pb.use_ik_limit_x = True
    if delta > 0:      # el tobillo va hacia atras: ese es el sentido natural
        pb.ik_min_x, pb.ik_max_x = math.radians(0.5), math.radians(179.5)
        sentido = "positivo"
    else:
        pb.ik_min_x, pb.ik_max_x = math.radians(-179.5), math.radians(-0.5)
        sentido = "negativo"
    print("   rodilla %s: +20 grados mueve el tobillo %+.3f m en Y -> limite en %s" % (lado, delta, sentido))

# Comprobacion de seguridad con las restricciones YA REACTIVADAS: es el test de verdad, porque asi
# el IK del rig de artistas tiene que ser capaz de sostener la postura de reposo con la cadena nueva.
for c in apagadas:
    c.mute = False
print("restricciones reactivadas: %d" % len(apagadas))

limpiar()
dg = bpy.context.evaluated_depsgraph_get()
ev = cuerpo.evaluated_get(dg)
malla = ev.to_mesh()
ahora = [ev.matrix_world @ v.co for v in malla.vertices]
ev.to_mesh_clear()
desvio = max((a - b).length for a, b in zip(ahora, referencia))
print("desvio maximo de la malla en reposo: %.6f m (debe ser 0)" % desvio)

bpy.ops.wm.save_as_mainfile(filepath=SALIDA)
print("guardado:", SALIDA)