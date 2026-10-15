"""Mide la figura de la referencia nueva (fondo blanco) y la imprime como mapa ASCII.

Con fondo blanco el aislamiento es directo: la figura es la componente conexa mayor de lo que no
es blanco. El mapa ASCII permite leer la postura midiendo, sin depender de una descripcion.
"""
import os
import sys
from collections import deque
from PIL import Image

REF = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\Lukas\AppData\Roaming\Hermes\composer-images\image_827048.png"
OUT = r"C:\Users\Lukas\p5x-datamining\_dl\ref_pose2"
os.makedirs(OUT, exist_ok=True)

im = Image.open(REF).convert("RGB")
W, H = im.size
print("original: %d x %d" % (W, H))

ESC = max(1, W // 1000)
w, h = W // ESC, H // ESC
px = im.resize((w, h)).load()
print("rejilla: %d x %d (1/%d)" % (w, h, ESC))


def es_fondo(r, g, b):
    return r > 232 and g > 232 and b > 232


mapa = [["." if es_fondo(*px[x, y]) else "#" for x in range(w)] for y in range(h)]

# componente conexa mayor
visto = [[False] * w for _ in range(h)]
mejor = []
for yy in range(h):
    for xx in range(w):
        if visto[yy][xx] or mapa[yy][xx] == ".":
            continue
        cola = deque([(xx, yy)])
        visto[yy][xx] = True
        pix = []
        while cola:
            cx, cy = cola.popleft()
            pix.append((cx, cy))
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)):
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < w and 0 <= ny < h and not visto[ny][nx] and mapa[ny][nx] == "#":
                    visto[ny][nx] = True
                    cola.append((nx, ny))
        if len(pix) > len(mejor):
            mejor = pix

es_fig = set(mejor)
xs = [p[0] for p in mejor]
ys = [p[1] for p in mejor]
x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
print("figura: %d celdas" % len(mejor))
print("caja: x %d..%d  y %d..%d  = %d x %d reales  (alto/ancho %.2f)"
      % (x0 * ESC, x1 * ESC, y0 * ESC, y1 * ESC, (x1 - x0) * ESC, (y1 - y0) * ESC,
         (y1 - y0) / max(1, x1 - x0)))


def clase(r, g, b):
    lum = (r * 299 + g * 587 + b * 114) // 1000
    mx, mn = max(r, g, b), min(r, g, b)
    if lum < 110:
        return "#"                       # negro: blazer, pelo oscuro, mango
    if r > 125 and r - g > 55 and r - b > 35:
        return "r"                       # rojo: lacito, puños
    if lum > 200 and mx - mn < 45:
        return "."                       # blanco: camisa, calcetines, hoja
    if 115 < lum < 245 and r > b + 12 and r >= g - 10:
        return "o"                       # piel: cara, manos
    return "+"

COLS, ROWS = 100, 58
print("\n=== silueta (100 x 58) ===")
print("    # oscuro   o piel(cara/manos)   r rojo   . blanco   + resto")
regla = "    "
for i in range(0, COLS, 10):
    regla += "%-10d" % (x0 * ESC + i * (x1 - x0) * ESC // COLS)
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
                p = (cx + dx, cy + dy)
                if p in es_fig:
                    k = clase(*px[p[0], p[1]])
                    if k in "or.":
                        c = k
                    elif c == " ":
                        c = "#"
        fila += c
    print("    " + fila)
print("    " + "".join(str(i % 10) for i in range(COLS)))

# recortes
c = im.crop((x0 * ESC, y0 * ESC, x1 * ESC, y1 * ESC))
c.save(os.path.join(OUT, "50_figura.png"))
print("\n   50_figura.png  %d x %d" % c.size)
alto = (y1 - y0) * ESC
cab = im.crop((x0 * ESC, y0 * ESC, x1 * ESC, y0 * ESC + alto // 4))
if cab.width < 800:
    cab = cab.resize((cab.width * 2, cab.height * 2))
cab.save(os.path.join(OUT, "51_cabeza.png"))
print("   51_cabeza.png  %d x %d" % cab.size)