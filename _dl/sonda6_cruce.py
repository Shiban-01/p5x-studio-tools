"""Cruza familia de bundle con prefijo de nombre: de donde sale de verdad cada cosa.

Responde a la pregunta que decide las carpetas: si las texturas de personaje (PC0xx) viven todas
en role_, o estan repartidas por shared_/part_/etc. y hay que clasificar por NOMBRE, no por familia.
"""
import collections
import json
import re
from pathlib import Path

D = json.loads(Path(r"C:\Users\Lukas\p5x-datamining\_dl\censo_texturas.json").read_text(encoding="utf-8"))
filas = D["filas"]
print("texturas:", len(filas))


def familia(f):
    return f["bundle"].split("/")[1].split("_")[0]


# 1) cuantos nombres PC0xx hay y en que familias viven
pc = [f for f in filas if re.match(r"^(PC|ps_|role|char)\d", f["nombre"], re.I)]
print()
print("=== nombres tipo personaje (PC0xx / ps_NNN / roleNNN) por familia ===")
c = collections.Counter(familia(f) for f in pc)
for k, n in c.most_common(8):
    print("   %-12s %6d" % (k, n))

# 2) prefijos top por familia (los 6 mas comunes de cada una)
print()
print("=== que hay dentro de cada familia (prefijos de nombre mas comunes) ===")
por_fam = collections.defaultdict(collections.Counter)
for f in filas:
    pref = re.split(r"[_\-]", f["nombre"])[0]
    por_fam[familia(f)][pref] += 1
for fam, n in sorted(((k, len(v)) for k, v in por_fam.items()), key=lambda x: -x[1]):
    tot = sum(por_fam[fam].values())
    top = ", ".join("%s(%d)" % (k[:14], v) for k, v in por_fam[fam].most_common(6))
    print("   %-12s %7d  %s" % (fam, tot, top[:110]))

# 3) sufijos por familia: que tipos de mapa tiene cada una
print()
print("=== sufijos (tipo de mapa) mas comunes por familia ===")
por_fam_suf = collections.defaultdict(collections.Counter)
for f in filas:
    suf = f["nombre"].rsplit("_", 1)[-1] if "_" in f["nombre"] else "(sin _)"
    por_fam_suf[familia(f)][suf] += 1
for fam in ("scn", "role", "part", "shared", "uitex", "atlas", "roletiny"):
    top = ", ".join("%s(%d)" % (k[:12], v) for k, v in por_fam_suf[fam].most_common(7))
    print("   %-12s %s" % (fam, top[:110]))

# 4) sprites vs texturas por familia (los sprites son casi siempre UI)
print()
print("=== Sprite vs Texture2D por familia ===")
t = collections.defaultdict(collections.Counter)
for f in filas:
    t[familia(f)][f["tipo"]] += 1
for fam, n in sorted(((k, sum(v.values())) for k, v in t.items()), key=lambda x: -x[1]):
    print("   %-12s %7d  Sprite=%d Texture2D=%d" % (fam, n, t[fam]["Sprite"], t[fam]["Texture2D"]))