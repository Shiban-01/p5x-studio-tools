"""Mide la piel de las dos figuras de la comparacion del usuario (juego a la izquierda, nuestra a la derecha).

Las cajas salen de mirar la imagen; aqui se comprueban (que haya piel de verdad dentro) y se saca el
color medio, para saber cuanto mas amarilla es la nuestra.
"""
from pathlib import Path

import numpy as np
from PIL import Image

ORIGEN = Path(r"C:\Users\Lukas\AppData\Roaming\Hermes\composer-images\image_be4a7c.png")
SALIDA = Path(r"C:\Users\Lukas\p5x-datamining\_dl\prueba_sombreado\comparacion_usuario")
SALIDA.mkdir(parents=True, exist_ok=True)

im = Image.open(ORIGEN).convert("RGB")
a = np.asarray(im, dtype=np.float32)

CAJAS = {
    "juego (izquierda)": (118, 288, 282, 468),
    "nuestra (derecha)": (352, 278, 542, 492),
}


def piel(rgb):
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    lum = 0.2125 * r + 0.7154 * g + 0.0721 * b
    return (lum > 120) & (r > 150) & (r >= g) & (g >= b) & ((r - b) > 12) & ((r - b) < 95) & (b < 235)


res = {}
for nombre, (x0, y0, x1, y1) in CAJAS.items():
    trozo = a[y0:y1, x0:x1]
    m = piel(trozo)
    rgb = trozo[m]
    if len(rgb) < 200:
        print("%-20s (poca piel: %d px, revisar la caja)" % (nombre, len(rgb)))
        continue
    lum = rgb @ np.array([0.2125, 0.7154, 0.0721])
    corte = np.percentile(lum, 55)
    medio = rgb.mean(0)
    claro = rgb[lum > corte].mean(0)
    oscuro = rgb[lum <= corte].mean(0)
    print("%-20s piel %d px (%.1f%% de la caja)" % (nombre, len(rgb), 100.0 * m.mean()))
    print("   media    #%02X%02X%02X   R %5.1f G %5.1f B %5.1f   calidez %+6.2f   saturacion(R-B)/R %.3f"
          % (int(medio[0]), int(medio[1]), int(medio[2]), medio[0], medio[1], medio[2],
             medio[0] - medio[2], (medio[0] - medio[2]) / max(medio[0], 1)))
    print("   luz      #%02X%02X%02X   R %5.1f G %5.1f B %5.1f   calidez %+6.2f"
          % (int(claro[0]), int(claro[1]), int(claro[2]), claro[0], claro[1], claro[2], claro[0] - claro[2]))
    print("   sombra   #%02X%02X%02X   R %5.1f G %5.1f B %5.1f   calidez %+6.2f"
          % (int(oscuro[0]), int(oscuro[1]), int(oscuro[2]), oscuro[0], oscuro[1], oscuro[2], oscuro[0] - oscuro[2]))
    res[nombre] = (medio, claro, oscuro)
    im.crop((x0, y0, x1, y1)).save(SALIDA / ("cara_%s.png" % nombre.split()[0]))

print()
if len(res) == 2:
    (n1, v1), (n2, v2) = list(res.items())
    print("nuestra - juego:")
    for i, etiqueta in enumerate(["media", "luz", "sombra"]):
        d = v2[i] - v1[i]
        print("   %-7s R %+6.1f  G %+6.1f  B %+6.1f   calidez %+6.2f" % (etiqueta, d[0], d[1], d[2], (d[0] - d[2])))
print("\nrecortes en", SALIDA)