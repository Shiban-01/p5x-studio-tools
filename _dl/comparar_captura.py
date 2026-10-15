"""Compara la cara del personaje en la captura del juego con las variantes que calculo aqui.

Saca una tira con las cuatro versiones y ademas mide el tono medio de la zona de la cara (color y
saturacion) para no depender solo de una lectura visual.
"""
import colorsys
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, r"C:\Users\Lukas\p5x-datamining\_dl")
import sombreado_lihui as S  # noqa: E402

CAPTURA = Path(r"C:\Users\Lukas\AppData\Roaming\Hermes\composer-images\image_781f40.png")
O = Path(r"C:\Users\Lukas\AppData\Local\hermes\cache\scratch\xiachuanling")
SALIDA = Path(r"C:\Users\Lukas\p5x-datamining\_dl\prueba_xiachuanling")
JSON_CHANGFU = Path(r"C:\Users\Lukas\p5x-datamining\_dl\lihui_shader_json"
                    r"\UI-DialogShader-changfu01-xiachuanling.json")
JSON_YINYING = Path(r"C:\Users\Lukas\p5x-datamining\_dl\lihui_shader_json"
                    r"\UI-DialogShader-yinying01-xiachuanling.json")


def capa(nombre):
    f = sorted(O.glob("xiachuanling-changfu-%s_#*.png" % nombre))
    return Image.open(f[0]).convert("RGBA")


def montar():
    base = Image.new("RGBA", capa("benti").size, (0, 0, 0, 0))
    for n in ["benti", "benti-zhi", "benti-yifu", "benti-toufa", "tongchang-yan1", "tongchang-zui1"]:
        base.alpha_composite(capa(n))
    return base


def sobre(im, fondo=(22, 26, 38, 255)):
    lona = Image.new("RGBA", im.size, fondo)
    lona.alpha_composite(im)
    return lona


def tono_medio(im, caja):
    """Color medio y tono/saturacion medios de una caja, contando solo pixeles opacos."""
    r = np.asarray(im.convert("RGBA"), dtype=np.float32)
    x0, y0, x1, y1 = caja
    trozo = r[y0:y1, x0:x1]
    rgb = trozo[..., :3][trozo[..., 3] > 200] / 255.0
    if len(rgb) == 0:
        return None
    media = rgb.mean(axis=0)
    hsv = np.array([colorsys.rgb_to_hsv(*p) for p in rgb])
    return media, hsv.mean(axis=0), len(rgb)


# recorte del personaje en la captura
cap = Image.open(CAPTURA).convert("RGBA")
W, H = cap.size
pers = cap.crop((int(W * 0.06), int(H * 0.10), int(W * 0.44), H))
print("captura:", cap.size, "| recorte personaje:", pers.size)

montaje = montar()
p_ch = S.leer_parametros(JSON_CHANGFU)
p_yi = S.leer_parametros(JSON_YINYING)
variantes = [
    ("captura", pers, None),
    ("crudo", sobre(montaje), None),
    ("changfu01 tal cual", sobre(S.sombrear_imagen(montaje, p_ch)), None),
    ("changfu01 v invertida", sobre(S.sombrear_imagen(montaje, p_ch, v_invertida=True)), None),
    ("yinying01", sobre(S.sombrear_imagen(montaje, p_yi)), None),
]

# cara: en la captura, arriba y centrada en el recorte; en el sprite, la misma zona relativa
def caja_cara(im):
    w, h = im.size
    return (int(w * 0.28), int(h * 0.03), int(w * 0.72), int(h * 0.30))


print()
print("%-26s %-22s %-22s %s" % ("variante", "color medio cara", "tono/sat", "pixeles"))
for nombre, im, _ in variantes:
    r = tono_medio(im, caja_cara(im))
    if r:
        media, hsv, n = r
        print("%-26s rgb(%.0f,%.0f,%.0f)      h=%3.0f s=%.2f v=%.2f   %d"
              % (nombre, media[0] * 255, media[1] * 255, media[2] * 255,
                 hsv[0] * 360, hsv[1], hsv[2], n))

# tira comparativa a la misma altura
alto = 620
trozos = []
for nombre, im, _ in variantes:
    esc = alto / im.height
    trozos.append(im.resize((int(im.width * esc), alto), Image.LANCZOS))
ancho = sum(t.width for t in trozos) + 16 * (len(trozos) - 1)
lona = Image.new("RGBA", (ancho, alto), (12, 12, 14, 255))
x = 0
for t in trozos:
    lona.alpha_composite(t, (x, 0))
    x += t.width + 16
lona.save(SALIDA / "comparacion_captura.png")
print()
print("tira guardada en", SALIDA / "comparacion_captura.png", lona.size)
print("orden:", " | ".join(n for n, _, _ in variantes))