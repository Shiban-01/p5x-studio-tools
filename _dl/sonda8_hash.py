"""Mide como termina el nombre de un bundle: cuanto mide el hash y que queda al quitarlo.

De esto depende el nombre de la carpeta "conjunto" (Categoria/conjunto/textura.png). Si el hash
siempre mide lo mismo, se puede cortar sin miedo; si no, hay que buscar otra regla.
"""
import collections
import re
from pathlib import Path

G = Path(r"C:\Users\Lukas\Downloads\P5X\Client\OuterPackage\Bundles\Windows")
largos = collections.Counter()
ejemplos = collections.defaultdict(list)
cortados = []

for p in sorted(G.rglob("*.bundle")):
    s = p.name[:-len(".bundle")]
    m = re.search(r"[0-9a-f]+$", s)
    if not m:
        largos["sin hex final"] += 1
        continue
    largos[len(m.group(0))] += 1
    if len(ejemplos[len(m.group(0))]) < 3:
        ejemplos[len(m.group(0))].append((s, s[: m.start()]))
    if len(cortados) < 12:
        queda = s[: m.start()].rstrip("_-")
        cortados.append((s, queda, m.group(0)))

print("=== largos del tramo hex final ===")
for k, n in largos.most_common(10):
    print("   %-14s %6d   %s" % (k, n, ejemplos.get(k, "")[:2]))

print()
print("=== que queda al cortar 8 (los 12 primeros) ===")
for s, queda, h in cortados:
    r = re.sub(r"[0-9a-f]{8}$", "", s).rstrip("_-")
    print("   %-40s -> %-30s (hash=%s, corte8=%s)" % (s[:40], queda[:30], h, r[:30]))

# cuantos quedarian igual cortando 8
exactos = 0
distintos = 0
vacios = 0
for p in G.rglob("*.bundle"):
    s = p.name[:-len(".bundle")]
    r = re.sub(r"[0-9a-f]{8}$", "", s).rstrip("_-")
    m = re.search(r"[0-9a-f]+$", s)
    if not r:
        vacios += 1
    elif m and m.group(0) == re.sub(r"[0-9a-f]{8}$", "", s)[len(r):]:
        exactos += 1
    elif m and len(m.group(0)) != 8:
        distintos += 1
print()
print("cortando exactamente 8 al final:")
print("   quedan bien:", exactos)
print("   el tramo hex NO media 8:", distintos)
print("   se quedarian sin nombre:", vacios)