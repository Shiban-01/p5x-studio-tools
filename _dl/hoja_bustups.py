"""Hoja de contacto con todos los bust-ups sombreados del lote, para revisarlos de un vistazo.

Rejilla con el nombre de cada uno debajo. Se escala cada bust-up a una altura fija y se recorta el
sobrante, para que la hoja no se vaya de tamano.
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SALIDA = Path(r"C:\Users\Lukas\p5x-datamining\_dl\bustups_sombreados")
HOJA = Path(r"C:\Users\Lukas\p5x-datamining\_dl\hoja_bustups.png")

COLUMNAS = 8
ALTO = 240
ANCHO = 190
MARGEN = 6
ETIQUETA = 22
FONDO = (18, 18, 22, 255)
TARJETA = (30, 30, 36, 255)


def fuente(tam):
    for ruta in (r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\arial.ttf"):
        if Path(ruta).exists():
            return ImageFont.truetype(ruta, tam)
    return ImageFont.load_default()


f = fuente(11)
ficheros = sorted(SALIDA.glob("*.png"))
print("bust-ups en la hoja: %d" % len(ficheros))
if not ficheros:
    raise SystemExit("no hay nada en %s" % SALIDA)

filas = (len(ficheros) + COLUMNAS - 1) // COLUMNAS
celda_alto = ALTO + ETIQUETA
hoja = Image.new("RGBA", (COLUMNAS * (ANCHO + MARGEN) + MARGEN,
                          filas * (celda_alto + MARGEN) + MARGEN), FONDO)
dib = ImageDraw.Draw(hoja)

for i, fichero in enumerate(ficheros):
    im = Image.open(fichero).convert("RGBA")
    esc = ALTO / im.height
    im = im.resize((max(1, int(im.width * esc)), ALTO), Image.LANCZOS)
    if im.width > ANCHO:                       # recorta el sobrante, centrado
        sobra = (im.width - ANCHO) // 2
        im = im.crop((sobra, 0, sobra + ANCHO, im.height))
    cx = MARGEN + (i % COLUMNAS) * (ANCHO + MARGEN)
    cy = MARGEN + (i // COLUMNAS) * (celda_alto + MARGEN)
    dib.rectangle([cx, cy, cx + ANCHO, cy + celda_alto], fill=TARJETA)
    hoja.alpha_composite(im, (cx + (ANCHO - im.width) // 2, cy + (ALTO - im.height) // 2))
    nombre = fichero.stem
    if len(nombre) > 30:
        nombre = nombre[:29] + "…"
    dib.text((cx + 4, cy + ALTO + 4), nombre, fill=(200, 200, 210, 255), font=f)

hoja.save(HOJA)
print("hoja:", HOJA, hoja.size)