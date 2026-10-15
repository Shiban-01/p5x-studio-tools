
"""Exporta OBJ (v/vt/vn/f + MTL) desde el GLB ya verificado. Se toma el GLB como fuente unica para
que OBJ y GLB no se puedan desincronizar. La rotacion de la raiz se hornea en los vertices, que es
lo que ve quien abre el OBJ en otro programa."""
import json, struct, os, numpy as np

GLB = r"C:/Users/Lukas/p5x-datamining/kotone_shiomi/01_modelo/glb/Kotone_Shiomi_completo.glb"
RAIZ = r"C:/Users/Lukas/p5x-datamining/kotone_shiomi/01_modelo/obj"
TEXDIR = "../../02_texturas"

def quat_a_mat(q):
    x, y, z, w = q
    return np.array([[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
                     [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
                     [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]])

def nodo_world(j, k, padre=None):
    nodo = j["nodes"][k]
    M = np.eye(4)
    if "matrix" in nodo:
        M = np.array(nodo["matrix"], dtype=float).reshape(4, 4).T
    else:
        R = quat_a_mat(nodo.get("rotation", [0, 0, 0, 1])) if "rotation" in nodo else np.eye(3)
        if "scale" in nodo: R = R @ np.diag(nodo["scale"])
        M[:3, :3] = R
        M[:3, 3] = nodo.get("translation", [0, 0, 0])
    hijos = {c: k for k in range(len(j["nodes"])) for c in j["nodes"][k].get("children", [])}
    p = next((padre for c, padre in hijos.items() if c == k), None)
    return (nodo_world(j, p) @ M) if p is not None else M

def leer(nombre):
    d = open(nombre, "rb").read()
    ln = struct.unpack_from("<I", d, 12)[0]
    j = json.loads(d[20:20+ln].decode())
    return j, d, 20 + ln + 8

def acc(j, d, off, i, tipo="<f4"):
    a = j["accessors"][i]; bv = j["bufferViews"][a["bufferView"]]
    comp = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}[a["type"]]
    return np.frombuffer(d, dtype=np.dtype(tipo), count=a["count"]*comp,
                         offset=off+bv.get("byteOffset", 0)+a.get("byteOffset", 0)).reshape(a["count"], comp)

def escribir(nombre_malla, salida, tex):
    j, d, off = leer(GLB)
    malla = next(m for m in j["meshes"] if m["name"] == nombre_malla)
    nodo_k = next(k for k, n in enumerate(j["nodes"]) if n.get("mesh") == j["meshes"].index(malla))
    W = nodo_world(j, nodo_k)
    R = W[:3, :3]
    os.makedirs(os.path.dirname(salida), exist_ok=True)
    mat = os.path.splitext(os.path.basename(salida))[0] + ".mtl"
    with open(salida, "w", encoding="utf-8") as f:
        f.write("# Kotone Shiomi (PC079) - Persona 5: The Phantom X\n")
        f.write("mtllib %s\n" % mat)
        base = 1
        for pi, pr in enumerate(malla["primitives"]):
            V = acc(j, d, off, pr["attributes"]["POSITION"]).astype(float)
            N = acc(j, d, off, pr["attributes"]["NORMAL"]).astype(float) if "NORMAL" in pr["attributes"] else None
            T = acc(j, d, off, pr["attributes"]["TEXCOORD_0"]).astype(float) if "TEXCOORD_0" in pr["attributes"] else None
            I = acc(j, d, off, pr["indices"], "<u4").reshape(-1, 3)
            Vw = (R @ V.T).T + W[:3, 3]
            Nw = (R @ N.T).T if N is not None else None
            for v in Vw: f.write("v %.6f %.6f %.6f\n" % tuple(v))
            if T is not None:
                for t in T: f.write("vt %.6f %.6f\n" % (t[0], 1.0 - t[1]))   # V volteada: glTF la tiene al reves
            if Nw is not None:
                for n in Nw: f.write("vn %.6f %.6f %.6f\n" % tuple(n))
            f.write("usemtl mat%d\n" % pi)
            for t in I:
                a, b, c = t + base
                s = "f %d/%d/%d %d/%d/%d %d/%d/%d" if (T is not None and Nw is not None) else "f %d %d %d"
                f.write((s % (a, a, a, b, b, b, c, c, c) if s.startswith("f %d/%d") else s % (a, b, c)) + "\n")
            base += len(V)
    with open(os.path.join(os.path.dirname(salida), mat), "w", encoding="utf-8") as f:
        for pi in range(len(malla["primitives"])):
            f.write("newmtl mat%d\nKd 1 1 1\n" % pi)
            if tex: f.write("map_Kd %s/%s\n" % (TEXDIR, tex))
    return len(malla["primitives"])

# destino de cada malla del GLB y la textura de su material (nombre del fichero en 02_texturas)
DESTINO = {
    "PC079_01_body_wholeexport_rig_PC079_01_body": ("cuerpo/cuerpo", "PC079_01_body01"),
    "PC079_01_body_wholeexport_rig_PC079_01_xiuzhang": ("cuerpo/brazalete", "PC079_01_xiuzhang"),
    "PC079_01_face_wholeexport_rig_bs_PC079_01_face": ("cara/cara", "PC079_01_face"),
    "PC079_01_face_wholeexport_rig_bs_PC079_01_eye": ("cara/ojo", "PC079_01_eye"),
    "PC079_01_face_wholeexport_rig_bs_PC079_01_eyelid": ("cara/parpado", "PC079_01_face"),
    "PC079_01_hair_wholeexport_rig_PC079_01_hair": ("pelo/pelo", "PC079_01_hair"),
    "PC079_01_body_wholeexport_rig_PC079_01_qiang": ("armas/lanza", "PC079_01_qiang"),
    "PC079_01_body_wholeexport_rig_PC079_01_qiangtao": ("armas/lanza_vaina", "PC079_01_qiangtao"),
    "PC079_01_gun_02_wholeexport_rig_wq_makpon_gun_02": ("armas/pistola", "Standard"),
}
# textura real de cada material del GLB (nombre del fichero, sin extension, tal como se guardo)
def textura_de(j, mat_i):
    mat = j["materials"][mat_i]
    idx = mat.get("pbrMetallicRoughness", {}).get("baseColorTexture", {}).get("index")
    if idx is None:
        return None
    img = j["textures"][idx].get("source")
    if img is None:
        return None
    im = j["images"][img]
    # las texturas van embebidas en el GLB: el nombre viene en "name"; si no, se usa el del mapa
    nombre = im.get("uri") or im.get("name")
    if not nombre:
        return None
    nombre = os.path.basename(nombre)
    return nombre if nombre.lower().endswith(".png") else nombre + ".png"

if __name__ == "__main__":
    j0, _, _ = leer(GLB)
    indice = {m["name"]: i for i, m in enumerate(j0["meshes"])}
    for malla, (sub, _) in DESTINO.items():
        if malla not in indice:
            print("  AVISO: el GLB no tiene %s" % malla); continue
        mat0 = j0["meshes"][indice[malla]]["primitives"][0].get("material")
        tex = (textura_de(j0, mat0) if mat0 is not None else None) or (DESTINO[malla][1] + ".png")
        n = escribir(malla, os.path.join(RAIZ, sub + ".obj"), tex)
        print("  %-22s %d submalla(s)  textura: %s" % (sub, n, tex))
