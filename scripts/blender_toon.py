"""Aplica el shader toon del juego (P5XToon.shader) al GLB, con nodos de Blender.

Unity no exporta su shader: es ShaderLab/HLSL y Blender no lo lee. Lo que si se puede es REPLICAR su
calculo -esta escrito en el propio shader- y ademas usar los valores AFINADOS DE CADA MATERIAL: los
.mat de la exportacion los conservan aunque el shader no viaje (el original apunta a un GUID perdido).

Calculo del shader del juego:

    ndl      = dot(N, -L)
    wrapped  = ndl * 0.5 + 0.5
    toon     = smoothstep(cut - 1/sharp, cut + 1/sharp, wrapped)
    shadow   = base * _ToonDarkColorTint * 2 * lerp(_ToonDarkMap, 1, 0.5)
    albedo   = lerp(shadow, base, toon)
    col      = albedo * (ambiente + luz * toon)
    rim      = smoothstep(grosor - suave, grosor + suave, 1 - sat(N·V))
    contorno = segunda pasada, cull front, grosor constante en pantalla

Traduccion a Blender:

  * El corte duro sale de un Diffuse BSDF BLANCO (da N·L con las luces de la escena) metido en un
    ColorRamp de interpolacion CONSTANTE. El corte del juego es con luz envuelta: 0.55 -> N·L = 0.10.
  * El corte y la suavidad VAN POR MATERIAL, y por eso la rampa se monta fuera del grupo: el pelo usa
    0.55/8, el cuerpo 0.55/8 y la cara 0.00 (o sea, sin banda: la cara del juego se sombrea con un
    mapa SDF aparte, que este shader no implementa).
  * Para que la banda SE VEA hace falta el tinte real de cada material, no el valor por defecto del
    shader: con el defecto (0.509 * 2 = 1.02) la sombra sale del mismo tono que la luz y todo queda
    plano. Los materiales del juego traen el suyo (el pelo 0.698/0.614/0.576).
  * El contorno del render lo dibuja Freestyle (silueta + pliegues). El casco invertido (Solidify con
    normales volteadas + descarte de caras traseras) queda en el .blend desactivado: en EEVEE Next el
    descarte no llega a aplicarse y el casco tapa el modelo entero.

Uso:
  blender --background --python blender_toon.py -- <modelo.glb> <carpeta_salida> [carpeta_de_.mat]
"""
import math
import os
import re
import sys

import bpy
from mathutils import Vector

ARG = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
GLB = ARG[0] if ARG else ""
SAL = ARG[1] if len(ARG) > 1 else (os.path.dirname(GLB) if GLB else ".")
CARPETA_MAT = ARG[2] if len(ARG) > 2 else ""
CONTORNO = 0.0035
os.makedirs(SAL, exist_ok=True)

AMBIENTE = (0.38, 0.38, 0.42, 1.0)
RIM_COLOR = (0.314, 0.314, 0.314, 1.0)
RIM_SUAVE = 0.1
OUTLINE_COLOR = (0.0, 0.0, 0.0, 1.0)
# Direccion HACIA la luz principal (como _WorldSpaceLightPos0 en el shader: arriba, delante y un
# poco a la derecha). El corte toon se calcula contra esta direccion, no contra las lamparas.
DIR_LUZ = (0.346, -0.742, 0.574)

# Valores por defecto del shader, para los materiales que no traigan los suyos.
DEF = dict(cut=0.55, sharp=12.0, tint=(0.509434, 0.509434, 0.509434),
           enable_dark=0.0, rim=0.0, rim_grosor=0.6, alfa=0.5)

for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)
bpy.ops.import_scene.gltf(filepath=GLB)


# ---------------------------------------------------------------- parametros del juego
def leer_material(ruta):
    with open(ruta, "r", encoding="utf-8", errors="ignore") as f:
        texto = f.read()

    def num(clave, defecto):
        m = re.search(r"^\s*-\s*%s:\s*(-?[\d.eE+-]+)\s*$" % re.escape(clave), texto, re.M)
        return float(m.group(1)) if m else defecto

    def color(clave, defecto):
        m = re.search(r"^\s*-\s*%s:\s*\{\s*r:\s*([\d.eE+-]+),\s*g:\s*([\d.eE+-]+),\s*b:\s*([\d.eE+-]+)"
                      % re.escape(clave), texto, re.M)
        return (float(m.group(1)), float(m.group(2)), float(m.group(3))) if m else defecto

    return dict(cut=num("_ToonCutLocation", DEF["cut"]),
                sharp=num("_ToonCutSharpness", DEF["sharp"]),
                tint=color("_ToonDarkColorTint", DEF["tint"]),
                enable_dark=num("_EnableToonDarkMap", DEF["enable_dark"]),
                rim=num("_EnableRim", 0.0) * num("_RimIntensity", 1.0),
                rim_grosor=num("_RimThickness1", DEF["rim_grosor"]),
                alfa=num("_Cutoff", DEF["alfa"]))


def params_de(nombre):
    """Los materiales del GLB se llaman como los del juego: se busca su .mat por prefijo comun."""
    if not CARPETA_MAT or not os.path.isdir(CARPETA_MAT):
        return DEF.copy(), None
    mejor, puntaje = None, -1
    for f in [x for x in os.listdir(CARPETA_MAT) if x.endswith(".mat")]:
        base = f[:-4]
        if nombre == base:
            return leer_material(os.path.join(CARPETA_MAT, f)), base
        comun = 0
        for a, b in zip(nombre, base):
            if a != b:
                break
            comun += 1
        if base.startswith(nombre) or nombre.startswith(base):
            comun += 8
        if comun > puntaje:
            mejor, puntaje = base, comun
    if mejor and puntaje >= 8:
        return leer_material(os.path.join(CARPETA_MAT, mejor + ".mat")), mejor
    return DEF.copy(), None


# ---------------------------------------------------------------- grupo de nodos
def grupo_toon():
    """Grupo reutilizable: recibe Base, Dark, Toon (el corte ya resuelto), DarkTint, Rim y grosor."""
    if "P5X_Toon" in bpy.data.node_groups:
        return bpy.data.node_groups["P5X_Toon"]
    g = bpy.data.node_groups.new("P5X_Toon", "ShaderNodeTree")
    for nombre, tipo in (("Base", "NodeSocketColor"), ("Dark", "NodeSocketColor"),
                         ("Toon", "NodeSocketFloat"), ("DarkTint", "NodeSocketColor"),
                         ("Rim", "NodeSocketFloat"), ("RimGrosor", "NodeSocketFloat")):
        g.interface.new_socket(nombre, in_out="INPUT", socket_type=tipo)
    g.interface.new_socket("Emission", in_out="OUTPUT", socket_type="NodeSocketColor")
    n = g.nodes
    ent = n.new("NodeGroupInput"); ent.location = (-1000, 0)
    sal = n.new("NodeGroupOutput"); sal.location = (900, 0)
    en_base, en_dark = ent.outputs["Base"], ent.outputs["Dark"]
    en_toon, en_tinte = ent.outputs["Toon"], ent.outputs["DarkTint"]
    en_rim, en_grosor = ent.outputs["Rim"], ent.outputs["RimGrosor"]

    def mix(loc, tipo, factor=1.0):
        m = n.new("ShaderNodeMix"); m.data_type = "RGBA"; m.location = loc
        m.blend_type = tipo
        m.inputs["Factor"].default_value = factor
        return m

    # sombra = base * tinte * 2 * lerp(darkMap, 1, 0.5)
    mitad = mix((-780, -80), "MIX", 0.5)
    g.links.new(en_dark, mitad.inputs[6]); mitad.inputs[7].default_value = (1, 1, 1, 1)
    tinte = mix((-600, -80), "MULTIPLY")
    g.links.new(en_base, tinte.inputs[6]); g.links.new(en_tinte, tinte.inputs[7])
    doble = mix((-420, -80), "MULTIPLY")
    g.links.new(tinte.outputs[2], doble.inputs[6]); doble.inputs[7].default_value = (2, 2, 2, 1)
    sombra = mix((-240, -80), "MULTIPLY")
    g.links.new(doble.outputs[2], sombra.inputs[6]); g.links.new(mitad.outputs[2], sombra.inputs[7])

    # albedo = lerp(sombra, base, toon)
    albedo = mix((-40, -80), "MIX")
    g.links.new(en_toon, albedo.inputs["Factor"])
    g.links.new(sombra.outputs[2], albedo.inputs[6]); g.links.new(en_base, albedo.inputs[7])

    # col = albedo*ambiente + albedo*toon
    amb = mix((160, 80), "MULTIPLY")
    g.links.new(albedo.outputs[2], amb.inputs[6]); amb.inputs[7].default_value = AMBIENTE
    toon_col = n.new("ShaderNodeMix"); toon_col.data_type = "RGBA"; toon_col.location = (-40, -320)
    toon_col.blend_type = "MIX"; toon_col.inputs["Factor"].default_value = 1.0
    g.links.new(en_toon, toon_col.inputs[6]); toon_col.inputs[7].default_value = (1, 1, 1, 1)
    luz = mix((160, -160), "MULTIPLY")      # el toon va como COLOR: con factor=toon, un factor 0
    g.links.new(albedo.outputs[2], luz.inputs[6])       # devolveria el albedo y no habria sombra
    g.links.new(toon_col.outputs[2], luz.inputs[7])
    suma = mix((340, -40), "ADD")
    g.links.new(amb.outputs[2], suma.inputs[6]); g.links.new(luz.outputs[2], suma.inputs[7])

    # rim = smoothstep(grosor - suave, grosor + suave, 1 - sat(N·V))
    # El grosor es una ENTRADA del grupo y las posiciones de un ColorRamp no se pueden conducir por
    # entrada, asi que el smoothstep se monta con cuentas: si se deja una rampa fija de 0 a 1, el rim
    # cubre toda la superficie como un degradado suave y se come el corte duro.
    capa = n.new("ShaderNodeLayerWeight"); capa.location = (160, -420)
    capa.inputs["Blend"].default_value = 0.5
    fondo_rim = n.new("ShaderNodeMath"); fondo_rim.location = (160, -560)      # grosor - suave
    fondo_rim.operation = "SUBTRACT"
    g.links.new(en_grosor, fondo_rim.inputs[0])
    fondo_rim.inputs[1].default_value = RIM_SUAVE
    resta = n.new("ShaderNodeMath"); resta.location = (340, -420)
    resta.operation = "SUBTRACT"
    g.links.new(capa.outputs["Facing"], resta.inputs[0])
    g.links.new(fondo_rim.outputs[0], resta.inputs[1])
    normaliza = n.new("ShaderNodeMath"); normaliza.location = (340, -560)
    normaliza.operation = "MULTIPLY"
    g.links.new(resta.outputs[0], normaliza.inputs[0])
    normaliza.inputs[1].default_value = 1.0 / (2.0 * RIM_SUAVE)
    recorte = n.new("ShaderNodeClamp"); recorte.location = (520, -420)
    g.links.new(normaliza.outputs[0], recorte.inputs[0])
    t2 = n.new("ShaderNodeMath"); t2.location = (700, -420)                    # t*t*(3 - 2t)
    t2.operation = "MULTIPLY"
    g.links.new(recorte.outputs[0], t2.inputs[0]); g.links.new(recorte.outputs[0], t2.inputs[1])
    tres = n.new("ShaderNodeMath"); tres.location = (700, -560)
    tres.operation = "MULTIPLY_ADD"
    g.links.new(recorte.outputs[0], tres.inputs[0])
    tres.inputs[1].default_value = -2.0; tres.inputs[2].default_value = 3.0
    suave = n.new("ShaderNodeMath"); suave.location = (860, -480)
    suave.operation = "MULTIPLY"
    g.links.new(t2.outputs[0], suave.inputs[0]); g.links.new(tres.outputs[0], suave.inputs[1])
    rim = mix((1030, -420), "MULTIPLY", 1.0)
    rim.inputs[6].default_value = tuple(c * 0.5 for c in RIM_COLOR[:3]) + (1.0,)
    g.links.new(suave.outputs[0], rim.inputs[7])       # un float entra como gris: color * scalar
    fuerza = mix((1200, -420), "MULTIPLY", 1.0)
    g.links.new(rim.outputs[2], fuerza.inputs[6])
    g.links.new(en_rim, fuerza.inputs[7])
    total = mix((700, -120), "ADD")
    g.links.new(suma.outputs[2], total.inputs[6]); g.links.new(fuerza.outputs[2], total.inputs[7])
    g.links.new(total.outputs[2], sal.inputs["Emission"])
    return g


GRUPO = grupo_toon()


# ---------------------------------------------------------------- material toon
def image_de_base(arbol):
    """La imagen que alimenta el color base (la primera TEX_IMAGE no siempre lo es: el GLB mete
    tambien el mapa de normales)."""
    for nodo in arbol.nodes:
        if nodo.type == "BSDF_PRINCIPLED" and nodo.inputs["Base Color"].links:
            origen = nodo.inputs["Base Color"].links[0].from_node
            if origen.type == "TEX_IMAGE":
                return origen.image
    for nodo in arbol.nodes:
        if nodo.type == "TEX_IMAGE" and nodo.image and "normal" not in nodo.image.name.lower():
            return nodo.image
    return None


CARPETA_TEXTURAS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "kotone_shiomi", "02_texturas")


def mapa_oscuro(nombre_base):
    """El mapa oscuro del juego (*_darkcolor.png) no viaja en el GLB: si el paquete lo tiene, se
    carga desde disco. El shader lo usa suavizado: lerp(darkMap, 1, 0.5)."""
    raiz = nombre_base.rsplit(".", 1)[0]
    if raiz.lower().endswith("_bc"):
        raiz = raiz[:-3]
    ruta = os.path.join(CARPETA_TEXTURAS, raiz + "_darkcolor.png")
    if os.path.exists(ruta):
        print("mapa oscuro:", os.path.basename(ruta))
        return bpy.data.images.load(ruta, check_existing=True)
    return None


def material_contorno():
    if "P5X_Outline" in bpy.data.materials:
        return bpy.data.materials["P5X_Outline"]
    m = bpy.data.materials.new("P5X_Outline")
    m.use_nodes = True
    m.node_tree.nodes.clear()
    salida = m.node_tree.nodes.new("ShaderNodeOutputMaterial")
    emi = m.node_tree.nodes.new("ShaderNodeEmission")
    emi.inputs["Color"].default_value = OUTLINE_COLOR
    m.node_tree.links.new(emi.outputs["Emission"], salida.inputs["Surface"])
    m.use_backface_culling = True
    return m


def aplicar_toon(mat):
    arbol = mat.node_tree
    base = image_de_base(arbol)
    par, mat_juego = params_de(mat.name)
    oscuro = mapa_oscuro(base.name) if (base is not None and par["enable_dark"] > 0.5) else None

    arbol.nodes.clear()
    salida = arbol.nodes.new("ShaderNodeOutputMaterial"); salida.location = (900, 0)
    principled = arbol.nodes.new("ShaderNodeBsdfPrincipled"); principled.location = (620, 0)
    principled.inputs["Base Color"].default_value = (0, 0, 0, 1)
    principled.inputs["Roughness"].default_value = 1.0
    if "Specular IOR Level" in principled.inputs:
        principled.inputs["Specular IOR Level"].default_value = 0.0
    arbol.links.new(principled.outputs["BSDF"], salida.inputs["Surface"])

    # corte toon de ESTE material, fuera del grupo (la posicion del escalon es por material).
    # Se calcula el N·L analiticamente con una direccion de luz FIJA, igual que el shader del juego
    # (luz direccional): meter un Diffuse BSDF real arrastraria la intensidad de la lampara de la
    # escena al calculo y el umbral dejaria de significar lo que significa en el shader.
    geonorm = arbol.nodes.new("ShaderNodeNewGeometry"); geonorm.location = (-880, 460)
    normalizar = arbol.nodes.new("ShaderNodeVectorMath"); normalizar.location = (-700, 460)
    normalizar.operation = "NORMALIZE"
    luzdir = arbol.nodes.new("ShaderNodeCombineXYZ"); luzdir.location = (-700, 300)
    for i, c in enumerate(DIR_LUZ):
        luzdir.inputs[i].default_value = c
    punto = arbol.nodes.new("ShaderNodeVectorMath"); punto.location = (-520, 460)
    punto.operation = "DOT_PRODUCT"
    envolver = arbol.nodes.new("ShaderNodeMath"); envolver.location = (-340, 460)
    envolver.operation = "MULTIPLY_ADD"
    envolver.inputs[1].default_value = 0.5; envolver.inputs[2].default_value = 0.5
    rampa = arbol.nodes.new("ShaderNodeValToRGB"); rampa.location = (-160, 460)
    rampa.color_ramp.interpolation = "CONSTANT"
    # la entrada es el N·L YA ENVUELTO: ahi el corte del juego vale _ToonCutLocation tal cual
    corte_w = min(max(par["cut"], 0.0), 1.0)
    ancho = 1.0 / max(par["sharp"], 0.0001)
    rampa.color_ramp.elements[0].position = corte_w
    rampa.color_ramp.elements[0].color = (0, 0, 0, 1)
    rampa.color_ramp.elements[1].position = min(corte_w + ancho, 1.0)
    rampa.color_ramp.elements[1].color = (1, 1, 1, 1)
    arbol.links.new(geonorm.outputs["Normal"], normalizar.inputs[0])
    arbol.links.new(normalizar.outputs[0], punto.inputs[0])
    arbol.links.new(luzdir.outputs[0], punto.inputs[1])
    arbol.links.new(punto.outputs["Value"], envolver.inputs[0])
    arbol.links.new(envolver.outputs[0], rampa.inputs["Fac"])

    grupo = arbol.nodes.new("ShaderNodeGroup"); grupo.location = (300, 0)
    grupo.node_tree = GRUPO
    arbol.links.new(rampa.outputs["Color"], grupo.inputs["Toon"])
    grupo.inputs["DarkTint"].default_value = tuple(par["tint"]) + (1.0,)
    grupo.inputs["Rim"].default_value = par["rim"]
    grupo.inputs["RimGrosor"].default_value = par["rim_grosor"]
    arbol.links.new(grupo.outputs["Emission"], principled.inputs["Emission Color"])
    principled.inputs["Emission Strength"].default_value = 1.0

    if base is not None:
        tex = arbol.nodes.new("ShaderNodeTexImage"); tex.location = (-620, 180)
        tex.image = base
        arbol.links.new(tex.outputs["Color"], grupo.inputs["Base"])
        # recorte alfa del shader del juego (TransparentCutout, cola 2450)
        alfa = arbol.nodes.new("ShaderNodeMath"); alfa.location = (-620, -260)
        alfa.operation = "GREATER_THAN"; alfa.inputs[1].default_value = par["alfa"]
        arbol.links.new(tex.outputs["Alpha"], alfa.inputs[0])
        arbol.links.new(alfa.outputs[0], principled.inputs["Alpha"])
        try:
            mat.blend_method = "CLIP"
            mat.alpha_threshold = par["alfa"]
        except (AttributeError, TypeError):
            pass
    else:
        grupo.inputs["Base"].default_value = (0.8, 0.8, 0.8, 1)
    if oscuro is not None:
        texd = arbol.nodes.new("ShaderNodeTexImage"); texd.location = (-620, -40)
        texd.image = oscuro
        arbol.links.new(texd.outputs["Color"], grupo.inputs["Dark"])
    else:
        grupo.inputs["Dark"].default_value = (1, 1, 1, 1)
    return base is not None, mat_juego, par


CONTORNO_MAT = material_contorno()
PROCESADOS = {}
cuerpos, con_textura, resumen = [], 0, []
for obj in [o for o in bpy.data.objects if o.type == "MESH" and o.data.vertices]:
    if obj.name.startswith(("Icosphere", "glTF")):
        continue
    for mat in [s for s in obj.data.materials if s is not None]:
        if mat.name in PROCESADOS:
            continue
        hay_base, mat_juego, par = aplicar_toon(mat)
        PROCESADOS[mat.name] = mat_juego
        con_textura += 1 if hay_base else 0
        resumen.append((mat.name, mat_juego, par["cut"], par["sharp"], par["rim"]))
    cuerpos.append(obj)

# --- contorno: duplicado con Solidify de normales volteadas (desactivado, ver cabecera) ---
contornos = []
for obj in cuerpos:
    dup = obj.copy()
    dup.data = obj.data.copy()
    dup.name = obj.name + "_contorno"
    dup.data.materials.clear()
    dup.data.materials.append(CONTORNO_MAT)
    bpy.context.collection.objects.link(dup)
    sol = dup.modifiers.new("contorno", "SOLIDIFY")
    sol.thickness = CONTORNO
    sol.offset = 1.0
    sol.use_flip_normals = True
    sol.use_rim = False
    dup.hide_render = True
    contornos.append(dup)

# ---------------------------------------------------------------- luces, camara y render
for o in [o for o in bpy.data.objects if o.type == "LIGHT"]:
    bpy.data.objects.remove(o, do_unlink=True)
luz_sol = bpy.data.objects.new("sol_clave", bpy.data.lights.new("sol_clave", "SUN"))
luz_sol.data.energy = 3.0
luz_sol.data.angle = math.radians(1.0)
luz_sol.rotation_euler = (math.radians(35), 0, math.radians(155))
bpy.context.collection.objects.link(luz_sol)
mundo = bpy.context.scene.world or bpy.data.worlds.new("World")
bpy.context.scene.world = mundo
mundo.use_nodes = True
fondo = mundo.node_tree.nodes.get("Background")
if fondo:
    fondo.inputs[0].default_value = AMBIENTE
    fondo.inputs[1].default_value = 1.0

mn = Vector((1e9,) * 3); mx = Vector((-1e9,) * 3)
for obj in cuerpos:
    for v in obj.data.vertices:
        w = obj.matrix_world @ v.co
        for k in range(3):
            mn[k] = min(mn[k], w[k]); mx[k] = max(mx[k], w[k])
centro = (mn + mx) / 2
alto = max(mx[2] - mn[2], 0.1)


def mirar(ang, dist, objetivo, lens=60.0):
    cam = bpy.data.objects.get("camara") or bpy.data.objects.new("camara", bpy.data.cameras.new("camara"))
    if cam.name not in bpy.context.collection.objects:
        bpy.context.collection.objects.link(cam)
    cam.data.lens = lens
    cam.location = (objetivo.x + dist * math.sin(math.radians(ang)),
                    objetivo.y - dist * math.cos(math.radians(ang)), objetivo.z)
    cam.rotation_euler = (objetivo - Vector(cam.location)).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = cam


esc = bpy.context.scene
for motor in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
    try:
        esc.render.engine = motor
        break
    except TypeError:
        continue
esc.render.image_settings.file_format = "PNG"
esc.render.film_transparent = False
# Blender 4+ aplica por defecto el transform de vista AgX, que apaga y desatura los colores planos:
# un render toon tiene que salir con el ESTANDAR.
try:
    esc.view_settings.view_transform = "Standard"
    esc.view_settings.look = "None"
except TypeError:
    pass
try:
    esc.eevee.taa_render_samples = 16
except AttributeError:
    pass

# --- contorno por Freestyle (fiable en EEVEE, a diferencia del casco invertido) ---
esc.render.use_freestyle = True
capa = esc.view_layers[0]
capa.use_freestyle = True
ajustes = capa.freestyle_settings
if not ajustes.linesets:
    ajustes.linesets.new("contorno")
ls = ajustes.linesets[0]
ls.select_silhouette = True
ls.select_border = True
ls.select_crease = True
ls.select_edge_mark = False
ls.linestyle.color = OUTLINE_COLOR[:3]
ls.linestyle.thickness = 1.6
ls.linestyle.use_chaining = True

vistas = (("toonblender_01_frente", 0, 1.0), ("toonblender_02_perfil", 90, 1.0),
          ("toonblender_03_trescuartos", 35, 1.0), ("toonblender_04_cara", 0, 0.32))
for nombre, ang, factor in vistas:
    dist = (alto / (2 * math.tan(math.radians(28) / 2))) * 1.15 * factor
    objetivo = centro if factor > 0.5 else Vector((centro.x, centro.y, mn[2] + alto * 0.88))
    esc.render.resolution_x = 900
    esc.render.resolution_y = 1350 if factor > 0.5 else 900
    mirar(ang, dist, objetivo)
    esc.render.filepath = os.path.join(SAL, nombre + ".png")
    bpy.ops.render.render(write_still=True)
    print("render:", esc.render.filepath)

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(SAL, "kotone_toon.blend"))
print("RESUMEN cuerpos=%d contornos=%d materiales_con_textura=%d" % (len(cuerpos), len(contornos), con_textura))
for fila in resumen:
    print("  material %-26s <- %-30s corte=%.2f suavidad=%.1f rim=%.1f" %
          (fila[0], str(fila[1]), fila[2], fila[3], fila[4]))
print("blend guardado en", os.path.join(SAL, "kotone_toon.blend"))
