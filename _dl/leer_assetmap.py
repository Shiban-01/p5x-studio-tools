"""Lee el assetMapName.txt (el 'assetmap') y busca donde vive un retrato de dialogo.

El fichero es un contenedor binario (flatbuffer) con los nombres de asset y los bundles. Aqui se
sacan las cadenas y se busca el nombre de un bust-up (p.ej. 'changfu01-aqi' o 'lihui-') para saber en
que bundle esta su textura.
"""
import re
from collections import Counter
from pathlib import Path

P = Path(r"C:\Users\Lukas\p5x-datamining\game_dump\fileContentOut\Bundles\Windows\105\assetMapName.txt")
print("tamano:", P.stat().st_size, "bytes")
d = P.read_bytes()
cadenas = [s.decode("ascii", "ignore") for s in re.findall(rb"[\x20-\x7e]{4,120}", d)]
print("cadenas:", len(cadenas), " distintas:", len(set(cadenas)))
print("muestra de 12:", cadenas[12:24])

print()
print("=== apariciones de lihui / changfu / aqi ===")
for aguja in ("lihui", "changfu", "aqi", "uitex", "bundle", ".png"):
    hits = [s for s in cadenas if aguja in s.lower()]
    print("   %-10s %6d   ej: %s" % (aguja, len(hits), hits[:3]))

print()
print("=== contexto alrededor de 'lihui' ===")
for i, s in enumerate(cadenas):
    if "lihui" in s.lower():
        print("   idx %d:" % i, cadenas[max(0, i - 2):i + 3])
        if i > 40:
            break