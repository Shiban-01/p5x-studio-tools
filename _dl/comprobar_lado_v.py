"""Comprueba, con el montaje de la propia app, en que sentido va el degradado.

La captura del juego de xiachuanling tiene la piel en #E7D4BC. Se mide la piel (los pixeles mas
claros del retrato) con el degradado normal y con la v invertida, y se ve cual se acerca mas.
"""
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
CAPTURA = (0xE7, 0xD4, 0xBC)
CLAVES = ["UI-DialogShader-changfu01-xiachuanling", "UI-DialogShader-changfu01-lizi",
          "UI-DialogShader-changfu-xindaozhen"]


def piel(im, cuantos=0.15):
    r = np.asarray(im.convert("RGBA"), dtype=np.float32)
    rgb = r[..., :3] / 255.0
    val = r[..., 3] > 200
    v = rgb.max(axis=-1)
    umbral = np.quantile(v[val], 1 - cuantos) if val.any() else 1.0
    sel = val & (v >= umbral)
    if not sel.any():
        return None
    return rgb[sel].mean(0)


def hexa(c):
    return "#%02X%02X%02X" % tuple(int(round(x * 255)) for x in c)


for clave in CLAVES:
    r = bustups.montar(clave, None, CARPETA, guardar=True)
    if not r.get("ok"):
        print("%-44s no monta" % clave)
        continue
    montaje = Image.open(r["ruta"]).convert("RGBA")
    p = S.leer_parametros(DL / "lihui_shader_json" / ("%s.json" % clave))
    c_crudo = piel(montaje)
    c_normal = piel(S.sombrear_imagen(montaje, p))
    c_volteado = piel(S.sombrear_imagen(montaje, p, v_invertida=True))

    def dist(c):
        return float(np.abs(np.array(c) - np.array(CAPTURA) / 255.0).mean() * 255)

    print("%-44s lienzo %s" % (clave.replace("UI-DialogShader-", ""), montaje.size))
    print("    crudo          %s   (a la captura: %.1f/255)" % (hexa(c_crudo), dist(c_crudo)))
    print("    normal         %s   (a la captura: %.1f/255)" % (hexa(c_normal), dist(c_normal)))
    print("    v invertida    %s   (a la captura: %.1f/255)" % (hexa(c_volteado), dist(c_volteado)))