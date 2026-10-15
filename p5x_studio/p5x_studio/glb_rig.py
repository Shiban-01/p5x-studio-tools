"""Ensambla un GLB riggeado (esqueleto + pesos de piel + expresiones) desde el volcado de Unity.

Por que existe: los bundles del juego traen las mallas y el esqueleto por separado, sin jerarquia de
renderizadores, asi que la unica forma de obtener huesos y pesos es montarlos dentro de Unity (ver
`unity.py` y el script `P5XSkeletonExport.cs`). Unity deja un volcado en binario compacto + JSON;
este modulo lo convierte en un GLB que se abre en Blender, Unity o cualquier visor, con su armadura.

Este es el ensamblador generico: la version original (`scripts/build_kotone_glb.py`) tenia a Kotone
escrito a mano (la lista de piezas, las rutas y la herencia de material del parpado). Aqui todo sale
del propio volcado, asi que sirve para cualquier personaje.

Como se reconstruye el esqueleto (esto es lo delicado, y esta explicado porque costo acertarlo):

  1. el espacio de bind de la malla es la referencia; para el hueso i, mundo(i) = inversa(ibm_i), de
     modo que mundo(i) * ibm_i = identidad y la pose de reposo reproduce la malla EXACTAMENTE;
  2. el arbol se deriva de esos mundos: local(j) = inversa(mundo(padre_j)) * mundo(j);
  3. los huesos que la lista del renderer deja fuera (estan en el prefab pero no tienen pesos, o sea
     que no tienen inversa de bind) se colocan ajustando el prefab al espacio de referencia con una
     rotacion rigida (Kabsch) sobre los huesos conocidos;
  4. la conversion a glTF (espejo en X para cambiar de mano + ejes Y arriba) se HORNEA en vertices,
     normales, huesos e inversas de bind: nada de nodo raiz con rotacion, que en Blender se dobla.

Sin numpy a proposito: el entorno de la herramienta solo trae Pillow, asi que el algebra (matrices
4x4, cuaterniones, autovalores por Jacobi y el ajuste rigido) esta escrito aqui en Python puro.
"""
from __future__ import annotations

import json
import math
import os
import struct
from pathlib import Path

from .idiomas import t

# --------------------------------------------------------------------------- matrices 4x4


def identidad() -> list[list[float]]:
    return [[1.0 if i == j else 0.0 for j in range(4)] for i in range(4)]


def mul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]


def inv(m):
    """Inversa por Gauss-Jordan. Devuelve None si es singular."""
    n = 4
    a = [row[:] + [1.0 if i == j else 0.0 for j in range(n)] for i, row in enumerate(m)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(a[r][col]))
        if abs(a[piv][col]) < 1e-12:
            return None
        a[col], a[piv] = a[piv], a[col]
        p = a[col][col]
        a[col] = [v / p for v in a[col]]
        for r in range(n):
            if r == col:
                continue
            f = a[r][col]
            if f:
                a[r] = [a[r][c] - f * a[col][c] for c in range(2 * n)]
    return [row[n:] for row in a]


def transpuesta(m):
    return [[m[j][i] for j in range(4)] for i in range(4)]


def quat_mat(q):
    x, y, z, w = q
    n = x * x + y * y + z * z + w * w
    if n < 1e-12:
        return identidad()
    s = 2.0 / n
    return [
        [1 - s * (y * y + z * z), s * (x * y - z * w), s * (x * z + y * w), 0.0],
        [s * (x * y + z * w), 1 - s * (x * x + z * z), s * (y * z - x * w), 0.0],
        [s * (x * z - y * w), s * (y * z + x * w), 1 - s * (x * x + y * y), 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]


def mat_quat(m):
    """Matriz 3x3 -> cuaternion (x, y, z, w)."""
    t = m[0][0] + m[1][1] + m[2][2]
    if t > 0:
        s = math.sqrt(t + 1.0) * 2
        w = 0.25 * s
        x = (m[2][1] - m[1][2]) / s
        y = (m[0][2] - m[2][0]) / s
        z = (m[1][0] - m[0][1]) / s
    elif m[0][0] > m[1][1] and m[0][0] > m[2][2]:
        s = math.sqrt(1.0 + m[0][0] - m[1][1] - m[2][2]) * 2
        w = (m[2][1] - m[1][2]) / s
        x = 0.25 * s
        y = (m[0][1] + m[1][0]) / s
        z = (m[0][2] + m[2][0]) / s
    elif m[1][1] > m[2][2]:
        s = math.sqrt(1.0 + m[1][1] - m[0][0] - m[2][2]) * 2
        w = (m[0][2] - m[2][0]) / s
        x = (m[0][1] + m[1][0]) / s
        y = 0.25 * s
        z = (m[1][2] + m[2][1]) / s
    else:
        s = math.sqrt(1.0 + m[2][2] - m[0][0] - m[1][1]) * 2
        w = (m[1][0] - m[0][1]) / s
        x = (m[0][2] + m[2][0]) / s
        y = (m[1][2] + m[2][1]) / s
        z = 0.25 * s
    v = [x, y, z, w]
    n = math.sqrt(sum(c * c for c in v))
    return [c / n for c in v] if n > 0 else [0.0, 0.0, 0.0, 1.0]


def _jacobi(a):
    """Autovalores/autovectores de una matriz SIMETRICA por rotaciones de Jacobi.

    Sustituye a numpy.linalg.eigh para el ajuste rigido. Devuelve (valores, vectores) con los
    autovectores en COLUMNA (vectores[i] = autovector i).
    """
    n = len(a)
    m = [row[:] for row in a]
    v = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    for _ in range(100):
        p, q = 0, 1
        mayor = 0.0
        for i in range(n):
            for j in range(i + 1, n):
                if abs(m[i][j]) > mayor:
                    mayor = abs(m[i][j])
                    p, q = i, j
        if mayor < 1e-14:
            break
        theta = (m[q][q] - m[p][p]) / (2.0 * m[p][q])
        t = (1.0 if theta >= 0 else -1.0) / (abs(theta) + math.sqrt(theta * theta + 1.0))
        c = 1.0 / math.sqrt(t * t + 1.0)
        s = t * c
        for k in range(n):
            mkp, mkq = m[k][p], m[k][q]
            m[k][p] = c * mkp - s * mkq
            m[k][q] = s * mkp + c * mkq
        for k in range(n):
            mpk, mqk = m[p][k], m[q][k]
            m[p][k] = c * mpk - s * mqk
            m[q][k] = s * mpk + c * mqk
        for k in range(n):
            vkp, vkq = v[k][p], v[k][q]
            v[k][p] = c * vkp - s * vkq
            v[k][q] = s * vkp + c * vkq
    valores = [m[i][i] for i in range(n)]
    vectores = [[v[i][j] for i in range(n)] for j in range(n)]
    return valores, vectores


def ajuste_rigido(P, B):
    """Rotacion + traslacion que mejor lleva los puntos P sobre los B (Kabsch).

    Se resuelve por el metodo del cuaternion (matriz K de 4x4 y su autovector mayor), que es estable
    y da siempre una rotacion propia (determinante +1), sin los casos degenerados del SVD.
    """
    n = len(P)
    pc = [sum(p[k] for p in P) / n for k in range(3)]
    bc = [sum(b[k] for b in B) / n for k in range(3)]
    s = [[0.0] * 3 for _ in range(3)]
    for p, b in zip(P, B):
        for i in range(3):
            for j in range(3):
                s[i][j] += (p[i] - pc[i]) * (b[j] - bc[j])
    sxx, sxy, sxz = s[0]
    syx, syy, syz = s[1]
    szx, szy, szz = s[2]
    K = [
        [sxx + syy + szz, syz - szy, szx - sxz, sxy - syx],
        [syz - szy, sxx - syy - szz, sxy + syx, szx + sxz],
        [szx - sxz, sxy + syx, -sxx + syy - szz, syz + szy],
        [sxy - syx, szx + sxz, syz + szy, -sxx - syy + szz],
    ]
    valores, vectores = _jacobi(K)
    q = vectores[valores.index(max(valores))]
    R = quat_mat(q)
    t = [bc[k] - sum(R[k][j] * pc[j] for j in range(3)) for k in range(3)]
    return R, t


# --------------------------------------------------------------------------- lectura del volcado


def cargar(dump: Path, parte: str, ext: str, tipo, forma=None):
    """Lee un binario del volcado. `tipo` es un code de struct ('f' o 'H'/'I')."""
    datos = (Path(dump) / (parte + "." + ext)).read_bytes()
    n = struct.calcsize("<" + tipo)
    valores = list(struct.unpack("<%d%s" % (len(datos) // n, tipo), datos[: (len(datos) // n) * n]))
    if forma:
        return [valores[i:i + forma] for i in range(0, len(valores), forma)]
    return valores


def cargar_archivo(dump: Path, nombre: str, tipo: str, forma=None):
    """Lee un binario del volcado por su nombre de fichero completo (los morphs ya lo traen)."""
    datos = (Path(dump) / nombre).read_bytes()
    n = struct.calcsize("<" + tipo)
    valores = list(struct.unpack("<%d%s" % (len(datos) // n, tipo), datos[: (len(datos) // n) * n]))
    if forma:
        return [valores[i:i + forma] for i in range(0, len(valores), forma)]
    return valores


def uv_gltf(dump: Path, parte: str):
    """Unity guarda la V de abajo arriba; glTF/OBJ/Blender la usan de arriba abajo."""
    uv = cargar(dump, parte, "uv0.bin", "f", 2)
    return [[u, 1.0 - v] for u, v in uv]


class Esqueleto:
    """Esqueleto del modelo, con los mundos de bind como referencia."""

    def __init__(self, dump: Path):
        datos = json.loads((Path(dump) / "esqueleto.json").read_text(encoding="utf-8"))
        huesos = datos["huesos"]
        self.padre = {h["nombre"]: h.get("padre") for h in huesos}
        self.trs = {h["nombre"]: (h["pos"], h["rot"], h["esc"]) for h in huesos}
        self.orden = []
        vistos = set()
        for h in huesos:
            nom = h["nombre"]
            if nom in vistos:
                # el prefab trae objetos repetidos (restricciones, colisionadores); con el nombre
                # duplicado el nodo se colgaba dos veces del mismo padre y Blender rechazaba el GLB
                continue
            vistos.add(nom)
            self.orden.append(nom)
        self.mundo: dict[str, list] = {}
        self.metodo: dict[str, str] = {}
        self.matrices: dict[str, list] = {}
        self.R = identidad()
        self.t = [0.0, 0.0, 0.0]

    def aprender(self, dump: Path, parte: str, referencia=False):
        """Guarda los mundos de bind de una pieza.

        OJO: las inversas de bind llevan dentro la matriz del OBJETO MALLA, que es distinta en cada
        pieza. Por eso la primera pieza que se aprende (el cuerpo) fija el ESPACIO DE REFERENCIA y
        las demas se normalizan a ese espacio con matriz_pieza().
        """
        if not referencia and self.mundo:
            M = self.matriz_pieza(dump, parte)
        else:
            M = identidad()
        self.matrices[parte] = M
        meta = json.loads((Path(dump) / (parte + ".json")).read_text(encoding="utf-8"))
        ibm = cargar(dump, parte, "ibm.bin", "f", 16)
        Minv = inv(M)
        for k, h in enumerate(meta["lista_huesos"]):
            nom = h.get("nombre")
            if not nom or k >= len(ibm):
                continue
            m4 = [ibm[k][r * 4:r * 4 + 4] for r in range(4)]
            w = inv(m4)
            if w is None or any(not math.isfinite(x) for row in w for x in row):
                continue
            w_ref = mul(w, Minv) if Minv else w
            if nom not in self.mundo:
                self.mundo[nom] = w_ref
                self.metodo[nom] = "bind"

    def matriz_pieza(self, dump: Path, parte: str, hueso_probe="Bip01 Pelvis"):
        """Matriz que lleva del espacio de bind de la pieza al de referencia: W_pieza = W_ref * M."""
        meta = json.loads((Path(dump) / (parte + ".json")).read_text(encoding="utf-8"))
        ibm = cargar(dump, parte, "ibm.bin", "f", 16)
        nombres = [h.get("nombre") for h in meta["lista_huesos"]]
        candidatos = [hueso_probe, "Bip01 Spine", "Bip01 Head", "Bip01 L Thigh",
                      "gun_Bone01", "wq_Bone01", "qiangtao_Bone11", "xiuzhang_Bone005"]
        for cand in candidatos:
            if cand in nombres and cand in self.mundo:
                k = nombres.index(cand)
                if k < len(ibm):
                    m4 = [ibm[k][r * 4:r * 4 + 4] for r in range(4)]
                    w = inv(m4)
                    if w:
                        return mul(inv(self.mundo[cand]), w)
        for k, nom in enumerate(nombres):
            if nom in self.mundo and k < len(ibm):
                m4 = [ibm[k][r * 4:r * 4 + 4] for r in range(4)]
                w = inv(m4)
                if w:
                    return mul(inv(self.mundo[nom]), w)
        return identidad()

    def completar(self, log=print):
        """Coloca los huesos que no tienen inversa de bind, ajustando el prefab al espacio de bind."""
        conocidos = [n for n in self.mundo if n in self.trs]
        if not conocidos:
            raise RuntimeError(t("gr_err_sin_hueso"))
        P = [self.trs[n][0] for n in conocidos]
        B = [[self.mundo[n][i][3] for i in range(3)] for n in conocidos]
        R, desp = ajuste_rigido(P, B)
        resid = []
        for p, b in zip(P, B):
            q = [sum(R[i][j] * p[j] for j in range(3)) + desp[i] for i in range(3)]
            resid.append(max(abs(q[i] - b[i]) for i in range(3)))
        resid.sort()
        log(t("gr_ajuste", resid[len(resid) // 2], resid[-1]))
        self.R, self.t = R, desp
        for nom in self.orden:
            if nom in self.mundo:
                continue
            pa = self.padre.get(nom)
            if pa is None:
                continue
            pos, rot, esc = self.trs[nom]
            m = quat_mat(rot)
            r = mul(mul(R, m), transpuesta(R))
            self.mundo[nom] = [[r[i][j] for j in range(3)] + [0.0] for i in range(3)] + \
                              [[sum(R[i][j] * pos[j] for j in range(3)) + desp[i] for i in range(3)] + [1.0]]
            self.metodo[nom] = "prefab"

    def locales(self):
        """Arbol con los huesos REALES (los que tienen mundo).

        Los huesos intermedios del prefab que no tengan mundo no se inventan: cada hueso se cuelga
        de su antecesor real mas cercano que si exista.
        """
        idx = {nom: i for i, nom in enumerate(n for n in self.orden if n in self.mundo)}
        self.padre_real = {}
        for nom in idx:
            pa = self.padre.get(nom)
            while pa is not None and pa not in idx:
                pa = self.padre.get(pa)
            self.padre_real[nom] = pa
        locales = {}
        for nom in idx:
            w = self.mundo[nom]
            pa = self.padre_real[nom]
            locales[nom] = mul(inv(self.mundo[pa]), w) if pa in idx else w
        return idx, locales


# --------------------------------------------------------------------------- contenedor glTF

COMP = {5126: "<f4", 5123: "<u2", 5125: "<u4", 5121: "<u1"}
NCOMP = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


class Gltf:
    def __init__(self, generador="p5x_studio/glb_rig"):
        self.bin = bytearray()
        self.j = {"asset": {"version": "2.0", "generator": generador},
                  "scene": 0, "scenes": [{"nodes": []}], "nodes": [], "accessors": [],
                  "bufferViews": [], "buffers": [{"byteLength": 0}], "materials": [],
                  "images": [], "textures": [], "samplers": [{"magFilter": 9729, "minFilter": 9987}],
                  "meshes": [], "skins": []}

    def acc(self, valores, fmt="<f4", tipo="SCALAR", minmax=True):
        """Anade un accessor. `valores` es una lista plana o de listas."""
        plano = []
        n = 1
        for v in valores:
            if isinstance(v, (list, tuple)):
                n = len(v)
                plano.extend(v)
            else:
                plano.append(v)
        tipo = tipo or {1: "SCALAR", 2: "VEC2", 3: "VEC3", 4: "VEC4", 16: "MAT4"}[n]
        while len(self.bin) % 4:
            self.bin += b"\0"
        off = len(self.bin)
        codigo = {"<f4": "f", "<u2": "H", "<u4": "I", "<u1": "B"}[fmt]
        self.bin += struct.pack("<%d%s" % (len(plano), codigo), *plano)
        comp = {"<f4": 5126, "<u2": 5123, "<u4": 5125, "<u1": 5121}[fmt]
        a = {"componentType": comp, "count": len(valores), "type": tipo,
             "bufferView": len(self.j["bufferViews"])}
        if minmax:
            cols = [plano[i::n] for i in range(n)]
            a["min"] = [min(c) for c in cols]
            a["max"] = [max(c) for c in cols]
        self.j["accessors"].append(a)
        self.j["bufferViews"].append({"buffer": 0, "byteOffset": off,
                                      "byteLength": len(plano) * struct.calcsize("<" + codigo)})
        return len(self.j["accessors"]) - 1

    def acc_mat4(self, matrices):
        """Accessor MAT4. OJO: glTF guarda las matrices en orden COLUMNA-mayor, y las nuestras vienen
        en fila-mayor: hay que trasponerlas al aplanarlas. Si no, cualquier lector que siga la spec
        (Blender, Unity, tres.js) lee la traspuesta y el esqueleto de reposo sale del reves: la malla
        se abre en picos porque cada vertice acaba atado a un hueso que no le toca."""
        plano = [m[i][j] for m in matrices for j in range(4) for i in range(4)]
        while len(self.bin) % 4:
            self.bin += b"\0"
        off = len(self.bin)
        self.bin += struct.pack("<%df" % len(plano), *plano)
        a = {"componentType": 5126, "count": len(matrices), "type": "MAT4",
             "bufferView": len(self.j["bufferViews"])}
        self.j["accessors"].append(a)
        self.j["bufferViews"].append({"buffer": 0, "byteOffset": off,
                                      "byteLength": len(plano) * 4})
        return len(self.j["accessors"]) - 1

    def empaquetar(self) -> bytes:
        self.j["buffers"][0]["byteLength"] = len(self.bin)
        js = json.dumps(self.j, separators=(",", ":")).encode()
        while len(js) % 4:
            js += b" "
        total = 12 + 8 + len(js) + 8 + len(self.bin)
        return (b"glTF" + struct.pack("<II", 2, total) + struct.pack("<I", len(js)) + b"JSON" + js
                + struct.pack("<I", len(self.bin)) + b"BIN\0" + bytes(self.bin))


# --------------------------------------------------------------------------- conversion de ejes

# Conversion de ejes del dato del juego (Z arriba) al glTF (Y arriba): (x, y, z) -> (x, z, y).
# OJO, ESTO ES UN ESPEJO (determinante -1), y tiene que serlo: el espacio del juego es ZURDO y el de
# glTF DIESTRO, asi que un simple giro (determinante +1) devuelve el modelo ESPEJADO. Al ser espejo,
# el orden de los triangulos HAY QUE VOLTEARLO o las caras quedan del reves respecto a las normales
# y el modelo se ve "con las texturas por dentro".
T = [[1.0, 0, 0, 0], [0, 0, 1.0, 0], [0, 1.0, 0, 0], [0, 0, 0, 1.0]]
TINV = inv(T)


def hornear(m):
    """Pasa una matriz del espacio de Unity al de glTF (espejo + ejes) horneandola."""
    return mul(mul(T, m), TINV)


def eje(v):
    """Aplica la conversion de ejes a un vector de 3."""
    return [v[0], v[2], v[1]]


def _det3(M):
    return (M[0][0] * (M[1][1] * M[2][2] - M[1][2] * M[2][1])
            - M[0][1] * (M[1][0] * M[2][2] - M[1][2] * M[2][0])
            + M[0][2] * (M[1][0] * M[2][1] - M[1][1] * M[2][0]))


def descomponer(L):
    """(posicion, rotacion, escala) de una matriz 4x4, ADMITIENDO escala negativa.

    Hace falta porque glTF (y Blender) escriben un nodo como TRS y una matriz ESPEJO (determinante
    negativo) no se puede escribir con una rotacion y escalas positivas: si se hace, el nodo acaba en
    otro sitio y los vertices que cuelgan de el salen disparados. Aqui se le pone el signo negativo a
    la columna mas larga y la rotacion resultante ya es propia.
    """
    cols = [math.sqrt(sum(L[i][j] ** 2 for i in range(3))) for j in range(3)]
    esc = list(cols)
    if _det3(L) < 0:
        k = max(range(3), key=lambda j: cols[j])
        esc[k] = -cols[k]
    norm = [[L[i][j] / (esc[j] + 1e-20) for j in range(3)] for i in range(3)]
    return [L[i][3] for i in range(3)], mat_quat(norm), esc


def trs_exacto(L, tol=1e-4):
    """¿La matriz se puede escribir como traslacion+rotacion+escala sin perder nada (sin cizalla)?"""
    pos, rot, esc = descomponer(L)
    R = quat_mat(rot)
    for i in range(3):
        for j in range(3):
            if abs(R[i][j] * esc[j] - L[i][j]) > tol:
                return False
        if abs(pos[i] - L[i][3]) > tol:
            return False
    return True


# --------------------------------------------------------------------------- piezas


def _clave_pieza(nombre: str) -> str:
    """Clave para desduplicar la cara con y sin expresiones: la version `_bs` sustituye a la llana."""
    return nombre.replace("_wholeexport_rig_bs_", "_wholeexport_rig_")


def _segmento_rig(nombre: str) -> str:
    """El trozo del nombre hasta `wholeexport_rig` (incluido el `_bs` si lo lleva): identifica el rig."""
    i = nombre.lower().find("_wholeexport_rig")
    return nombre[: i + len("_wholeexport_rig")] if i >= 0 else nombre


def listar_partes(dump: Path) -> list[str]:
    """Partes del volcado, ya desduplicadas (se queda la version con mas expresiones)."""
    dump = Path(dump)
    candidatas = []
    for p in sorted(dump.glob("*.json")):
        if p.stem in ("resumen", "esqueleto", "log"):
            continue
        if not (dump / (p.stem + ".pos.bin")).is_file():
            continue
        meta = json.loads(p.read_text(encoding="utf-8"))
        candidatas.append((p.stem, meta.get("expresiones", 0), meta.get("vertices", 0)))
    mejores: dict[str, tuple] = {}
    for nombre, expr, verts in candidatas:
        k = _clave_pieza(nombre)
        if k not in mejores or expr > mejores[k][1]:
            mejores[k] = (nombre, expr, verts)
    partes = [v[0] for v in mejores.values()]
    # el cuerpo primero: fija el espacio de referencia del esqueleto
    def prioridad(n):
        b = n.lower()
        return (0 if b.endswith("_body") else 1, n)
    partes.sort(key=prioridad)
    return partes


def ruta_textura(nombre: str, raices) -> Path | None:
    for base in raices:
        base = Path(base)
        if not base.is_dir():
            continue
        directo = base / nombre
        if directo.is_file():
            return directo
        for raiz, _, ficheros in os.walk(base):
            if nombre in ficheros:
                return Path(raiz) / nombre
    return None


# sufijos con los que el juego nombra el color base y la normal de una pieza
SUFIJOS_COLOR = ("_bc", "_bcm", "_basecolor", "_maintex")
SUFIJOS_NORMAL = ("_nm", "_nmas", "_normal", "_bump")


def indice_pngs(raices) -> dict:
    """Mapa `nombre en minusculas -> ruta` de todos los PNG bajo las raices (una sola pasada).

    Respaldo para los materiales que no resuelven sus texturas desde el bundle (las suyas viven en
    un bundle de dependencia `cab-...` que no se abre): se buscan los PNG ya extraidos por el
    nombre del material. Se indexa una vez, no por submalla, que si no el GLB tarda minutos.
    """
    out = {}
    for base in raices:
        base = Path(base)
        if not base.is_dir():
            continue
        for raiz, _, ficheros in os.walk(base):
            for f in ficheros:
                if f.lower().endswith(".png"):
                    out.setdefault(f.lower(), Path(raiz) / f)
    return out


def _pngs_de_token(pngs: dict, token: str, sufijos) -> list:
    """PNG cuyo nombre empieza por `token` y acaba en alguno de esos sufijos, sin `lodlow` primero.

    OJO: los ficheros acaban en `_bc.png`, no en `_bc`, asi que se compara el nombre SIN la
    extension (comparar el nombre entero con `_bc` no encontraba nada y el cuerpo se quedaba sin
    textura).
    """
    t = (token or "").lower()
    if not t:
        return []
    cand = [p for nom, p in pngs.items()
            if nom.startswith(t) and any(nom[:-4].endswith(s) for s in sufijos)]
    cand.sort(key=lambda p: (1 if "lodlow" in p.stem.lower() else 0, len(p.stem), p.stem.lower()))
    return cand


def _tokens_textura(nombre_malla: str) -> list:
    """Posibles prefijos con los que empiezan las TEXTURAS de una malla, de mas a menos fiable.

    El nombre del juego es `<actor>_<traje>_<pieza>_wholeexport_rig_<prefijo_textura>_<pieza>`, y el
    prefijo de textura es lo que hay TRAS `_rig_`. Pero ese trozo no siempre vale: `closer` tiene la
    malla `closer_normal_body_wholeexport_rig_clsoer_normal_body1` (el juego escribe `clsoer` con las
    letras cambiadas y le pega un `1`), y sus PNG son `closer_normal_body_bc.png`. Por eso se prueban
    tambien lo que va ANTES de `_wholeexport` (que si es `closer_normal_body`) y el token del rig sin
    el numero de variante final. Con esto el cuerpo y la cara dejan de salir sin pintar en el GLB.
    """
    n = (nombre_malla or "").lower()
    out = []
    j = n.find("_rig_")
    if j >= 0:
        toks = [x for x in n[j + 5:].strip("_").split("_") if x]
        while toks and toks[0] in ("bs", "ps", "b"):
            toks = toks[1:]
        if toks:
            out.append("_".join(toks))
            if toks[-1][-1:].isdigit():
                sin_num = toks[-1].rstrip("0123456789")
                if sin_num:
                    out.append("_".join(toks[:-1] + [sin_num]))
    i = n.find("_wholeexport")
    if i > 0:
        out.append(n[:i])
    vistos, limpio = set(), []
    for t in out:
        if t and t not in vistos:
            vistos.add(t)
            limpio.append(t)
    return limpio


def construir(dump, salida, nombre: str, partes=None, texturas=(), log=None) -> dict:
    """Ensambla el GLB riggeado. Devuelve las cuentas medidas del resultado."""
    dump = Path(dump)
    log = log or (lambda s: None)
    if not (dump / "esqueleto.json").is_file():
        raise RuntimeError(t("gr_err_sin_esqueleto_json"))
    partes = partes or listar_partes(dump)
    if not partes:
        raise RuntimeError(t("gr_err_sin_malla"))
    raices_textura = [Path(t) for t in texturas]
    pngs = indice_pngs(raices_textura)

    esq = Esqueleto(dump)
    for k, parte in enumerate(partes):
        esq.aprender(dump, parte, referencia=(k == 0))
    log(t("gr_huesos_mundo", len(esq.mundo)))
    esq.completar(log)

    # --- huesos "raros": algunas matrices de bind traen ESPEJO (determinante negativo, tipico en la
    # cara: el lado derecho es copia espejada del izquierdo) o ESCALA no uniforme. Un hueso de Blender
    # no puede representar ni lo uno ni lo otro (solo rotacion + su longitud), asi que al importar el
    # GLB Blender aproxima el hueso y los vertices que cuelgan de el salen disparados: ese es el
    # "estallido radial". Se dejan los mundos como ROTACION PURA (se ortonormalizan las columnas y se
    # le cambia el signo a la mas larga si hay espejo). En reposo no cambia NADA: la piel sigue siendo
    # mundo * inversa de bind = identidad, o sea que la malla se ve exactamente igual; solo se pierde
    # la escala/espejo al POSAR ese hueso concreto.
    espejos = 0
    for nom, w in list(esq.mundo.items()):
        cols = [math.sqrt(sum(w[i][j] ** 2 for i in range(3))) for j in range(3)]
        for j in range(3):
            for i in range(3):
                w[i][j] /= (cols[j] + 1e-20)
        if _det3(w) < 0:
            k = max(range(3), key=lambda j: cols[j])
            for i in range(3):
                w[i][k] = -w[i][k]
            espejos += 1
    log(t("gr_huesos_espejo", espejos))

    idx, locales = esq.locales()
    orden = [n for n in esq.orden if n in idx]
    log(t("gr_nodos", len(orden)))

    # --- reparacion de la jerarquia: si un hueso cuelga de un padre con escala NO uniforme, su
    # matriz local lleva cizalla y no se puede escribir como traslacion+rotacion+escala. glTF no
    # tiene cizalla, asi que ese hueso se cuelga de la raiz con su matriz de mundo entera: la piel
    # sigue siendo exacta (mundo * inversa de bind = identidad) aunque pierda ese enlace de padre.
    def _recalcular():
        return {nom: (mul(inv(esq.mundo[esq.padre_real[nom]]), esq.mundo[nom])
                      if esq.padre_real.get(nom) in idx else esq.mundo[nom]) for nom in idx}

    sueltos = []
    for _ in range(3):
        malos = [nom for nom in orden if not trs_exacto(hornear(locales[nom]))]
        if not malos:
            break
        for nom in malos:
            esq.padre_real[nom] = None
        sueltos += malos
        locales = _recalcular()
    if sueltos:
        log(t("gr_huesos_cizalla", len(set(sueltos))))

    g = Gltf()
    base = len(g.j["nodes"])
    for nom in orden:
        L = hornear(locales[nom])
        pos, rot, cols = descomponer(L)
        g.j["nodes"].append({"name": nom,
                             "translation": [round(x, 7) for x in pos],
                             "rotation": [round(x, 7) for x in rot],
                             "scale": [round(x, 7) for x in cols]})
    for nom in orden:
        pa = esq.padre_real.get(nom)
        if pa in idx:
            g.j["nodes"][base + idx[pa]].setdefault("children", []).append(base + idx[nom])
    raices = [base + i for nom, i in idx.items() if esq.padre_real.get(nom) not in idx]
    # OJO: la raiz NO lleva rotacion. El nodo de la malla tambien cuelga de aqui y glTF IGNORA la
    # transformada del nodo de una malla con piel, asi que una rotacion aqui se le aplica al esqueleto
    # pero no a los vertices: la malla entera sale girada respecto a sus huesos.
    g.j["nodes"].append({"name": nombre + "_raiz", "children": raices})
    raiz = len(g.j["nodes"]) - 1

    mib = [hornear(inv(esq.mundo[n])) for n in orden]
    acc_ibm = g.acc_mat4(mib)
    # UNA sola piel para todas las piezas (todas comparten el mismo esqueleto). Con una piel por malla
    # Blender monta una armadura por cada una y la deformacion en reposo sale mal.
    piel = len(g.j["skins"])
    # OJO: sin la clave `skeleton`. Blender la usa para elegir la raiz de la armadura y, si apunta a
    # un nodo que no es antecesor de TODOS los huesos, monta mal el esqueleto y la malla en reposo
    # sale deformada. El GLB de referencia de Kotone tampoco la lleva.
    g.j["skins"].append({"joints": list(range(base, base + len(orden))),
                         "inverseBindMatrices": acc_ibm})

    # --- materiales (nombre -> definicion), leyendo las texturas del volcado
    mats_por_nombre = {}
    principal_de_pieza = {}
    for parte in partes:
        meta = json.loads((dump / (parte + ".json")).read_text(encoding="utf-8"))
        for m in meta.get("materiales", []):
            mats_por_nombre[m.get("nombre") or "material"] = m
        if meta.get("materiales"):
            principal_de_pieza[parte] = meta["materiales"][0].get("nombre")

    cache_img: dict[str, int] = {}

    def _imagen(p: Path, nombre: str) -> int:
        """Incrusta un PNG y devuelve el indice de textura. Repite el mismo PNG una sola vez."""
        if nombre in cache_img:
            return cache_img[nombre]
        datos = p.read_bytes()
        bv = len(g.j["bufferViews"])
        off = len(g.bin)
        g.bin += datos
        g.j["bufferViews"].append({"buffer": 0, "byteOffset": off, "byteLength": len(datos)})
        g.j["images"].append({"bufferView": bv, "mimeType": "image/png", "name": nombre})
        g.j["textures"].append({"source": len(g.j["images"]) - 1, "sampler": 0})
        cache_img[nombre] = len(g.j["textures"]) - 1
        return cache_img[nombre]

    def material(nom_mat, tokens=None):
        """Indice del material `nom_mat`, creandolo si hace falta.

        `tokens` son los prefijos con los que pueden empezar sus TEXTURAS sacados del nombre de la
        MALLA (`_tokens_textura`): se usan cuando el nombre del material no encuentra ningun PNG, que
        es lo que pasa con las erratas del juego (`clsoer_normal_body1`).
        """
        if not nom_mat and not tokens:
            return None
        if not nom_mat:
            nom_mat = "mat_" + tokens[0]
        for i, mm in enumerate(g.j["materials"]):
            if mm.get("name") == nom_mat:
                return i
        src = mats_por_nombre.get(nom_mat)
        mat = {"name": nom_mat,
               "pbrMetallicRoughness": {"baseColorFactor": [1, 1, 1, 1], "metallicFactor": 0.0,
                                        "roughnessFactor": 0.8}}
        if src:
            for tx in src.get("texturas", []):
                slot, tex = tx.get("slot", ""), tx.get("textura")
                if not tex:
                    continue
                p = ruta_textura(tex, raices_textura)
                if not p:
                    continue
                ti = _imagen(p, tex)
                if slot in ("_MainTex", "_BaseMap", "_BaseColorMap"):
                    mat["pbrMetallicRoughness"]["baseColorTexture"] = {"index": ti}
                elif slot == "_BumpMap":
                    mat["normalTexture"] = {"index": ti}
        # Respaldo: si el material no trajo color base, sus texturas viven en un bundle de
        # dependencia que aqui no se abre. Se buscan entre los PNG ya extraidos por el nombre del
        # material (`PC077_01_body` -> `PC077_01_body_bc.png`), que es lo que hace el MTL del OBJ.
        # Si el nombre del material no da nada (o no habia material), se prueban los tokens sacados
        # del NOMBRE DE LA MALLA: es lo que salva a los personajes con erratas en el token del rig.
        pbr = mat["pbrMetallicRoughness"]
        for tok in [nom_mat] + list(tokens or []):
            if "baseColorTexture" in pbr:
                break
            col = _pngs_de_token(pngs, tok, SUFIJOS_COLOR)
            if col:
                pbr["baseColorTexture"] = {"index": _imagen(col[0], col[0].name)}
        for tok in [nom_mat] + list(tokens or []):
            if "normalTexture" in mat:
                break
            nor = _pngs_de_token(pngs, tok, SUFIJOS_NORMAL)
            if nor:
                mat["normalTexture"] = {"index": _imagen(nor[0], nor[0].name)}
        g.j["materials"].append(mat)
        return len(g.j["materials"]) - 1

    # --- mallas
    nodos_malla = []
    mallas_con_pesos = 0
    for parte in partes:
        meta = json.loads((dump / (parte + ".json")).read_text(encoding="utf-8"))
        pos = cargar(dump, parte, "pos.bin", "f", 3)
        nrm = cargar(dump, parte, "nrm.bin", "f", 3)
        uv0 = uv_gltf(dump, parte)
        Mp = esq.matrices[parte]
        pos = [[sum(Mp[i][j] * v[j] for j in range(3)) + Mp[i][3] for i in range(3)] for v in pos]
        Minv3 = inv(Mp)[:3] if inv(Mp) else identidad()[:3]
        nrm = [[sum(Minv3[j][i] * v[j] for j in range(3)) for i in range(3)] for v in nrm]
        bidx = cargar(dump, parte, "bidx.bin", "H", 4)
        bwgt = cargar(dump, parte, "bwgt.bin", "f", 4)
        if any(sum(w) > 1e-6 for w in bwgt):
            mallas_con_pesos += 1
        pos = [eje(v) for v in pos]
        nrm = [eje(v) for v in nrm]

        nombres = [h.get("nombre") for h in meta["lista_huesos"]]
        remap = [idx.get(nom, 0) for nom in nombres]
        faltan = sum(1 for nom in nombres if nom not in idx)
        if faltan:
            log(t("gr_aviso_huesos", parte[-20:], faltan))
        jidx = [[remap[b] for b in fila] for fila in bidx]

        atrib = {"POSITION": g.acc(pos, "<f4", "VEC3"),
                 "NORMAL": g.acc(nrm, "<f4", "VEC3"),
                 "TEXCOORD_0": g.acc(uv0, "<f4", "VEC2"),
                 "JOINTS_0": g.acc(jidx, "<u2", "VEC4"),
                 "WEIGHTS_0": g.acc(bwgt, "<f4", "VEC4")}

        prims = []
        for i in range(meta["submallas"]):
            tri = cargar(dump, parte, "tris%d.bin" % i, "I")
            tri = [tri[k:k + 3] for k in range(0, len(tri), 3)]
            tri = [[t[0], t[2], t[1]] for t in tri]   # bobinado volteado (T es un espejo)
            pr = {"attributes": dict(atrib), "indices": g.acc([x for t in tri for x in t], "<u4")}
            nom_mat = None
            if i < len(meta.get("materiales", [])):
                nom_mat = meta["materiales"][i].get("nombre")
            if not nom_mat or nom_mat == "Standard":
                # herencia: otra pieza del MISMO rig (el parpado no trae material propio)
                seg = _segmento_rig(meta["malla"])
                for otra in partes:
                    if otra == parte:
                        continue
                    meta2 = json.loads((dump / (otra + ".json")).read_text(encoding="utf-8"))
                    if _segmento_rig(meta2["malla"]) == seg and meta2.get("materiales"):
                        nom_mat = meta2["materiales"][0].get("nombre")
                        if nom_mat:
                            log(t("gr_material_heredado", parte[-20:], nom_mat))
                            break
            mi = material(nom_mat, _tokens_textura(meta["malla"]))
            if mi is not None:
                pr["material"] = mi
            objetivos = []
            for exp in meta.get("lista_expresiones", []):
                for fr in exp["frames"]:
                    dv = cargar_archivo(dump, fr["bin"], "f", 3)
                    objetivos.append(g.acc([eje(v) for v in dv], "<f4", "VEC3"))
            if objetivos:
                pr["targets"] = [{"POSITION": a} for a in objetivos]
            prims.append(pr)

        malla = {"name": meta["parte"], "primitives": prims}
        if any(p.get("targets") for p in prims):
            nombres_exp = _nombres_expresiones(meta)
            malla["extras"] = {"targetNames": nombres_exp}
            malla["weights"] = [0.0] * len(nombres_exp)
        g.j["meshes"].append(malla)
        g.j["nodes"].append({"name": meta["parte"] + "_MALLA", "mesh": len(g.j["meshes"]) - 1,
                             "skin": piel})
        nodos_malla.append(len(g.j["nodes"]) - 1)
        log(t("gr_parte", parte[-22:], len(pos), len(nombres), meta["submallas"],
              len(meta.get("lista_expresiones", []))))

    # herencia de material por indice (si a una pieza se le perdio, hereda el de la donante)
    malla_por_pieza = {m.get("name"): m for m in g.j["meshes"]}
    for parte in partes:
        meta = json.loads((dump / (parte + ".json")).read_text(encoding="utf-8"))
        malla = malla_por_pieza.get(meta["parte"])
        if not malla:
            continue
        seg = _segmento_rig(meta["malla"])
        don = next((m for m in g.j["meshes"]
                    if m is not malla and m.get("name") and _segmento_rig(m["name"]) == seg), None)
        if not don or not don["primitives"]:
            continue
        idx_don = don["primitives"][0].get("material")
        for pr in malla["primitives"]:
            mat = pr.get("material")
            pbr = g.j["materials"][mat].get("pbrMetallicRoughness", {}) if mat is not None else {}
            if "baseColorTexture" not in pbr and idx_don is not None:
                pr["material"] = idx_don

    # herencia por PARTE (cuerpo/cara/pelo/ojos/armas): si a una variante no se le pudo casar la
    # textura por nombre, usa el atlas que SI tiene otra malla de la misma parte. Es la misma regla
    # que sigue la ruta de OBJ/MTL (`principal_por_parte`), y evita que un cuerpo se quede sin textura
    # solo porque su nombre de malla no coincide con el de su atlas (tipico en los NPC de multitud).
    def _parte_de(nombre: str) -> str:
        n = (nombre or "").lower()
        for clave, parte in (("face", "face"), ("hair", "hair"), ("eye", "eyes"),
                             ("weapon", "weapons"), ("gun", "weapons"), ("qiang", "weapons")):
            if clave in n:
                return parte
        return "body"

    don_por_parte = {}
    for m in g.j["meshes"]:
        if not m.get("primitives"):
            continue
        mat = m["primitives"][0].get("material")
        if mat is None:
            continue
        if "baseColorTexture" in g.j["materials"][mat].get("pbrMetallicRoughness", {}):
            don_por_parte.setdefault(_parte_de(m.get("name")), mat)
    for m in g.j["meshes"]:
        don = don_por_parte.get(_parte_de(m.get("name")))
        if don is None:
            continue
        for pr in m["primitives"]:
            mat = pr.get("material")
            pbr = g.j["materials"][mat].get("pbrMetallicRoughness", {}) if mat is not None else {}
            if "baseColorTexture" not in pbr:
                pr["material"] = don

    for nm in nodos_malla:
        g.j["nodes"][raiz].setdefault("children", []).append(nm)
    g.j["scenes"][0]["nodes"] = [raiz]

    datos = g.empaquetar()
    salida = Path(salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_bytes(datos)

    stats = {"ruta": str(salida), "mb": round(len(datos) / 1e6, 2),
             "huesos": len(orden), "mallas": len(g.j["meshes"]),
             "mallas_con_pesos": mallas_con_pesos, "armaduras": len(g.j["skins"]),
             "materiales": len(g.j["materials"]), "texturas": len(g.j["textures"]),
             "expresiones": sum(len(m.get("extras", {}).get("targetNames", []))
                                for m in g.j["meshes"])}
    log(t("gr_glb_escrito", salida, stats["mb"], stats["huesos"], stats["mallas"],
          stats["mallas_con_pesos"], stats["armaduras"]))
    return stats


def _nombres_expresiones(meta):
    v = []
    for exp in meta.get("lista_expresiones", []):
        for _ in exp["frames"]:
            v.append(exp["nombre"])
    return v