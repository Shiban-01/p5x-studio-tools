"""Mide cada malla de los GLB del paquete: tamano y centro. Para saber que armas hay de verdad."""
import json, os, struct, sys
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


def recorrer(js, idx, M, sal):
    for i in idx:
        n = js["nodes"][i]
        Mi = M @ trs(n)
        if "mesh" in n:
            sal.append((Mi, n["mesh"]))
        recorrer(js, n.get("children", []), Mi, sal)


def medir(ruta):
    js, bin_ = leer(ruta)
    inst = []
    recorrer(js, js["scenes"][0]["nodes"], np.eye(4), inst)
    filas = []
    for M, im in inst:
        for pr in js["meshes"][im]["primitives"]:
            p = acc(js, bin_, pr["attributes"]["POSITION"]).astype(np.float64)
            p = p @ M[:3, :3].T + M[:3, 3]
            lo, hi = p.min(axis=0), p.max(axis=0)
            mat = js["materials"][pr["material"]]["name"] if "material" in pr else "?"
            filas.append((js["meshes"][im].get("name", "?"), mat, len(p), hi - lo, (lo + hi) / 2))
    return filas


print("=== mallas de Kotone_Shiomi_full.glb ===")
for nombre, mat, n, d, c in medir(os.path.join(GLB_DIR, "Kotone_Shiomi_full.glb")):
    corto = nombre.split("_rig_")[-1]
    print("  %-26s %-18s %6d v  %.3f x %.3f x %.3f  centro=(%6.2f, %5.2f, %5.2f)"
          % (corto, mat, n, d[0], d[1], d[2], c[0], c[1], c[2]))

print("\n=== GLB de arma sueltos ===")
for f in ["Kotone_Shiomi_weapon_spear.glb", "Kotone_Shiomi_weapon_spear_sheath.glb",
          "Kotone_Shiomi_weapon_pistol.glb"]:
    etiqueta = f.replace("Kotone_Shiomi_weapon_", "").replace(".glb", "")
    for nombre, mat, n, d, c in medir(os.path.join(GLB_DIR, f)):
        print("  %-14s %-26s %-18s %5d v  %.3f x %.3f x %.3f  centro=(%6.2f, %5.2f, %5.2f)"
              % (etiqueta, nombre.split("_rig_")[-1], mat, n, d[0], d[1], d[2], c[0], c[1], c[2]))

print("\n=== mallas sin transformar (crudo, sin jerarquia de nodos) ===")
for f in ["Kotone_Shiomi_weapon_spear.glb", "Kotone_Shiomi_weapon_pistol.glb"]:
    js, bin_ = leer(os.path.join(GLB_DIR, f))
    for i, m in enumerate(js["meshes"]):
        for pr in m["primitives"]:
            p = acc(js, bin_, pr["attributes"]["POSITION"]).astype(np.float64)
            lo, hi = p.min(axis=0), p.max(axis=0)
            print("  %-34s %5d v  %.3f x %.3f x %.3f" % (m.get("name", "?")[-30:], len(p),
                                                         *(hi - lo)))