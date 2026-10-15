"""Compara el sombreado tal cual dice el GLSL (sin tope) con el tope en el tono del degradado.

Mide, en el mismo montaje de la app: cuanto calidez suma el shader a los pixeles claros, y para
xiachuanling (el unico con captura del juego) la distancia de la piel a esa captura.
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

DL = Path(r"C:\Users\Lukas\p5x-datamining\_dl")
sys.path.insert(0, str(DL))
sys.path.insert(0, r"C:\Users\Lukas\p5x-datamining\p5x_studio")
import sombreado_lihui as S  # noqa: E402
from p5x_studio import bustups  # noqa: E402

CARPETA = Path(r"C:\Users\Lukas\Desktop\P5X Studio Tools\extracted\portraits")
CAPTURA = np.array([0xE7, 0xD4, 0xBC]) / 255.0
LUM = np.array([0.2125, 0.7154, 0.0721], dtype=np.float32)


def claros(im):
    a = np.asarray(im.convert("RGBA"), dtype=np.float32)
    rgb = a[..., :3] / 255.0
    vis = a[..., 3] > 128
    lum = (rgb * LUM).sum(-1)
    sel = vis & (lum > 0.82)
    if sel.sum() < 100:
        return None
    return rgb[sel].mean(0)


datos = json.loads((DL / "emparejado_bustups.json").read_text(encoding="utf-8"))["emparejados"]
print("%-30s | %-22s | %-22s" % ("bust-up", "sin tope (GLSL literal)", "con tope"))
print("-" * 82)
filas = []
for clave in sorted(datos)[:12]:
    r = bustups.montar(clave, None, CARPETA, guardar=True)
    if not r.get("ok"):
        continue
    m = Image.open(r["ruta"]).convert("RGBA")
    p = S.leer_parametros(DL / "lihui_shader_json" / ("%s.json" % clave))
    c0 = claros(m)
    c_sin = claros(S.sombrear_imagen(m, p, tope=False))
    c_con = claros(S.sombrear_imagen(m, p, tope=True))
    if c0 is None or c_sin is None or c_con is None:
        continue
    fmt = lambda c: "#%02X%02X%02X %+.3f" % (int(c[0] * 255), int(c[1] * 255), int(c[2] * 255), float(c[0] - c[2]))
    print("%-30s | %-22s | %-22s" % (clave.replace("UI-DialogShader-", ""), fmt(c_sin), fmt(c_con)))
    filas.append((c0, c_sin, c_con))

a = np.array([float(x[0][0] - x[0][2]) for x in filas])
s = np.array([float(x[1][0] - x[1][2]) - float(x[0][0] - x[0][2]) for x in filas])
t = np.array([float(x[2][0] - x[2][2]) - float(x[0][0] - x[0][2]) for x in filas])
print()
print("calidez (R-B) que SUMA el shader, sobre %d bust-ups:" % len(filas))
print("   crudo   media %+.3f" % a.mean())
print("   sin tope: media %+.3f  max %+.3f" % (s.mean(), s.max()))
print("   con tope: media %+.3f  max %+.3f" % (t.mean(), t.max()))

# el unico con captura del juego
clave = "UI-DialogShader-changfu01-xiachuanling"
r = bustups.montar(clave, None, CARPETA, guardar=True)
m = Image.open(r["ruta"]).convert("RGBA")
p = S.leer_parametros(DL / "lihui_shader_json" / ("%s.json" % clave))
print()
print("contra la captura del juego (piel #E7D4BC):")
for nombre, im in (("crudo", m),
                   ("sin tope", S.sombrear_imagen(m, p, tope=False)),
                   ("con tope", S.sombrear_imagen(m, p, tope=True))):
    c = claros(im)
    if c is None:
        continue
    d = float(np.abs(c - CAPTURA).mean() * 255)
    print("   %-10s #%02X%02X%02X   distancia %.1f/255" % (nombre, int(c[0] * 255), int(c[1] * 255), int(c[2] * 255), d))