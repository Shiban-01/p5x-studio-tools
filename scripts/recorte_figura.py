"""Recorta solo la figura de la ilustracion de referencia, sin el texto del fondo.

La figura esta en la franja izquierda del banner; el texto oscuro del fondo esta a la derecha y
ensuciaba la caja anterior. Se busca la caja dentro de la franja izquierda y se sacan recortes.
"""
import os
from PIL import Image

REF = r"C:\Users\Lukas\AppData\Roaming\Hermes\composer-images\image_9324d5.png"
OUT = r"C:\Users\Lukas\p5x-datamining\_dl\ref_kotone"
os.makedirs(OUT, exist_ok=True)

im = Image.open(REF).convert("RGB")
W, H = im.size
px = im.load()

def oscuro(x, y):
    r, g, b = px[x, y]
    return (r * 299 + g * 587 + b * 114) // 1000 < 95

limite = int(W * 0.45)
col = [0] * limite
for y in range(0, H, 2):
    for x in range(0, limite, 2):
        if oscuro(x, y):
            col[x] += 1
idx = [i for i, n in enumerate(col) if n > max(col) * 0.05]
x0, x1 = max(0, min(idx) - 50), min(W, max(idx) + 50)
print("franja de la figura: x %d..%d de %d" % (min(idx), max(idx), W))

fila = [0] * H
for y in range(0, H, 2):
    for x in range(x0, x1, 3):
        if oscuro(x, y):
            fila[y] += 1
idx2 = [i for i, n in enumerate(fila) if n > max(fila) * 0.04]
y0, y1 = max(0, min(idx2) - 40), min(H, max(idx2) + 40)
print("caja de la figura: x %d..%d  y %d..%d  = %d x %d" % (x0, x1, y0, y1, x1 - x0, y1 - y0))

def guardar(nombre, caja, alto_max=1400):
    c = im.crop(caja)
    if c.height > alto_max:
        c = c.resize((int(c.width * alto_max / c.height), alto_max))
    c.save(os.path.join(OUT, nombre))
    print("   %-24s %d x %d" % (nombre, c.size[0], c.size[1]))

alto = y1 - y0
print("\nrecortes:")
guardar("20_figura.png", (x0, y0, x1, y1))
guardar("21_cabeza.png", (x0, y0, x1, y0 + int(alto * 0.30)), 1100)
guardar("22_brazos_torso.png", (x0, y0 + int(alto * 0.15), x1, y0 + int(alto * 0.72)), 1200)
guardar("23_piernas.png", (x0, y0 + int(alto * 0.5), x1, y1), 1200)