"""Reconocimiento: que indices hay en el dump, cuantos bundles, y si el indice virtual los enlaza."""
import re
from pathlib import Path

RAIZ = Path(r"C:\Users\Lukas\p5x-datamining\game_dump")
IDX = RAIZ / "_vfileIndexV2.fb"

d = IDX.read_bytes()
print("indice %s: %d bytes" % (IDX.name, len(d)))
print("cabecera:", d[:32].hex(" "))
cadenas = re.findall(rb"[\x20-\x7e]{4,}", d)
print("cadenas legibles: %d" % len(cadenas))
for c in cadenas[:25]:
    print("   ", c.decode("ascii", "replace"))

bundles = sorted((RAIZ / "fileContentOut" / "Bundles" / "Windows").glob("**/*.bundle"))
print("\nbundles: %d" % len(bundles))
sospechosos = [b for b in bundles if re.search(r"manifest|depend|shared|common|core|main", b.name, re.I)]
print("bultos que huelen a manifiesto/comunes (%d):" % len(sospechosos))
for b in sospechosos[:20]:
    print("   %-60s %.1f KB" % (b.relative_to(RAIZ / 'fileContentOut' / 'Bundles' / 'Windows'), b.stat().st_size / 1024))

mapas = sorted((RAIZ / "fileContentOut" / "Bundles" / "Windows").glob("**/assetMapName.txt"))
print("\nficheros assetMapName.txt: %d" % len(mapas))
total = 0
for m in mapas:
    total += sum(1 for _ in m.open(encoding="utf-8", errors="replace"))
print("entradas en total: %d" % total)