"""Construye el modelo de Source (SMD + esqueleto ValveBiped) a partir de Kotone.

Idea: no se rehace el rig en Blender. Se escribe el SMD a mano, que da control total:
  - El ESQUELETO usa los nombres, la jerarquia y las orientaciones de reposo de los supervivientes
    de L4D2 (medidas del .mdl del juego), que son las mismas que usa Garry's Mod (ValveBiped).
  - Las POSICIONES de los huesos son las articulaciones reales de Kotone, medidas de su propio rig.
  - Los PESOS se remapean: cada grupo de vertices del juego va al hueso ValveBiped que le corresponde
    (tabla explicita para el cuerpo, y el hueso mas cercano para pelo, falda, accesorios...).
  - Source solo admite 3 pesos por vertice, asi que se toman los 3 mayores y se renormaliza.
  - Las armas (lanza, vaina, pistola) se dejan fuera: un modelo de jugador no las lleva.
  - Unidades: Source usa pulgadas (1 unidad = 0,0254 m). La orientacion NO cambia: los modelos de
    Source miran hacia -Y con +Z arriba, igual que Blender y que este modelo (medido: los dedos de
    los pies apuntan a -Y).

Uso: blender --background --python construir_source.py -- <salida.smd>
"""
import json
import math
import os
import sys

import bpy

BLEND = r"C:\Users\Lukas\p5x-datamining\kotone_artista\Kotone_Shiomi.blend"
HUESOS_L4D2 = r"C:\Users\Lukas\p5x-datamining\_dl\l4d2\huesos_producer.json"
PULGADAS = 1.0 / 0.0254
# cuanto se reduce la malla para que el modelo entre en un solo trozo de Source (21845 vertices)
RATIO_REDUCCION = 0.6

# --- huesos que se exportan: nombre ValveBiped -> (hueso de Kotone del que se toma la posicion, padre) ---
# La posicion se toma de la cabeza del hueso indicado; la orientacion, del superviviente de L4D2.
HUESOS = [
    ("Pelvis", "Bip01 Pelvis", None),
    ("Spine", "Bip01 Spine", "Pelvis"),
    ("Spine1", "Bip01 Spine1", "Spine"),
    ("Spine2", "Bip01 Spine2", "Spine1"),
    ("Spine4", "SPINE4_SINTETICO", "Spine2"),
    ("Neck1", "Bip01 Neck", "Spine4"),
    ("Head1", "Bip01 Head", "Neck1"),
    ("L_Clavicle", "Bip01 L Clavicle", "Spine4"),
    ("L_UpperArm", "UpperArm_L_01", "L_Clavicle"),
    ("L_Forearm", "Forearm_L_01", "L_UpperArm"),
    ("L_Hand", "Bip01 L Hand", "L_Forearm"),
    ("R_Clavicle", "Bip01 R Clavicle", "Spine4"),
    ("R_UpperArm", "UpperArm_R_01", "R_Clavicle"),
    ("R_Forearm", "Forearm_R_01", "R_UpperArm"),
    ("R_Hand", "Bip01 R Hand", "R_Forearm"),
    ("L_Thigh", "Thigh_L_01", "Pelvis"),
    ("L_Calf", "Calf_L_01", "L_Thigh"),
    ("L_Foot", "Bip01 L Foot", "L_Calf"),
    ("L_Toe0", "Bip01 L Toe0", "L_Foot"),
    ("R_Thigh", "Thigh_R_01", "Pelvis"),
    ("R_Calf", "Calf_R_01", "R_Thigh"),
    ("R_Foot", "Bip01 R Foot", "R_Calf"),
    ("R_Toe0", "Bip01 R Toe0", "R_Foot"),
]
# dedos: mismo nombre en los dos rigs, solo hay que prefijar
for lado in ("L", "R"):
    for dedo in (0, 1, 2, 3, 4):
        HUESOS.append(("%s_Finger%d" % (lado, dedo), "Bip01 %s Finger%d" % (lado, dedo), "%s_Hand" % lado))
        HUESOS.append(("%s_Finger%d1" % (lado, dedo), "Bip01 %s Finger%d1" % (lado, dedo),
                       "%s_Finger%d" % (lado, dedo)))
        HUESOS.append(("%s_Finger%d2" % (lado, dedo), "Bip01 %s Finger%d2" % (lado, dedo),
                       "%s_Finger%d1" % (lado, dedo)))
# huesos de arma y referencia (posicion relativa copiada del juego)
HUESOS.append(("weapon_bone", "RELATIVO:R_Hand", "R_Hand"))
HUESOS.append(("L_weapon_bone", "RELATIVO:L_Hand", "L_Hand"))
HUESOS.append(("forward", "RELATIVO:Head1", "Head1"))
HUESOS.append(("attachment_armL_T", "RELATIVO:L_Forearm", "L_Forearm"))
HUESOS.append(("attachment_armR_T", "RELATIVO:R_Forearm", "R_Forearm"))

# --- grupos de vertices que van a un hueso concreto (el resto, al hueso mas cercano) ---
MAPA = {
    "Bip01 Pelvis": "Pelvis", "Bip01 Spine": "Spine", "Bip01 Spine1": "Spine1",
    "Bip01 Spine2": "Spine2", "Bip01 Neck": "Neck1", "Bip01 Head": "Head1",
    "BN_head": "Head1",
    "Bip01 L Clavicle": "L_Clavicle", "Bip01 R Clavicle": "R_Clavicle",
    "Bip01 L Hand": "L_Hand", "Bip01 R Hand": "R_Hand",
    "Bip01 L Foot": "L_Foot", "Bip01 R Foot": "R_Foot",
    "Bip01 L Toe0": "L_Toe0", "Bip01 R Toe0": "R_Toe0",
    "UpperArm_L_01": "L_UpperArm", "UpperArm_L_02": "L_UpperArm",
    "UpperArm_R_01": "R_UpperArm", "UpperArm_R_02": "R_UpperArm",
    "Forearm_L_01": "L_Forearm", "Forearm_L_02": "L_Forearm",
    "Forearm_R_01": "R_Forearm", "Forearm_R_02": "R_Forearm",
    "Thigh_L_01": "L_Thigh", "Thigh_L_02": "L_Thigh",
    "Thigh_R_01": "R_Thigh", "Thigh_R_02": "R_Thigh",
    "Calf_L_01": "L_Calf", "Calf_L_02": "L_Calf", "Bone_xi_L": "L_Calf",
    "Calf_R_01": "R_Calf", "Calf_R_02": "R_Calf", "Bone_xi_R": "R_Calf",
}
for lado in ("L", "R"):
    for dedo in (0, 1, 2, 3, 4):
        MAPA["Bip01 %s Finger%d" % (lado, dedo)] = "%s_Finger%d" % (lado, dedo)
        MAPA["Bip01 %s Finger%d1" % (lado, dedo)] = "%s_Finger%d1" % (lado, dedo)
        MAPA["Bip01 %s Finger%d2" % (lado, dedo)] = "%s_Finger%d2" % (lado, dedo)
MAPA["Bip01 %s Finger01" % "L"] = "L_Finger01"
MAPA["Bip01 %s Finger02" % "L"] = "L_Finger02"

# materiales de armas que no entran en un modelo de jugador
MATERIALES_FUERA = ("qiang", "qiangtao", "pistola")


def quat_local_a_matriz(q):
    """Quaternion (x,y,z,w) local -> matriz 3x3 de filas, para el bloque skeleton del SMD."""
    x, y, z, w = q
    return [
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ]


def quat_a_euler(q):
    """Quaternion (x,y,z,w) local -> angulos de Euler (radianes) para el bloque skeleton del SMD.

    El SMD espera <indice> <px> <py> <pz> <rx> <ry> <rz>: TRES angulos, no una matriz. Escribir una
    matriz hacia que studiomdl leyera su primera fila como si fueran angulos, y los huesos quedaban
    girados (medido: mi Spine1 acababa a lo largo de -Z en vez de +X, y las animaciones de
    $includemodel encajan sobre huesos con otra orientacion).
    La conversion (y su inversa) esta verificada contra los 82 huesos del survivor_producer.mdl
    del juego: reproducen sus quaternions exactamente (coincidencia 1.000000).
    """
    x, y, z, w = q
    roll = math.atan2(2 * (w * x + y * z), 1 - 2 * (x * x + y * y))
    pitch = math.asin(max(-1.0, min(1.0, 2 * (w * y - z * x))))
    yaw = math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))
    return (roll, pitch, yaw)


def aplicar(m, v):
    return [sum(m[i][j] * v[j] for j in range(3)) for i in range(3)]


def main():
    salida = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "kotone.smd"
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    l4d2 = {b["nombre"].replace("ValveBiped.", ""): b for b in json.load(open(HUESOS_L4D2))["huesos"]}

    # --- 1) posicion global (en metros, mundo) de cada hueso de destino ---
    hueso_de = {b.name: b for b in arm.data.bones}
    global_m = {}
    for nombre, fuente, _ in HUESOS:
        if fuente.startswith("RELATIVO:"):
            continue                                    # se calcula despues, como offset del juego
        if fuente == "SPINE4_SINTETICO":
            a = arm.matrix_world @ hueso_de["Bip01 Spine2"].head_local
            b = arm.matrix_world @ hueso_de["Bip01 Neck"].head_local
            global_m[nombre] = (a + b) * 0.5            # a mitad de camino entre pecho y cuello
            continue
        if fuente not in hueso_de:
            raise SystemExit("falta el hueso %s en el rig de Kotone" % fuente)
        global_m[nombre] = arm.matrix_world @ hueso_de[fuente].head_local

    # --- 2) local de cada hueso = R(padre global)^-1 * (hijo_global - padre_global) ---
    #     con las rotaciones GLOBALES de L4D2 (asi las animaciones del juego encajan)
    def rot_global(nombre):
        m = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
        cadena = []
        n = nombre
        while n is not None:
            cadena.append(n)
            n = dict((h[0], h[2]) for h in HUESOS).get(n)
        for n in reversed(cadena):
            # OJO con el orden: la cadena va de la raiz al hueso, y la matriz del mundo se acumula
            # como R(raiz) * R(hijo) * ... Poniendo R(hijo) * R(raiz) las posiciones salian
            # expresadas en un sistema girado y la columna se torcia hacia -Z.
            m = multiplicar(m, quat_local_a_matriz(l4d2["Bip01_" + n]["quat"]))
        return m

    def multiplicar(a, b):
        return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]

    def inversa_rot(m):
        return [[m[j][i] for j in range(3)] for i in range(3)]

    padres = dict((h[0], h[2]) for h in HUESOS)
    orden = []
    for nombre, _, _ in HUESOS:
        cadena = []
        n = nombre
        while n is not None and n not in orden:
            cadena.append(n)
            n = padres[n]
        orden.extend(reversed(cadena))
    orden = list(dict.fromkeys(orden))

    local = {}
    for nombre in orden:
        if nombre in global_m:
            continue
        padre = padres[nombre]
        fuente = dict((h[0], h[1]) for h in HUESOS)[nombre]
        ref = fuente.split(":")[1]
        # offset local del juego (en pulgadas) aplicado al hueso de referencia
        nombre_l4d2 = "Bip01_" + ref
        if nombre_l4d2 in l4d2:
            off = l4d2[nombre_l4d2 if nombre in ("weapon_bone", "L_weapon_bone", "forward",
                                                 "attachment_armL_T", "attachment_armR_T") else nombre_l4d2]["pos"]
            off = [off[0] / PULGADAS, off[1] / PULGADAS, off[2] / PULGADAS]
            # los offsets de arma/forward se copian del juego solo si el nombre coincide
            off = [0, 0, 0]
        else:
            off = [0, 0, 0]
        p = global_m[ref]
        desp = aplicar(rot_global(ref), off)
        global_m[nombre] = (p[0] + desp[0], p[1] + desp[1], p[2] + desp[2])

    # offsets reales de arma y referencia, tal como los tiene el juego (relativos a la mano/cabeza)
    for nombre, ref in (("weapon_bone", "Bip01_R_Hand"), ("L_weapon_bone", "Bip01_L_Hand"),
                        ("forward", "Bip01_Head1"), ("attachment_armL_T", "Bip01_L_Forearm"),
                        ("attachment_armR_T", "Bip01_R_Forearm")):
        off = l4d2[ref]["pos"]
        off_m = [off[0] / PULGADAS, off[1] / PULGADAS, off[2] / PULGADAS]
        ref_kotone = {v: k for k, v in MAPA.items()}.get(ref.replace("Bip01_", "").replace("_", " "), None)
        p = global_m[[h[0] for h in HUESOS if h[0] == nombre.replace("weapon_bone", "R_Hand")][0]] if False else None
        base = global_m[{"weapon_bone": "R_Hand", "L_weapon_bone": "L_Hand", "forward": "Head1",
                         "attachment_armL_T": "L_Forearm", "attachment_armR_T": "R_Forearm"}[nombre]]
        desp = aplicar(rot_global({"weapon_bone": "R_Hand", "L_weapon_bone": "L_Hand", "forward": "Head1",
                                   "attachment_armL_T": "L_Forearm", "attachment_armR_T": "R_Forearm"}[nombre]), off_m)
        global_m[nombre] = (base[0] + desp[0], base[1] + desp[1], base[2] + desp[2])

    for nombre in orden:
        padre = padres[nombre]
        gp = global_m[nombre]
        if padre is None:
            local[nombre] = list(gp)
        else:
            pp = global_m[padre]
            d = [gp[i] - pp[i] for i in range(3)]
            local[nombre] = aplicar(inversa_rot(rot_global(padre)), d)

    print("huesos a exportar:", len(orden))
    for n in orden[:6]:
        print("   %-22s local(pulgadas) %8.2f %8.2f %8.2f" % (n, *[v * PULGADAS for v in local[n]]))

    # --- 3) mapeo de pesos ---
    def destino(grupo, pos_m):
        if grupo in MAPA:
            return MAPA[grupo]
        # el hueso mas cercano de la lista, midiendo desde la cabeza del grupo
        mejor, dist = None, 1e9
        for nombre, _, _ in HUESOS:
            d = sum((global_m[nombre][i] - pos_m[i]) ** 2 for i in range(3))
            if d < dist:
                mejor, dist = nombre, d
        return mejor

    mapa_final = {}
    for ob in bpy.data.objects:
        if ob.type != "MESH":
            continue
        for g in ob.vertex_groups:
            hb = hueso_de.get(g.name) if g.name in hueso_de else None
            if hb is not None:
                pos = arm.matrix_world @ hb.head_local
            else:
                pos = (0.0, 0.0, 0.0)
            mapa_final[g.name] = destino(g.name, pos)
    json.dump(mapa_final, open(os.path.splitext(salida)[0] + "_mapa_pesos.json", "w"), indent=1, sort_keys=True)
    print("grupos de vertices:", len(mapa_final))

    # --- 4) escribir el SMD ---
    # El esqueleto tiene que ser EXACTAMENTE el del juego: los mismos 82 huesos, en el mismo orden
    # y con la misma jerarquia. $includemodel exige esqueleto identico; si no, las secuencias de
    # anim_producer.mdl apuntan a huesos que no existen y el juego se cae al cargar el mapa.
    # Comprobado: el modelo del juego tiene 82 huesos y el mio tenia 58.
    SIN_BIP01 = {"weapon_bone", "L_weapon_bone", "forward", "attachment_armL_T", "attachment_armR_T"}

    def nombre_juego(n):
        return "ValveBiped.%s" % n if n in SIN_BIP01 else "ValveBiped.Bip01_%s" % n

    juego = json.load(open(HUESOS_L4D2))["huesos"]
    orden_juego = [b["nombre"] for b in juego]
    indices = {n: i for i, n in enumerate(orden_juego)}
    indice_mio = {}
    for n in orden:
        nj = nombre_juego(n)
        if nj not in indices:
            raise SystemExit("mi hueso %s no existe en el esqueleto del juego (%s)" % (n, nj))
        indice_mio[n] = indices[nj]
    mios = {nombre_juego(n) for n in orden}
    faltan = [j for j in orden_juego if j not in mios]
    print("esqueleto: %d huesos del juego | %d con proporciones de Kotone | %d heredados del juego"
          % (len(orden_juego), len(orden), len(faltan)))
    if faltan:
        print("   heredados:", ", ".join(f.replace("ValveBiped.Bip01_", "").replace("ValveBiped.", "")
                                          for f in faltan))

    lineas = ["version 1", "nodes"]
    for i, b in enumerate(juego):
        lineas.append('%d "%s" %d' % (i, b["nombre"], b["padre"]))
    lineas.append("end")
    lineas.append("skeleton")
    lineas.append("time 0")
    for i, b in enumerate(juego):
        # el SMD quiere angulos de Euler, no una matriz (ver quat_a_euler)
        r = quat_a_euler(b["quat"])
        corto = b["nombre"].replace("ValveBiped.Bip01_", "").replace("ValveBiped.", "")
        if corto in local and b["nombre"] == nombre_juego(corto):
            p = [v * PULGADAS for v in local[corto]]
        else:
            p = list(b["pos"])          # hueso que Kotone no tiene: se copia del juego
        lineas.append("%d %.6f %.6f %.6f %.6f %.6f %.6f"
                      % (i, p[0], p[1], p[2], r[0], r[1], r[2]))
    lineas.append("end")
    lineas.append("triangles")

    total_verts = 0
    total_tris = 0
    for ob in sorted([o for o in bpy.data.objects if o.type == "MESH"], key=lambda o: o.name):
        materiales = [m.name for m in ob.data.materials]
        if any(any(fuera in m.lower() for fuera in MATERIALES_FUERA) for m in materiales):
            print("   se deja fuera la malla %s (materiales %s)" % (ob.name, materiales))
            continue
        me = ob.data
        # Source mete 21845 vertices por modelo; con 24.000 el modelo se parte en dos trozos.
        # Se reduce la malla (los pesos y las UV se interpolan) para que entre holgado en uno solo.
        origen = ob
        copia = me.copy()
        temp = bpy.data.objects.new("temp_decimado", copia)
        bpy.context.collection.objects.link(temp)
        temp.matrix_world = ob.matrix_world
        # las expresiones (formas clave) no se pueden reducir: Source usa otro sistema (flex),
        # asi que para este modelo se quitan. La malla se queda igual, en su forma de reposo.
        if copia.shape_keys:
            print("   %s: se quitan %d formas clave (expresiones)" % (origen.name, len(copia.shape_keys.key_blocks)))
            bpy.context.view_layer.objects.active = temp
            temp.shape_key_clear()
        bpy.context.view_layer.objects.active = temp
        mod = temp.modifiers.new("reducir", "DECIMATE")
        mod.decimate_type = "COLLAPSE"
        mod.ratio = RATIO_REDUCCION
        bpy.ops.object.modifier_apply(modifier="reducir")
        antes, despues = len(me.vertices), len(copia.vertices)
        me = copia
        ob = temp
        # los NOMBRES de los grupos viven en el objeto, no en la malla: se toman del original
        grupos = origen.vertex_groups
        print("   %s: %d -> %d vertices (x%.2f)" % (origen.name, antes, despues, RATIO_REDUCCION))
        me.calc_loop_triangles()
        uv = me.uv_layers.active.data if me.uv_layers.active else None
        mw = ob.matrix_world
        por_vertice = {}
        for v in me.vertices:
            pesos = {}
            for ge in v.groups:
                if ge.weight <= 0.0005:
                    continue
                nombre_g = grupos[ge.group].name
                destino_n = mapa_final.get(nombre_g)
                if destino_n is None:
                    continue
                pesos[destino_n] = pesos.get(destino_n, 0.0) + ge.weight
            if not pesos:
                pesos = {"Pelvis": 1.0}
            mejores = sorted(pesos.items(), key=lambda kv: -kv[1])[:3]      # Source: 3 pesos maximo
            suma = sum(p for _, p in mejores) or 1.0
            por_vertice[v.index] = [(n, p / suma) for n, p in mejores if p / suma > 0.0005]
        for tri in me.loop_triangles:
            material = materiales[tri.material_index] if materiales else "body01"
            cortos = {"PC079_01_body01": "body01", "PC079_01_body02": "body02", "PC079_01_eye": "eye",
                      "PC079_01_face": "face", "PC079_01_hair": "hair", "PC079_01_xiuzhang": "xiuzhang"}
            # El material va ANTES DE CADA TRIANGULO. Comprobado con -dumpmaterials: si se escribe
            # una sola vez por grupo, studiomdl cuenta cada linea de vertice como un material nuevo
            # y aborta con "Too many materials used, max 32". Repetido por triangulo, cuenta 6.
            lineas.append(cortos.get(material, material))
            for li in tri.loops:
                v = me.vertices[me.loops[li].vertex_index]
                p = mw @ v.co
                nrm = (mw.to_3x3() @ v.normal)
                largo = math.sqrt(nrm.x ** 2 + nrm.y ** 2 + nrm.z ** 2) or 1.0
                u, vv = (uv[li].uv if uv else (0.0, 0.0))
                enlaces = por_vertice.get(v.index, [("Pelvis", 1.0)])
                lineas.append("%d %.6f %.6f %.6f %.6f %.6f %.6f %.6f %.6f %d %s" % (
                    indice_mio[enlaces[0][0]], p.x * PULGADAS, p.y * PULGADAS, p.z * PULGADAS,
                    nrm.x / largo, nrm.y / largo, nrm.z / largo, u, vv, len(enlaces),
                    " ".join("%d %.6f" % (indice_mio[n], w) for n, w in enlaces)))
                total_verts += 1
            total_tris += 1
    lineas.append("end")
    open(salida, "w", encoding="utf-8", newline="\n").write("\n".join(lineas) + "\n")
    print("SMD escrito:", salida)
    print("  vertices (con duplicados por bucle): %d | triangulos: %d | lineas: %d" %
          (total_verts, total_tris, len(lineas)))


main()