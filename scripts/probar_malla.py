"""Comprueba que ibm = inversa(mundo_hueso) * mundo_malla.

El IBM que trae la malla no es solo la inversa del hueso en reposo: lleva incorporada la
transformacion del OBJETO MALLA. Si es asi, mundo(hueso) * ibm debe dar lo mismo para todos los
huesos de la pieza (la matriz de la malla), y con eso puedo calcular el IBM de CUALQUIER hueso del
esqueleto completo, aunque la lista del renderer no lo incluya.
"""
import json
import os

import numpy as np

RAIZ = r"C:\Users\Lukas\p5x-datamining"
DUMP = os.path.join(RAIZ, "_dl", "kotone_dump")
PREFAB = os.path.join(RAIZ, "unity_com", "esqueleto_prefab.json")

PARTES = ["PC079_01_body_wholeexport_rig_PC079_01_body",
          "PC079_01_face_wholeexport_rig_bs_PC079_01_face",
          "PC079_01_face_wholeexport_rig_bs_PC079_01_eye",
          "PC079_01_face_wholeexport_rig_bs_PC079_01_eyelid",
          "PC079_01_hair_wholeexport_rig_PC079_01_hair",
          "PC079_01_body_wholeexport_rig_PC079_01_qiangtao",
          "PC079_01_body_wholeexport_rig_PC079_01_xiuzhang"]


def mat_trs(pos, rot, esc, trasponer_rot=False):
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


huesos = json.load(open(PREFAB, encoding="utf-8"))["huesos"]
mapa = {h["nombre"]: i for i, h in enumerate(huesos)}

for trasponer in (False, True):
    cache = {}

    def mundo(i):
        if i in cache:
            return cache[i]
        h = huesos[i]
        L = mat_trs(h["pos"], h["rot"], h["esc"], trasponer)
        p = mapa.get(h.get("padre"))
        cache[i] = (mundo(p) @ L) if p is not None else L
        return cache[i]

    print(f"\n================ trasponer_rot={trasponer} ================")
    for parte in PARTES:
        f = os.path.join(DUMP, parte + ".json")
        if not os.path.exists(f):
            continue
        meta = json.load(open(f, encoding="utf-8"))
        lista = meta["lista_huesos"]
        ibm = np.fromfile(os.path.join(DUMP, parte + ".ibm.bin"), dtype="<f4").reshape(-1, 4, 4)
        mallas = []
        for k, h in enumerate(lista):
            nom = h.get("nombre")
            if not nom or nom not in mapa or k >= len(ibm):
                continue
            mallas.append(mundo(mapa[nom]) @ np.linalg.inv(ibm[k]))
        if not mallas:
            continue
        ref = mallas[0]
        peor_malla = max(float(np.abs(mm - ref).max()) for mm in mallas)
        # posicion de la malla y error al reconstruir todos los ibm con esa matriz
        peor_ibm = 0.0
        for k, h in enumerate(lista):
            nom = h.get("nombre")
            if not nom or nom not in mapa or k >= len(ibm):
                continue
            calc = np.linalg.inv(mundo(mapa[nom]) @ np.linalg.inv(ibm[k])) @ np.linalg.inv(ibm[k])
            calc = np.linalg.inv(mundo(mapa[nom]) @ np.linalg.inv(ibm[k]))
            peor_ibm = max(peor_ibm, float(np.abs(calc - ibm[k]).max()))
        print(f"  {parte[:46]:46s} dispersion de la matriz de malla: {peor_malla:.6f}   "
              f"posicion malla: {np.round(ref[:3,3], 4)}   error ibm: {peor_ibm:.6f}")
    cache.clear()