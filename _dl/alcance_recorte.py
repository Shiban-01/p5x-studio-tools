"""Alcance del recorte en la carpeta del bulk: cuantas texturas necesitan arreglo.

El censo guarda una fila por PNG con su tipo (Sprite / Texture2D) y sus bytes. Un sprite recortado
pesa menos que su textura entera, asi que comparando los pares del MISMO nombre se ve cuantos hay
recortados y cuanto pesa el problema. Aqui solo se mide: no se toca la carpeta del bulk.
"""
import json
from collections import Counter, defaultdict
from pathlib import Path

DL = Path(r"C:\Users\Lukas\p5x-datamining\_dl")
censo = json.loads((DL / "censo_texturas.json").read_text(encoding="utf-8"))
filas = censo["filas"]
print("filas del censo: %d" % len(filas))

por_nombre = defaultdict(list)
for f in filas:
    por_nombre[f["nombre"]].append(f)

tipos = Counter(f["tipo"] for f in filas)
print("tipos:", dict(tipos))

solo_uno = par_igual = par_menor = par_mayor = 0
peor = []
for nombre, grupo in por_nombre.items():
    if len(grupo) == 1:
        solo_uno += 1
        continue
    pesos = sorted(g["bytes"] for g in grupo)
    if pesos[0] == pesos[-1]:
        par_igual += 1
    else:
        par_menor += 1
        peor.append((pesos[-1] / max(pesos[0], 1), nombre, pesos))

print()
print("nombres con UN solo PNG:            %d" % solo_uno)
print("nombres con varios PNG del mismo peso: %d" % par_igual)
print("nombres con varios PNG y pesos distintos (candidatos a recorte): %d" % par_menor)
peor.sort(reverse=True)
print()
print("los 12 con mas diferencia de peso (el pequeno es el recortado):")
for ratio, nombre, pesos in peor[:12]:
    print("   %-52s %8d vs %8d B  (x%.1f)" % (nombre[:52], pesos[0], pesos[-1], ratio))

print()
print("nombres totales en el censo: %d" % len(por_nombre))