"""Comprueba si Blender ha MODIFICADO los vertices al importar, y si los huesos coinciden con el glTF.

Uso: blender --background --python comparar_import.py -- <glb>
"""
import json
import struct
import sys

import bpy

ruta = sys.argv[sys.argv.index("--") + 1]


def leer_glb(p):
    b = open(p, "rb").read()
    off, js, bin_ = 12, None, b""
    while off < len(b):
        ln, ty = struct.unpack_from("<II", b, off)
        off += 8
        c = b[off:off + ln]
        off += ln
        if ty == 0x4E4F534A:
            js = json.loads(c.decode("utf-8"))
        elif ty == 0x004E4942:
            bin_ = c
    return js, bin_


js, bin_ = leer_glb(ruta)


def acc(i):
    a = js["accessors"][i]
    bv = js["bufferViews"][a["bufferView"]]
    n = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}[a["type"]]
    ch, tam = {5126: ("f", 4), 5123: ("H", 2), 5125: ("I", 4), 5121: ("B", 1)}[a["componentType"]]
    off = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    paso = tam * n
    return [struct.unpack_from("<" + ch * n, bin_, off + k * paso) for k in range(a["count"])]


bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=ruta)

# vertices importados vs accessor
for mi, malla in enumerate(js["meshes"][:3]):
    a = acc(malla["primitives"][0]["attributes"]["POSITION"])
    obj = next((o for o in bpy.data.objects if o.type == "MESH" and o.data.vertices
                and abs(len(o.data.vertices) - len(a)) == 0), None)
    if obj is None:
        print("  no encuentro objeto con %d vertices" % len(a))
        continue
    peor = 0.0
    for i, v in enumerate(a):
        d = max(abs(obj.data.vertices[i].co[k] - v[k]) for k in range(3))
        peor = max(peor, d)
    print("  %-44s verts=%d  diferencia maxima accessor-vs-importado: %.4f"
          % (malla["name"][-44:], len(a), peor))

# huesos: matriz_local de Blender vs global del glTF
arm = next((o for o in bpy.data.objects if o.type == "ARMATURE"), None)
if arm is None:
    print("  sin armadura")
else:
    padres = {}
    for i, n in enumerate(js["nodes"]):
        for c in n.get("children", []):
            padres[c] = i

    def mul(A, B):
        return [[sum(A[i][k] * B[k][j] for k in range(4)) for j in range(4)] for i in range(4)]

    def trs(n):
        t = n.get("translation", [0, 0, 0])
        q = n.get("rotation", [0, 0, 0, 1])
        s = n.get("scale", [1, 1, 1])
        x, y, z, w = q
        R = [[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
             [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
             [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]]
        M = [[1.0 if i == j else 0.0 for j in range(4)] for i in range(4)]
        for i in range(3):
            for j in range(3):
                M[i][j] = R[i][j] * s[j]
            M[i][3] = t[i]
        return M

    def glob(i):
        M = trs(js["nodes"][i])
        p = padres.get(i)
        while p is not None:
            M = mul(trs(js["nodes"][p]), M)
            p = padres.get(p)
        return M

    huesos = {b.name: b for b in arm.data.bones}
    peores = []
    for i, n in enumerate(js["nodes"]):
        nom = n.get("name")
        if nom not in huesos:
            continue
        G = glob(i)
        L = huesos[nom].matrix_local
        d = max(abs(L[r][c] - G[r][c]) for r in range(4) for c in range(4))
        peores.append((d, nom))
    peores.sort(reverse=True)
    print("  huesos comparados: %d   desajustados (>1e-3): %d"
          % (len(peores), sum(1 for d, _ in peores if d > 1e-3)))
    for d, nom in peores[:6]:
        print("     %.4f  %s" % (d, nom))