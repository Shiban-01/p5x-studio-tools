"""Decide de donde saca la rampa de alfa sus dos POSICIONES, midiendo contra la captura del juego.

El GLSL usa `_GradientAlphaBottomPosition` / `_GradientAlphaTopPosition` (mas los dos valores
`GradientAlphaBottom/Top` = 0.274 y 1.0 del JSON). Esas dos posiciones no vienen en el fichero: las
calcula el C#. Los candidatos son las paradas de la curva de alfa o las del color. Se prueban ambas.
"""
import sys

import numpy as np

sys.path.insert(0, r"C:\Users\Lukas\p5x-datamining\_dl")
import comparar_captura as C  # noqa: E402
import medir_piel_captura as M  # noqa: E402
import sombreado_lihui as S  # noqa: E402


def main():
    montaje = C.montar()
    mascara = np.asarray(montaje, dtype=np.float32)[..., 3] > 200
    p = S.leer_parametros(C.JSON_CHANGFU)

    ref = M.piel(C.pers, (0, 0) + C.pers.size, None, cuantos=0.15)
    rgb255 = tuple(int(round(x * 255)) for x in ref[0])
    print("captura del juego: #%02X%02X%02X  rgb%s  h=%3.0f s=%.2f v=%.2f\n"
          % (*rgb255, str(rgb255), ref[1][0] * 360, ref[1][1], ref[1][2]))

    t_alfa = (float(p["claves_alfa"][0][0]), float(p["claves_alfa"][-1][0]))
    t_color = (float(p["claves_color"][0][0]), float(p["claves_color"][-1][0]))
    valores = [p["alfa_abajo"], p["alfa_arriba"]]

    casos = [
        ("posiciones de las claves de alfa (actual)", t_alfa),
        ("posiciones de las claves de color", t_color),
        ("tramo 0..1 entero", (0.0, 1.0)),
    ]

    print("%-42s %-22s %-26s %s" % ("posiciones de la rampa", "piel media", "hsv", "distancia a la captura"))
    for nombre, (a, b) in casos:
        q = dict(p)
        q["claves_alfa"] = [(a, valores[0]), (b, valores[1])]
        im = S.sombrear_imagen(montaje, q)
        r = M.piel(im, (0, 0) + im.size, mascara, cuantos=0.15)
        media, hsv, n = r
        m = tuple(int(round(x * 255)) for x in media)
        d = float(np.abs(media - ref[0]).mean() * 255)
        print("%-42s #%02X%02X%02X  rgb%-18s h=%3.0f s=%.2f v=%.2f   %.1f/255   (R %+.1f G %+.1f B %+.1f)"
              % (nombre, *m, str(m), hsv[0] * 360, hsv[1], hsv[2], d, *((media - ref[0]) * 255)))
    return 0


if __name__ == "__main__":
    sys.exit(main())