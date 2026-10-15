"""Monta los 15 bust-ups que salian sin cara y guarda una hoja para mirarlos."""
import sys
from pathlib import Path

from PIL import Image

APP = Path(r"C:\Users\Lukas\p5x-datamining\p5x_studio")
sys.path.insert(0, str(APP))
from p5x_studio import bustups  # noqa: E402

CARPETA = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(bustups.carpeta_texturas())
SALIDA = Path(r"C:\Users\Lukas\p5x-datamining\_dl\prueba_sombreado\los_15.png")

SIN_CARA = ["guaidao01-bainiao", "guaidao01-qinyinmianju", "guaidao01-yemaopengzi01",
            "guaidao01-xisenyangcai-face", "guaidaofu01-qinyin", "sifu01-lizi",
            "yongzhuang-lizi", "yongzhuang-yemaopengzi"]

imagenes = []
print("indice: %d nombres (refrescado)" % len(bustups.indice(CARPETA, refrescar=True)))
for corta in SIN_CARA:
    r = bustups.montar("UI-DialogShader-" + corta, None, CARPETA, guardar=True)
    if not r.get("ok"):
        print("%-30s no monta" % corta)
        continue
    im = Image.open(r["ruta"]).convert("RGBA")
    if im.height > 420:
        im = im.resize((int(im.width * 420 / im.height), 420), Image.LANCZOS)
    imagenes.append((corta, im))
    print("%-30s %s  capas: %s" % (corta, im.size, ",".join(c.get("paso") or "?" for c in r["capas"])))

ancho = sum(im.width for _, im in imagenes) + 12 * len(imagenes)
alto = 420
hoja = Image.new("RGBA", (ancho, alto), (24, 24, 28, 255))
x = 6
for _, im in imagenes:
    hoja.alpha_composite(im, (x, (alto - im.height) // 2))
    x += im.width + 12
hoja.save(SALIDA)
print("hoja:", SALIDA, hoja.size)