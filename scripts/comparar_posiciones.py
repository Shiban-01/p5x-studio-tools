"""Compara las posiciones RELATIVAS de los huesos (prefab vs inversa del ibm del juego).

Las posiciones relativas cancelan la transformacion del objeto malla, asi que si coinciden, la
jerarquia del prefab es la buena y lo unico que faltaba era el orden de encadenado. Ademas lista
los huesos intermedios que la lista del renderer se deja fuera.
"""
import json
import os

import numpy as np

RAIZ = r"C:\Users\Lukas\p5x-datamining"
DUMP = os.path.join(RAIZ, "_dl", "kotone_dump")
PREFAB = os.path.join(RAIZ, "unity_com", "esqueleto_prefab.json")
PARTE = "PC079_01_body_wholeexport_rig_PC079_01_body"

huesos = json.load(open(PREFAB, encoding="utf-8"))["huesos"]
mapa = {h["nombre"]: i for i, h in enumerate(huesos)}
padre_de = {h["nombre"]: h.get("padre") for h in huesos}


def mat_trs(pos, rot, esc):
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
    m[:3, :3] = r * np.array(esc)
    m[:3, 3] = pos
    return m


cache = {}


def mundo(i):
    if i in cache:
        return cache[i]
    h = huesos[i]
    L = mat_trs(h["pos"], h["rot"], h["esc"])
    p = mapa.get(h.get("padre"))
    cache[i] = (mundo(p) @ L) if p is not None else L
    return cache[i]


meta = json.load(open(os.path.join(DUMP, PARTE + ".json"), encoding="utf-8"))
lista = meta["lista_huesos"]
ibm = np.fromfile(os.path.join(DUMP, PARTE + ".ibm.bin"), dtype="<f4").reshape(-1, 4, 4)
nombres = [h.get("nombre") for h in lista]

# huesos validos en ambos lados
pares = []
for k, nom in enumerate(nombres):
    if not nom or nom not in mapa or k >= len(ibm):
        continue
    p_pre = mundo(mapa[nom])[:3, 3]
    p_dum = np.linalg.inv(ibm[k])[:3, 3]
    pares.append((nom, p_pre, p_dum))

print(f"huesos comparables: {len(pares)} de {len(nombres)}")
# desplazamientos relativos al primer hueso comparable
_, p0_pre, p0_dum = pares[0]
peor = 0.0
peor_nom = None
for nom, p_pre, p_dum in pares:
    d = np.abs((p_pre - p0_pre) - (p_dum - p0_dum)).max()
    if d > peor:
        peor, peor_nom = d, nom
print(f"peor diferencia en posiciones RELATIVAS: {peor:.6f} m  ({peor_nom})")

print("\nprimeros 8 huesos: prefab vs juego (relativo)")
for nom, p_pre, p_dum in pares[:8]:
    print(f"   {nom:22s} prefab {np.round(p_pre - p0_pre, 4)}   juego {np.round(p_dum - p0_dum, 4)}")

# cuantos saltos hay entre un hueso y su antecesor que SI esta en la lista
print("\n-- huesos de la lista cuyo padre NO esta en la lista (saltos) --")
saltos = 0
for k, nom in enumerate(nombres):
    if not nom:
        continue
    pa = padre_de.get(nom)
    if pa is not None and pa not in nombres:
        saltos += 1
        if saltos <= 12:
            # subir hasta el primer antecesor que si este
            anc, niveles = pa, 1
            while anc is not None and anc not in nombres:
                anc = padre_de.get(anc)
                niveles += 1
            print(f"   {nom:26s} padre real {pa[:26]:26s} -> antecesor en la lista: {anc}  ({niveles} saltos)")
print(f"   total huesos con padre fuera de la lista: {saltos}")

print("\n-- huesos del prefab ausentes de la lista del cuerpo (intermedios) --")
ausentes = [n for n in mapa if n not in nombres]
print(f"   {len(ausentes)}: {sorted(ausentes)[:20]}")
# cadena del brazo izquierdo
print("\n-- cadena del brazo izquierdo en el prefab --")
n = "Bip01 L Hand"
cad = []
while n and len(cad) < 12:
    cad.append(n)
    n = padre_de.get(n)
print("   " + " <- ".join(cad))