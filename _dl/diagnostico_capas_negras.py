"""¿Que capa mete el negro de la cara? Se mide el negro opaco de cada capa del montaje.

Si el cuerpo sale mayoritariamente negro, es que la capa elegida como `benti` no es la piel sino una
silueta (o una variante de sombra), y hay que buscar la capa de cuerpo correcta.
"""
import json
from pathlib import Path

from PIL import Image

DL = Path(r"C:\Users\Lukas\p5x-datamining\_dl")
co = json.loads((DL / "bustups_montados" / "UI-DialogShader-changfu01-xiachuanling.json")
                .read_text(encoding="utf-8"))

for c in co["capas"]:
    im = Image.open(c["png"]).convert("RGBA")
    px = im.load()
    tot = neg = claro = 0
    for y in range(0, im.height, 4):
        for x in range(0, im.width, 4):
            r, g, b, a = px[x, y]
            if a > 128:
                tot += 1
                if r < 40 and g < 40 and b < 40:
                    neg += 1
                elif r > 190 and g > 160:
                    claro += 1
    if tot:
        print("%-9s %-44s opacos %5d | negro %5.1f%% | claro %5.1f%%"
              % (c["paso"], c["nombre"][:44], tot, neg * 100.0 / tot, claro * 100.0 / tot))
    else:
        print("%-9s %-44s (sin pixeles opacos)" % (c["paso"], c["nombre"][:44]))

# ¿que otras capas hay para este personaje en el censo?
censo = json.loads((DL / "censo_texturas.json").read_text(encoding="utf-8"))["filas"]
print()
print("capas del censo con 'xiachuanling-changfu-benti':")
for f in censo:
    if f["nombre"].startswith("xiachuanling-changfu-benti"):
        print("   %-50s %-10s %s" % (f["nombre"], f["tipo"], f["bundle"]))