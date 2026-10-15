"""Mapa ASCII de la referencia usando el canal alfa como mascara.

La imagen es RGBA: el alfa aisla la figura exactamente, sin adivinar fondos. Sobre esa mascara se
imprime la silueta en texto con clases de color, para poder leer la postura midiendo.
"""
import os
import sys
from PIL import Image

REF = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\Lukas\AppData\Roaming\Hermes\composer-images\image_827048.png"
OUT = r"C:\Users\Lukas\p5x-datamining\_dl\ref_pose2"
os.makedirs(OUT, exist_ok=True)

im = Image.open(REF).convert("RGBA")
W, H = im.size
px = im.load()
print("imagen: %d x %d RGBA" % (W, H))


def es_fig(x, y):
    return px[x, y][3] > 128


# caja de la figura
xs = [x for x in range(W) if any(es_fig(x, y) for y in range(0, H, 4))]
ys = [y for y in range(H) if any(es_fig(x, y) for x in range(0, W, 4))]
x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
print("caja: x %d..%d  y %d..%d  = %d x %d  (alto/ancho %.2f)"
      % (x0, x1, y0, y1, x1 - x0, y1 - y0, (y1 - y0) / max(1, x1 - x0)))

# recuento de clases
def clase(r, g, b, a):
    if a < 128:
        return " "
    lum = (r * 299 + g * 587 + b * 114) // 1000
    mx, mn = max(r, g, b), min(r, g, b)
    if lum < 110:
        return "#"
    if r > 125 and r - g > 55 and r - b > 35:
        return "r"
    if lum > 200 and mx - mn < 45:
        return "."
    if 115 < lum < 245 and r > b + 12 and r >= g - 10:
        return "o"
    return "+"

cuenta = {}
for y in range(y0, y1 + 1, 2):
    for x in range(x0, x1 + 1, 2):
        c = clase(*px[x, y])
        if c != " ":
            cuenta[c] = cuenta.get(c, 0) + 1
print("clases:", cuenta)

COLS, ROWS = 100, 60
print("\n=== silueta (%d x %d) ===" % (COLS, ROWS))
print("    # oscuro   o piel(cara/manos)   r rojo   . blanco   + resto")
regla = "    "
for i in range(0, COLS, 10):
    regla += "%-10d" % (x0 + i * (x1 - x0) // COLS)
print(regla)
paso_x = max(1, (x1 - x0) // COLS)
paso_y = max(1, (y1 - y0) // ROWS)
for ry in range(ROWS):
    fila = ""
    for rx in range(COLS):
        cx = x0 + (x1 - x0) * rx // COLS
        cy = y0 + (y1 - y0) * ry // ROWS
        c = " "
        for dy in range(paso_y):
            for dx in range(paso_x):
                xx, yy = cx + dx, cy + dy
                if 0 <= xx < W and 0 <= yy < H:
                    k = clase(*px[xx, yy])
                    if k in "or.":
                        c = k
                    elif k == "#" and c == " ":
                        c = "#"
        fila += c
    print("    " + fila)
print("    " + "".join(str(i % 10) for i in range(COLS)))

# recortes con transparencia conservada
im.crop((x0, y0, x1 + 1, y1 + 1)).save(os.path.join(OUT, "60_figura.png"))
alto = y1 - y0
cab = im.crop((x0, y0, x1 + 1, y0 + alto // 4))
if cab.width < 800:
    cab = cab.resize((cab.width * 2, cab.height * 2))
cab.save(os.path.join(OUT, "61_cabeza.png"))
print("\n   60_figura.png y 61_cabeza.png (%d x %d)" % cab.size)

# lineas guia: por cada banda, los extremos de la silueta en x
print("\n=== extremos de la silueta por banda (para reconstruir la postura) ===")
print("   banda  izq   der   ancho")
for f in range(0, 100, 4):
    ya = y0 + (y1 - y0) * f // 100
    yb = y0 + (y1 - y0) * (f + 4) // 100
    xl, xr = None, None
    for y in range(ya, max(yb, ya + 1)):
        for x in range(x0, x1 + 1):
            if es_fig(x, y):
                if xl is None or x < xl:
                    xl = x
                if xr is None or x > xr:
                    xr = x
    if xl is not None:
        print("   %3d%%  %4d  %4d  %5d" % (f, xl, xr, xr - xl))