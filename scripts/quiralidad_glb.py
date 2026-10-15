
"""Mide la quiralidad de un GLB: signo de det([izquierda, arriba, delante]).
Un giro (determinante +1) NO cambia este signo; un espejo SI lo cambia. Asi se sabe si dos
exportaciones son la misma geometria girada o una es el espejo de la otra."""
import json, struct, os, numpy as np, sys

def leer(p):
    d = open(p, "rb").read(); ln = struct.unpack_from("<I", d, 12)[0]
    return json.loads(d[20:20+ln].decode()), d, 20 + ln + 8

def acc(j, d, off, i, tipo="<f4"):
    a = j["accessors"][i]; bv = j["bufferViews"][a["bufferView"]]
    comp = {"SCALAR":1,"VEC2":2,"VEC3":3,"VEC4":4}[a["type"]]
    return np.frombuffer(d, dtype=np.dtype(tipo), count=a["count"]*comp,
                         offset=off+bv.get("byteOffset",0)+a.get("byteOffset",0)).reshape(a["count"], comp)

def quat(q):
    x, y, z, w = q
    return np.array([[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
                     [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
                     [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]])

def mundos(j):
    """matriz de mundo de cada nodo, en el orden del array; y el padre de cada uno"""
    padre = {}
    for k, n in enumerate(j["nodes"]):
        for c in n.get("children", []):
            padre[c] = k
    cache = {}
    def W(k):
        if k in cache: return cache[k]
        n = j["nodes"][k]
        M = np.eye(4)
        if "matrix" in n:
            M = np.array(n["matrix"], dtype=float).reshape(4,4).T
        else:
            R = quat(n["rotation"]) if "rotation" in n else np.eye(3)
            if "scale" in n: R = R @ np.diag(n["scale"])
            M[:3,:3] = R
            M[:3,3] = n.get("translation", [0,0,0])
        M = (W(padre[k]) @ M) if k in padre else M
        cache[k] = M
        return M
    return W, padre

def medir(p):
    j, d, off = leer(p)
    W, _ = mundos(j)
    hueso = {}
    for k, n in enumerate(j["nodes"]):
        if "Bip01 Head" in (n.get("name") or ""): hueso["cabeza"] = k
        if "Bip01 Pelvis" in (n.get("name") or ""): hueso["pelvis"] = k
        if "Bip01 L Hand" in (n.get("name") or ""): hueso["L"] = k
        if "Bip01 R Hand" in (n.get("name") or ""): hueso["R"] = k
    faltan = [x for x in ("cabeza","pelvis","L","R") if x not in hueso]
    if faltan:
        return None, "faltan huesos: %s" % faltan
    ojo = None
    for m in j["meshes"]:
        if any(t in m["name"].lower() for t in ("eye", "ojo", "iris")):
            ojo = m; break
    if ojo is None:
        return None, "sin malla de ojo (mallas: %s)" % [m["name"][-24:] for m in j["meshes"]]
    k = next(i for i, n in enumerate(j["nodes"]) if n.get("mesh") == j["meshes"].index(ojo))
    V = acc(j, d, off, ojo["primitives"][0]["attributes"]["POSITION"]).astype(float)
    Vw = V @ W(k)[:3,:3].T + W(k)[:3,3]
    P = {n: W(i)[:3,3] for n, i in hueso.items()}
    arriba = P["cabeza"] - P["pelvis"]
    izquierda = P["L"] - P["R"]
    delante = Vw.mean(axis=0) - P["cabeza"]
    M = np.stack([izquierda, arriba, delante])
    return float(np.linalg.det(M)), "cabeza %s | manos L %s R %s | ojo %s" % (
        np.round(P["cabeza"],2), np.round(P["L"],2), np.round(P["R"],2), np.round(Vw.mean(axis=0),2))

for p in sys.argv[1:]:
    signo, detalle = medir(p)
    etiqueta = os.path.basename(p)
    print("%-34s %s" % (etiqueta, ("det %+.5f   %s" % (signo, detalle)) if signo is not None else "NO MEDIBLE: " + detalle))
