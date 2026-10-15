"""Compara en que espacio de color hace las cuentas el juego, midiendo la piel contra la captura.

Nuestra piel sale mas calida que la de la captura (azul 8 puntos abajo, el tono 5 grados de mas).
El sospechoso es el espacio: si el juego hace las cuentas en lineal y nosotros en gamma, el tono se
desplaza. Aqui se prueban las variantes contra la misma captura y se ve cual clava el color.

Variantes:
  A  gamma, como esta ahora (con el tope del degradado)
  B  gamma sin tope
  C  lineal, tal cual esta el codigo (el degradado del JSON se queda en gamma)
  D  lineal de verdad: la imagen Y los colores del degradado del JSON pasan a lineal
"""
import copy
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, r"C:\Users\Lukas\p5x-datamining\_dl")
import comparar_captura as C  # noqa: E402
import medir_piel_captura as M  # noqa: E402
import sombreado_lihui as S  # noqa: E402


def linealizar_degradado(p):
    """Los colores del degradado del JSON vienen en sRGB: en un proyecto lineal el shader los recibe ya convertidos."""
    q = copy.deepcopy(p)
    q["claves_color"] = [(t, tuple(float(x) for x in S.a_lineal(np.array(c, dtype=np.float32))))
                         for (t, c) in p["claves_color"]]
    return q


def main():
    montaje = C.montar()
    mascara = np.asarray(montaje, dtype=np.float32)[..., 3] > 200
    p = S.leer_parametros(C.JSON_CHANGFU)

    variantes = [
        ("A gamma (actual)", {"tope": True, "lineal": False}, p),
        ("B gamma sin tope", {"tope": False, "lineal": False}, p),
        ("C lineal a medias", {"tope": True, "lineal": True}, p),
        ("D lineal completo", {"tope": True, "lineal": True}, linealizar_degradado(p)),
        ("D2 lineal completo sin tope", {"tope": False, "lineal": True}, linealizar_degradado(p)),
    ]

    print("%-30s %-22s %-26s %s" % ("variante", "piel media", "hsv", "distancia a la captura"))
    ref = None
    for nombre, kw, pp in variantes:
        im = S.sombrear_imagen(montaje, pp, **kw)
        r = M.piel(im, (0, 0) + im.size, mascara, cuantos=0.15)
        if not r:
            print("%-30s (sin pixeles)" % nombre)
            continue
        media, hsv, n = r
        rgb255 = tuple(int(round(x * 255)) for x in media)
        if ref is None:
            ref = media
            print("%-30s #%02X%02X%02X  rgb%-18s h=%3.0f s=%.2f v=%.2f"
                  % (nombre, *rgb255, str(rgb255), hsv[0] * 360, hsv[1], hsv[2]))
        else:
            d = float(np.abs(media - ref).mean() * 255)
            print("%-30s #%02X%02X%02X  rgb%-18s h=%3.0f s=%.2f v=%.2f   %.1f/255"
                  % (nombre, *rgb255, str(rgb255), hsv[0] * 360, hsv[1], hsv[2], d))
        print("      desglose: R %+.1f  G %+.1f  B %+.1f respecto a la captura"
              % tuple((media - ref) * 255))
    return 0


if __name__ == "__main__":
    sys.exit(main())