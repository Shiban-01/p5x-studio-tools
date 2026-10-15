"""Silueta limpia en ASCII (solo forma) y localizacion de la cabeza y las manos.

La silueta pura permite leer la postura como si fuera una sombra. Ademas se localizan la cabeza
(el bloque de piel mas alto) y las manos (los otros bloques de piel), que son los puntos que hay
que calcar con precision.
"""
import os
import sys
from PIL import Image

REF = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\Lukas\AppData\Roaming\Hermes\composer-images\image_827048.png"
im = Image.open(REF).convert("RGBA")
W, H = im.size
px = im.load()

def fig(x, y):
    return px[x, y][3] > 128

xs = [x for x in range(W) if any(fig(x, y) for y in range(0, H, 4))]
ys = [y for y in range(H) if any(fig(x, y) for x in range(0, W, 4))]
x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
print("caja: x %d..%d  y %d..%d  = %d x %d" % (x0, x1, y0, y1, x1 - x0, y1 - y0))
print("centro de masas de la silueta y area: ", end="")
area = sum(1 for y in range(y0, y1 + 1) for x in range(x0, x1 + 1) if fig(x, y))
sx = sum(x for y in range(y0, y1 + 1, 2) for x in range(x0, x1 + 1, 2) if fig(x, y))
sy = sum(y for y in range(y0, y1 + 1, 2) for x in range(x0, x1 + 1, 2) if fig(x, y))
n = sum(1 for y in range(y0, y1 + 1, 2) for x in range(x0, x1 + 1, 2) if fig(x, y))
print("area=%d  centro=(%d, %d)" % (area, sx // n, sy // n))

COLS, ROWS = 104, 62
paso_x = (x1 - x0) / COLS
paso_y = (y1 - y0) / ROWS
print("\n=== silueta limpia (%d x %d) ===" % (COLS, ROWS))
regla = "     "
for i in range(0, COLS, 10):
    regla += "%-10d" % int(x0 + i * paso_x)
print(regla)
for ry in range(ROWS):
    fila = ""
    for rx in range(COLS):
        cx = int(x0 + rx * paso_x)
        cy = int(y0 + ry * paso_y)
        # la celda es figura si al menos un 25% de sus pixeles lo son
        tot = hay = 0
        for dy in range(0, max(1, int(paso_y)), 2):
            for dx in range(0, max(1, int(paso_x)), 2):
                xx, yy = cx + dx, cy + dy
                if x0 <= xx <= x1 and y0 <= yy <= y1:
                    tot += 1
                    if fig(xx, yy):
                        hay += 1
        fila += "#" if tot and hay / tot > 0.25 else ("." if hay else " ")
    print("    " + fila)
print("     " + "".join(str(i % 10) for i in range(COLS)))

# bloques de piel: cabeza y manos
print("\n=== bloques de piel (cara y manos) ===")
visto = [[False] * W for _ in range(H)]
bloques = []
for yy in range(y0, y1 + 1, 2):
    for xx in range(x0, x1 + 1, 2):
        if visto[yy][xx] or not fig(xx, yy):
            continue
        r, g, b, a = px[xx, yy]
        lum = (r * 299 + g * 587 + b * 114) // 1000
        if not (115 < lum < 245 and r > b + 12 and r >= g - 10):
            visto[yy][xx] = True
            continue
        # inundar la zona de piel
        pila = [(xx, yy)]
        visto[yy][xx] = True
        pix = []
        while pila:
            cx, cy = pila.pop()
            pix.append((cx, cy))
            for dx, dy in ((2, 0), (-2, 0), (0, 2), (0, -2)):
                nx, ny = cx + dx, cy + dy
                if x0 <= nx <= x1 and y0 <= ny <= y1 and not visto[ny][nx] and fig(nx, ny):
                    rr, gg, bb, aa = px[nx, ny]
                    l2 = (rr * 299 + gg * 587 + bb * 114) // 1000
                    if 115 < l2 < 245 and rr > bb + 12 and rr >= gg - 10:
                        visto[ny][nx] = True
                        pila.append((nx, ny))
        if len(pix) > 150:
            bloques.append(pix)

bloques.sort(key=lambda p: min(q[1] for q in p))
for i, bl in enumerate(bloques[:8]):
    bx0, bx1 = min(q[0] for q in bl), max(q[0] for q in bl)
    by0, by1 = min(q[1] for q in bl), max(q[1] for q in bl)
    cx, cy = sum(q[0] for q in bl) // len(bl), sum(q[1] for q in bl) // len(bl)
    print("   bloque %d: %5d px   caja x %3d..%3d  y %3d..%3d   centro (%3d, %3d)   [%d%% del alto]"
          % (i, len(bl), bx0, bx1, by0, by1, cx, cy, 100 * (cy - y0) // max(1, y1 - y0)))