"""Renderiza los GLB de Kotone y sus armas (rasterizador propio, sin dependencias 3D).

Las armas son DOS PISTOLAS y su funda, no una lanza: la malla del juego se llama `PC079_01_qiang`
(枪 = pistola), su funda `PC079_01_qiangtao` (枪套 = funda) y la segunda `wq_makpon_gun_02`.

Sirve para dos cosas: (1) generar las imagenes de vista previa del paquete; (2) COMPROBAR las
coordenadas UV: si estan mal, la textura sale repartida al azar por la cara y se ve a la legua.

Lee el GLB a mano (contenedor, accesores, materiales, imagenes embebidas), aplica la jerarquia
de nodos y rasteriza con z-buffer, interpolando la UV por pixel y muestreando la textura.
Sombreado simple (lambert + ambiente) para que se distingan los volumenes.

Acepta VARIOS GLB en la misma pasada: cada pieza del paquete (cuerpo, armas) viene con el esqueleto
completo y su malla en la posicion de reposo, asi que superponerlos los alinea sin tocar nada.

Uso:  python scripts/preview_modelos.py
"""
import json
import os
import struct
import numpy as np
from PIL import Image

RAIZ = r"C:\Users\Lukas\p5x-datamining"
GLB_DIR = os.path.join(RAIZ, "kotone_shiomi", "01_model", "glb")
SAL = os.path.join(RAIZ, "kotone_shiomi", "preview")
COMP = {5120: "b", 5121: "B", 5122: "h", 5123: "H", 5125: "I", 5126: "f"}
NC = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


def leer_glb(ruta):
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


def cargar_texturas(js, bin_):
    tex = {}
    for i, im in enumerate(js.get("images", [])):
        bv = js["bufferViews"][im["bufferView"]]
        d = bin_[bv.get("byteOffset", 0): bv.get("byteOffset", 0) + bv["byteLength"]]
        tex[i] = np.array(Image.open(__import__("io").BytesIO(d)).convert("RGBA"))
    return tex


def rasterizar(fuentes, salida, yaw=0.0, pitch=0.0, ancho=620, alto=900):
    """fuentes: lista de (js, bin_). Se dibujan todas juntas, en su espacio comun."""
    cy, sy = np.cos(yaw), np.sin(yaw)
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    cp, sp = np.cos(pitch), np.sin(pitch)
    Rx = np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]])
    R = Rx @ Ry

    piezas = []
    todos = []
    sin_textura = 0
    for js, bin_ in fuentes:
        inst = []
        recorrer(js, js["scenes"][0]["nodes"], np.eye(4), inst)
        texs = cargar_texturas(js, bin_)
        for M, im in inst:
            for pr in js["meshes"][im]["primitives"]:
                p = acc(js, bin_, pr["attributes"]["POSITION"]).astype(np.float64)
                n = acc(js, bin_, pr["attributes"]["NORMAL"]).astype(np.float64)
                uv = acc(js, bin_, pr["attributes"]["TEXCOORD_0"]).astype(np.float64)
                t = acc(js, bin_, pr["indices"]).reshape(-1, 3)
                p = p @ M[:3, :3].T + M[:3, 3]
                n = n @ np.linalg.inv(M[:3, :3]).T
                p = p @ R.T
                n = n @ R.T
                mat = js["materials"][pr["material"]] if "material" in pr else None
                img = None
                if mat:
                    b = mat.get("pbrMetallicRoughness", {}).get("baseColorTexture")
                    if b:
                        img = texs.get(js["textures"][b["index"]]["source"])
                if img is None:
                    sin_textura += 1
                piezas.append({"p": p, "n": n, "uv": uv, "t": t, "img": img,
                               "nombre": mat["name"] if mat else "sin material"})
                todos.append(p)
    V = np.vstack(todos)
    lo, hi = V.min(axis=0), V.max(axis=0)
    cen = (lo + hi) / 2
    esc = min(ancho / max(hi[0] - lo[0], 1e-6) * 0.8, alto / max(hi[1] - lo[1], 1e-6) * 0.92)
    print(f"  yaw={np.degrees(yaw):6.1f}  alto={hi[1]-lo[1]:.2f}m  ancho={hi[0]-lo[0]:.2f}m  "
          f"fondo={hi[2]-lo[2]:.2f}m  piezas={len(piezas)}")

    img_out = np.zeros((alto, ancho, 4), dtype=np.float64)
    img_out[..., 3] = 1.0
    fondo = np.array([24, 24, 28]) / 255.0
    img_out[..., :3] = fondo
    zbuf = np.full((alto, ancho), -1e9)
    luz = np.array([0.35, 0.55, 0.75])
    luz /= np.linalg.norm(luz)
    for pz in piezas:
        p, n, uv, t, img = pz["p"], pz["n"], pz["uv"], pz["t"], pz["img"]
        px = (p[:, 0] - cen[0]) * esc + ancho / 2
        py = alto / 2 - (p[:, 1] - cen[1]) * esc
        pzc = p[:, 2]
        for tri in t:
            x, y, z = px[tri], py[tri], pzc[tri]
            x0, x1 = int(max(0, np.floor(x.min()))), int(min(ancho - 1, np.ceil(x.max())))
            y0, y1 = int(max(0, np.floor(y.min()))), int(min(alto - 1, np.ceil(y.max())))
            if x1 < x0 or y1 < y0:
                continue
            area = (x[1] - x[0]) * (y[2] - y[0]) - (x[2] - x[0]) * (y[1] - y[0])
            if abs(area) < 1e-9:
                continue
            xs, ys = np.meshgrid(np.arange(x0, x1 + 1), np.arange(y0, y1 + 1))
            w0 = ((x[1] - xs) * (y[2] - ys) - (x[2] - xs) * (y[1] - ys)) / area
            w1 = ((x[2] - xs) * (y[0] - ys) - (x[0] - xs) * (y[2] - ys)) / area
            w2 = 1 - w0 - w1
            dentro = (w0 >= -0.002) & (w1 >= -0.002) & (w2 >= -0.002)
            if not dentro.any():
                continue
            zz = w0 * z[0] + w1 * z[1] + w2 * z[2]
            sub = zbuf[y0:y1 + 1, x0:x1 + 1]
            mejor = dentro & (zz > sub)
            if not mejor.any():
                continue
            nn = (w0[..., None] * n[tri[0]] + w1[..., None] * n[tri[1]] + w2[..., None] * n[tri[2]])
            nn /= np.maximum(np.linalg.norm(nn, axis=2, keepdims=True), 1e-9)
            diff = np.clip(nn @ luz, 0, 1)
            color = (0.62 + 0.45 * diff)[..., None] * 0.96 + 0.06
            if img is not None:
                uu = (w0 * uv[tri[0], 0] + w1 * uv[tri[1], 0] + w2 * uv[tri[2], 0]) % 1.0
                vv = (w0 * uv[tri[0], 1] + w1 * uv[tri[1], 1] + w2 * uv[tri[2], 1]) % 1.0
                h, w = img.shape[:2]
                sx = np.clip((uu * (w - 1)).astype(int), 0, w - 1)
                sy = np.clip((vv * (h - 1)).astype(int), 0, h - 1)
                texel = img[sy, sx].astype(np.float64) / 255.0
                a = texel[..., 3:4]
                rgb = texel[..., :3] * color
                mezcla = (rgb * a + fondo * (1 - a))
            else:
                mezcla = np.broadcast_to(np.array([0.75, 0.25, 0.85]), (*color.shape[:2], 3))
            dst = img_out[y0:y1 + 1, x0:x1 + 1]
            m = mejor[..., None]
            dst[..., :3] = np.where(m, mezcla, dst[..., :3])
            sub[mejor] = zz[mejor]
    Image.fromarray((np.clip(img_out[..., :3], 0, 1) * 255).astype(np.uint8)).save(salida)
    print(f"  -> {os.path.basename(salida)}   (piezas sin textura: {sin_textura})")


def hoja_de_contacto(ficheros, salida, esc=0.62):
    ims = [Image.open(os.path.join(SAL, f)) for f in ficheros]
    ims = [i.resize((int(i.width * esc), int(i.height * esc))) for i in ims]
    W = sum(i.width for i in ims)
    H = max(i.height for i in ims)
    hoja = Image.new("RGB", (W, H), (18, 18, 22))
    x = 0
    for i in ims:
        hoja.paste(i, (x, 0))
        x += i.width
    hoja.save(os.path.join(SAL, salida))
    print(f"  -> {salida}  ({W}x{H})")


if __name__ == "__main__":
    os.makedirs(SAL, exist_ok=True)
    kotone = leer_glb(os.path.join(GLB_DIR, "Kotone_Shiomi_full.glb"))
    armas = {n: leer_glb(os.path.join(GLB_DIR, "Kotone_Shiomi_weapon_%s.glb" % n))
             for n in ("gun_01", "gun_holster", "gun_02")}

    print("=== Kotone completo (4 vistas) ===")
    rasterizar([kotone], os.path.join(SAL, "01_front.png"), yaw=0.0)
    rasterizar([kotone], os.path.join(SAL, "02_right_side.png"), yaw=np.radians(-90))
    rasterizar([kotone], os.path.join(SAL, "03_three_quarter.png"), yaw=np.radians(-35), pitch=np.radians(-6))
    rasterizar([kotone], os.path.join(SAL, "04_back.png"), yaw=np.radians(180))

    print("\n=== primer plano de la cara ===")
    im = Image.open(os.path.join(SAL, "01_front.png"))
    w, h = im.size
    im.crop((int(w * 0.32), int(h * 0.01), int(w * 0.68), int(h * 0.20))).resize(
        (int(w * 0.36 * 2.2), int(h * 0.19 * 2.2))).save(os.path.join(SAL, "05_face_closeup.png"))
    print("  -> 05_face_closeup.png")

    print("\n=== hoja de contacto de Kotone ===")
    hoja_de_contacto(["01_front.png", "03_three_quarter.png", "02_right_side.png", "04_back.png"],
                     "00_contact_sheet.png")

    print("\n=== armas sueltas ===")
    for idx, n in ((6, "gun_01"), (7, "gun_holster"), (8, "gun_02")):
        rasterizar([armas[n]], os.path.join(SAL, "%02d_weapon_%s.png" % (idx, n)),
                   yaw=np.radians(-30), pitch=np.radians(-8), ancho=700, alto=560)
    hoja_de_contacto(["06_weapon_gun_01.png", "07_weapon_gun_holster.png", "08_weapon_gun_02.png"],
                     "09_weapons_contact_sheet.png", esc=0.72)

    print("\n=== Kotone con el arma (como viene en el paquete) ===")
    rasterizar([kotone, armas["gun_01"], armas["gun_holster"]],
               os.path.join(SAL, "10_kotone_with_gun_01.png"),
               yaw=np.radians(-35), pitch=np.radians(-6))
    # detalle de la cadera: es donde se ve la pistola enfundada, o sea "Kotone con su arma"
    print("\n=== detalle de la cadera ===")
    im = Image.open(os.path.join(SAL, "03_three_quarter.png"))
    w, h = im.size
    im.crop((int(w * 0.44), int(h * 0.28), int(w * 0.86), int(h * 0.54))).resize(
        (int(w * 0.42 * 2.4), int(h * 0.26 * 2.4))).save(os.path.join(SAL, "11_hip_detail.png"))
    print("  -> 11_hip_detail.png")