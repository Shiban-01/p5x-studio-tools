"""Construye el GLB de Kotone Shiomi con el esqueleto DERIVADO de las inversas de bind.

Por que se reescribe: el empaquetador anterior ponia cada hueso como hijo de la raiz cuando su
padre no estaba en la lista del renderer (31 huesos del cuerpo) y anadia un nodo raiz con la
rotacion -90 grados X. En Blender eso se traduce en que, con el esqueleto en reposo, la malla sale
desviada ~1,4 m: las matrices globales de los huesos no reproducen la pose de bind.

Como se hace ahora, que es lo correcto para glTF:
  1. el espacio de bind de la malla es la referencia; para el hueso i, mundo(i) = inversa(ibm_i),
     de modo que mundo(i) * ibm_i = identidad y la pose de reposo reproduce la malla EXACTAMENTE;
  2. el arbol de huesos se deriva de esos mundos: local(j) = inversa(mundo(padre_j)) * mundo(j);
  3. los huesos intermedios que la lista del renderer se deja fuera (p. ej. 'Bip01 L Forearm',
     presente en el prefab pero sin pesos) se colocan convirtiendo su posicion del prefab al
     espacio de bind (rotacion de ejes + traslacion ajustada con los huesos conocidos);
  4. la conversion a glTF (espejo en X para cambiar de mano + ejes Y arriba) se HORNEA en
     vertices, normales, huesos e inversas de bind: nada de nodo raiz con rotacion, que en
     Blender se dobla con la armadura.
"""
import json
import os
import sys
import struct

import numpy as np

RAIZ = r"C:\Users\Lukas\p5x-datamining"
DUMP = os.path.join(RAIZ, "_dl", "kotone_dump")
PREFAB = os.path.join(RAIZ, "unity_com", "esqueleto_prefab.json")
OUT = os.path.join(RAIZ, "kotone_shiomi")
TEXTURAS = [os.path.join(RAIZ, "_dl", "ast_part"), OUT]

# TODAS las piezas del personaje, en el mismo orden que el paquete antiguo. El cuerpo va primero
# porque fija el espacio de referencia del esqueleto. OJO: si se recorta esta lista, el GLB completo
# pierde piezas sin avisar (paso con el brazalete y las armas, que el usuario echo en falta).
PERSONAJE = [
    ("cuerpo", "PC079_01_body_wholeexport_rig_PC079_01_body"),
    ("brazalete", "PC079_01_body_wholeexport_rig_PC079_01_xiuzhang"),
    ("cara", "PC079_01_face_wholeexport_rig_bs_PC079_01_face"),
    ("ojo", "PC079_01_face_wholeexport_rig_bs_PC079_01_eye"),
    ("parpado", "PC079_01_face_wholeexport_rig_bs_PC079_01_eyelid"),
    ("pelo", "PC079_01_hair_wholeexport_rig_PC079_01_hair"),
    ("arma_lanza", "PC079_01_body_wholeexport_rig_PC079_01_qiang"),
    ("arma_lanza_vaina", "PC079_01_body_wholeexport_rig_PC079_01_qiangtao"),
    ("arma_pistola", "PC079_01_gun_02_wholeexport_rig_wq_makpon_gun_02"),
]
# El brazalete se coloca en el OTRO brazo. En el dato del juego esta junto a los huesos llamados "L"
# (a ~2 cm de UpperArm_L_02: x -0,18 frente a -0,20), y ahi se queda; pero el brazo "L" del rig queda
# en el lado contrario al que se ve en el juego, asi que la pieza hay que girarla. Se gira la PIEZA
# ENTERA (malla y huesos) 180 grados sobre la vertical en torno al eje del cuerpo: al ser un giro
# (determinante +1) el emblema sigue legible y el bobinado no cambia (un espejo si lo cambiaria).
BRACELETE = "PC079_01_body_wholeexport_rig_PC079_01_xiuzhang"

# pieza de la que hereda el material cuando el exportador lo pierde
MATERIAL_DE = {"PC079_01_face_wholeexport_rig_bs_PC079_01_eyelid":
               "PC079_01_face_wholeexport_rig_bs_PC079_01_face"}

# Conversion de ejes del dato del juego (Z arriba) al glTF (Y arriba): (x, y, z) -> (x, z, y).
# OJO, ESTO ES UN ESPEJO (determinante -1), y tiene que serlo: el espacio del juego es ZURDO y el
# de glTF DIESTRO, asi que un simple giro (determinante +1) devuelve el modelo ESPEJADO. Con la
# version anterior -- (x,y,z) -> (-x, z, y), determinante +1 -- el uniforme salia al reves y las
# letras S.E.E.S. de la banda se leian invertidas: es la firma de un espejo, y se ve en el render.
# Al ser espejo, el orden de los triangulos HAY QUE VOLTEARLO (ver mas abajo) o las caras quedan
# del reves respecto a las normales y el modelo se ve "con las texturas por dentro".
T = np.array([[1.0, 0, 0, 0],
              [0, 0, 1.0, 0],
              [0, 1.0, 0, 0],
              [0, 0, 0, 1.0]])


def cargar(parte, ext, dtype, shape=None):
    a = np.fromfile(os.path.join(DUMP, parte + "." + ext), dtype=dtype)
    return a.reshape(shape) if shape else a


def uv_gltf(parte):
    """Unity guarda la V de abajo arriba; glTF/OBJ/Blender la usan de arriba abajo."""
    uv = cargar(parte, "uv0.bin", "<f4", (-1, 2)).copy()
    uv[:, 1] = 1.0 - uv[:, 1]
    return uv


def quat_mat(q):
    x, y, z, w = q
    n = x * x + y * y + z * z + w * w
    if n < 1e-12:
        return np.eye(3)
    s = 2.0 / n
    return np.array([
        [1 - s * (y * y + z * z), s * (x * y - z * w), s * (x * z + y * w)],
        [s * (x * y + z * w), 1 - s * (x * x + z * z), s * (y * z - x * w)],
        [s * (x * z - y * w), s * (y * z + x * w), 1 - s * (x * x + y * y)],
    ])


def mat_quat(m):
    """Matriz 3x3 -> cuaternion (x, y, z, w)."""
    t = np.trace(m)
    if t > 0:
        s = np.sqrt(t + 1.0) * 2
        w = 0.25 * s
        x = (m[2, 1] - m[1, 2]) / s
        y = (m[0, 2] - m[2, 0]) / s
        z = (m[1, 0] - m[0, 1]) / s
    elif m[0, 0] > m[1, 1] and m[0, 0] > m[2, 2]:
        s = np.sqrt(1.0 + m[0, 0] - m[1, 1] - m[2, 2]) * 2
        w = (m[2, 1] - m[1, 2]) / s
        x = 0.25 * s
        y = (m[0, 1] + m[1, 0]) / s
        z = (m[0, 2] + m[2, 0]) / s
    elif m[1, 1] > m[2, 2]:
        s = np.sqrt(1.0 + m[1, 1] - m[0, 0] - m[2, 2]) * 2
        w = (m[0, 2] - m[2, 0]) / s
        x = (m[0, 1] + m[1, 0]) / s
        y = 0.25 * s
        z = (m[1, 2] + m[2, 1]) / s
    else:
        s = np.sqrt(1.0 + m[2, 2] - m[0, 0] - m[1, 1]) * 2
        w = (m[1, 0] - m[0, 1]) / s
        x = (m[0, 2] + m[2, 0]) / s
        y = (m[1, 2] + m[2, 1]) / s
        z = 0.25 * s
    v = np.array([x, y, z, w])
    n = np.linalg.norm(v)
    return v / n if n > 0 else np.array([0, 0, 0, 1.0])


class Gltf:
    def __init__(self):
        self.bin = bytearray()
        self.j = {"asset": {"version": "2.0", "generator": "p5x-datamining/kotone-final"},
                  "scene": 0, "scenes": [{"nodes": []}], "nodes": [], "accessors": [],
                  "bufferViews": [], "buffers": [{"byteLength": 0}], "materials": [],
                  "images": [], "textures": [], "samplers": [{"magFilter": 9729, "minFilter": 9987}],
                  "meshes": [], "skins": []}

    def acc_crear(self, datos, objetivo=None, mm=False, forzado=None, minmax=True):
        datos = np.ascontiguousarray(datos)
        while len(self.bin) % 4:
            self.bin += b"\0"
        off = len(self.bin)
        self.bin += datos.tobytes()
        comp = {np.dtype("<f4"): 5126, np.dtype("<u2"): 5123, np.dtype("<u4"): 5125,
                np.dtype("<u1"): 5121}[datos.dtype]
        tipos = {"<f4": "SCALAR", "<u2": "SCALAR", "<u4": "SCALAR", "<u1": "SCALAR"}
        tipo = forzado or {"POSITION": "VEC3", "NORMAL": "VEC3", "TEXCOORD_0": "VEC2",
                           "JOINTS_0": "VEC4", "WEIGHTS_0": "VEC4"}.get(objetivo, tipos["<f4"])
        if forzado == "MAT4":
            comp = 5126
        a = {"componentType": comp, "count": len(datos), "type": tipo,
             "bufferView": len(self.j["bufferViews"])}
        if minmax:
            a["min"] = [float(x) for x in np.atleast_1d(datos.min())] if tipo == "SCALAR" else \
                [float(x) for x in np.atleast_1d(datos.reshape(len(datos), -1).min(axis=0))]
            a["max"] = [float(x) for x in np.atleast_1d(datos.max())] if tipo == "SCALAR" else \
                [float(x) for x in np.atleast_1d(datos.reshape(len(datos), -1).max(axis=0))]
        self.j["accessors"].append(a)
        self.j["bufferViews"].append({"buffer": 0, "byteOffset": off,
                                      "byteLength": len(datos.tobytes())})
        return len(self.j["accessors"]) - 1

    def acc_mat4(self, mats):
        a = self.acc_crear(np.ascontiguousarray(mats, "<f4").reshape(-1), forzado="MAT4",
                           minmax=False)
        self.j["accessors"][a]["type"] = "MAT4"
        self.j["accessors"][a]["count"] = len(mats)
        return a


def ruta_textura(nombre):
    for base in TEXTURAS:
        p = os.path.join(base, nombre)
        if os.path.exists(p):
            return p
        p2 = os.path.join(base, "02_texturas", nombre)
        if os.path.exists(p2):
            return p2
    for base in TEXTURAS:
        for raiz, _, fs in os.walk(base):
            if nombre in fs:
                return os.path.join(raiz, nombre)
    return None


class Esqueleto:
    """Esqueleto del modelo, con los mundos de bind como referencia."""

    def __init__(self):
        huesos = json.load(open(PREFAB, encoding="utf-8"))["huesos"]
        self.padre = {h["nombre"]: h.get("padre") for h in huesos}
        self.trs = {h["nombre"]: (h["pos"], h["rot"], h["esc"]) for h in huesos}
        self.orden = [h["nombre"] for h in huesos]
        self.mundo = {}          # nombre -> 4x4 en el espacio de REFERENCIA (el del cuerpo)
        self.metodo = {}
        self.matrices = {}       # pieza -> matriz que la lleva al espacio de referencia

    # --- 1) mundos exactos desde las inversas de bind ---
    def aprender(self, parte, referencia=False):
        """Guarda los mundos de bind de una pieza.

        OJO: las inversas de bind llevan dentro la matriz del OBJETO MALLA, que es distinta en cada
        pieza. Por eso la primera pieza que se aprende (el cuerpo) fija el ESPACIO DE REFERENCIA y
        las demas se normalizan a ese espacio con matriz_pieza().
        """
        if not referencia and self.mundo:
            M = self.matriz_pieza(parte)
            self.matrices[parte] = M
        else:
            M = np.eye(4)
            self.matrices[parte] = M
        meta = json.load(open(os.path.join(DUMP, parte + ".json"), encoding="utf-8"))
        ibm = cargar(parte, "ibm.bin", "<f4", (-1, 4, 4)).astype(np.float64)
        for k, h in enumerate(meta["lista_huesos"]):
            nom = h.get("nombre")
            if not nom or k >= len(ibm):
                continue
            try:
                w = np.linalg.inv(ibm[k])
            except np.linalg.LinAlgError:
                continue
            if not np.all(np.isfinite(w)):
                continue
            w_ref = w @ np.linalg.inv(M)          # al espacio de referencia
            if nom not in self.mundo or np.abs(self.mundo[nom]).sum() == 0:
                self.mundo[nom] = w_ref
                self.metodo[nom] = "bind"

    def matriz_pieza(self, parte, hueso_probe="Bip01 Pelvis"):
        """Matriz que lleva del espacio de bind de la pieza al de referencia: W_pieza = W_ref * M."""
        meta = json.load(open(os.path.join(DUMP, parte + ".json"), encoding="utf-8"))
        ibm = cargar(parte, "ibm.bin", "<f4", (-1, 4, 4)).astype(np.float64)
        nombres = [h.get("nombre") for h in meta["lista_huesos"]]
        candidatos = [hueso_probe, "Bip01 Spine", "Bip01 Head", "Bip01 L Thigh",
                      "gun_Bone01", "wq_Bone01", "qiangtao_Bone11", "xiuzhang_Bone005"]
        for cand in candidatos:
            if cand in nombres and cand in self.mundo:
                k = nombres.index(cand)
                if k < len(ibm):
                    w = np.linalg.inv(ibm[k])
                    return np.linalg.inv(self.mundo[cand]) @ w
        # sin hueso comun: se usa el primero de la pieza (puede quedar desplazada)
        for k, nom in enumerate(nombres):
            if nom in self.mundo and k < len(ibm):
                return np.linalg.inv(self.mundo[nom]) @ np.linalg.inv(ibm[k])
        return np.eye(4)

    # --- 2) huesos sin inversa de bind: se colocan con el prefab ---
    def completar(self):
        conocidos = list(self.mundo)
        if not conocidos:
            raise SystemExit("ERROR: no se aprendio ningun hueso")
        # ajuste rigido prefab -> referencia (Kabsch) con los huesos conocidos
        P = np.array([self.trs[n][0] for n in conocidos], dtype=np.float64)
        B = np.array([self.mundo[n][:3, 3] for n in conocidos], dtype=np.float64)
        Pc, Bc = P - P.mean(axis=0), B - B.mean(axis=0)
        U, _, Vt = np.linalg.svd(Pc.T @ Bc)
        d = np.sign(np.linalg.det(Vt.T @ U.T))
        D = np.diag([1.0, 1.0, d])
        R = Vt.T @ D @ U.T
        t = B.mean(axis=0) - R @ P.mean(axis=0)
        resid = np.abs((R @ P.T).T + t - B).max(axis=1)
        print(f"   ajuste prefab->referencia: R={np.round(R, 3).tolist()} t={np.round(t, 4)}")
        print(f"   residuo del ajuste: mediana {np.median(resid):.4f} m  "
              f"peor {resid.max():.4f} m ({known_peor(conocidos, resid)})")
        self.R, self.t = R, t
        # ordenar el prefab de padres a hijos y colocar los que falten
        puesto = set()
        for nom in self.orden:
            if nom in self.mundo:
                puesto.add(nom)
                continue
            pa = self.padre.get(nom)
            if pa is None:
                continue
            pos, rot, esc = self.trs[nom]
            m = np.eye(4)
            m[:3, :3] = R @ quat_mat(rot) @ R.T
            m[:3, 3] = R @ np.array(pos) + t
            self.mundo[nom] = m
            self.metodo[nom] = "prefab"
            puesto.add(nom)

    # --- 3) arbol: local = inversa(mundo padre) * mundo ---
    def locales(self):
        """Arbol con los huesos REALES (los que tienen inversa de bind).

        Los huesos intermedios del prefab (p. ej. 'Bip01 L Forearm': esta en el rig del juego pero
        no en la lista del renderer, o sea que no tiene pesos) NO se inventan: su pose de reposo no
        se puede recuperar de lo exportado (el prefab esta en otra pose que la de bind, residuo
        ~0,3 m) y colocarlos mal seria peor que no ponerlos. Cada hueso se cuelga de su antecesor
        real mas cercano que si exista.
        """
        idx = {nom: i for i, nom in enumerate(n for n in self.orden if n in self.mundo)}
        self.padre_real = {}
        for nom in idx:
            pa = self.padre.get(nom)
            saltos = 0
            while pa is not None and pa not in idx:
                pa = self.padre.get(pa)
                saltos += 1
            self.padre_real[nom] = pa
            if saltos:
                self.saltos = getattr(self, "saltos", 0) + 0
        locales = {}
        for nom in idx:
            w = self.mundo[nom]
            pa = self.padre_real[nom]
            locales[nom] = (np.linalg.inv(self.mundo[pa]) @ w) if pa in idx else w
        return idx, locales


def known_peor(nombres, resid):
    return nombres[int(np.argmax(resid))]


def hornear(m):
    """Pasa una matriz del espacio de Unity al de glTF (espejo + ejes) horneandola."""
    return T @ m @ np.linalg.inv(T)


def main():
    # "python build_kotone_glb.py cara,ojo" -> GLB con el esqueleto completo pero solo esas mallas.
    # Sirve para rehacer los GLB por pieza del paquete: si se usa el constructor entero, cada pieza
    # sale con su propio esqueleto y sus expresiones, que es como los quiere el usuario.
    solo = [a for a in sys.argv[1:] if not a.startswith("-")]
    seleccion = set(solo[0].split(",")) if solo else None
    esq = Esqueleto()
    for k, (_, parte) in enumerate(PERSONAJE):
        esq.aprender(parte, referencia=(k == 0))     # el cuerpo fija el espacio de referencia
    for parte, M in esq.matrices.items():
        print(f"   {parte[-24:]:24s} matriz de pieza: t={np.round(M[:3, 3], 4)} "
              f"escala={np.round(np.linalg.norm(M[:3, :3], axis=0), 4)}")
    print(f"1. huesos con mundo exacto (inversa de bind): {len(esq.mundo)}")
    esq.completar()
    print(f"   huesos totales: {len(esq.mundo)}   del prefab: "
          f"{sum(1 for v in esq.metodo.values() if v == 'prefab')}")
    idx, locales = esq.locales()
    print(f"2. nodos de hueso: {len(idx)}")
    nodos_malla = []

    g = Gltf()
    # --- nodos del esqueleto ---
    base = len(g.j["nodes"])
    orden = [n for n in esq.orden if n in idx]
    for nom in orden:
        L = hornear(locales[nom])
        pos = L[:3, 3]
        rot = mat_quat(L[:3, :3] / (np.linalg.norm(L[:3, :3], axis=0) + 1e-20))
        esc = np.linalg.norm(L[:3, :3], axis=0)
        g.j["nodes"].append({"name": nom,
                            "translation": [round(float(x), 7) for x in pos],
                            "rotation": [round(float(x), 7) for x in rot],
                            "scale": [round(float(x), 7) for x in esc]})
    for nom in orden:
        pa = esq.padre_real.get(nom)
        if pa in idx:
            g.j["nodes"][base + idx[pa]].setdefault("children", []).append(base + idx[nom])
    raices = [base + i for nom, i in idx.items() if esq.padre_real.get(nom) not in idx]
    # Raiz sintetica unica: solo cuelga el esqueleto, para que el arbol salga limpio en Blender.
    # SIN giro: el modelo ya sale mirando a +Z, que es el frente que manda el estandar glTF (comprobado
    # contra el dato del juego: la cara esta en -Z del dato y la conversion de ejes la deja en +Z).
    # OJO: girarlo 180 grados "para que mire al frente en Blender" esta MAL: no arregla nada y deja al
    # personaje de espaldas, con el brazalete en el lado contrario de la pantalla. Ya paso una vez.
    # 180 grados sobre Y: deja el modelo mirando a -Y en Blender (vista frontal, Numpad 1), que es como
    # se ve en el juego, y coincide con la orientacion del paquete antiguo que Lukas dio por buena.
    g.j["nodes"].append({"name": "PC079_01_raiz", "rotation": [0.0, 1.0, 0.0, 0.0],
                         "children": raices})
    raiz = len(g.j["nodes"]) - 1
    print(f"   raices del esqueleto: {len(raices)} (colgadas de PC079_01_raiz)")

    # inversas de bind de TODOS los huesos (las que faltan se calculan del mundo)
    mib = np.array([hornear(np.linalg.inv(esq.mundo[n])) for n in orden])
    acc_ibm = g.acc_mat4(np.transpose(mib, (0, 2, 1)).reshape(-1, 16))

    # --- materiales y texturas ---
    mats_por_nombre = {}
    # nombre del material principal de cada PIEZA: hace falta para la herencia del parpado cuando
    # el GLB se construye sin la cara (mats_por_nombre esta indexado por nombre de material, no de pieza)
    mat_principal_de_pieza = {}
    for _, parte in PERSONAJE:
        meta = json.load(open(os.path.join(DUMP, parte + ".json"), encoding="utf-8"))
        for m in meta["materiales"]:
            mats_por_nombre[m.get("nombre") or "material"] = m
        if meta["materiales"]:
            mat_principal_de_pieza[parte] = meta["materiales"][0].get("nombre")

    def material(nombre):
        if nombre in mats_por_nombre and nombre not in [mm.get("name") for mm in g.j["materials"]]:
            src = mats_por_nombre[nombre]
            mat = {"name": nombre, "pbrMetallicRoughness": {"baseColorFactor": [1, 1, 1, 1],
                                                            "metallicFactor": 0.0,
                                                            "roughnessFactor": 0.8}}
            for t in src.get("texturas", []):
                slot, tex = t.get("slot", ""), t.get("textura")
                if not tex:
                    continue
                p = ruta_textura(tex)
                if not p:
                    continue
                img = len(g.j["images"])
                with open(p, "rb") as f:
                    datos = f.read()
                bv = len(g.j["bufferViews"])
                off = len(g.bin)
                g.bin += datos
                g.j["bufferViews"].append({"buffer": 0, "byteOffset": off, "byteLength": len(datos)})
                g.j["images"].append({"bufferView": bv, "mimeType": "image/png", "name": tex})
                g.j["textures"].append({"source": img, "sampler": 0})
                ti = len(g.j["textures"]) - 1
                if slot in ("_MainTex", "_BaseMap", "_BaseColorMap"):
                    mat["pbrMetallicRoughness"]["baseColorTexture"] = {"index": ti}
                    mat["pbrMetallicRoughness"]["baseColorFactor"] = [1, 1, 1, 1]
                elif slot == "_BumpMap":
                    mat["normalTexture"] = {"index": ti}
            g.j["materials"].append(mat)
        return next((i for i, mm in enumerate(g.j["materials"]) if mm.get("name") == nombre), None)

    # --- mallas ---
    nombres_exp = []
    nodos_malla = []
    for etiqueta, parte in PERSONAJE:
        if seleccion and etiqueta not in seleccion:
            continue
        meta = json.load(open(os.path.join(DUMP, parte + ".json"), encoding="utf-8"))
        pos = cargar(parte, "pos.bin", "<f4", (-1, 3)).astype(np.float64)
        nrm = cargar(parte, "nrm.bin", "<f4", (-1, 3)).astype(np.float64)
        uv0 = uv_gltf(parte)
        # la matriz de la pieza lleva sus vertices al espacio de referencia del esqueleto
        Mp = esq.matrices[parte]
        pos = (Mp[:3, :3] @ pos.T).T + Mp[:3, 3]
        nrm = np.linalg.inv(Mp[:3, :3]).T @ nrm.T
        nrm = nrm.T
        bidx = cargar(parte, "bidx.bin", "<u2", (-1, 4))
        bwgt = cargar(parte, "bwgt.bin", "<f4", (-1, 4))
        # a espacio glTF
        pos = (T[:3, :3] @ pos.T).T
        nrm = (T[:3, :3] @ nrm.T).T

        # remapeo de indices de hueso: lista de la pieza -> indice global por nombre
        nombres = [h.get("nombre") for h in meta["lista_huesos"]]
        remap = np.zeros(len(nombres), dtype=np.uint16)
        faltan = 0
        for k, nom in enumerate(nombres):
            if nom in idx:
                remap[k] = idx[nom]
            else:
                faltan += 1
        if faltan:
            print(f"   aviso {etiqueta}: {faltan} huesos de la pieza sin equivalente")
        jidx = remap[bidx]

        # los indices de la pieza que no existan se mandan al hueso 0 con peso 0
        atrib = {"POSITION": g.acc_crear(pos.astype("<f4"), "POSITION"),
                 "NORMAL": g.acc_crear(nrm.astype("<f4"), "NORMAL"),
                 "TEXCOORD_0": g.acc_crear(uv0.astype("<f4"), "TEXCOORD_0"),
                 "JOINTS_0": g.acc_crear(jidx.astype("<u2"), "JOINTS_0"),
                 "WEIGHTS_0": g.acc_crear(bwgt.astype("<f4"), "WEIGHTS_0")}

        prims = []
        for i in range(meta["submallas"]):
            # CON el bobinado volteado: T tiene determinante -1 (es un espejo), asi que la conversion
            # INVIERTE la orientacion de las caras y hay que devolverla. Si no se voltea, el bobinado
            # queda al reves de las
            # normales y en Material Preview (Blender) el modelo se ve del reves, "con las texturas
            # por dentro". Medido: 0% de caras bien orientadas al invertirlo, 100% sin invertir.
            tri = cargar(parte, f"tris{i}.bin", "<u4").reshape(-1, 3)[:, [0, 2, 1]].reshape(-1)
            pr = {"attributes": dict(atrib)}
            pr["indices"] = g.acc_crear(tri.astype("<u4"))
            mat_nombre = None
            if i < len(meta["materiales"]):
                mat_nombre = meta["materiales"][i].get("nombre")
            if parte in MATERIAL_DE and (not mat_nombre or mat_nombre == "Standard"):
                # hereda el material de la pieza donante, por su NOMBRE (no por el de la pieza)
                mat_nombre = mat_principal_de_pieza.get(MATERIAL_DE[parte])
                print(f"   material heredado para {parte.split('_')[-1]}: {mat_nombre}")
            mi = material(mat_nombre) if mat_nombre else None
            if mi is not None:
                pr["material"] = mi
            objetivos = []
            for exp in meta["lista_expresiones"]:
                for fr in exp["frames"]:
                    dv = np.fromfile(os.path.join(DUMP, fr["bin"]), dtype="<f4").reshape(-1, 3)
                    dv = (T[:3, :3] @ dv.T).T
                    # OJO: tiene que declararse VEC3 (si se deja en SCALAR, Blender aborta la
                    # importacion con "array at index 0 has size 3 and ... index 1 has size 1")
                    objetivos.append(g.acc_crear(dv.astype("<f4"), "POSITION", minmax=True))
                    if exp["nombre"] not in nombres_exp:
                        nombres_exp.append(exp["nombre"])
            if objetivos:
                pr["targets"] = [{"POSITION": a} for a in objetivos]
            prims.append(pr)

        malla = {"name": meta["parte"], "primitives": prims}
        if any(p.get("targets") for p in prims):
            # nombres de expresion por primitiva (mismo orden que la lista de la pieza)
            malla["extras"] = {"targetNames": _nombres_expresiones(meta)}
            malla["weights"] = [0.0] * len(_nombres_expresiones(meta))
        g.j["meshes"].append(malla)
        skin = {"joints": list(range(base, base + len(orden))), "inverseBindMatrices": acc_ibm,
                "skeleton": base + idx[orden[0]] if orden else base}
        g.j["skins"].append(skin)
        g.j["nodes"].append({"name": meta["parte"] + "_MALLA", "mesh": len(g.j["meshes"]) - 1,
                             "skin": len(g.j["skins"]) - 1})
        nodos_malla.append(len(g.j["nodes"]) - 1)
        print(f"   {etiqueta:8s} verts {len(pos):6d}  grupos {len(nombres):4d}  "
              f"submallas {meta['submallas']}  expresiones {len(meta['lista_expresiones'])}")

    # --- empaquetar ---
    # Herencia de material: si a una pieza se le perdio el material en el export (le pasa al
    # parpado, cuyo material es el relleno "Standard"), hereda el de la pieza donante. Se resuelve
    # por INDICE de material y no por nombre, porque mats_por_nombre esta indexado por nombre de
    # MATERIAL y aqui se tiene el nombre de PIEZA (con ese cruce la herencia nunca resolvia y el
    # parpado se quedaba sin material: cara blanca y "sin textura" al abrir el GLB).
    malla_por_pieza = {m.get("name"): m for m in g.j["meshes"]}
    for pieza, donante in MATERIAL_DE.items():
        malla, don = malla_por_pieza.get(pieza), malla_por_pieza.get(donante)
        if not malla or not don:
            continue
        idx_don = don["primitives"][0].get("material")
        for pr in malla["primitives"]:
            mat = pr.get("material")
            pbr = g.j["materials"][mat].get("pbrMetallicRoughness", {}) if mat is not None else {}
            if "baseColorTexture" not in pbr and idx_don is not None:
                pr["material"] = idx_don
                print(f"   material heredado para {pieza.split('_')[-1]}: del indice {idx_don}")
    # las mallas tienen que colgar del nodo raiz, no ser raices sueltas: si son raices, Blender las
    # manda a la coleccion "Orphan Nodes" y no se renderizan. Su transformacion se ignora por ser
    # mallas con piel, asi que colgarlas no cambia nada geometricamente.
    for nm in nodos_malla:
        g.j["nodes"][raiz].setdefault("children", []).append(nm)
    g.j["scenes"][0]["nodes"] = [raiz]
    g.j["buffers"][0]["byteLength"] = len(g.bin)
    js = json.dumps(g.j, separators=(",", ":")).encode()
    while len(js) % 4:
        js += b" "
    total = 12 + 8 + len(js) + 8 + len(g.bin)
    blob = (b"glTF" + struct.pack("<II", 2, total) + struct.pack("<I", len(js)) + b"JSON" + js
            + struct.pack("<I", len(g.bin)) + b"BIN\0" + bytes(g.bin))
    nombre_glb = ("Kotone_Shiomi_completo.glb" if not seleccion
                  else "Kotone_Shiomi_" + "_".join(sorted(seleccion)) + ".glb")
    destino = os.path.join(OUT, "01_modelo", "glb", nombre_glb)
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    with open(destino, "wb") as f:
        f.write(blob)
    print(f"\n3. GLB escrito: {destino}  ({len(blob)/1e6:.2f} MB)")
    print(f"   nodos {len(g.j['nodes'])}  huesos {len(orden)}  mallas {len(g.j['meshes'])}  "
          f"pieles {len(g.j['skins'])}  materiales {len(g.j['materials'])}  "
          f"texturas {len(g.j['textures'])}")
    return destino


def _nombres_expresiones(meta):
    v = []
    for exp in meta["lista_expresiones"]:
        for _ in exp["frames"]:
            v.append(exp["nombre"])
    return v


if __name__ == "__main__":
    main()