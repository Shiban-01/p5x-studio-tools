"""Revision objetiva de los bust-ups del lote: descarta los vacios y los que salen casi negros.

Los sospechosos de verdad son dos: PNG sin pixeles opacos (no se monto nada) y PNG casi negros
(se apilo el contorno en lugar del cuerpo). El resto es cosa del dibujo, no del proceso.
"""
import json
from pathlib import Path

import numpy as np
from PIL import Image

DL = Path(r"C:\Users\Lukas\p5x-datamining\_dl")
SALIDA = DL / "bustups_sombreados"
LUZ = np.array([0.2125, 0.7154, 0.0721])

vacios, oscuros, sanos = [], [], []
for f in sorted(SALIDA.glob("*.png")):
    r = np.asarray(Image.open(f).convert("RGBA"), dtype=np.float32) / 255.0
    alfa = r[..., 3]
    opacos = alfa > 0.5
    frac = float(opacos.mean())
    if frac < 0.02:
        vacios.append((f.stem, frac))
        continue
    lum = float((r[..., :3][opacos] * LUZ).sum(-1).mean())
    if lum < 0.25:
        oscuros.append((f.stem, frac, lum))
    else:
        sanos.append((f.stem, frac, lum))

print("bust-ups revisados: %d" % (len(vacios) + len(oscuros) + len(sanos)))
print("   vacios (menos del 2%% de pixeles opacos): %d" % len(vacios))
for n, fr in vacios:
    print("      %-56s opacos %.1f%%" % (n, fr * 100))
print("   sospechosos de ser contorno (luminancia < 0.25): %d" % len(oscuros))
for n, fr, lu in oscuros:
    print("      %-56s opacos %.1f%% luz %.3f" % (n, fr * 100, lu))
print("   sanos: %d" % len(sanos))
if sanos:
    fr = np.array([s[1] for s in sanos])
    lu = np.array([s[2] for s in sanos])
    print("      opacos: mediana %.1f%% (min %.1f%% max %.1f%%)"
          % (np.median(fr) * 100, fr.min() * 100, fr.max() * 100))
    print("      luminancia: mediana %.3f (min %.3f max %.3f)" % (np.median(lu), lu.min(), lu.max()))

(DL / "revision_lote.json").write_text(json.dumps(
    {"vacios": vacios, "oscuros": oscuros, "sanos": len(sanos)}, ensure_ascii=False, indent=1),
    encoding="utf-8")