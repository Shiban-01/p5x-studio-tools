"""Localiza las dos caras de la comparacion del usuario y mide el color de la piel de cada una.

Busca la piel (pixeles calidos y claros) y la separa en grupos por columnas; de cada grupo saca el
color medio de la piel. Asi se ve cual es mas amarilla sin depender de etiquetas.
"""
from pathlib import Path

import numpy as np
from PIL import Image

ORIGEN = Path(r"C:\Users\Lukas\AppData\Roaming\Hermes\composer-images\image_be4a7c.png")
SALIDA = Path(r"C:\Users\Lukas\p5x-datamining\_dl\prueba_sombreado\comparacion_usuario")
SALIDA.mkdir(parents=True, exist_ok=True)

im = Image.open(ORIGEN).convert("RGB")
a = np.asarray(im, dtype=np.float32)
alto, ancho = a.shape[:2]

r, g, b = a[..., 0], a[..., 1], a[..., 2]
lum = 0.2125 * r + 0.7154 * g + 0.0721 * b
piel = (lum > 140) & (r > 170) & (r >= g) & (g >= b) & ((r - b) > 10) & ((r - b) < 90) & (b < 230)
print("imagen %s   pixeles de piel: %d (%.1f%%)" % (im.size, piel.sum(), 100.0 * piel.sum() / piel.size))

columnas = piel.sum(0)
# separa en grupos por columnas con piel, dejando un hueco minimo entre grupos
grupos, inicio, hueco = [], None, 0
for x in range(ancho):
    if columnas[x] > 3:
        if inicio is None:
            inicio = x
        hueco = 0
    elif inicio is not None:
        hueco += 1
        if hueco > max(24, ancho // 40):
            grupos.append((inicio, x - hueco))
            inicio = None
if inicio is not None:
    grupos.append((inicio, ancho - 1))
grupos = [t for t in grupos if piel[:, t[0]:t[1] + 1].sum() > 400]
print("grupos de piel:", grupos)

for i, (x0, x1) in enumerate(grupos):
    sel = piel.copy()
    sel[:, :x0] = False
    sel[:, x1 + 1:] = False
    filas = np.argwhere(sel)
    y0, y1 = filas[:, 0].min(), filas[:, 0].max()
    rgb = a[sel]
    media = rgb.mean(0)
    claro = rgb[rgb @ np.array([0.2125, 0.7154, 0.0721]) > np.percentile(rgb @ np.array([0.2125, 0.7154, 0.0721]), 60)]
    mc = claro.mean(0)
    print("\ngrupo %d: x %d..%d  y %d..%d   (%d pixeles de piel)" % (i + 1, x0, x1, y0, y1, len(rgb)))
    print("   piel (todos)   R %5.1f G %5.1f B %5.1f   calidez %+6.2f" % (media[0], media[1], media[2], media[0] - media[2]))
    print("   piel (claros)  #%02X%02X%02X   R %5.1f G %5.1f B %5.1f   calidez %+6.2f"
          % (int(mc[0]), int(mc[1]), int(mc[2]), mc[0], mc[1], mc[2], mc[0] - mc[2]))
    im.crop((max(0, x0 - 20), max(0, y0 - 20), min(ancho, x1 + 20), min(alto, y1 + 20))).save(
        SALIDA / ("cara_%d.png" % (i + 1)))
    print("   recorte: %s" % (SALIDA / ("cara_%d.png" % (i + 1))))

if len(grupos) == 2:
    a1 = a.copy(); a1[:, :] = False
    medias = []
    for (x0, x1) in grupos:
        sel = piel.copy(); sel[:, :x0] = False; sel[:, x1 + 1:] = False
        rgb = a[sel]
        medias.append(rgb.mean(0))
    d = medias[1] - medias[0]
    print("\ndiferencia (grupo 2 - grupo 1): R %+.1f G %+.1f B %+.1f  |  calidez %+.2f"
          % (d[0], d[1], d[2], (medias[1][0] - medias[1][2]) - (medias[0][0] - medias[0][2])))