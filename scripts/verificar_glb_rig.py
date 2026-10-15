#!/usr/bin/env python3
"""Verifica un GLB riggeado sin depender de numpy: cuenta armaduras, huesos por armadura, mallas y
vertices con peso, y comprueba que los accesores cuadran con sus bufferViews.

Es la prueba de que el fichero se puede abrir: si los accesores apuntan mal, leer los vertices
revienta o da longitudes incoherentes.

Uso: python verificar_glb_rig.py <fichero.glb>
"""
import json
import struct
import sys
from pathlib import Path

COMP = {5120: ("b", 1), 5121: ("B", 1), 5122: ("h", 2), 5123: ("H", 2), 5125: ("I", 4), 5126: ("f", 4)}
NCOMP = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


def leer_glb(ruta):
    datos = Path(ruta).read_bytes()
    assert datos[:4] == b"glTF", "no es un GLB (falta la firma)"
    ver, total = struct.unpack("<II", datos[4:12])
    assert ver == 2, "version glTF %d" % ver
    assert total == len(datos), "el tamano declarado (%d) no es el real (%d)" % (total, len(datos))
    off, js, binc = 12, None, None
    while off < len(datos):
        largo, tipo = struct.unpack("<II", datos[off:off + 8])
        cuerpo = datos[off + 8:off + 8 + largo]
        if tipo == 0x4E4F534A:
            js = json.loads(cuerpo.decode("utf-8"))
        elif tipo == 0x004E4942:
            binc = cuerpo
        off += 8 + largo
    assert js is not None, "sin chunk JSON"
    return js, binc


def acc(js, binc, i):
    a = js["accessors"][i]
    bv = js["bufferViews"][a["bufferView"]]
    fmt, tam = COMP[a["componentType"]]
    n = NCOMP[a["type"]]
    ini = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    fin = ini + a["count"] * n * tam
    assert fin <= len(binc), "accessor %d se sale del buffer" % i
    return list(struct.unpack("<%d%s" % (a["count"] * n, fmt), binc[ini:fin])), n


def main(ruta):
    js, binc = leer_glb(ruta)
    errores = []
    skins = js.get("skins", [])
    mallas = js.get("meshes", [])
    print("fichero: %s  (%.2f MB)" % (Path(ruta).name, Path(ruta).stat().st_size / 1e6))
    print("armaduras: %d" % len(skins))
    huesos_por_skin = []
    for i, s in enumerate(skins):
        ibm, n = acc(js, binc, s["inverseBindMatrices"])
        n_matrices = len(ibm) // 16
        huesos_por_skin.append(len(s["joints"]))
        if len(s["joints"]) != n_matrices:
            errores.append("skin %d: %d huesos pero %d matrices" % (i, len(s["joints"]), n_matrices))
    if huesos_por_skin:
        print("huesos por armadura: %s" % sorted(set(huesos_por_skin)))
    print("mallas: %d" % len(mallas))
    con_pesos = 0
    for m in mallas:
        for pr in m["primitives"]:
            at = pr["attributes"]
            ok_j = "JOINTS_0" in at
            ok_w = "WEIGHTS_0" in at
            n_verts = js["accessors"][at["POSITION"]]["count"]
            if ok_w:
                w, n = acc(js, binc, at["WEIGHTS_0"])
                con_peso = sum(1 for i in range(0, len(w), 4) if sum(w[i:i + 4]) > 1e-6)
            else:
                con_peso = 0
            if ok_j:
                j, _ = acc(js, binc, at["JOINTS_0"])
            else:
                j = []
            if ok_j and ok_w and con_peso > 0:
                con_pesos += 1
            if not (ok_j and ok_w):
                errores.append("%s: falta JOINTS_0/WEIGHTS_0" % m["name"])
            if ok_w and con_peso != n_verts:
                errores.append("%s: %d de %d vertices con peso" % (m["name"], con_peso, n_verts))
            if j and max(j) >= (max(huesos_por_skin) if huesos_por_skin else 0):
                errores.append("%s: indice de hueso %d fuera de rango" % (m["name"], max(j)))
            print("  malla %-46s verts %6d  JOINTS_0=%s WEIGHTS_0=%s  con peso %6d"
                  % (m["name"][-46:], n_verts, ok_j, ok_w, con_peso))
    print("primitivas con pesos: %d" % con_pesos)
    print("materiales: %d  texturas: %d  imagenes: %d" % (len(js.get("materials", [])),
                                                          len(js.get("textures", [])),
                                                          len(js.get("images", []))))
    for im in js.get("images", []):
        bv = js["bufferViews"][im["bufferView"]]
        ini = bv.get("byteOffset", 0)
        if binc[ini:ini + 8] != b"\x89PNG\r\n\x1a\n":
            errores.append("imagen %s: no es un PNG" % im.get("name"))
    if errores:
        print("\nERRORES:\n  " + "\n  ".join(errores[:10]))
        return 1
    print("\nOK: estructura coherente, todas las mallas con pesos.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))