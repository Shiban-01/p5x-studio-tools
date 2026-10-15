"""Encuadra la figura por sus zonas oscuras (blazer, pelo) y saca recortes estrechos.

El banner lleva texto semitransparente, asi que la silueta por color no sirve. La figura es lo
unico oscuro: con eso se saca una caja fiable y recortes que el visor pueda leer enteros.
"""
import os
from PIL import Image

REF = r"C:\Users\Lukas\AppData\Roaming\Hermes\composer-images\image_9324d5.png"
OUT = r"C:\Users\Lukas\p5x-datamining\_dl\ref_kotone"
os.makedirs(OUT, exist_ok=True)

im = Image.open(REF).convert("RGB")
W, H = im.size
px = im.load()

# columnas y filas con pixeles oscuros (blazer negro, pelo castano oscuro)
col = [0] * W
fila = [0] * H
for y in range(0, H, 2):
    for x in range(0, W, 2):
        r, g, b = px[x, y]
        if (r * 299 + g * 587 + b * 114) // 1000 < 95:
            col[x] += 1
            fila[y] += 1

def extremos(v, umbral):
    idx = [i for i, n in enumerate(v) if n > umbral]
    return (min(idx), max(idx)) if idx else None

umbral_col = max(col) * 0.06
umbral_fila = max(fila) * 0.06
cx = extremos(col, umbral_col)
cy = extremos(fila, umbral_fila)
print("columnas con figura: %s de %d" % (cx, W))
print("filas con figura:    %s de %d" % (cy, H))

# el cuerpo esta en la banda de columnas; se recorta con margen
x0 = max(0, cx[0] - 40)
x1 = min(W, cx[1] + 40)
y0 = max(0, cy[0] - 40)
y1 = min(H, cy[1] + 40)
print("caja de la figura: (%d, %d) - (%d, %d)  = %d x %d" % (x0, y0, x1, y1, x1 - x0, y1 - y0))

def guardar(nombre, caja, alto_max=1500):
    c = im.crop(caja)
    if c.height > alto_max:
        c = c.resize((int(c.width * alto_max / c.height), alto_max))
    c.save(os.path.join(OUT, nombre))
    print("   %-22s %d x %d" % (nombre, c.size[0], c.size[1]))

print("\nrecortes:")
guardar("10_figura.png", (x0, y0, x1, y1))
alto = y1 - y0
guardar("11_cara.png", (x0, y0, x1, y0 + alto // 4), 1000)
guardar("12_torso_brazos.png", (x0, y0 + alto // 5, x1, y0 + int(alto * 0.7)), 1200)
guardar("13_piernas.png", (x0, y0 + int(alto * 0.55), x1, y1), 1200)