
"""Comprueba si una exportacion es la misma geometria que el dato del juego o su ESPEJO.
Invariante: signo de det([izquierda, arriba, delante]). Los giros lo conservan; un espejo lo invierte.
La medida se hace en el dato del juego (espacio de la pieza) y en el GLB, y se comparan los signos."""
import json, os, struct, numpy as np

D = r"C:/Users/Lukas/p5x-datamining/_dl/kotone_dump"
GLB = r"C:/Users/Lukas/p5x-datamining/kotone_shiomi/01_modelo/glb/Kotone_Shiomi_completo.glb"
B = "PC079_01_body_wholeexport_rig_PC079_01_body"

def pos(d):
    return np.fromfile(d + ".pos.bin", dtype="<f4").reshape(-1, 3).astype(float)

def ibm(d):
    return np.fromfile(d + ".ibm.bin", dtype="<f4").reshape(-1, 4, 4).astype(float)

def nombres(d):
    return [h["nombre"] for h in json.load(open(d + ".json", encoding="utf-8"))["lista_huesos"]]

def quat(q):
    x, y, z, w = q
    return np.array([[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
                     [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
                     [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]])

def acc(j, dd, off, i, tipo="<f4"):
    a = j["accessors"][i]; bv = j["bufferViews"][a["bufferView"]]
    comp = {"SCALAR":1,"VEC2":2,"VEC3":3,"VEC4":4}[a["type"]]
    return np.frombuffer(dd, dtype=np.dtype(tipo), count=a["count"]*comp,
                         offset=off+bv.get("byteOffset",0)+a.get("byteOffset",0)).reshape(a["count"], comp)

def marcador(izq, arr, delante, etiqueta):
    M = np.stack([izq, arr, delante])
    v = float(np.linalg.det(M))
    print("%-22s det %+0.6f   |izq| %.3f  |arr| %.3f  |del| %.3f  -> %s" % (
        etiqueta, v, np.linalg.norm(izq), np.linalg.norm(arr), np.linalg.norm(delante),
        "DIESTRO (A)" if v > 0 else "LEVOGIRO/ESPEJO (B)"))
    return v

print("=== 1. DATO DEL JUEGO (espacio de la pieza) ===")
nb = nombres(os.path.join(D, B)); ib = ibm(os.path.join(D, B))
# el volcado guarda las matrices en forma de vector fila: tras trasponer, la traslacion
# esta en la ULTIMA FILA, no en la ultima columna (esto ya se comio una medicion antes)
w = lambda nom: np.linalg.inv(ib[nb.index(nom)].T)[3, :3]
ojo = pos(os.path.join(D, "PC079_01_face_wholeexport_rig_bs_PC079_01_eye")).mean(axis=0)
pelo = pos(os.path.join(D, "PC079_01_hair_wholeexport_rig_PC079_01_hair")).mean(axis=0)
print("   cabeza %s  pelvis %s" % (np.round(w("Bip01 Head"),3), np.round(w("Bip01 Pelvis"),3)))
print("   ojo %s   pelo %s" % (np.round(ojo,3), np.round(pelo,3)))
sig_juego = marcador(w("Bip01 L Hand") - w("Bip01 R Hand"),
                     w("Bip01 Head") - w("Bip01 Pelvis"),
                     ojo - pelo, "dato del juego")

print("=== 2. GLB ACTUAL ===")
d = open(GLB, "rb").read(); ln = struct.unpack_from("<I", d, 12)[0]
j = json.loads(d[20:20+ln].decode()); off = 20 + ln + 8
padre = {}
for k, n in enumerate(j["nodes"]):
    for c in n.get("children", []): padre[c] = k
cache = {}
def W(k):
    if k in cache: return cache[k]
    n = j["nodes"][k]; M = np.eye(4)
    if "matrix" in n: M = np.array(n["matrix"], dtype=float).reshape(4,4).T
    else:
        R = quat(n["rotation"]) if "rotation" in n else np.eye(3)
        if "scale" in n: R = R @ np.diag(n["scale"])
        M[:3,:3] = R; M[:3,3] = n.get("translation", [0,0,0])
    M = (W(padre[k]) @ M) if k in padre else M
    cache[k] = M; return M
def nodo_de(nombre):
    return next(k for k, n in enumerate(j["nodes"]) if n.get("name") == nombre)
def centro_malla(pista):
    m = next(m for m in j["meshes"] if pista in m["name"].lower())
    k = next(i for i, n in enumerate(j["nodes"]) if n.get("mesh") == j["meshes"].index(m))
    V = acc(j, d, off, m["primitives"][0]["attributes"]["POSITION"]).astype(float)
    return (V @ W(k)[:3,:3].T + W(k)[:3,3]).mean(axis=0)
ojo_g = centro_malla("eye"); pelo_g = centro_malla("hair")
print("   ojo %s   pelo %s" % (np.round(ojo_g,3), np.round(pelo_g,3)))
sig_glb = marcador(W(nodo_de("Bip01 L Hand"))[:3,3] - W(nodo_de("Bip01 R Hand"))[:3,3],
                   W(nodo_de("Bip01 Head"))[:3,3] - W(nodo_de("Bip01 Pelvis"))[:3,3],
                   ojo_g - pelo_g, "GLB actual")
print()
print("VEREDICTO:", "MISMA quiralidad (solo girado)" if (sig_juego > 0) == (sig_glb > 0)
      else "EL GLB ES EL ESPEJO DEL DATO DEL JUEGO")
