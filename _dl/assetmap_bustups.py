"""Lista los nombres de textura de bust-up de dialogo (changfu) y su bundle, desde el assetmap."""
import re
from pathlib import Path

MAPA = Path(r"C:\Users\Lukas\p5x-datamining\game_dump\fileContentOut\Bundles\Windows\105\assetMapName.txt")
d = MAPA.read_bytes()
cadenas = [s.decode("ascii", "ignore") for s in re.findall(rb"[\x20-\x7e]{3,120}", d)]

# pares (asset, bundle): se guarda el bundle que acompana a cada nombre de asset
pares = []
for i, s in enumerate(cadenas):
    if i + 1 < len(cadenas) and cadenas[i + 1].endswith(".bundle"):
        pares.append((s, cadenas[i + 1]))
print("pares asset/bundle:", len(pares))

con_changfu = [(a, b) for a, b in pares if "changfu" in a.lower()]
print("entradas con changfu:", len(con_changfu))
for a, b in con_changfu[:25]:
    print("   %-44s -> %s" % (a[:44], b))

print()
print("=== nombres de asset con pinta de cuerpo de bust-up (shenti/benti) ===")
for a, b in pares:
    if re.search(r"(shenti|benti|zhengti)$", a, re.I) and "-" in a:
        print("   %-44s -> %s" % (a[:44], b))
        if len([1 for _ in ()]) > 5:
            break