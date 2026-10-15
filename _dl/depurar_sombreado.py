"""Depura UN bust-up paso a paso: donde se cuela el amarillo y si el EffectFactor se respeta.

Uso:  depurar_sombreado.py <clave-o-trozo> [carpeta]
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


def main():
    trozo = sys.argv[1]
    datos = json.loads((DL / "emparejado_bustups.json").read_text(encoding="utf-8"))["emparejados"]
    claves = [k for k in datos if trozo in k]
    if not claves:
        print("no encuentro", trozo)
        return 1
    clave = claves[0]
    print("bust-up:", clave)

    r = bustups.montar(clave, None, CARPETA, guardar=True)
    crudo = Image.open(r["ruta"]).convert("RGBA")
    p = S.leer_parametros(DL / "lihui_shader_json" / ("%s.json" % clave))
    print("parametros: EF %.3f | base %.2f/%.2f/%.2f | gra %.2f/%.2f/%.2f | alfa %.3f..%.3f | alfa pos %.4f..%.4f"
          % (p["effect_factor"], p["brillo"], p["saturacion"], p["contraste"],
             p["gra_brillo"], p["gra_saturacion"], p["gra_contraste"],
             p["alfa_abajo"], p["alfa_arriba"], p["claves_alfa"][0][0], p["claves_alfa"][-1][0]))
    print("claves de color:")
    for t, c in p["claves_color"]:
        print("   t=%.4f  #%02X%02X%02X  (B/R %.2f)" % (t, int(c[0] * 255), int(c[1] * 255), int(c[2] * 255),
                                                        (c[2] / c[0]) if c[0] else 0))

    # repetir la cuenta a mano sobre los pixeles claros
    a = np.asarray(crudo, dtype=np.float32) / 255.0
    col, alfa = a[..., :3], a[..., 3]
    alto, ancho = col.shape[:2]
    u = (np.arange(ancho, dtype=np.float32) + 0.5) / ancho
    v = 1.0 - (np.arange(alto, dtype=np.float32) + 0.5) / alto
    U, V = np.meshgrid(u, v)
    ang = np.radians(p["angulo"])
    lin = (U - 0.5) * np.sin(-ang) + (V - 0.5) * np.cos(ang) + 0.5
    rad = np.sqrt(((U - p["centro"][0]) * p["proporcion"][0]) ** 2
                  + ((V - p["centro"][1]) * p["proporcion"][1]) ** 2) * 2.0
    coord = lin + p["modo"] * (rad - lin)
    pos, cols = S.muestrear_8(p["claves_color"])
    g = S.degradado_8(coord, pos, cols)
    base = S.tono(col, p["brillo"], p["saturacion"], p["contraste"])
    g_t = S.tono(g * p["gra_brillo"], 1.0, p["gra_saturacion"], p["gra_contraste"])
    gra = g_t * base
    btm, top = float(p["claves_alfa"][0][0]), float(p["claves_alfa"][-1][0])
    t = np.minimum(np.maximum(coord - btm, 0.001) / max(top - btm, 0.001), 1.0)
    ga = (t * (p["alfa_arriba"] - p["alfa_abajo"]) + p["alfa_abajo"])
    ga = np.where(coord <= btm, p["alfa_abajo"], np.where(coord >= top, p["alfa_arriba"], ga))
    mezcla = base + ga[..., None] * (gra - base)
    final = col + p["effect_factor"] * (mezcla - col)

    # pixeles claros
    lum = (col * np.array([0.2125, 0.7154, 0.0721])).sum(-1)
    claros = (alfa > 0.5) & (lum > 0.82)
    print()
    print("pixeles claros analizados: %d" % claros.sum())
    def m(x, nombre):
        if x.ndim == 3:
            c = x[claros].mean(0)
            print("   %-24s #%02X%02X%02X   B/R %.3f" % (nombre, int(c[0]*255), int(c[1]*255), int(c[2]*255),
                                                          c[2]/c[0] if c[0] else 0))
        else:
            print("   %-24s media %.4f  min %.4f  max %.4f" % (nombre, x[claros].mean(), x[claros].min(), x[claros].max()))
    m(col, "1 textura (col)")
    m(base, "2 tono base")
    m(g, "3 degradado crudo")
    m(g_t, "4 degradado con su tono")
    m(gra, "5 degradado x base")
    m(ga, "6 rampa de alfa (ga)")
    m(mezcla, "7 mezcla")
    m(final, "8 FINAL")
    print()
    print("   coord en los claros    media %.4f  min %.4f  max %.4f" % (coord[claros].mean(), coord[claros].min(), coord[claros].max()))
    print("   con EF %.3f la mezcla aporta el %.1f%% del cambio de la 7 a la 8" % (p["effect_factor"], p["effect_factor"]*100))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())