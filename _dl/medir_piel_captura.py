"""Mide el tono de la piel (los pixeles mas claros de la zona de la cara) en la captura y en mis
variantes. Solo cuenta pixeles del sprite (alfa alto en el montaje) para no medir el fondo.
"""
import colorsys
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, r"C:\Users\Lukas\p5x-datamining\_dl")
import sombreado_lihui as S  # noqa: E402
import comparar_captura as C  # noqa: E402


def piel(im, caja, mascara=None, cuantos=0.3):
    """Tono medio de los pixeles mas claros (la piel) dentro de una caja."""
    r = np.asarray(im.convert("RGBA"), dtype=np.float32)
    x0, y0, x1, y1 = caja
    rgb = r[y0:y1, x0:x1, :3] / 255.0
    val = r[y0:y1, x0:x1, 3] > 200
    if mascara is not None:
        val &= mascara[y0:y1, x0:x1]
    v = rgb.max(axis=-1)
    umbral = np.quantile(v[val], 1 - cuantos) if val.any() else 1.0
    sel = val & (v >= umbral)
    if not sel.any():
        return None
    m = rgb[sel]
    hsv = np.array([colorsys.rgb_to_hsv(*p) for p in m])
    return m.mean(axis=0), hsv.mean(axis=0), int(sel.sum())


montaje = C.montar()
mascara = np.asarray(montaje, dtype=np.float32)[..., 3] > 200
p_ch = S.leer_parametros(C.JSON_CHANGFU)
p_yi = S.leer_parametros(C.JSON_YINYING)

paneles = [
    ("captura del juego", C.pers, None),
    ("crudo (sin sombra)", C.sobre(montaje), mascara),
    ("changfu01 tal cual", C.sobre(S.sombrear_imagen(montaje, p_ch)), mascara),
    ("changfu01 v invertida", C.sobre(S.sombrear_imagen(montaje, p_ch, v_invertida=True)), mascara),
    ("yinying01", C.sobre(S.sombrear_imagen(montaje, p_yi)), mascara),
]

print("%-24s %-20s %-24s %s" % ("variante", "piel media", "hsv", "pix"))
ref = None
for nombre, im, masc in paneles:
    r = piel(im, (0, 0) + im.size, masc, cuantos=0.15)
    if not r:
        print("%-24s (sin pixeles)" % nombre)
        continue
    media, hsv, n = r
    rgb255 = tuple(int(round(x * 255)) for x in media)
    etiqueta = "#%02X%02X%02X" % rgb255
    if ref is None:
        ref = media
        print("%-24s %s  rgb%-18s h=%3.0f s=%.2f v=%.2f  %d"
              % (nombre, etiqueta, str(rgb255), hsv[0] * 360, hsv[1], hsv[2], n))
    else:
        d = float(np.abs(media - ref).mean() * 255)
        print("%-24s %s  rgb%-18s h=%3.0f s=%.2f v=%.2f  %d   distancia a la captura: %.1f/255"
              % (nombre, etiqueta, str(rgb255), hsv[0] * 360, hsv[1], hsv[2], n, d))