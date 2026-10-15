"""Localiza la figura en la ilustracion de referencia y saca recortes legibles.

El fondo es magenta plano, asi que la figura se separa por color. Se guardan recortes a tamano
util para poder leer la pose (cuerpo entero, cara, brazos) sin que el visor los reduzca.
"""
import os
from PIL import Image

REF = r"C:\Users\Lukas\AppData\Roaming\Hermes\composer-images\image_9324d5.png"
OUT = r"C:\Users\Lukas\p5x-datamining\_dl\ref_kotone"
os.makedirs(OUT, exist_ok=True)

im = Image.open(REF).convert("RGB")
W, H = im.size
print("original:", W, "x", H)

# color de fondo = el mas frecuente
pequena = im.resize((W // 8, H // 8))
colores = pequena.getcolors(pequena.width * pequena.height)
colores.sort(reverse=True)
fondo = colores[0][1]
print("color de fondo mas frecuente:", fondo, "-> %d%% de la muestra" % (100 * colores[0][0] // (pequena.width * pequena.height)))
print("siguientes:", [c[1] for c in colores[1:5]])

# mascara: pixeles que se alejan del fondo
px = pequena.load()
mask = Image.new("L", pequena.size, 0)
mp = mask.load()
for y in range(pequena.height):
    for x in range(pequena.width):
        r, g, b = px[x, y]
        if abs(r - fondo[0]) + abs(g - fondo[1]) + abs(b - fondo[2]) > 90:
            mp[x, y] = 255

bbox_p = mask.getbbox()
if not bbox_p:
    print("no se separa nada del fondo")
    raise SystemExit
escala = 8
bbox = tuple(v * escala for v in bbox_p)
print("caja de la figura (aprox, incluye texto):", bbox,
      "-> %.0f%% del ancho, %.0f%% del alto" % (100 * (bbox[2]-bbox[0]) / W, 100 * (bbox[3]-bbox[1]) / H))

# recortes utiles
def guardar(nombre, caja, alto_max=1400):
    c = im.crop(caja)
    if c.height > alto_max:
        c = c.resize((int(c.width * alto_max / c.height), alto_max))
    p = os.path.join(OUT, nombre)
    c.save(p)
    print("   %-26s %s  (%d x %d)" % (nombre, c.size, c.size[0], c.size[1]))

print("\nrecortes:")
guardar("00_completa.png", (0, 0, W, H), 1000)
guardar("01_figura.png", bbox)
# la cara: el tercio superior de la figura, con margen
x0, y0, x1, y1 = bbox
alto = y1 - y0
guardar("02_cara.png", (max(0, x0 - 60), max(0, y0 - 60), min(W, x1 + 60), y0 + alto // 3), 1200)
guardar("03_torso.png", (max(0, x0 - 60), y0 + alto // 5, min(W, x1 + 60), y0 + int(alto * 0.75)), 1200)
guardar("04_piernas.png", (max(0, x0 - 60), y0 + int(alto * 0.6), min(W, x1 + 60), min(H, y1 + 60)), 1200)
print("\nguardado en", OUT)