"""Valida el esqueleto completo del prefab contra las inversas de bind que trae el juego.

Idea: la inversa de bind que trae la malla para el hueso i es inversa(mundo_en_reposo_i). Si
reconstruyo el reposo recorriendo la jerarquia del prefab (padre * local) y las dos coinciden,
entonces el esqueleto del prefab sirve para reemplazar la lista parcial del renderer (que deja
31 huesos sin padre) sin mover nada.

Uso: python validar_esqueleto.py
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
          "PC079_01_hair_wholeexport_rig_PC079_01_hair"]


def mat_trs(pos, rot, esc):
    m = np.eye(4, dtype=np.float64)
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
    m[:3, :3] = r * np.array(esc, dtype=np.float64)
    m[:3, 3] = pos
    return m


def main():
    huesos = json.load(open(PREFAB, encoding="utf-8"))["huesos"]
    mapa = {h["nombre"]: i for i, h in enumerate(huesos)}
    print(f"prefab: {len(huesos)} transforms")
    sin_padre = [h["nombre"] for h in huesos if h.get("padre") is None]
    print(f"raices del prefab: {sin_padre}")

    cache = {}

    def mundo(i):
        if i in cache:
            return cache[i]
        h = huesos[i]
        L = mat_trs(h["pos"], h["rot"], h["esc"])
        p = mapa.get(h.get("padre"))
        cache[i] = (mundo(p) @ L) if p is not None else L
        return cache[i]

    print("\n-- comparacion: inversa(mundo del prefab)  vs  ibm del volcado --")
    for parte in PARTES:
        f = os.path.join(DUMP, parte + ".json")
        if not os.path.exists(f):
            print(f"   {parte}: sin volcado")
            continue
        meta = json.load(open(f, encoding="utf-8"))
        lista = meta["lista_huesos"]
        ibm = np.fromfile(os.path.join(DUMP, parte + ".ibm.bin"), dtype="<f4").reshape(-1, 4, 4)
        peor, peor_h = 0.0, None
        faltan = 0
        for k, h in enumerate(lista):
            nom = h.get("nombre")
            if not nom or nom not in mapa or k >= len(ibm):
                faltan += 1
                continue
            calc = np.linalg.inv(mundo(mapa[nom]))
            d = float(np.abs(calc - ibm[k]).max())
            if d > peor:
                peor, peor_h = d, nom
        print(f"   {parte[:46]:46s} huesos {len(lista):3d}  sin nombre/en prefab: {faltan}  "
              f"peor diferencia: {peor:.6f} ({peor_h})")

    print("\n-- posiciones de reposo de algunos huesos (mundo, en metros) --")
    for nom in ["Bip01 Pelvis", "Bip01 Spine", "Bip01 Head", "Bip01 L Hand", "Bip01 L Foot",
                "Bip01 L Thigh", "BN_head"]:
        if nom in mapa:
            t = mundo(mapa[nom])[:3, 3]
            print(f"   {nom:16s} {np.round(t, 4)}")
        else:
            print(f"   {nom:16s} (no esta)")

    # el prefab trae huesos que la lista del cuerpo no tenia
    cuerpo = json.load(open(os.path.join(DUMP, PARTES[0] + ".json"), encoding="utf-8"))
    del_cuerpo = {h.get("nombre") for h in cuerpo["lista_huesos"] if h.get("nombre")}
    intermedios = sorted(del_cuerpo ^ set(mapa))
    print(f"\nhuesos del prefab que NO estaban en la lista del renderer: {len(set(mapa) - del_cuerpo)}")
    print("   ejemplos:", sorted(set(mapa) - del_cuerpo)[:15])


if __name__ == "__main__":
    main()