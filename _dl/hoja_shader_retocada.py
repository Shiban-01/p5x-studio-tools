"""Hoja de contacto de los 120 retratos CON shader, con el pipeline de la app (que es el retocado).

Sale a _dl/prueba_sombreado/hoja_shader_retocada.png, en la misma rejilla que la hoja anterior para
poder compararlas de un vistazo.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, r"C:\Users\Lukas\p5x-datamining\p5x_studio")
from PIL import Image, ImageDraw  # noqa: E402

from p5x_studio import bustups  # noqa: E402

DL = Path(r"C:\Users\Lukas\p5x-datamining\_dl")
CARPETA = Path(r"C:\Users\Lukas\Desktop\P5X Studio Tools\extracted\portraits")
SALIDA = DL / "prueba_sombreado" / "hoja_shader_retocada.png"
ANCHO, ALTO = 190, 218
COLS = 12
FONDO = (26, 28, 34, 255)

datos = json.loads((DL / "emparejado_bustups.json").read_text(encoding="utf-8"))["emparejados"]
claves = sorted(datos)
filas = (len(claves) + COLS - 1) // COLS
hoja = Image.new("RGBA", (COLS * ANCHO, filas * ALTO), FONDO)
dib = ImageDraw.Draw(hoja)
fallos = []
for i, clave in enumerate(claves):
    r = bustups.montar(clave, None, CARPETA, guardar=True, shader=True)
    if not r.get("ok") or not r.get("shader"):
        fallos.append(clave)
        continue
    with Image.open(r["ruta"]) as im:
        im = im.convert("RGBA")
        im.thumbnail((ANCHO - 8, ALTO - 22))
        x = (i % COLS) * ANCHO + (ANCHO - im.size[0]) // 2
        y = (i // COLS) * ALTO + (ALTO - 20 - im.size[1]) // 2
        hoja.alpha_composite(im, (x, y))
    dib.text(((i % COLS) * ANCHO + 4, (i // COLS) * ALTO + ALTO - 16),
             clave.replace("UI-DialogShader-", ""), fill=(150, 152, 160, 255))
    if (i + 1) % 20 == 0:
        print("%d/%d" % (i + 1, len(claves)), flush=True)

SALIDA.parent.mkdir(parents=True, exist_ok=True)
hoja.convert("RGB").save(SALIDA)
print("hoja:", SALIDA, hoja.size)
print("sin shader o fallos:", len(fallos), fallos[:5])