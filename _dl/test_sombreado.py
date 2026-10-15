"""Pruebas de la implementacion del sombreado: dos casos que DEBEN dar identidad exacta.

1) EffectFactor = 0  -> el resultado tiene que ser la imagen original, pixel a pixel.
2) todos los tonos a 1 y un degradado blanco puro con rampa de alfa 1 -> tambien identidad.

Si alguna falla, el algebra de sombreado_lihui.py no es fiel al shader.
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, r"C:\Users\Lukas\p5x-datamining\_dl")
import sombreado_lihui as S  # noqa: E402

PNG = Path(r"C:\Users\Lukas\AppData\Local\hermes\cache\scratch\retrato_dialogo"
           r"\uitex_ichangfu6f75658d.bundle_export\CAB-38286dc0972cb5c9d028384c6a1633f6"
           r"\zhuimingyoumei-changfu-shenti.png")
JSON_REAL = Path(r"C:\Users\Lukas\p5x-datamining\_dl\lihui_shader_json"
                 r"\UI-DialogShader-richang01-zhimingyoumei.json")
SALIDA = Path(r"C:\Users\Lukas\p5x-datamining\_dl\prueba_sombreado")


def original():
    return np.asarray(Image.open(PNG).convert("RGBA"), dtype=np.int16)


print("=== 1) EffectFactor = 0 debe ser identidad ===")
p = S.leer_parametros(JSON_REAL)
p["effect_factor"] = 0.0
salida = np.asarray(S.sombrear(PNG, p), dtype=np.int16)
dif = np.abs(salida - original())
print("   pixel mas distinto:", int(dif.max()), " pixeles distintos:", int((dif.sum(-1) > 0).sum()))
print("   ->", "OK" if dif.max() == 0 else "FALLA")

print()
print("=== 2) tonos neutros + degradado blanco + rampa 1..1 debe ser identidad ===")
p = S.leer_parametros(JSON_REAL)
p.update({"effect_factor": 1.0, "brillo": 1.0, "saturacion": 1.0, "contraste": 1.0,
          "gra_brillo": 1.0, "gra_saturacion": 1.0, "gra_contraste": 1.0,
          "alfa_arriba": 1.0, "alfa_abajo": 1.0, "desenfoque": False,
          "claves_color": [(0.0, (1.0, 1.0, 1.0)), (1.0, (1.0, 1.0, 1.0))]})
salida = np.asarray(S.sombrear(PNG, p), dtype=np.int16)
dif = np.abs(salida - original())
print("   pixel mas distinto:", int(dif.max()), " pixeles distintos:", int((dif.sum(-1) > 0).sum()))
print("   ->", "OK" if dif.max() <= 1 else "FALLA")   # <=1 por el redondeo a 8 bits

print()
print("=== 3) un toque de realidad: el degradado del JSON cambia la imagen ===")
p = S.leer_parametros(JSON_REAL)
salida = np.asarray(S.sombrear(PNG, p), dtype=np.int16)
base = original()
dif = np.abs(salida - base)
opacos = base[..., 3] > 200
print("   pixel mas distinto:", int(dif.max()), "  cambio medio en pixeles opacos: %.2f"
      % float(dif[..., :3][opacos].mean()))
salida_p = S.sombrear(PNG, p)
salida_p.save(SALIDA / "verificacion_sombreado.png")
print("   guardado", SALIDA / "verificacion_sombreado.png")