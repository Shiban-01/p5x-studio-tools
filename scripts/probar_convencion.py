"""Prueba variantes de convencion de matriz para casar inversa(mundo) con el ibm del volcado."""
import json
import os

import numpy as np

RAIZ = r"C:\Users\Lukas\p5x-datamining"
DUMP = os.path.join(RAIZ, "_dl", "kotone_dump")
PREFAB = os.path.join(RAIZ, "unity_com", "esqueleto_prefab.json")
PARTE = "PC079_01_body_wholeexport_rig_PC079_01_body"
PARTE2 = "PC079_01_face_wholeexport_rig_bs_PC079_01_face"


def mat_trs(pos, rot, esc, trasponer_rot):
    m = np.eye(4)
    x, y, z, w = rot
    n = x * x + y * y + z * z + w * w
    if n < 1e-12:
        r = np.eye(3)
    else:
        s = 2.0 / n
        r = np.array([
            [1 - s * (y * y + z * z), s * (x * y - z * w), s * (x * z + y * w)],
            [s * (x * y + z * w), 1 - s * (x * x + z * z), s * (y * z - x * w)],
            [s * (x * z - y * w), s * (y * z + x * w), 1 - s * (x * x + y * y)],
        ])
    if trasponer_rot:
        r = r.T
    m[:3, :3] = r * np.array(esc)
    m[:3, 3] = pos
    return m


def probar(huesos, mapa, trasponer_rot, orden):
    cache = {}

    def mundo(i):
        if i in cache:
            return cache[i]
        h = huesos[i]
        L = mat_trs(h["pos"], h["rot"], h["esc"], trasponer_rot)
        p = mapa.get(h.get("padre"))
        if p is None:
            cache[i] = L
        else:
            cache[i] = (mundo(p) @ L) if orden == "padre_L" else (L @ mundo(p))
        return cache[i]

    res = {}
    for parte in (PARTE, PARTE2):
        meta = json.load(open(os.path.join(DUMP, parte + ".json"), encoding="utf-8"))
        ibm = np.fromfile(os.path.join(DUMP, parte + ".ibm.bin"), dtype="<f4").reshape(-1, 4, 4)
        peor = 0.0
        peor_h = None
        for k, h in enumerate(meta["lista_huesos"]):
            nom = h.get("nombre")
            if not nom or nom not in mapa or k >= len(ibm):
                continue
            calc = np.linalg.inv(mundo(mapa[nom]))
            d = float(np.abs(calc - ibm[k]).max())
            if d > peor:
                peor, peor_h = d, nom
        res[parte[:30]] = (peor, peor_h)
    return res


huesos = json.load(open(PREFAB, encoding="utf-8"))["huesos"]
mapa = {h["nombre"]: i for i, h in enumerate(huesos)}
for trasponer in (False, True):
    for orden in ("padre_L", "L_padre"):
        r = probar(huesos, mapa, trasponer, orden)
        print(f"trasponer_rot={trasponer!s:5s} orden={orden:8s} -> " +
              "  ".join(f"{k}: {v[0]:.6f} ({v[1]})" for k, v in r.items()))