"""Sonda: como se llaman de verdad las texturas dentro de cada familia de bundles.

No extrae nada: solo lee la tabla de objetos de unos cuantos bundles de cada prefijo para ver
que nombres hay (y su contenedor), que es lo que decide si se pueden clasificar por carpetas.
"""
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, r"C:\Users\Lukas\p5x-datamining\p5x_studio")
from p5x_studio import motor, ajustes

G = Path(r"C:\Users\Lukas\Downloads\P5X\Client\OuterPackage\Bundles\Windows")

# un par de bundles de cada familia
por_familia = defaultdict(list)
for p in sorted(G.rglob("*.bundle")):
    fam = p.name.split("_")[0]
    if len(por_familia[fam]) < 2:
        por_familia[fam].append(p)
    if len(por_familia) >= 14 and all(len(v) >= 2 for v in por_familia.values()):
        break

print("familias:", {k: len(v) for k, v in por_familia.items()})
print()
for fam in sorted(por_familia):
    for p in por_familia[fam]:
        rel = str(p.relative_to(G)).replace("\\", "/")
        try:
            recursos = motor.abrir_bundle(rel)
        except Exception as e:
            print("  %-22s FALLA %s: %s" % (rel, type(e).__name__, e))
            continue
        texturas = [r for r in recursos if "tex" in str(r[1]).lower() or "sprite" in str(r[1]).lower()]
        print("=== %-34s %d recursos, %d texturas ===" % (rel, len(recursos), len(texturas)))
        for n, tip, cont, tam in texturas[:8]:
            print("      %-38s %-10s %8s  %s" % (str(n)[:38], tip, tam, str(cont)[:70]))
        if len(texturas) > 8:
            print("      ... y %d mas" % (len(texturas) - 8))