"""Comprueba si hace falta aplicar la PIEL (skinning) al renderizar los GLB.

Compara la posicion de cada malla dibujando los vertices crudos (lo que hacia el rasterizador)
y aplicando la piel: para cada vertice, la suma de peso_j * (matriz_mundo(hueso_j) * IBM_j).

Si el modelo estuviera exportado en la pose de reposo con los vertices ya colocados, las dos
medidas coincidirian. Si no, la diferencia dice donde va cada pieza de verdad (por ejemplo, si la
pistola del tobillo esta guardada en el origen y solo el juego la coloca al usarla).
"""
import json
import os
import struct
import numpy as np

GLB_DIR = r"C:\Users\Lukas\p5x-datamining\kotone_shiomi\01_model\glb"
COMP = {5120: "b", 5121: "B", 5122: "h", 5123: "H", 5125: "I", 5126: "f"}
NC = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


def leer(ruta):
    d = open(ruta, "rb").read()
    off, js, bin_ = 12, None, None
    while off < len(d):
        largo, tipo = struct.unpack("<II", d[off:off + 8])
        if tipo == 0x4E4F534A:
            js = json.loads(d[off + 8:off + 8 + largo].decode("utf-8"))
        elif tipo == 0x004E4942:
            bin_ = d[off + 8:off + 8 + largo]
        off += 8 + largo
    return js, bin_


def acc(js, bin_, i):
    a = js["accessors"][i]
    bv = js["bufferViews"][a["bufferView"]]
    n = NC[a["type"]]
    arr = np.frombuffer(bin_[bv.get("byteOffset", 0) + a.get("byteOffset", 0):],
                        dtype=np.dtype(COMP[a["componentType"]]).newbyteorder("<"),
                        count=a["count"] * n)
    return arr.reshape(-1, n) if n > 1 else arr


def trs(n):
    M = np.eye(4)
    if "translation" in n:
        M[:3, 3] = n["translation"]
    if "scale" in n:
        M[:3, :3] = np.diag(n["scale"]) @ M[:3, :3]
    if "rotation" in n:
        x, y, z, w = n["rotation"]
        R = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                      [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                      [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
        M[:3, :3] = R @ M[:3, :3]
    return M


def mundos(js):
    """matriz de mundo de cada nodo"""
    W = {}

    def baja(idx, M):
        for i in idx:
            n = js["nodes"][i]
            Mi = M @ trs(n)
            W[i] = Mi
            baja(n.get("children", []), Mi)

    baja(js["scenes"][0]["nodes"], np.eye(4))
    return W


def analizar(ruta):
    js, bin_ = leer(ruta)
    W = mundos(js)
    print("\n=== %s ===" % os.path.basename(ruta))
    hay_skin = "skins" in js
    print("  skins: %d" % len(js.get("skins", [])))

    inst = []

    def baja(idx, M):
        for i in idx:
            n = js["nodes"][i]
            Mi = M @ trs(n)
            if "mesh" in n:
                inst.append((i, Mi, n["mesh"], n.get("skin")))
            baja(n.get("children", []), Mi)

    baja(js["scenes"][0]["nodes"], np.eye(4))

    for nodo, M, im, skin_i in inst:
        for pr in js["meshes"][im]["primitives"]:
            p = acc(js, bin_, pr["attributes"]["POSITION"]).astype(np.float64)
            crudo = p @ M[:3, :3].T + M[:3, 3]
            lo_c, hi_c = crudo.min(axis=0), crudo.max(axis=0)

            if skin_i is None:
                print("  %-34s SIN piel: %.3f x %.3f x %.3f  centro=(%6.2f, %5.2f, %5.2f)"
                      % (js["meshes"][im].get("name", "?")[-33:], *(hi_c - lo_c),
                         *((lo_c + hi_c) / 2)))
                continue

            sk = js["skins"][skin_i]
            joints = sk["joints"]
            ibm = acc(js, bin_, sk["inverseBindMatrices"]).astype(np.float64).reshape(-1, 4, 4)
            ibm = np.transpose(ibm, (0, 2, 1))          # glTF guarda por columnas
            J = acc(js, bin_, pr["attributes"]["JOINTS_0"]).astype(np.int64)
            Wt = acc(js, bin_, pr["attributes"]["WEIGHTS_0"]).astype(np.float64)
            if J.max() >= len(joints):
                print("  %-34s indices de hueso fuera de rango" % js["meshes"][im].get("name", "?")[-33:])
                continue
            # matriz de cada hueso: mundo(hueso) * IBM
            JM = np.stack([W.get(joints[j], np.eye(4)) @ ibm[j] for j in range(len(joints))])
            p4 = np.concatenate([p, np.ones((len(p), 1))], axis=1)
            piel = np.zeros((len(p), 3))
            for k in range(4):
                m = JM[J[:, k]]                                    # (n,4,4)
                v = np.einsum("nij,nj->ni", m, p4)[:, :3]
                piel += Wt[:, k:k + 1] * v
            piel = piel @ M[:3, :3].T + M[:3, 3]
            lo_p, hi_p = piel.min(axis=0), piel.max(axis=0)

            print("  %-34s crudo: %.3f x %.3f x %.3f centro=(%6.2f, %5.2f, %5.2f)"
                  % (js["meshes"][im].get("name", "?")[-33:], *(hi_c - lo_c), *((lo_c + hi_c) / 2)))
            print("  %-34s piel : %.3f x %.3f x %.3f centro=(%6.2f, %5.2f, %5.2f)"
                  % ("", *(hi_p - lo_p), *((lo_p + hi_p) / 2)))


for f in ["Kotone_Shiomi_full.glb", "Kotone_Shiomi_weapon_pistol.glb",
          "Kotone_Shiomi_weapon_spear.glb"]:
    analizar(os.path.join(GLB_DIR, f))