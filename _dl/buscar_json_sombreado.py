"""Busca el dato de sombreado por bust-up dentro de los bundles extraidos (TextAsset con JSON)."""
import json
import re
from pathlib import Path

D = Path(r"C:\Users\Lukas\p5x-datamining\game_dump\fileContentOut\Bundles\Windows")
claves = [b'"colors"', b'"gradient"', b'"Colors"', b'"points"', b'"shadowColor"', b'"topColor"',
          b'"bottomColor"', b'"lihui"', b'"GradientColors"', b'gradientColors']
print("=== claves JSON en los bundles extraidos ===")
total = 0
for p in sorted(D.rglob("*.bundle")):
    d = p.read_bytes()
    hits = {k.decode(): d.count(k) for k in claves if k in d}
    if hits:
        total += 1
        print("   %-46s %s" % (p.relative_to(D).as_posix()[:46], hits))
print("bundles con alguna clave:", total)

json_datos = Path(r"C:\Users\Lukas\Downloads\P5X\Client\OuterPackage\HotFixTemp\zeus-hf-data.json")
if json_datos.exists():
    txt = json_datos.read_text(encoding="utf-8", errors="replace")
    print()
    print("=== zeus-hf-data.json  (%d KB) ===" % (len(txt) // 1024))
    print("   empieza:", txt[:200].replace("\n", " "))
    for c in ('"colors"', '"gradient"', "lihui", "Color"):
        print("   %-12s -> %d apariciones" % (c, txt.count(c)))
    try:
        d = json.loads(txt)
        print("   claves de primer nivel:", list(d)[:8] if isinstance(d, dict) else type(d).__name__)
    except Exception as e:
        print("   (no es json plano:", type(e).__name__, ")")