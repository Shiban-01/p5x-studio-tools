"""Compara espacio gamma contra espacio lineal midiendo piel y contraste, contra la captura.

Si el juego va en espacio de color lineal, la multiplicacion del degradado ocurre en lineal y las
medias tintas salen mas claras que haciendolo en gamma. Aqui se mide: tono de piel y desviacion
tipica de la luminancia (contraste) en los pixeles del sprite.
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, r"C:\Users\Lukas\p5x-datamining\_dl")
import sombreado_lihui as S  # noqa: E402
import comparar_captura as C  # noqa: E402
from medir_piel_captura import piel  # noqa: E402

montaje = C.montar()
mascara = np.asarray(montaje, dtype=np.float32)[..., 3] > 200
p = S.leer_parametros(C.JSON_CHANGFU)


def luminancia(im, masc):
    r = np.asarray(im.convert("RGBA"), dtype=np.float32) / 255.0
    lum = (r[..., :3] * np.array([0.2125, 0.7154, 0.0721])).sum(-1)
    val = r[..., 3] > (200.0 / 255.0)
    if masc is not None:
        val &= masc
    return lum[val]


variantes = [
    ("captura del juego", C.pers, None),
    ("crudo", C.sobre(montaje), mascara),
    ("gamma (tal cual)", C.sobre(S.sombrear_imagen(montaje, p)), mascara),
    ("lineal", C.sobre(S.sombrear_imagen(montaje, p, lineal=True)), mascara),
]

print("%-22s %-22s %-24s %s" % ("variante", "piel", "hsv", "luminancia (media +- desv)"))
ref = None
for nombre, im, masc in variantes:
    r = piel(im, (0, 0) + im.size, masc, cuantos=0.15)
    lum = luminancia(im, masc)
    if not r:
        continue
    media, hsv, n = r
    rgb255 = tuple(int(round(x * 255)) for x in media)
    etiqueta = "#%02X%02X%02X" % rgb255
    if ref is None:
        ref = media
        extra = ""
    else:
        extra = "   dist piel: %.1f/255" % float(np.abs(media - ref).mean() * 255)
    print("%-22s %s  h=%3.0f s=%.2f v=%.2f   %.3f +- %.3f%s"
          % (nombre, etiqueta, hsv[0] * 360, hsv[1], hsv[2], lum.mean(), lum.std(), extra))

# tira comparativa gamma vs lineal
alto = 700
trozos = []
for nombre, im, _ in variantes[2:]:
    esc = alto / im.height
    trozos.append(im.resize((int(im.width * esc), alto), Image.LANCZOS))
esc = alto / C.pers.height
trozos.insert(0, C.pers.resize((int(C.pers.width * esc), alto), Image.LANCZOS))
lona = Image.new("RGBA", (sum(t.width for t in trozos) + 24 * 2, alto), (12, 12, 14, 255))
x = 0
for t in trozos:
    lona.alpha_composite(t, (x, 0))
    x += t.width + 24
salida = C.SALIDA / "gamma_vs_lineal.png"
lona.save(salida)
print()
print("tira guardada en", salida, lona.size)
print("orden: captura | gamma | lineal")