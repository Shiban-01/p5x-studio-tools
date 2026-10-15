"""Verifica los GLB generados: (1) parsea el contenedor y comprueba que los accesores y los
bufferViews cuadran con las mallas esperadas; (2) rasteriza el modelo completo a PNG para
comprobar con los ojos que es una figura humanoide y que la orientacion es correcta.

Parsear el GLB aqui, desde cero, ya es una prueba de que el fichero es coherente: si los
accesores apuntan mal, la lectura de vertices revienta o da basura.
"""
import json
import os
import struct
import sys
import numpy as np

RAIZ = r"C:\Users\Lukas\p5x-datamining"
DUMP = os.path.join(RAIZ, "_dl", "kotone_dump")
PKG = os.path.join(RAIZ, "kotone_shiomi")

COMP = {5120: ("b", 1), 5121: ("B", 1), 5122: ("h", 2), 5123: ("H", 2), 5125: ("I", 4), 5126: ("f", 4)}
NCOMP = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


def leer_glb(ruta):
    with open(ruta, "rb") as f:
        datos = f.read()
    assert datos[:4] == b"glTF", "no es un GLB (falta la firma)"
    ver, total = struct.unpack("<II", datos[4:12])
    assert ver == 2, f"version glTF {ver}"
    assert total == len(datos), f"el tamano declarado ({total}) no es el real ({len(datos)})"
    off, js, bin_ = 12, None, None
    while off < len(datos):
        largo, tipo = struct.unpack("<II", datos[off:off + 8])
        cuerpo = datos[off + 8: off + 8 + largo]
        if tipo == 0x4E4F534A:
            js = json.loads(cuerpo.decode("utf-8"))
        elif tipo == 0x004E4942:
            bin_ = cuerpo
        off += 8 + largo
    assert js is not None, "sin chunk JSON"
    return js, bin_


def acc_leer(js, bin_, i):
    a = js["accessors"][i]
    bv = js["bufferViews"][a["bufferView"]]
    fmt, tam = COMP[a["componentType"]]
    n = NCOMP[a["type"]]
    crudo = bin_[bv.get("byteOffset", 0) + a.get("byteOffset", 0):]
    arr = np.frombuffer(crudo, dtype=np.dtype(fmt).newbyteorder("<"), count=a["count"] * n)
    return arr.reshape(-1, n) if n > 1 else arr


def validar(ruta, partes_esperadas=None):
    js, bin_ = leer_glb(ruta)
    err = []
    instancias = []
    _recorrer(js, js["scenes"][0]["nodes"], np.eye(4), instancias)
    n_parts = len(instancias)
    vistos = 0
    for _M, im in instancias:
        malla = js["meshes"][im]
        for pr in malla["primitives"]:
            pos = acc_leer(js, bin_, pr["attributes"]["POSITION"])
            n = len(pos)
            vistos += n
            for k, idx in pr["attributes"].items():
                if acc_leer(js, bin_, idx).shape[0] != n:
                    err.append(f"{malla['name']}: {k} con {acc_leer(js, bin_, idx).shape[0]} != {n}")
            tri = acc_leer(js, bin_, pr["indices"])
            if tri.size % 3:
                err.append(f"{malla['name']}: indices no multiplo de 3")
            if tri.max(initial=0) >= n:
                err.append(f"{malla['name']}: indice {tri.max()} fuera de rango ({n} vertices)")
            for t in pr.get("targets", []):
                d = acc_leer(js, bin_, t["POSITION"])
                if len(d) != n:
                    err.append(f"{malla['name']}: morph con {len(d)} != {n}")
    # pieles
    for i, skin in enumerate(js.get("skins", [])):
        ibm = acc_leer(js, bin_, skin["inverseBindMatrices"])
        if len(ibm) != len(skin["joints"]):
            err.append(f"skin {i}: {len(ibm)} matrices para {len(skin['joints'])} huesos")
    # imagenes
    for im in js.get("images", []):
        bv = js["bufferViews"][im["bufferView"]]
        d = bin_[bv.get("byteOffset", 0): bv.get("byteOffset", 0) + bv["byteLength"]]
        if d[:8] != b"\x89PNG\r\n\x1a\n":
            err.append(f"imagen {im.get('name')}: no es un PNG")
    print(f"{os.path.basename(ruta):34s} nodos_malla={n_parts:2d} vertices={vistos:6d} "
          f"skins={len(js.get('skins', [])):2d} imagenes={len(js.get('images', [])):2d} "
          f"morphs={sum(len(p.get('targets', [])) for m in js['meshes'] for p in m['primitives']):2d} "
          f"-> {'OK' if not err else 'ERRORES: ' + '; '.join(err[:3])}")
    return js, bin_, err


def _trs(n):
    M = np.eye(4, dtype=np.float64)
    if "translation" in n:
        M[:3, 3] = n["translation"]
    if "scale" in n:
        M[:3, :3] = np.diag(n["scale"])
    if "rotation" in n:
        x, y, z, w = n["rotation"]
        R = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                      [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                      [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
        M[:3, :3] = R @ M[:3, :3]
    return M


def _recorrer(js, indices, M, salida):
    for i in indices:
        n = js["nodes"][i]
        Mi = M @ _trs(n)
        if "mesh" in n:
            salida.append((Mi, n["mesh"]))
        _recorrer(js, n.get("children", []), Mi, salida)


def rasterizar(js, bin_, ruta_png, ancho=560, alto=760):
    """Rasteriza simple (z-buffer, color plano por pieza) desde el frente (-Z), en la orientacion
    del glTF: X derecha, Y arriba. Sirve para comprobar que hay una figura humanoide."""
    img = np.zeros((alto, ancho, 3), dtype=np.uint8)
    zbuf = np.full((alto, ancho), -1e9, dtype=np.float32)
    # primero: encuadre global a partir del cuerpo
    instancias = []
    _recorrer(js, js["scenes"][0]["nodes"], np.eye(4), instancias)
    todos = []
    for M, im in instancias:
        for pr in js["meshes"][im]["primitives"]:
            v = acc_leer(js, bin_, pr["attributes"]["POSITION"]).astype(np.float64)
            todos.append(v @ M[:3, :3].T + M[:3, 3])
    V = np.vstack(todos)
    lo, hi = V.min(axis=0), V.max(axis=0)
    print(f"  bounds del modelo: min={np.round(lo,3)} max={np.round(hi,3)} "
          f"(alto={hi[1]-lo[1]:.2f} m)")
    cen = (lo + hi) / 2
    esc = min(ancho / (hi[0] - lo[0]) * 0.85, alto / (hi[1] - lo[1]) * 0.9)
    paleta = [(230, 200, 170), (200, 165, 205), (235, 195, 90), (150, 170, 200), (200, 90, 90),
              (120, 190, 160), (220, 220, 220), (160, 140, 120), (100, 100, 140)]
    ip = 0
    for M, im in instancias:
        color = paleta[ip % len(paleta)]
        ip += 1
        for pr in js["meshes"][im]["primitives"]:
            v = (acc_leer(js, bin_, pr["attributes"]["POSITION"]).astype(np.float64)
                 @ M[:3, :3].T + M[:3, 3])
            t = acc_leer(js, bin_, pr["indices"]).reshape(-1, 3)
            # proyeccion ortografica frontal: x derecha, y arriba
            px = (v[:, 0] - cen[0]) * esc + ancho / 2
            py = alto / 2 - (v[:, 1] - cen[1]) * esc
            pz = v[:, 2]
            for tri in t:
                x = px[tri]; y = py[tri]; z = pz[tri]
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
                if mejor.any():
                    img[y0:y1 + 1, x0:x1 + 1][mejor] = color
                    sub[mejor] = zz[mejor]
    fondo = np.all(img == 0, axis=2)
    img[fondo] = (18, 18, 22)
    from PIL import Image
    Image.fromarray(img).save(ruta_png)
    print(f"  rasterizado -> {ruta_png}")


if __name__ == "__main__":
    glbs = sorted(os.listdir(os.path.join(PKG, "01_modelo", "glb")))
    print("=== validacion estructural ===")
    for f in glbs:
        validar(os.path.join(PKG, "01_modelo", "glb", f))
    print("\n=== rasterizado del modelo completo (verificacion visual) ===")
    js, bin_, _ = validar(os.path.join(PKG, "01_modelo", "glb", "Kotone_Shiomi_completo.glb"))
    rasterizar(js, bin_, os.path.join(RAIZ, "_dl", "kotone_glb_vista.png"))
