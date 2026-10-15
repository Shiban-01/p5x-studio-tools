"""Mide el modelo de sombreado correcto (ga constante, sacado del codigo del juego) contra la captura.

Hallazgo: en UIMultipleMaterial.Update(), `_GradientAlphaBottomPosition` se pone a 0.0 con `xorps xmm2,
xmm2` y `_GradientAlphaTopPosition` se lee de una constante del .rdata que tambien vale 0.0. Con las dos
posiciones a 0 y coord >= 0 (el GLSL compara `coord >= TopPosition`), la rampa se queda en
`_GradientAlphaTop`: o sea, el degradado se mezcla a plena fuerza y `GradientAlphaBottom` no se usa.

Aqui se comparan, contra la piel de la captura del juego:
  A  lo que habia (rampa entre las posiciones de las claves de color, con tope)
  B  ga = GradientAlphaTop (lo que dice el codigo), sin tope
  C  ga = GradientAlphaTop, con tope
  D  la rampa vieja (posiciones de las claves de alfa) para ver de donde venimos
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
    r255 = tuple(int(round(x * 255)) for x in ref[0])
    print("captura del juego: #%02X%02X%02X  rgb%s\n" % (*r255, str(r255)))

    def con_posiciones(abajo, arriba):
        q = dict(p)
        q["pos_alfa_abajo"], q["pos_alfa_arriba"] = abajo, arriba
        return q

    t_color = (float(p["claves_color"][0][0]), float(p["claves_color"][-1][0]))
    t_alfa = (float(p["claves_alfa"][0][0]), float(p["claves_alfa"][-1][0]))

    casos = [
        ("A  rampa con posiciones de color (lo que habia)", con_posiciones(*t_color), {"tope": True}),
        ("B  0..1, las del codigo, sin tope", con_posiciones(0.0, 1.0), {"tope": False}),
        ("C  0..1, las del codigo, con tope", con_posiciones(0.0, 1.0), {"tope": True}),
        ("D  rampa con posiciones de alfa (lo anterior)", con_posiciones(*t_alfa), {"tope": True}),
    ]

    print("%-46s %-22s %-24s %s" % ("variante", "piel", "hsv", "distancia"))
    for nombre, pp, kw in casos:
        im = S.sombrear_imagen(montaje, pp, **kw)
        r = M.piel(im, (0, 0) + im.size, mascara, cuantos=0.15)
        media, hsv, n = r
        m = tuple(int(round(x * 255)) for x in media)
        d = float(np.abs(media - ref[0]).mean() * 255)
        print("%-46s #%02X%02X%02X  rgb%-18s h=%3.0f s=%.2f v=%.2f   %.1f/255  (R %+.1f G %+.1f B %+.1f)"
              % (nombre, *m, str(m), hsv[0] * 360, hsv[1], hsv[2], d, *((media - ref[0]) * 255)))
    return 0


if __name__ == "__main__":
    sys.exit(main())