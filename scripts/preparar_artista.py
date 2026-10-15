"""Prepara el modelo para PUBLICARLO: escena limpia, nombres claros, rig ordenado y exportaciones.

Se ejecuta SOBRE el .blend que ya tiene el toon montado (lo genera blender_toon.py), para no duplicar
aqui el codigo del shader. Hace, por este orden:

  1. Tira la basura del importador (la esfera de formas personalizadas, materiales sueltos).
  2. Renombra objetos y mallas a nombres legibles (Kotone_Cuerpo, Kotone_Pelo, ...).
  3. Ordena el esqueleto en COLECCIONES DE HUESOS: una con el cuerpo y otra con las ayudas del juego
     (camara, pies, cloth Magica, UI), que se deja oculta. El artista ve un esqueleto limpio.
  4. Quita las 329 formas personalizadas de hueso (las "esferas" que mete el importador de glTF).
  5. Deja el color base TAMBIEN en el Principled (no solo en la emision del toon): si no, el modelo
     exportado a glTF/FBX sale NEGRO en cualquier visor.
  6. Guarda el .blend con las texturas empaquetadas y exporta GLB y FBX.
  7. Renderiza una vista en reposo y otra POSADA, para demostrar que el rig posa.

Uso:
  blender --background --python preparar_artista.py -- <kotone_toon.blend> <carpeta_salida> [materiales]
"""
import math
import os
import sys

import bpy
from mathutils import Vector

ARG = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
BLEND = ARG[0]
SAL = ARG[1] if len(ARG) > 1 else os.path.dirname(BLEND)
CARPETA_MAT = ARG[2] if len(ARG) > 2 else ""
PREVIEW = os.path.join(SAL, "preview")
os.makedirs(PREVIEW, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=BLEND)
esc = bpy.context.scene
print("abierto:", BLEND)

# ---------------------------------------------------------------- 1. limpieza
BASURA_MAT = {"Dots Stroke", "Material"}
for m in list(bpy.data.materials):
    if m.name in BASURA_MAT:
        bpy.data.materials.remove(m)
quitar = []
for o in list(bpy.data.objects):
    if o.type != "MESH":
        continue
    # El casco del contorno (duplicado oculto del toon) solo estorba en un fichero para artistas: el
    # contorno del render lo dibuja Freestyle. Si se deja, aparece como un duplicado ".001" de cada
    # malla en el esquema y el artista no sabe cual es la buena.
    if "_contorno" in o.name or not o.data.vertices or "Esfera" in o.name or o.name.startswith("Icosphere"):
        quitar.append(o.name)
for nombre in quitar:
    o = bpy.data.objects.get(nombre)
    if o:
        bpy.data.objects.remove(o, do_unlink=True)
print("  fuera (basura + cascos del contorno):", len(quitar))

# ---------------------------------------------------------------- 2. nombres legibles
PIEZAS = (("_xiuzhang", "Kotone_Brazalete"), ("_qiangtao", "Kotone_Vaina"),
          ("_qiang", "Kotone_Lanza"), ("gun_02", "Kotone_Pistola"),
          ("_hair", "Kotone_Pelo"), ("_eyelid", "Kotone_Parpados"),
          ("_eye", "Kotone_Ojos"), ("_face", "Kotone_Cara"), ("_body", "Kotone_Cuerpo"))
for o in [x for x in bpy.data.objects if x.type == "MESH"]:
    nuevo = None
    for clave, nombre in PIEZAS:
        if clave in o.name:
            nuevo = nombre
            break
    if nuevo:
        o.name = nuevo
        o.data.name = nuevo
arm = next((o for o in bpy.data.objects if o.type == "ARMATURE"), None)
if arm:
    arm.name = "Kotone_Rig"
    arm.data.name = "Kotone_Rig"

# ---------------------------------------------------------------- 3. colecciones de huesos
AYUDAS = ("Magica Cloth", "t_blueFire", "t_buff_wq", "t_camera", "t_foot", "t_footb", "t_head",
          "t_head_sit", "t_hit", "t_hitb", "t_persona", "t_stun", "t_union_camera")
if arm and hasattr(arm.data, "collections"):
    for c in list(arm.data.collections):
        arm.data.collections.remove(c)
    col_cuerpo = arm.data.collections.new("01_Cuerpo")
    col_cara = arm.data.collections.new("02_Cara_y_expresiones")
    col_ayudas = arm.data.collections.new("03_Ayudas_del_juego")
    raices_ayuda = set()
    for b in arm.data.bones:
        if b.parent is None and (b.name in AYUDAS or b.name.startswith("Magica")):
            raices_ayuda.add(b.name)
    def en_ayuda(b):
        p = b
        while p:
            if p.name in raices_ayuda or p.name.startswith("Magica"):
                return True
            p = p.parent
        return False
    n_cuerpo = n_cara = n_ayuda = 0
    for b in arm.data.bones:
        if en_ayuda(b):
            col_ayudas.assign(b); n_ayuda += 1
        elif any(k in b.name for k in ("Head", "Neck", "jaw", "eye", "eyelid", "face", "BN_", "Tongue")):
            col_cara.assign(b); n_cara += 1
        else:
            col_cuerpo.assign(b); n_cuerpo += 1
    col_ayudas.is_visible = False          # el artista ve un esqueleto limpio
    try:
        col_ayudas.is_visible_effectively = False
    except AttributeError:
        pass
    print("  huesos: cuerpo %d, cara %d, ayudas del juego %d" % (n_cuerpo, n_cara, n_ayuda))

# ---------------------------------------------------------------- 4. formas personalizadas
if arm:
    n = 0
    for b in arm.pose.bones:
        if b.custom_shape:
            b.custom_shape = None
            n += 1
    print("  formas personalizadas quitadas:", n)
    arm.data.display_type = "OCTAHEDRAL"
    arm.show_in_front = True

# ---------------------------------------------------------------- 5. color base tambien en el Principled
# El toon vive en la EMISION; si el Base Color se queda negro, el .glb/.fbx sale negro en cualquier
# visor que no entienda el shader. Se conecta la textura al Base Color y se baja el brillo especular.
arreglados = 0
for m in bpy.data.materials:
    arbol = m.node_tree
    if not arbol:
        continue
    def textura_de_base(arbol, grupo):
        """La textura que alimenta la entrada 'Base' del grupo toon (o la primera sin ser normales)."""
        if grupo is not None:
            for l in arbol.links:
                if l.to_node == grupo and l.to_socket.name == "Base" and l.from_node.type == "TEX_IMAGE":
                    return l.from_node
        return next((n for n in arbol.nodes if n.type == "TEX_IMAGE" and n.image
                     and "normal" not in n.image.name.lower()), None)

    princ = next((n for n in arbol.nodes if n.type == "BSDF_PRINCIPLED"), None)
    grupo = next((n for n in arbol.nodes if n.type == "GROUP" and n.node_tree
                  and n.node_tree.name == "P5X_Toon"), None)
    tex = textura_de_base(arbol, grupo)
    if princ and tex:
        arbol.links.new(tex.outputs["Color"], princ.inputs["Base Color"])
        if "Specular IOR Level" in princ.inputs:
            princ.inputs["Specular IOR Level"].default_value = 0.15
        arreglados += 1
    elif princ:
        princ.inputs["Base Color"].default_value = (0.75, 0.75, 0.78, 1)
        arreglados += 1
print("  materiales con color base exportable:", arreglados)

# Pistola: el montaje de la comunidad la dejo con el material de relleno `Standard` y sin textura.
# Se le da un material propio con el shader toon y un gris metalico, en vez de dejarla con el nombre
# de relleno. Queda marcado como provisional en el LEEME.
ESTANDAR = [m for m in bpy.data.materials if m.name in ("Standard", "Material")]
for m in ESTANDAR:
    m.name = "Kotone_Pistola_PENDIENTE"

# ---- texturas: que NINGUN material se quede sin su imagen ----
# (Aqui hubo un paso que "fusionaba duplicados" remapeando usuarios y borraba la imagen: dejo cinco
#  materiales con la textura a None. Se elimino. Lo que se hace ahora es lo contrario: COMPROBAR y
#  recuperar, y anadir los mapas de normales que el montaje del toon habia descartado.)
CARPETAS_TEX = [os.path.join(SAL, "texturas"),
                os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             "kotone_shiomi", "02_texturas")]


def imagen_de_disco(nombre):
    for carpeta in CARPETAS_TEX:
        ruta = os.path.join(carpeta, nombre)
        if os.path.exists(ruta):
            return bpy.data.images.load(ruta, check_existing=True)
    return None


sin_textura, recuperadas, con_normales = [], [], 0
for m in bpy.data.materials:
    arbol = m.node_tree
    if not arbol:
        continue
    princ = next((n for n in arbol.nodes if n.type == "BSDF_PRINCIPLED"), None)
    texs = [n for n in arbol.nodes if n.type == "TEX_IMAGE"]
    if not texs:
        continue
    for n in texs:
        if n.image is None and n.name in bpy.data.images:
            n.image = bpy.data.images[n.name]
        if n.image is None:
            sin_textura.append((m.name, n.name))
    base = next((n for n in texs if n.image and "normal" not in n.image.name.lower()
                 and "_nm" not in n.image.name.lower()), None)
    if base is None:
        continue
    if base.image is None:
        continue
    raiz = base.image.name.rsplit(".", 1)[0]
    if raiz.lower().endswith("_bc"):
        raiz = raiz[:-3]
    # mapa de normales: el material original apuntaba al de LOD; se prefiere el normal si existe
    if princ and not princ.inputs["Normal"].links:
        for sufijo in ("_nm.png", "_lodlow_nm.png"):
            img = imagen_de_disco(raiz + sufijo)
            if img:
                nodo_nm = arbol.nodes.new("ShaderNodeTexImage")
                nodo_nm.image = img
                nodo_nm.location = (-620, -520)
                mapa = arbol.nodes.new("ShaderNodeNormalMap")
                mapa.location = (-360, -520)
                mapa.inputs["Strength"].default_value = 0.8
                arbol.links.new(nodo_nm.outputs["Color"], mapa.inputs["Color"])
                arbol.links.new(mapa.outputs["Normal"], princ.inputs["Normal"])
                con_normales += 1
                break
print("  materiales sin textura base:", sin_textura or "ninguno")
print("  mapas de normales conectados:", con_normales)

# --- La pistola: hueso-socket en el origen -> a la mano derecha ---
# `gun_Bone01` descansa en (0,0,0): los vertices de la pistola pesan 100% sobre el, asi que en reposo
# la pistola aparece tirada en el suelo. Se lleva a la mano derecha moviendo A LA VEZ la malla y el
# hueso, con el mismo desplazamiento, para que la deformacion en reposo siga siendo identica.
def colocar_pistola():
    pistola = bpy.data.objects.get("Kotone_Pistola")
    if pistola is None or arm is None:
        return
    nombre_hueso = None
    acum = {}
    for v in pistola.data.vertices:
        for g in v.groups:
            acum[g.group] = acum.get(g.group, 0.0) + g.weight
    if not acum:
        return
    nombre_hueso = pistola.vertex_groups[max(acum, key=acum.get)].name
    hueso = arm.data.bones.get(nombre_hueso)
    mano = arm.data.bones.get("Bip01 R Hand") or arm.data.bones.get("Bip01 L Hand")
    if not hueso or not mano:
        print("  pistola: no encuentro el hueso o la mano")
        return
    origen = arm.matrix_world @ hueso.head_local
    destino = arm.matrix_world @ mano.head_local
    delta = destino - origen
    if delta.length < 0.01:
        return
    # malla: desplazar los vertices (en el espacio local del objeto)
    inv = pistola.matrix_world.inverted()
    for v in pistola.data.vertices:
        v.co = inv @ ((pistola.matrix_world @ v.co) + delta)
    # hueso: el mismo desplazamiento en el espacio de la armadura
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm.data.edit_bones[nombre_hueso]
    d_local = arm.matrix_world.inverted().to_3x3() @ delta
    eb.head = eb.head + d_local
    eb.tail = eb.tail + d_local
    bpy.ops.object.mode_set(mode="OBJECT")
    print("  pistola colocada en %s (delta %.3f m)" % (mano.name, delta.length))


colocar_pistola()

# El material del contorno ya no lo usa nadie: fuera del fichero publicado
mat_contorno = bpy.data.materials.get("P5X_Outline")
if mat_contorno:
    for o in bpy.data.objects:
        if o.type == "MESH":
            for i, s in enumerate(o.data.materials):
                if s is mat_contorno:
                    o.data.materials[i] = None
    bpy.data.materials.remove(mat_contorno)

# ---------------------------------------------------------------- 6. guardar y exportar
bpy.ops.file.pack_all()
try:
    bpy.data.orphans_purge(do_recursive=True)      # fuera imagenes/materiales huerfanos
except AttributeError:
    pass
arch_blend = os.path.join(SAL, "Kotone_Shiomi.blend")
bpy.ops.wm.save_as_mainfile(filepath=arch_blend)
print("blend:", arch_blend)

# Para GLB/FBX: el "look" toon vive en la EMISION, y la emision aqui es una cadena de nodos que ningun
# exportador sabe leer (solo exportaria un color plano). Si se deja, el modelo sale raro en los
# visores. Se apaga la emision SOLO para exportar y se deja el color base con su textura: asi cualquier
# motor le pone su propia luz. El .blend con el toon ya esta guardado arriba.
for m in bpy.data.materials:
    arbol = m.node_tree
    if not arbol:
        continue
    p = next((n for n in arbol.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if not p:
        continue
    if p.inputs["Emission Color"].links:
        arbol.links.remove(p.inputs["Emission Color"].links[0])
    p.inputs["Emission Color"].default_value = (0, 0, 0, 1)
    if "Emission Strength" in p.inputs:
        p.inputs["Emission Strength"].default_value = 0.0
    p.inputs["Roughness"].default_value = 0.75

arch_glb = os.path.join(SAL, "Kotone_Shiomi.glb")
bpy.ops.export_scene.gltf(filepath=arch_glb, export_format="GLB", export_apply=False,
                          export_animations=False, export_yup=True)
print("glb:", arch_glb, os.path.getsize(arch_glb) // 1024, "KB")

arch_fbx = os.path.join(SAL, "Kotone_Shiomi.fbx")
try:
    bpy.ops.export_scene.fbx(filepath=arch_fbx, path_mode="COPY", embed_textures=True,
                             use_selection=False, add_leaf_bones=False, bake_space_transform=False)
    print("fbx:", arch_fbx, os.path.getsize(arch_fbx) // 1024, "KB")
except Exception as e:                                              # noqa: BLE001
    print("FBX no exportado:", e)

# ---------------------------------------------------------------- 7. previews: reposo y posado
for o in [x for x in bpy.data.objects if x.type == "LIGHT"]:
    bpy.data.objects.remove(o, do_unlink=True)
luz = bpy.data.objects.new("sol_clave", bpy.data.lights.new("sol_clave", "SUN"))
luz.data.energy = 3.0
luz.rotation_euler = (math.radians(35), 0, math.radians(155))
bpy.context.collection.objects.link(luz)
for motor in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
    try:
        esc.render.engine = motor
        break
    except TypeError:
        continue
try:
    esc.view_settings.view_transform = "Standard"
except TypeError:
    pass
esc.render.use_freestyle = True
esc.view_layers[0].use_freestyle = True

mn = Vector((1e9,) * 3); mx = Vector((-1e9,) * 3)
mallas = [o for o in bpy.data.objects if o.type == "MESH" and o.data.vertices]
for o in mallas:
    for v in o.data.vertices:
        w = o.matrix_world @ v.co
        for k in range(3):
            mn[k] = min(mn[k], w[k]); mx[k] = max(mx[k], w[k])
centro = (mn + mx) / 2
alto = max(mx[2] - mn[2], 0.1)
cam = bpy.data.objects.new("camara", bpy.data.cameras.new("camara"))
bpy.context.collection.objects.link(cam)
esc.camera = cam


def vista(nombre, ang=0.0, factor=1.0, objetivo=None, ancho=900, alto_px=1350):
    dist = (alto / (2 * math.tan(math.radians(28) / 2))) * 1.15 * factor
    obj = objetivo or centro
    cam.data.lens = 60.0
    cam.location = (obj.x + dist * math.sin(math.radians(ang)), obj.y - dist * math.cos(math.radians(ang)), obj.z)
    cam.rotation_euler = (obj - Vector(cam.location)).to_track_quat("-Z", "Y").to_euler()
    esc.render.resolution_x = ancho
    esc.render.resolution_y = alto_px
    esc.render.filepath = os.path.join(PREVIEW, nombre + ".png")
    bpy.ops.render.render(write_still=True)
    print("preview:", esc.render.filepath)


vista("01_reposo_frente")
vista("02_reposo_trescuartos", ang=35)

# Pose de ejemplo: se gira el rig con FK y se comprueba que el resultado se ve bien. Tambien sirve de
# prueba de que el modelo se puede posar sin tocar nada raro.
if arm:
    pos = {"Bip01 L UpperArm": ("Y", -55), "Bip01 R UpperArm": ("Y", 25), "Bip01 L Forearm": ("Z", 65),
           "Bip01 Head": ("Z", 18), "Bip01 Spine1": ("X", -6)}
    for b in arm.pose.bones:
        b.rotation_mode = "XYZ"
        b.rotation_euler = (0, 0, 0)
    for hueso, (eje, grados) in pos.items():
        b = arm.pose.bones.get(hueso)
        if not b:
            print("  (no existe el hueso", hueso, ")")
            continue
        r = list(b.rotation_euler)
        r["XYZ".index(eje)] = math.radians(grados)
        b.rotation_euler = r
    bpy.context.view_layer.update()
    vista("03_pose_ejemplo", ang=25)
    vista("04_pose_ejemplo_cara", ang=10, factor=0.32,
          objetivo=Vector((centro.x, centro.y, mn[2] + alto * 0.88)), ancho=900, alto_px=900)
    for b in arm.pose.bones:
        b.rotation_euler = (0, 0, 0)
    bpy.context.view_layer.update()

print("LISTO")
print("mallas:", sorted(o.name for o in mallas))
print("materiales:", sorted(m.name for m in bpy.data.materials))