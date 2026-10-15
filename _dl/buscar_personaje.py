"""Busca el bundle de los sprites de un personaje por su nombre en pinyin, en el assetmap."""
import re
import sys
from collections import Counter
from pathlib import Path

MAPA = Path(r"C:\Users\Lukas\p5x-datamining\game_dump\fileContentOut\Bundles\Windows\105\assetMapName.txt")
G = Path(r"C:\Users\Lukas\Downloads\P5X\Client\OuterPackage\Bundles\Windows")

nombre = sys.argv[1] if len(sys.argv) > 1 else "xiachuanling"
d = MAPA.read_bytes()
cadenas = [s.decode("ascii", "ignore") for s in re.findall(rb"[\x20-\x7e]{3,120}", d)]

hits = [(i, s) for i, s in enumerate(cadenas) if nombre in s]
print("coincidencias con %s: %d" % (nombre, len(hits)))
bundles = Counter()
for i, s in hits:
    for j in (i - 1, i + 1):
        if 0 <= j < len(cadenas) and cadenas[j].endswith(".bundle"):
            bundles[cadenas[j]] += 1
print("bundles asociados:")
for b, n in bundles.most_common(12):
    ruta = list(G.rglob(b))
    print("   %-46s x%-4d %s" % (b, n, ruta[0].parent.name + "/" if ruta else "(no esta en disco)"))

print()
print("=== nombres de asset que contienen el personaje ===")
for i, s in hits[:20]:
    print("   ", s[:70])