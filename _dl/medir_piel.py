"""Mide si la PIEL de un GLB deforma la malla en reposo (deberia ser identidad).

Para cada vertice calcula `suma_j w_j * (global(j) * ibm_j) * v` y lo compara con `v`. Si el error es
0, la malla en reposo sale intacta. Si no, dice que huesos lo causan.

Uso: python medir_piel.py <glb> [max_vertices]
"""
import json
import struct
import sys
from pathlib import Path

TAM = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}
TIPO = {"<f4": 4, "<u2": 2, "<u4": 4, "<u1": 1}


def leer_glb(ruta):
    b = Path(ruta).read_bytes()
    off, js, bin_ = 12, None, b""
    while off < len(b):
        ln, ty = struct.unpack_from("<II", b, off)
        off += 8
        trozo = b[off:off + ln]
        off += ln
        if ty == 0x4E4F534A:
            js = json.loads(trozo.decode("utf-8"))
        elif ty == 0x004E4942:
            bin_ = trozo
    return js, bin_


def acc(js, bin_, i):
    a = js["accessors"][i]
    bv = js["bufferViews"][a["bufferView"]]
    n = TAM[a["type"]]
    ch, tam = {5126: ("f", 4), 5123: ("H", 2), 5125: ("I", 4), 5121: ("B", 1)}[a["componentType"]]
    paso = tam * n
    off = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    out = []
    for k in range(a["count"]):
        out.append(struct.unpack_from("<" + ch * n, bin_, off + k * paso))
    return out


def mul(A, B):
    return [[sum(A[i][k] * B[k][j] for k in range(4)) for j in range(4)] for i in range(4)]


def ident():
    return [[1.0 if i == j else 0.0 for j in range(4)] for i in range(4)]


def trs(n):
    t = n.get("translation", [0, 0, 0])
    q = n.get("rotation", [0, 0, 0, 1])
    s = n.get("scale", [1, 1, 1])
    x, y, z, w = q
    R = [[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
         [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
         [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]]
    M = ident()
    for i in range(3):
        for j in range(3):
            M[i][j] = R[i][j] * s[j]
        M[i][3] = t[i]
    return M


ruta = sys.argv[1]
limite = int(sys.argv[2]) if len(sys.argv) > 2 else 300
js, bin_ = leer_glb(ruta)

padres = {}
for i, n in enumerate(js["nodes"]):
    for c in n.get("children", []):
        padres[c] = i


def glob(i):
    M = trs(js["nodes"][i])
    p = padres.get(i)
    while p is not None:
        M = mul(trs(js["nodes"][p]), M)
        p = padres.get(p)
    return M


print("mallas=%d skins=%d nodos=%d" % (len(js["meshes"]), len(js.get("skins", [])), len(js["nodes"])))
for mi, malla in enumerate(js["meshes"][:4]):
    pr = malla["primitives"][0]
    if "JOINTS_0" not in pr["attributes"]:
        print("  %s: sin piel" % malla["name"][-40:])
        continue
    pos = acc(js, bin_, pr["attributes"]["POSITION"])
    ji = acc(js, bin_, pr["attributes"]["JOINTS_0"])
    jw = acc(js, bin_, pr["attributes"]["WEIGHTS_0"])
    skin = js["skins"][js["nodes"][next(i for i, n in enumerate(js["nodes"])
                                       if n.get("mesh") == mi)]["skin"]]
    joints = skin["joints"]
    ibm = acc(js, bin_, skin["inverseBindMatrices"])
    G = [glob(j) for j in joints]

    def m4(v):
        # glTF: matrices en COLUMNA-mayor
        return [[v[c * 4 + r] for c in range(4)] for r in range(4)]

    M = [mul(G[j], m4(ibm[j])) for j in range(len(joints))]
    peor = 0.0
    peor_v = None
    suma = 0.0
    for k in range(min(limite, len(pos))):
        v = pos[k]
        w = jw[k]
        tot = sum(w)
        if tot <= 0:
            continue
        out = [0.0, 0.0, 0.0]
        for c in range(4):
            if w[c] <= 0:
                continue
            j = ji[k][c]
            Mj = M[j]
            for r in range(3):
                out[r] += (w[c] / tot) * (Mj[r][0] * v[0] + Mj[r][1] * v[1] + Mj[r][2] * v[2] + Mj[r][3])
        d = max(abs(out[r] - v[r]) for r in range(3))
        suma += d
        if d > peor:
            peor, peor_v = d, k
    print("  %-46s verts=%d  error medio=%.4f  peor=%.4f (vert %s)"
          % (malla["name"][-46:], len(pos), suma / max(1, min(limite, len(pos))), peor, peor_v))
    if peor > 0.01:
        k = peor_v
        print("      vertice %d pos=%s joints=%s pesos=%s" % (k, [round(x, 3) for x in pos[k]], ji[k], [round(x, 3) for x in jw[k]]))
        for c in range(4):
            j = ji[k][c]
            print("        j=%d %-28s desplaza a %s" % (j, js["nodes"][joints[j]].get("name", "?")[:28],
                                                       [round(x, 3) for x in [M[j][r][0] * pos[k][0] + M[j][r][1] * pos[k][1] + M[j][r][2] * pos[k][2] + M[j][r][3] for r in range(3)]]))