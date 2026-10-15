"""Aisla la figura del banner y la imprime como mapa ASCII para leer la pose sin depender de vision.

El texto del fondo es magenta-violaceo (r-g alto y b-g alto) y se conecta con la figura, asi que
se descarta por color. Despues la silueta se imprime en una rejilla de texto donde cada caracter
es una clase: piel (cara/manos), rojo (lacito, brazalete, aparato), oscuro (pelo, blazer) y claro.
Con ese mapa se puede leer la postura midiendo, no interpretando.
"""
import os
from collections import deque
from PIL import Image

REF = r"C:\Users\Lukas\AppData\Roaming\Hermes\composer-images\image_9324d5.png"
OUT = r"C:\Users\Lukas\p5x-datamining\_dl\ref_kotone"
os.makedirs(OUT, exist_ok=True)

im = Image.open(REF).convert("RGB")
W, H = im.size
ESC = 4
w, h = W // ESC, H // ESC
px = im.resize((w, h)).load()
print("rejilla de trabajo: %d x %d (1/%d)" % (w, h, ESC))


def tipo(r, g, b):
    """'fondo' (lienzo o magenta), 'texto' (magenta-violaceo) o 'figura'"""
    if r > 225 and g > 225 and b > 225:
        return "fondo"
    if r > 190 and g < 175 and r - g > 65 and b > 85 and b - g > 25:
        return "fondo"                     # magenta del cartel
    if r - g > 60 and b - g > 25:
        return "texto"                     # letras del fondo
    return "figura"


def clase(r, g, b):
    lum = (r * 299 + g * 587 + b * 114) // 1000
    mx, mn = max(r, g, b), min(r, g, b)
    if lum < 105:
        return "#"                          # oscuro: pelo, blazer
    if r > 125 and r - g > 55 and r - b > 35:
        return "r"                          # rojo: lacito, brazalete
    if lum > 200 and mx - mn < 45:
        return "."                          # blanco: camisa, cuello
    if 115 < lum < 242 and r > b + 15 and r >= g - 8:
        return "o"                          # piel: cara, manos
    return "+"


mapa = [[tipo(*px[x, y]) for x in range(w)] for y in range(h)]

# componente conexa mas grande de 'figura'
visto = [[False] * w for _ in range(h)]
mejor = []
for yy in range(h):
    for xx in range(w):
        if visto[yy][xx] or mapa[yy][xx] != "figura":
            continue
        cola = deque([(xx, yy)])
        visto[yy][xx] = True
        pix = []
        while cola:
            cx, cy = cola.popleft()
            pix.append((cx, cy))
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < w and 0 <= ny < h and not visto[ny][nx] and mapa[ny][nx] == "figura":
                    visto[ny][nx] = True
                    cola.append((nx, ny))
        if len(pix) > len(mejor):
            mejor = pix

print("figura: %d celdas (%.0f px reales)" % (len(mejor), len(mejor) * ESC * ESC))
es_fig = set(mejor)
xs = [p[0] for p in mejor]
ys = [p[1] for p in mejor]
print("caja: x %d..%d  y %d..%d  = %d x %d reales"
      % (min(xs) * ESC, max(xs) * ESC, min(ys) * ESC, max(ys) * ESC,
         (max(xs) - min(xs)) * ESC, (max(ys) - min(ys)) * ESC))

# mapa ASCII: 84 columnas
COLS, ROWS = 84, 48
x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
print("\n=== silueta de la figura (%d x %d) ===" % (COLS, ROWS))
print("    # pelo/blazer   o piel(cara/manos)   r rojo   . blanco   + resto")
cab = "    "
for i in range(0, COLS, 10):
    cab += "%-10d" % (x0 * ESC + i * (x1 - x0) * ESC // COLS)
print(cab)
for ry in range(ROWS):
    fila = ""
    for rx in range(COLS):
        cx = x0 + (x1 - x0) * rx // COLS
        cy = y0 + (y1 - y0) * ry // ROWS
        # muestrear la celda buscando algo de la figura
        mejor_c = " "
        for dy in range(max(1, (y1 - y0) // ROWS)):
            for dx in range(max(1, (x1 - x0) // COLS)):
                p = (cx + dx, cy + dy)
                if p in es_fig:
                    c = clase(*px[p[0], p[1]])
                    if c in "or.":
                        mejor_c = c
                    elif mejor_c == " ":
                        mejor_c = "#"
        fila += mejor_c
    print("    " + fila)
print("    " + "".join(str(i % 10) for i in range(COLS)))