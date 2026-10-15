"""Del SMD saca los hitboxes y escribe el QC, el idle y los .qc de cada juego.

- Hitboxes: la caja envolvente de los vertices que cuelgan de cada hueso, en pulgadas. Sin esto
  L4D2 no detecta los impactos en el superviviente.
- idle.smd: un unico fotograma con el esqueleto, que es todo lo que necesita un modelo de jugador.
- Los .qc: uno para L4D2 (reemplaza a Rochelle) y otro para Garry's Mod (playermodel).

Uso: python qc_source.py <smd_entrada> <carpeta_salida>
"""
import math
import os
import sys

# Las 17 cajas del survivor_producer.mdl del juego, con su grupo de impacto. Los grupos son los
# estandar de Source (HITGROUP_*): 1 cabeza, 2 pecho, 3 estomago, 4 brazo izquierdo, 5 derecho,
# 6 pierna izquierda, 7 derecha. Antes usaba 8..13, que no existen.
# EL CONJUNTO TIENE QUE LLAMARSE "L4D": es el nombre que llevan TODOS los humanoides de L4D2 (los 4
# supervivientes, los anim_*, el Hunter, el Boomer, la Witch) y el juego lo busca por nombre.
CAJAS = [
    ("ValveBiped.Bip01_Pelvis", 3), ("ValveBiped.Bip01_Spine1", 3), ("ValveBiped.Bip01_Spine2", 2),
    ("ValveBiped.Bip01_Neck1", 1), ("ValveBiped.Bip01_Head1", 1),
    ("ValveBiped.Bip01_L_UpperArm", 4), ("ValveBiped.Bip01_L_Forearm", 4), ("ValveBiped.Bip01_L_Hand", 4),
    ("ValveBiped.Bip01_R_UpperArm", 5), ("ValveBiped.Bip01_R_Forearm", 5), ("ValveBiped.Bip01_R_Hand", 5),
    ("ValveBiped.Bip01_L_Thigh", 6), ("ValveBiped.Bip01_L_Calf", 6), ("ValveBiped.Bip01_L_Toe0", 6),
    ("ValveBiped.Bip01_R_Thigh", 7), ("ValveBiped.Bip01_R_Calf", 7), ("ValveBiped.Bip01_R_Toe0", 7),
]
# las cajas se inflan un poco: los impactos deben cubrir el cuerpo, no la malla exacta
HOLGURA = 0.30


def leer_smd(ruta):
    """Devuelve (huesos, esqueleto, triangulos) del SMD: nombres, transformadas y vertices con pesos."""
    huesos, esqueleto, tris = [], [], []
    modo = None
    for linea in open(ruta, encoding="utf-8", errors="replace"):
        s = linea.strip()
        if s in ("nodes", "skeleton", "triangles", "vertexanimation"):
            modo = s
            continue
        if s == "end":
            modo = None
            continue
        if not s:
            continue
        if modo == "nodes":
            partes = s.split('"')
            huesos.append((partes[1], int(s.split()[-1])))
        elif modo == "skeleton":
            if s.startswith("time"):
                continue
            v = [float(x) for x in s.split()]
            esqueleto.append(v)
        elif modo == "triangles":
            v = s.split()
            if len(v) < 10:                      # nombre de material
                continue
            tris.append(v)
    return huesos, esqueleto, tris


def quat_de_euler(e):
    """Angulos de Euler del SMD -> quaternion. Es la convencion de Valve (mathlib AngleQuaternion),
    verificada contra los 82 huesos del modelo del juego: reproduce sus quaternions exactos."""
    x, y, z = e
    sr, cr = math.sin(x / 2), math.cos(x / 2)
    sp, cp = math.sin(y / 2), math.cos(y / 2)
    sy, cy = math.sin(z / 2), math.cos(z / 2)
    return (sr * cp * cy - cr * sp * sy, cr * sp * cy + sr * cp * sy,
            cr * cp * sy - sr * sp * cy, cr * cp * cy + sr * sp * sy)


def matriz(q):
    x, y, z, w = q
    return [[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]]


def multiplicar(a, b):
    """Producto de matrices 4x4 (las transformadas de los huesos)."""
    n = len(a)
    return [[sum(a[i][k] * b[k][j] for k in range(n)) for j in range(n)] for i in range(n)]


def transformada_local(linea):
    """De una linea del bloque skeleton (indice, posicion, 3 angulos): matriz 4x4 local."""
    R = matriz(quat_de_euler(linea[4:7]))
    return [[R[i][0], R[i][1], R[i][2], linea[1 + i]] for i in range(3)] + [[0.0, 0.0, 0.0, 1.0]]


def mundiales(huesos, esqueleto):
    """Matriz mundial de cada hueso, acumulando la del padre (el padre sale del bloque nodes)."""
    local = {i: transformada_local(esqueleto[i]) for i in range(len(esqueleto))}
    W = {}

    def calc(i):
        if i in W:
            return W[i]
        p = huesos[i][1]
        base = calc(p) if 0 <= p < len(huesos) and p != i else \
            [[1.0 if a == b else 0.0 for b in range(4)] for a in range(4)]
        W[i] = multiplicar(base, local[i])
        return W[i]

    for i in range(len(esqueleto)):
        calc(i)
    return W


def invertir(M):
    """Inversa de una transformada rigida: rotacion traspuesta y traslacion girada."""
    at = [[M[j][i] for j in range(3)] for i in range(3)]
    t = [M[i][3] for i in range(3)]
    t2 = [-sum(at[i][k] * t[k] for k in range(3)) for i in range(3)]
    return [[at[i][j] for j in range(3)] + [t2[i]] for i in range(3)] + [[0.0, 0.0, 0.0, 1.0]]


def huesos_con_vertices(tris):
    """Indices de hueso a los que va colgado algun vertice (el dominante, peso >= 0,35)."""
    fuera = set()
    for v in tris:
        for k in range(int(v[9])):
            if float(v[11 + 2 * k]) >= 0.35:
                fuera.add(int(v[10 + 2 * k]))
    return fuera


def cajas(huesos, esqueleto, tris):
    """Caja envolvente, en el espacio LOCAL de cada hueso, de la geometria que cuelga de el.

    Los vertices del SMD estan en el espacio del mundo: se pasan al local del hueso con la inversa
    de su matriz mundial. Si un hueso no lleva vertices propios (los dedos de los pies), se usa la
    geometria de sus descendientes, de modo que la caja sigue cubriendo esa parte del cuerpo.
    """
    por_hueso = {}
    for v in tris:
        pos = [float(x) for x in v[1:4]]
        enlaces = int(v[9])
        mejor, pesomejor = None, 0.35
        for k in range(enlaces):
            n = int(v[10 + 2 * k])
            w = float(v[11 + 2 * k])
            if w > pesomejor:
                mejor, pesomejor = n, w
        if mejor is not None:
            por_hueso.setdefault(mejor, []).append(pos)

    hijos = {}
    for i, (_, p) in enumerate(huesos):
        hijos.setdefault(p, []).append(i)

    def descendientes(i):
        fuera, pila = [], [i]
        while pila:
            a = pila.pop()
            fuera.append(a)
            pila.extend(hijos.get(a, []))
        return fuera

    W = mundiales(huesos, esqueleto)
    idx = {n: i for i, (n, _) in enumerate(huesos)}
    salida = {}
    for nombre, grupo in CAJAS:
        i = idx.get(nombre)
        if i is None:
            continue
        puntos = list(por_hueso.get(i, []))
        if not puntos:
            # el hueso no lleva geometria propia (los dedos de los pies): se usa la de sus
            # descendientes, de modo que la caja sigue cubriendo esa parte del cuerpo
            for j in descendientes(i):
                if j != i:
                    puntos.extend(por_hueso.get(j, []))
        if not puntos:
            print("   aviso: %s y sus hijos no llevan geometria" % nombre)
            continue
        inv = invertir(W[i])
        mn = [1e9] * 3
        mx = [-1e9] * 3
        for p in puntos:
            q = [sum(inv[r][k] * p[k] for k in range(3)) + inv[r][3] for r in range(3)]
            for r in range(3):
                mn[r] = min(mn[r], q[r])
                mx[r] = max(mx[r], q[r])
        salida[nombre] = (grupo, [v - HOLGURA for v in mn], [v + HOLGURA for v in mx])
    return salida


def escribir_idle(ruta, huesos, esqueleto):
    with open(ruta, "w", encoding="utf-8", newline="\n") as f:
        f.write("version 1\nnodes\n")
        for i, (n, p) in enumerate(huesos):
            f.write('%d "%s" %d\n' % (i, n, p))
        f.write("end\nskeleton\ntime 0\n")
        for v in esqueleto:
            f.write(" ".join("%.6f" % x for x in v) + "\n")
        f.write("end\n")


def qc(nombre_modelo, cdmaterials, idle, rellenos="", cajas_txt="", superficie="flesh"):
    return """// Generado por qc_source.py - Kotone Shiomi para Source
$modelname "%s"

$body "kotone" "Kotone_Shiomi.smd"
$cdmaterials "%s"
$surfaceprop "%s"
$mostlyopaque

$sequence idle "%s" fps 30 loop

$attachment "eyes" "ValveBiped.Bip01_Head1" -2.09 -2.75 0.85 rotate 0 -80.11 -90
$attachment "forward" "ValveBiped.Bip01_Head1" 2.00 -3.00 0.00 rotate 0 0 0
$attachment "anim_attachment_RH" "ValveBiped.Bip01_R_Hand" 0 0 0 rotate 0 0 0
$attachment "anim_attachment_LH" "ValveBiped.Bip01_L_Hand" 0 0 0 rotate 0 0 0

// Estos attachment no se usan en el juego: solo fuerzan a studiomdl a NO borrar los huesos de
// arma y referencia, que no llevan vertices y por eso se caen del modelo compilado.
$attachment "weapon_ref" "ValveBiped.weapon_bone" 0 0 0 rotate 0 0 0
$attachment "l_weapon_ref" "ValveBiped.L_weapon_bone" 0 0 0 rotate 0 0 0
$attachment "arml_ref" "ValveBiped.attachment_armL_T" 0 0 0 rotate 0 0 0
$attachment "armr_ref" "ValveBiped.attachment_armR_T" 0 0 0 rotate 0 0 0

// Relleno automatico: TODOS los huesos del esqueleto del juego que no llevan vertices. Sin esto
// studiomdl los borra, el modelo se queda con menos huesos que anim_producer.mdl y el juego se
// cae al cargar el mapa ($includemodel exige esqueleto identico).
%s

// El conjunto se llama "L4D", como el de todos los humanoides del juego: L4D2 lo busca por nombre.
// Las coordenadas van en el espacio LOCAL del hueso, y son minimo y maximo (no centro y tamano).
$hboxset "L4D"
%s
""" % (nombre_modelo, cdmaterials, superficie, idle, rellenos, cajas_txt)


if __name__ == "__main__":
    smd = sys.argv[1]
    destino = sys.argv[2]
    os.makedirs(destino, exist_ok=True)
    huesos, esqueleto, tris = leer_smd(smd)
    con_vertices = huesos_con_vertices(tris)
    print("SMD: %d huesos, %d triangulos, %d huesos con vertices"
          % (len(huesos), len(tris), len(con_vertices)))
    hechas = cajas(huesos, esqueleto, tris)
    lineas = []
    for nombre, grupo in CAJAS:
        if nombre not in hechas:
            continue
        grupo, mn, mx = hechas[nombre]
        lineas.append('$hbox %d "%s" %.2f %.2f %.2f %.2f %.2f %.2f'
                      % (grupo, nombre, mn[0], mn[1], mn[2], mx[0], mx[1], mx[2]))
        print("   hbox grupo %-2d %-28s min(%7.2f %7.2f %7.2f) max(%6.2f %6.2f %6.2f)"
              % (grupo, nombre.split("_", 1)[1], mn[0], mn[1], mn[2], mx[0], mx[1], mx[2]))
    if len(lineas) != len(CAJAS):
        print("   AVISO: solo %d de las %d cajas del juego" % (len(lineas), len(CAJAS)))
    # huesos que no llevan vertices: hay que conservarlos con un attachment de relleno
    ya = {"ValveBiped.weapon_bone", "ValveBiped.L_weapon_bone",
          "ValveBiped.attachment_armL_T", "ValveBiped.attachment_armR_T"}
    rellenos = []
    for i, (nombre, _) in enumerate(huesos):
        if i in con_vertices or nombre in ya:
            continue
        corto = nombre.replace("ValveBiped.Bip01_", "").replace("ValveBiped.", "")
        rellenos.append('$attachment "att_%s" "%s" 0 0 0 rotate 0 0 0' % (corto, nombre))
    print("   huesos sin vertices conservados con attachment de relleno: %d" % len(rellenos))
    escribir_idle(os.path.join(destino, "idle.smd"), huesos, esqueleto)
    abierto = open(os.path.join(destino, "kotone_l4d2.qc"), "w", encoding="utf-8", newline="\n")
    abierto.write(qc("survivors/survivor_producer.mdl", "models/kotone", "idle.smd",
                     "\n".join(rellenos), "\n".join(lineas)))
    abierto.close()
    abierto = open(os.path.join(destino, "kotone_gmod.qc"), "w", encoding="utf-8", newline="\n")
    abierto.write(qc("player/kotone/kotone.mdl", "models/kotone", "idle.smd",
                     "\n".join(rellenos), "\n".join(lineas)))
    abierto.close()
    print("escritos: idle.smd, kotone_l4d2.qc, kotone_gmod.qc en", destino)