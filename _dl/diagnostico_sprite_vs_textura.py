"""Los dos ficheros que puede haber por capa: ¿cual es la piel y cual la silueta?

Se miden por separado `<nombre>.png` y `<nombre>_#NN.png` (uno es el Sprite recortado y otro el
Texture2D). Si uno es negro al 100% y el otro tiene color, la eleccion por tamano esta mal.
"""
from pathlib import Path

from PIL import Image

CACHE = Path(r"C:\Users\Lukas\p5x-datamining\_dl\bustups_cache")


def medir(p):
    im = Image.open(p).convert("RGBA")
    px = im.load()
    tot = neg = claro = color = 0
    for y in range(0, im.height, 3):
        for x in range(0, im.width, 3):
            r, g, b, a = px[x, y]
            if a > 128:
                tot += 1
                if r < 40 and g < 40 and b < 40:
                    neg += 1
                elif r > 190 and g > 160:
                    claro += 1
                elif max(r, g, b) - min(r, g, b) > 25:
                    color += 1
    return im.size, tot, neg, claro, color


for carpeta in sorted(CACHE.glob("uitex_changfu*")):
    if not any(carpeta.glob("xiachuanling-changfu-benti.png")):
        continue
    for nombre in ("xiachuanling-changfu-benti", "xiachuanling-changfu-benti-toufa",
                   "xiachuanling-changfu-benti-yifu", "xiachuanling-changfu-tongchang-yan1"):
        ficheros = sorted(carpeta.glob("%s.png" % nombre)) + sorted(carpeta.glob("%s_#*.png" % nombre))
        for p in ficheros:
            tam, tot, neg, claro, color = medir(p)
            print("%-46s %-40s %-11s opacos %5d | negro %5.1f%% | claro %5.1f%% | color %5.1f%%"
                  % (nombre[:46], p.name[:40], "%dx%d" % tam, tot,
                     neg * 100.0 / max(tot, 1), claro * 100.0 / max(tot, 1),
                     color * 100.0 / max(tot, 1)))
    break