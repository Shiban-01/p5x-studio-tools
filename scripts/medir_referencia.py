"""Mide la figura de la referencia: silueta, piel (cara y manos), rojo y oscuro.

La descripcion por vision se contradice a si misma, asi que la pose se saca midiendo: donde estan
la cara y las manos (piel), donde el pelo y el blazer (oscuro), donde el lacito y el brazalete
(rojo), y como se ensancha la silueta a cada altura. Con eso se decide que brazo y que pierna van
delante sin depender de una interpretacion.
"""
import os
from PIL import Image

REF = r"C:\Users\Lukas\AppData\Roaming\Hermes\composer-images\image_9324d5.png"
OUT = r"C:\Users\Lukas\p5x-datamining\_dl\ref_kotone"
os.makedirs(OUT, exist_ok=True)

im = Image.open(REF).convert("RGB")
W, H = im.size
px = im.load()

X0, X1 = 600, 2000          # franja de la figura (medida antes: 670..1922, con margen)
Y0, Y1 = 0, H

def clasifica(r, g, b):
    """devuelve 'piel', 'oscuro', 'rojo', 'blanco' o None"""
    lum = (r * 299 + g * 587 + b * 114) // 1000
    mx, mn = max(r, g, b), min(r, g, b)
    if lum < 95:
        return "oscuro"
    # rojo saturado (lacito, brazalete, aparato de la cadera)
    if r > 120 and r - g > 70 and r - b > 50 and mx - mn > 80:
        return "rojo"
    if lum > 205 and mx - mn < 40:
        return "blanco"
    # piel: mas rojo que azul, claro, sin llegar a blanco
    if 130 < lum < 235 and r > b + 18 and r >= g >= b - 10:
        return "piel"
    return None

# silueta = todo lo que no sea el fondo (blanco del lienzo o magenta)
FONDO = [(255, 255, 255), (255, 99, 142)]

def es_fondo(r, g, b):
    for fr, fg, fb in FONDO:
        if abs(r - fr) + abs(g - fg) + abs(b - fb) < 40:
            return True
    return False

filas = {}
cuenta = {"piel": 0, "oscuro": 0, "rojo": 0, "blanco": 0}
for y in range(Y0, Y1, 2):
    izq = der = None
    for x in range(X0, X1, 2):
        r, g, b = px[x, y]
        if not es_fondo(r, g, b):
            if izq is None:
                izq = x
            der = x
            c = clasifica(r, g, b)
            if c:
                cuenta[c] += 1
    if izq is not None:
        filas[y] = (izq, der)

ys = sorted(filas)
print("filas con figura: %d..%d" % (ys[0], ys[-1]))
alto = ys[-1] - ys[0]
print("altura de la figura: %d px" % alto)
print("recuento de clases:", cuenta)

print("\n=== perfil de anchura (cada 5%% de la altura) ===")
print("   %altura   ancho   centro   borde_izq  borde_der")
for f in range(0, 101, 5):
    y = ys[0] + int(alto * f / 100)
    y = min(y, ys[-1])
    if y in filas:
        izq, der = filas[y]
        print("   %3d%%     %4d    %6d   %7d   %8d" % (f, der - izq, (izq + der) // 2, izq, der))

# extremos: el punto mas alto, el mas bajo, el mas a la izquierda y el mas a la derecha
mas_izq = min(filas.items(), key=lambda kv: kv[1][0])
mas_der = max(filas.items(), key=lambda kv: kv[1][1])
print("\n=== extremos ===")
print("   punto mas alto:  y=%d  (x %d..%d)" % (ys[0], filas[ys[0]][0], filas[ys[0]][1]))
print("   punto mas bajo:  y=%d  (x %d..%d)" % (ys[-1], filas[ys[-1]][0], filas[ys[-1]][1]))
print("   mas a la izquierda: x=%d en y=%d" % (mas_izq[1][0], mas_izq[0]))
print("   mas a la derecha:   x=%d en y=%d" % (mas_der[1][1], mas_der[0]))

# mapa de clases por zonas, para localizar cara y manos
print("\n=== donde esta la piel (cara y manos), en bandas de 10%% ===")
for f in range(0, 100, 10):
    ya, yb = ys[0] + int(alto * f / 100), ys[0] + int(alto * (f + 10) / 100)
    xs = []
    for y in range(ya, min(yb, ys[-1]), 3):
        for x in range(X0, X1, 3):
            r, g, b = px[x, y]
            if clasifica(r, g, b) == "piel":
                xs.append(x)
    if xs:
        print("   %3d%%-%3d%%  piel: x %d..%d  centro %d  (%d px)" % (f, f + 10, min(xs), max(xs), (min(xs) + max(xs)) // 2, len(xs)))
    else:
        print("   %3d%%-%3d%%  sin piel" % (f, f + 10))

print("\n=== donde esta el rojo (lacito, brazalete, aparato) ===")
for f in range(0, 100, 10):
    ya, yb = ys[0] + int(alto * f / 100), ys[0] + int(alto * (f + 10) / 100)
    xs = []
    for y in range(ya, min(yb, ys[-1]), 3):
        for x in range(X0, X1, 3):
            r, g, b = px[x, y]
            if clasifica(r, g, b) == "rojo":
                xs.append(x)
    if xs:
        print("   %3d%%-%3d%%  rojo: x %d..%d  centro %d  (%d px)" % (f, f + 10, min(xs), max(xs), (min(xs) + max(xs)) // 2, len(xs)))

# recorte de la cabeza a buena resolucion para leer la cara
y_cara = ys[0] + int(alto * 0.22)
c = im.crop((X0, ys[0], X1, y_cara))
c = c.resize((c.width * 2, c.height * 2)) if c.width < 700 else c
c.save(os.path.join(OUT, "30_cabeza_zoom.png"))
print("\n   recorte de cabeza: %d x %d  -> 30_cabeza_zoom.png" % c.size)