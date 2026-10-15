"""Compara, por la cadena del torso, la posicion de la CABEZA del hueso en Blender (rest y pose) con
la que dice el glTF. Si el rest no coincide, Blender ha reconstruido mal la pose de reposo.

Uso: blender --background --python cadena_huesos.py -- <glb>
"""
import json
import struct
import sys
from pathlib import Path

import bpy

ruta = sys.argv[sys.argv.index("--") + 1]

CADENA = ["t_persona", "Bip01", "Bip01 Pelvis", "Bip01 Spine", "Bip01 Spine1", "Bip01 Spine2",
          "Bip01 Neck", "Bip01 Head", "bn_head"]

b = Path(ruta).read_bytes()
off, js = 12, None
while off < len(b):
    ln, ty = struct.unpack_from("<II", b, off)
    off += 8
    c = b[off:off + ln]
    off += ln
    if ty == 0x4E4F534A:
        js = json.loads(c.decode("utf-8"))


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


bpy.ops.wm.read_factory_settings(use_empty=True)
if ruta.lower().endswith(".fbx"):
    bpy.ops.import_scene.fbx(filepath=ruta)
else:
    bpy.ops.import_scene.gltf(filepath=ruta)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
print("armadura %s  matrix_world=%s" % (arm.name, [round(x, 3) for r in arm.matrix_world for x in r]))

for nm in CADENA:
    if nm not in arm.data.bones:
        continue
    bo = arm.data.bones[nm]
    pb = arm.pose.bones[nm]
    i = next((k for k, n in enumerate(js["nodes"]) if n.get("name") == nm), None)
    g = None
    if i is not None:
        G = glob(i)
        g = [G[0][3], -G[2][3], G[1][3]]
    print("%-16s REST t=%s  POSE t=%s  gltf t=%s"
          % (nm, [round(x, 4) for x in bo.matrix_local.translation],
             [round(x, 4) for x in pb.matrix.translation],
             [round(x, 4) for x in g] if g else None))
    print("                 padre blender=%-18s padre gltf=%s"
          % (bo.parent.name if bo.parent else None,
             js["nodes"][padres[i]].get("name") if i is not None and padres.get(i) is not None else None))