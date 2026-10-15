"""Prepara el modelo para MMD: nombres estandar japoneses, IK de piernas y materiales legibles por el PMX.

Claves de MMD (y de por que se hace asi):
- Las coreografias VMD mueven huesos POR NOMBRE. Sin `センター`, `上半身`, `腕`, `ひじ`, `脚`, `ひざ`,
  `足首` no hay forma de aplicarles una coreografia: quedan quietas. De ahi el renombrado.
- MMD espera que `上半身` y `下半身` sean HERMANOS bajo `センター`. En el esqueleto del juego `上半身`
  cuelga de `下半身`, con lo que girar la cadera giraria todo el tronco (los VMD giran la cadera a
  menudo). Se reparenta, sin mover nada de sitio: la deformacion en reposo no cambia.
- El IK de piernas se hace con dos huesos por lado, `足ＩＫ` y `つま先ＩＫ`, como en cualquier modelo de
  MMD. El limite del giro de la rodilla se decide MIDIENDO cual de los dos signos la dobla hacia atras.
- Los materiales se aplanan: se busca la textura de base dentro del grupo de nodos del toon y se
  conecta directa al Principled, porque el exportador de PMX solo entiende una textura conectada.

Uso: blender --background --python preparar_mmd.py -- <blend_entrada> <carpeta_salida>
"""
import os
import sys

import math

import bpy
from mathutils import Vector

ARG = sys.argv[sys.argv.index("--") + 1:]
CON_IK = not (len(ARG) > 2 and ARG[2] == "sin_ik")   # variante de diagnostico: sin IK if "--" in sys.argv else []
ENTRADA = ARG[0]
SALIDA = ARG[1] if len(ARG) > 1 else os.path.dirname(ENTRADA)
try:      # el complemento de MMD es una extension: hay que activarla en cada sesion
    bpy.ops.preferences.addon_enable(module="bl_ext.user_default.mmd_tools")
except Exception as e:
    print("aviso activando mmd_tools:", e)
bpy.ops.wm.open_mainfile(filepath=ENTRADA)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
bpy.context.view_layer.objects.active = arm

# ---------------------------------------------------------------- 1. nombres estandar
DEDOS = (("Finger0", "親指0"), ("Finger01", "親指1"), ("Finger02", "親指2"),
         ("Finger1", "人指1"), ("Finger11", "人指2"), ("Finger12", "人指3"),
         ("Finger2", "中指1"), ("Finger21", "中指2"), ("Finger22", "中指3"),
         ("Finger3", "薬指1"), ("Finger31", "薬指2"), ("Finger32", "薬指3"),
         ("Finger4", "小指1"), ("Finger41", "小指2"), ("Finger42", "小指3"))


def mapa_nombres(nombre):
    """Nombre del juego -> nombre estandar de MMD."""
    if nombre == "Bip01":
        return "全ての親"
    if nombre == "Bip01 Pelvis":
        return "下半身"
    if nombre == "Bip01 Spine":
        return "上半身"
    if nombre == "Bip01 Spine1":
        return "上半身2"
    if nombre in ("Bip01 Neck",):
        return "首"
    if nombre in ("Bip01 Head",):
        return "頭"
    for lado, kanji in (("L", "左"), ("R", "右")):
        if not nombre.startswith("Bip01 %s " % lado):
            continue
        resto = nombre[len("Bip01 %s " % lado):]
        # El estandar de MMD pone el lado DELANTE: 左腕, 左ひじ, 左足, 左ひざ, 左足首. Con el lado
        # detras (`腕.左`) MMD no reconoce el hueso y ninguna coreografia VMD lo mueve.
        fijos = {"Clavicle": "肩", "UpperArm": "腕", "Forearm": "ひじ", "Hand": "手首",
                 "Thigh": "足", "Calf": "ひざ", "Foot": "足首", "Toe0": "つま先"}
        if resto in fijos:
            return "%s%s" % (kanji, fijos[resto])
        for dedo, kanji_dedo in DEDOS:
            if resto == dedo:
                return "%s%s" % (kanji, kanji_dedo)
    return None


cambios = {}
for b in arm.data.bones:
    nuevo = mapa_nombres(b.name)
    if nuevo and b.name != nuevo:
        cambios[b.name] = nuevo
for viejo, nuevo in cambios.items():
    if nuevo in arm.data.bones:
        print("  (ya existe %s, no se renombra %s)" % (nuevo, viejo))
        continue
    arm.data.bones[viejo].name = nuevo
    for o in bpy.data.objects:
        g = o.vertex_groups.get(viejo) if o.type == "MESH" else None
        if g:
            g.name = nuevo
print("huesos renombrados al estandar MMD: %d" % len(cambios))
print("   cadena:", sorted(v for v in cambios.values())[:12], "...")

# ---------------------------------------------------------------- 2. jerarquia MMD
eb = arm.data.edit_bones
bpy.ops.object.mode_set(mode="EDIT")
if "センター" not in eb:
    c = eb.new("センター")
    b = eb["下半身"]
    c.head = Vector((b.head.x, b.head.y, b.head.z))
    c.tail = c.head + Vector((0, 0, 0.12))
    c.use_deform = False
    c.parent = eb.get("全ての親")
    b.parent = c                      # 下半身 cuelga del centro
    b.use_connect = False
if "上半身" in eb and eb["上半身"].parent and eb["上半身"].parent.name == "下半身":
    eb["上半身"].parent = eb["センター"]      # hermanos, como espera MMD
    eb["上半身"].use_connect = False

# ---------------------------------------------------------------- 3. IK de piernas
for lado, kanji in (("L", "左"), ("R", "右")):
    hueso_pie = "%s足首" % kanji
    if hueso_pie not in eb:
        continue
    pie = eb[hueso_pie]
    if "%s足ＩＫ" % kanji not in eb:
        ik = eb.new("%s足ＩＫ" % kanji)
        ik.head = pie.head.copy()
        ik.tail = pie.head + Vector((0, 0, -0.10))
        ik.use_deform = False
        ik.parent = eb["全ての親"]
    if "%sつま先ＩＫ" % kanji not in eb:
        t = eb.new("%sつま先ＩＫ" % kanji)
        toe = eb.get("%sつま先" % kanji)
        t.head = (toe.tail.copy() if toe else pie.head + Vector((0, 0.08, 0)))
        t.tail = t.head + Vector((0, 0.08, 0))
        t.use_deform = False
        t.parent = eb["%s足ＩＫ" % kanji]
bpy.ops.object.mode_set(mode="OBJECT")

for lado, kanji in (("L", "左"), ("R", "右")):
    if "%sひざ" % kanji not in arm.pose.bones:
        continue
    c = arm.pose.bones["%sひざ" % kanji].constraints.new("IK")
    c.iterations = 40        # el exportador escribe esto como "bucle de IK"; MMD usa valores ~40,
                             # el defecto de Blender es 500 y no aporta nada aqui
    c.target = arm
    c.subtarget = "%s足ＩＫ" % kanji
    c.chain_count = 2
    c.use_tail = True
    c.use_rotation = False
    c2 = arm.pose.bones["%s足首" % kanji].constraints.new("IK")
    c2.target = arm
    c2.subtarget = "%sつま先ＩＫ" % kanji
    c2.chain_count = 1
    c2.use_tail = True
    c2.use_rotation = False
print("IK montado: %d restricciones" % sum(1 for b in arm.pose.bones for c in b.constraints if c.type == "IK"))


# Comprobacion de que el IK de piernas de verdad tira de la malla. OJO: con una restriccion IK el
# resultado NO aparece en rotation_euler (esa queda a 0 y me llevo a un diagnostico falso), hay que
# medir el desplazamiento de la malla evaluada.
# la malla del CUERPO por nombre: "la primera de mas de 1000 vertices" es el pelo, y medir ahi da 0.000
mesh_ik = bpy.data.objects.get("Kotone_Cuerpo") or next(
    o for o in bpy.data.objects if o.type == "MESH" and len(o.data.vertices) > 1000)
altura_modelo = (max((o.matrix_world @ v.co).z for o in bpy.data.objects if o.type == "MESH" and o.data.vertices
                     for v in o.data.vertices)
                 - min((o.matrix_world @ v.co).z for o in bpy.data.objects if o.type == "MESH" and o.data.vertices
                       for v in o.data.vertices))


def _co_actual():
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    ev = mesh_ik.evaluated_get(dg)
    m = ev.to_mesh()
    co = [ev.matrix_world @ v.co for v in m.vertices]
    ev.to_mesh_clear()
    return co


def limpiar_pose():
    for b in arm.pose.bones:
        b.rotation_mode = "XYZ"
        b.rotation_euler = (0, 0, 0)
        b.location = (0, 0, 0)
    bpy.context.view_layer.update()


def mover_control_mundo(bone, delta):
    local = bone.bone.matrix_local.to_3x3().inverted() @ Vector(delta)
    bone.location = tuple(bone.location[i] + local[i] for i in range(3))


limpiar_pose()
base = _co_actual()
for lado, kanji in (("L", "左"), ("R", "右")):
    objetivo = arm.pose.bones.get("%s足ＩＫ" % kanji)
    if not objetivo:
        continue
    limpiar_pose()
    pb_rodilla = arm.pose.bones.get("%sひざ" % kanji)
    c_ik = pb_rodilla.constraints[0] if pb_rodilla and pb_rodilla.constraints else None
    if c_ik:
        print("    restriccion: target=%s subtarget=%s cadena=%d mute=%s influencia=%.2f"
              % (c_ik.target.name if c_ik.target else None, c_ik.subtarget, c_ik.chain_count, c_ik.mute, c_ik.influence))
    h_antes = (arm.matrix_world @ objetivo.head).copy()
    mover_control_mundo(objetivo, (0, -0.35, 0))
    bpy.context.view_layer.update()
    h_despues = (arm.matrix_world @ objetivo.head).copy()
    print("    el control se mueve: %.3f m" % (h_despues - h_antes).length)
    if pb_rodilla:
        vis = pb_rodilla.matrix.to_euler()
        print("    rotacion REAL de la rodilla (matriz visual, incluye restricciones): "
              "(%.1f, %.1f, %.1f) grados" % tuple(math.degrees(a) for a in vis))
    ahora = _co_actual()
    desp = max((a - b).length for a, b in zip(ahora, base))
    limpiar_pose()
    print("  IK de %s: adelantar el pie 0.35 m mueve la malla %.3f m (%.0f%% de la altura)"
          % (kanji, desp, 100 * desp / altura_modelo))
print("  (sin limites de angulo: un limite mal puesto bloquea la rodilla, y un IK que no funciona es peor)")

# ---------------------------------------------------------------- 4. materiales planos para el PMX
def buscar_textura(arbol, visto=None):
    """La primera imagen del arbol, mirando tambien dentro de los grupos de nodos."""
    visto = visto or set()
    for n in arbol.nodes:
        if n.type == "TEX_IMAGE" and n.image:
            return n.image
        if n.type == "GROUP" and n.node_tree and n.node_tree.name not in visto:
            visto.add(n.node_tree.name)
            img = buscar_textura(n.node_tree, visto)
            if img:
                return img
    return None


planos = 0
for mat in bpy.data.materials:
    if not mat.use_nodes or mat.name.startswith("REPINTAR"):
        continue
    img = buscar_textura(mat.node_tree)
    mat.node_tree.nodes.clear()
    out = mat.node_tree.nodes.new("ShaderNodeOutputMaterial")
    pr = mat.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
    pr.inputs["Base Color"].default_value = (1, 1, 1, 1)
    pr.inputs["Roughness"].default_value = 0.5
    pr.inputs["Specular IOR Level"].default_value = 0.0
    mat.node_tree.links.new(pr.outputs["BSDF"], out.inputs["Surface"])
    if hasattr(mat, "mmd_material"):
        mat.mmd_material.diffuse_color = (1.0, 1.0, 1.0)
        mat.mmd_material.alpha = 1.0
    if img:
        tex = mat.node_tree.nodes.new("ShaderNodeTexImage")
        # El exportador de PMX busca el nodo por NOMBRE: "mmd_base_tex". Si se llama de otra forma, el
        # material sale en el PMX sin textura (nos pasó: 9 materiales sin textura).
        tex.name = "mmd_base_tex"
        tex.label = "mmd_base_tex"
        tex.image = img
        mat.node_tree.links.new(tex.outputs["Color"], pr.inputs["Base Color"])
        mat.node_tree.links.new(tex.outputs["Alpha"], pr.inputs["Alpha"])
        planos += 1
print("materiales aplanados con su textura conectada: %d de %d" % (planos, len(bpy.data.materials)))

# ---------------------------------------------------------------- 5. expresiones con nombre japones
MORFOS = {"face_xiao": "笑い", "mouth_xiao": "笑い(口)", "face_miyanxiao": "目笑い",
          "mouth_miyanxiao": "目笑い(口)", "face_shengqi": "怒り", "mouth_shengqi": "怒り(口)",
          "face_beiai": "悲しい", "mouth_beiai": "悲しい(口)", "face_jingya": "びっくり",
          "mouth_jingya": "びっくり(口)", "normal_blink": "まばたき",
          "eyelid_jingya": "びっくり(まぶた)", "eye_jingya": "びっくり(目)",
          "eye_beiai": "悲しい(目)", "eye_xiao": "笑い(目)",
          "a": "あ", "i": "い", "u": "う", "e": "え", "o": "お",
          "mouth_positive": "口+(ポジティブ)", "mouth_negative": "口-(ネガティブ)"}
renombrados = 0
for o in bpy.data.objects:
    if o.type != "MESH" or not o.data.shape_keys:
        continue
    for kb in o.data.shape_keys.key_blocks:
        if kb.name in MORFOS:
            kb.name = MORFOS[kb.name]
            renombrados += 1
print("expresiones renombradas al japones de MMD: %d" % renombrados)

# ---------------------------------------------------------------- 5b. texturas a disco (el PMX las necesita como ficheros)
# Las imagenes venian empaquetadas en el .blend: sin ruta en disco el exportador no puede copiarlas y
# el PMX sale con materiales SIN textura. Se escriben a tex/ y se apunta cada imagen ahi.
TEXDIR = os.path.join(SALIDA, "tex")
os.makedirs(TEXDIR, exist_ok=True)
escritas = 0
for img in bpy.data.images:
    if not img.name or img.users == 0 or img.size[0] == 0:
        continue
    nombre = os.path.basename(img.name)
    if not nombre.lower().endswith((".png", ".tga", ".bmp", ".jpg", ".jpeg")):
        nombre += ".png"
    import re
    m = re.match(r".+?\.(png|tga|bmp|jpg|jpeg)", nombre, re.IGNORECASE)     # se corta en la 1a extension
    nombre = m.group(0) if m else nombre
    destino = os.path.join(TEXDIR, nombre)
    try:
        img.filepath_raw = destino
        img.file_format = "PNG"
        img.save()
        escritas += 1
    except Exception as e:
        print("  no se pudo escribir %s: %s" % (nombre, e))
print("texturas escritas a tex/: %d" % escritas)

# ---------------------------------------------------------------- 6. estructura de modelo MMD + exportar
# El exportador exige la jerarquia de MMD: un objeto raiz con mmd_type='ROOT' del que cuelgan armadura
# y mallas. Se crea con la funcion DEL PROPIO COMPLEMENTO (FnModel.create) y no a mano, porque ademas
# genera los frames de pantalla ("Root" y "表情"). Con la raiz creada a mano el PMX salia con CERO
# frames, que es lo que MMD usa para armar el panel de huesos y expresiones.
try:    # el complemento es una EXTENSION: su modulo va con prefijo
    from bl_ext.user_default.mmd_tools.core.model import Model as ModeloMMD
except ImportError:
    from mmd_tools.core.model import Model as ModeloMMD

# La escala NO se copia: el complemento trae 12.5 por defecto, que para este modelo da 13 unidades
# cuando el estandar de MMD son ~20 (el Miku oficial, medido igual, importa a 20.12). Se calcula:
zs = [(o.matrix_world @ v.co).z for o in bpy.data.objects if o.type == "MESH" and o.data.vertices
      for v in o.data.vertices]
altura = max(zs) - min(zs)
escala = 20.0 / altura
print("altura del modelo: %.4f -> escala calculada para MMD: %.3f (el complemento pone 12.5 por defecto)" % (altura, escala))

raiz = bpy.data.objects.get("Kotone_Shiomi")
if raiz is None or raiz.mmd_type != "ROOT":
    modelo = ModeloMMD.create("Kotone Shiomi", "Kotone Shiomi", escala, "Kotone_Shiomi",
                              armature_object=arm)
    modelo.initialDisplayFrames(reset=True)     # crea los frames "Root" y "表情"
    raiz = bpy.data.objects["Kotone_Shiomi"]
raiz.mmd_root.name = "Kotone Shiomi"
raiz.mmd_root.name_e = "Kotone Shiomi"
raiz.mmd_root.comment = ("Modelo reconstruido desde el juego (PC079). Uso de aficionados; "
                         "los derechos son de Atlus / SEGA / Perfect World.")
for o in bpy.data.objects:
    if o.type in ("MESH", "ARMATURE") and o.parent is None:
        o.parent = raiz
        o.matrix_parent_inverse = raiz.matrix_world.inverted()

# frames de pantalla: sin ellos MMD se cae al cargar el modelo
frames = raiz.mmd_root.display_item_frames
morphs = [kb.name for o in bpy.data.objects if o.type == "MESH" and o.data.shape_keys
          for kb in o.data.shape_keys.key_blocks if kb.name != "Basis"]

f_root = frames.get("Root") or frames.add()
f_root.name, f_root.name_e, f_root.is_special = "Root", "Root", True
f_root.data.clear()
for nombre_hueso in ("全ての親", "センター", "下半身", "上半身", "上半身2", "首", "頭"):
    if nombre_hueso in arm.pose.bones:
        it = f_root.data.add()
        it.type, it.name = "BONE", nombre_hueso

f_exp = frames.get("表情") or frames.add()
f_exp.name, f_exp.name_e, f_exp.is_special = "表情", "Facial", True
f_exp.data.clear()
for nombre_morph in morphs:
    it = f_exp.data.add()
    it.type, it.morph_type, it.name = "MORPH", "vertex_morphs", nombre_morph

f_ik = frames.get("IK") or frames.add()
f_ik.name, f_ik.name_e, f_ik.is_special = "IK", "IK", False
f_ik.data.clear()
for nombre_hueso in ("左足ＩＫ", "右足ＩＫ", "左つま先ＩＫ", "右つま先ＩＫ"):
    if nombre_hueso in arm.pose.bones:
        it = f_ik.data.add()
        it.type, it.name = "BONE", nombre_hueso
print("frames de pantalla: %d -> %s" % (len(frames), [(f.name, len(f.data)) for f in frames]))

if not CON_IK:
    # variante de diagnostico: quitar los huesos de IK y sus restricciones, para ver si el problema
    # esta en el IK de piernas o en otra parte del modelo
    for pb in list(arm.pose.bones):
        for c in list(pb.constraints):
            pb.constraints.remove(c)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    for n in ("左足ＩＫ", "右足ＩＫ", "左つま先ＩＫ", "右つま先ＩＫ"):
        b = arm.data.edit_bones.get(n)
        if b:
            arm.data.edit_bones.remove(b)
    bpy.ops.object.mode_set(mode="OBJECT")
    for f in frames:
        if f.name == "IK":
            f.data.clear()
    print("variante SIN IK: quitados 4 huesos y sus restricciones")

pmx = os.path.join(SALIDA, "Kotone_Shiomi.pmx")
bpy.ops.object.select_all(action="DESELECT")
raiz.select_set(True)
bpy.context.view_layer.objects.active = raiz
print("estructura MMD lista; mmd_type de la raiz:", raiz.mmd_type)
bpy.ops.mmd_tools.export_pmx(filepath=pmx, scale=escala, copy_textures_mode="OVERWRITE",
                             ik_angle_limits="EXPORT_ALL", log_level="WARNING")
print("pmx:", os.path.getsize(pmx) // 1024, "KB")
print("LISTO")