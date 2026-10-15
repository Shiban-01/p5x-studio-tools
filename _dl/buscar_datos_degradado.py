"""Busca donde vive el dato de degradado por bust-up: en los MonoBehaviours de los bundles ui_*.

Localiza las apariciones de 'gradient'/'lihui' en los bundles de interfaz extraidos y muestra el
texto legible de alrededor, que es donde se ven los nombres de los campos serializados.
"""
import re
from pathlib import Path

D = Path(r"C:\Users\Lukas\p5x-datamining\game_dump\fileContentOut\Bundles\Windows")

lupa = re.compile(rb"[Gg]radient|lihui|Gradation")
objetivo = [
    D / "005" / "ui_mainui498d6b82.bundle",
    D / "019" / "ui_s_login4ac66034.bundle",
    D / "101" / "ui_nbasedui37afe8ed.bundle",
    D / "095" / "uitex_on-part13f30638d.bundle",
]
for p in objetivo:
    if not p.exists():
        print("(no existe)", p.name)
        continue
    d = p.read_bytes()
    hits = [m.start() for m in lupa.finditer(d)]
    print("=== %s  (%.2f MB)  apariciones: %d" % (p.name, len(d) / 1e6, len(hits)))
    vistos = {}
    for h in hits[:40]:
        for s in re.findall(rb"[\x20-\x7e]{4,60}", d[max(0, h - 220):h + 220]):
            vistos.setdefault(s.decode("ascii", "ignore"), 0)
            vistos[s.decode("ascii", "ignore")] += 1
    for s, n in sorted(vistos.items(), key=lambda kv: -kv[1])[:22]:
        print("      %-58s x%d" % (s[:58], n))
    print()

# los manifiestos de texto que aparecen ahi (incluido el "assetMapName" del que hablaba Aaron)
for t in (D / "105" / "assetMapName.txt", D / "104" / "zeusBundleManifest.txt"):
    if t.exists():
        lineas = t.read_text(encoding="utf-8", errors="replace").splitlines()
        print("=== %s  (%d lineas) ===" % (t.name, len(lineas)))
        for l in lineas[:6]:
            print("      ", l[:110])
        con_grad = [l for l in lineas if "gradient" in l.lower()]
        print("      lineas con 'gradient': %d %s" % (len(con_grad), con_grad[:3]))
        print()