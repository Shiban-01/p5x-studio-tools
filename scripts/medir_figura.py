"""Aisla la figura por componente conexa (no por color) y mide su pose.

Antes fallaba porque el fondo magenta se colaba como 'rojo' y la franja de columnas cortaba el
brazo extendido. Ahora: fondo = blanco del lienzo o magenta (con tolerancia), se etiquetan las
componentes conexas y se toma la mayor de la mitad izquierda, que es la figura. Sobre esa mascara
se miden silueta, piel (cara y manos), rojo (lacito, brazalete, aparato) y oscuro (pelo, blazer).
"""
import os
import sys
from collections import deque
from PIL import Image

sys.setrecursionlimit(100000)
REF = r"C:\Users\Lukas\AppData\Roaming\Hermes\composer-images\image_9324d5.png"
OUT = r"C:\Users\Lukas\p5x-datamining\_dl\ref_kotone"
os.makedirs(OUT, exist_ok=True)

im = Image.open(REF).convert("RGB")
W, H = im.size
ESC = 3                                   # trabajar a 1/3 de resolucion
w, h = W // ESC, H // ESC
peq = im.resize((w, h))
px = peq.load()
print("trabajando a %d x %d (1/%d de %d x %d)" % (w, h, ESC, W, H))


def es_fondo(r, g, b):
    """blanco del lienzo o magenta del fondo"""
    if r > 225 and g > 225 and b > 225:
        return True
    if r > 190 and g < 170 and r - g > 70 and b > 90:
        return True
    return False


# etiquetar componentes conexas de NO fondo
visto = [[False] * w for _ in range(h)]
comp = []
for yy in range(h):
    for xx in range(w):
        if visto[yy][xx]:
            continue
        r, g, b = px[xx, yy]
        if es_fondo(r, g, b):
            visto[yy][xx] = True
            continue
        cola = deque([(xx, yy)])
        visto[yy][xx] = True
        pix = []
        while cola:
            cx, cy = cola.popleft()
            pix.append((cx, cy))
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < w and 0 <= ny < h and not visto[ny][nx]:
                    r2, g2, b2 = px[nx, ny]
                    if not es_fondo(r2, g2, b2):
                        visto[ny][nx] = True
                        cola.append((nx, ny))
        if len(pix) > 300:
            comp.append(pix)

comp.sort(key=len, reverse=True)
print("componentes grandes: %d  (mayores: %s)" % (len(comp), [len(c) for c in comp[:6]]))

# la figura: la mayor cuyo centro este en la mitad izquierda
figura = None
for c in comp:
    cx = sum(p[0] for p in c) / len(c) * ESC
    if cx < W * 0.5:
        figura = c
        break
if figura is None:
    print("no se encontro la figura")
    raise SystemExit
print("figura: %d px a 1/%d  -> %.0f px reales" % (len(figura), ESC, len(figura) * ESC * ESC))

# mapa de la figura
es_fig = [[False] * w for _ in range(h)]
for x, y in figura:
    es_fig[y][x] = True

xs = [p[0] for p in figura]
ys = [p[1] for p in figura]
X0, X1, Y0, Y1 = min(xs) * ESC, max(xs) * ESC, min(ys) * ESC, max(ys) * ESC
print("caja de la figura: x %d..%d  y %d..%d  = %d x %d" % (X0, X1, Y0, Y1, X1 - X0, Y1 - Y0))
alto = Y1 - Y0
print("proporcion alto/ancho: %.2f" % (alto / (X1 - X0)))


def clasifica(r, g, b):
    lum = (r * 299 + g * 587 + b * 114) // 1000
    mx, mn = max(r, g, b), min(r, g, b)
    if lum < 100:
        return "oscuro"
    if r > 130 and r - g > 60 and r - b > 40:
        return "rojo"
    if lum > 200 and mx - mn < 45:
        return "blanco"
    if 120 < lum < 240 and r > b + 15 and r >= g - 5:
        return "piel"
    return "otros"


print("\n=== perfil de la silueta y clases por banda ===")
print("   banda   ancho  borde_izq  borde_der  centro | piel(centro,n)  rojo(centro,n)")
for f in range(0, 100, 5):
    ya = min(ys) + int((max(ys) - min(ys)) * f / 100)
    yb = min(ys) + int((max(ys) - min(ys)) * (f + 5) / 100)
    filas = [y for y in range(ya, max(yb, ya + 1)) if any(es_fig[y])]
    if not filas:
        continue
    izq = min(min(x for x in range(w) if es_fig[y][x]) for y in filas)
    der = max(max(x for x in range(w) if es_fig[y][x]) for y in filas)
    piel, rojo = [], []
    for y in filas:
        for x in range(izq, der + 1):
            if es_fig[y][x]:
                r, g, b = px[x, y]
                c = clasifica(r, g, b)
                if c == "piel":
                    piel.append(x)
                elif c == "rojo":
                    rojo.append(x)
    p = "%d,%d" % ((min(piel) + max(piel)) // 2 * ESC, len(piel)) if piel else "-"
    rr = "%d,%d" % ((min(rojo) + max(rojo)) // 2 * ESC, len(rojo)) if rojo else "-"
    print("   %3d%%    %5d    %7d   %8d  %6d | %-16s %s"
          % (f, (der - izq) * ESC, izq * ESC, der * ESC, (izq + der) // 2 * ESC, p, rr))

# recortes: figura entera y cabeza a 2x
c = im.crop((X0, Y0, X1, Y1))
c.save(os.path.join(OUT, "40_figura.png"))
print("\n   40_figura.png  %d x %d" % c.size)
yc = Y0 + int(alto * 0.25)
cab = im.crop((X0, Y0, X1, yc))
if cab.width < 700:
    cab = cab.resize((cab.width * 2, cab.height * 2))
cab.save(os.path.join(OUT, "41_cabeza.png"))
print("   41_cabeza.png  %d x %d" % cab.size)

# mascara de la silueta, para comparar luego con el render
m = Image.new("L", (X1 - X0, Y1 - Y0), 0)
mp = m.load()
for y in range(min(ys), max(ys) + 1):
    for x in range(w):
        if es_fig[y][x]:
            for dy in range(ESC):
                for dx in range(ESC):
                    xx, yy = x * ESC - X0 + dx, y * ESC - Y0 + dy
                    if 0 <= xx < m.width and 0 <= yy < m.height:
                        mp[xx, yy] = 255
m.save(os.path.join(OUT, "42_silueta.png"))
print("   42_silueta.png %d x %d (mascara para comparar con el render)" % m.size)