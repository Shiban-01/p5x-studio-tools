"""Prueba si el C# premultiplica los colores del degradado por su alfa antes de subirlos al shader.

El material recibe `_GradientColors` (array) y `_GradientPositions` (array), y el GLSL NO tiene ningun
array de alfa: la alfa entra solo por la rampa de dos valores. Pero la clase que lo cuece se llama
UIMultipleMaterial y guarda TAMBIEN `gradientAlpha`. Si las claves del Gradient son RGBA (como en Unity),
lo natural es que el array que sube al shader lleve el color ya multiplicado por su alfa: asi la curva de
alfa influye en la fuerza del degradado sin necesitar un uniform extra.

Se compara contra la piel de la captura del juego:
  A  colores crudos (lo que habia)
  B  color * alfa(t) interpolada de las claves de alfa
  C  color * alfa(t), normalizado para que el color mas fuerte siga valiendo 1
"""
import sys

import numpy as np

sys.path.insert(0, r"C:\Users\Lukas\p5x-datamining\_dl")
import comparar_captura as C  # noqa: E402
import medir_piel_captura as M  # noqa: E402
import sombreado_lihui as S  # noqa: E402


def alfa_en(claves, t):
    """Valor de alfa de la curva de claves (t en 0..1), con salto plano fuera de los extremos."""
    if t <= claves[0][0]:
        return claves[0][1]
    if t >= claves[-1][0]:
        return claves[-1][1]
    for (t0, a0), (t1, a1) in zip(claves, claves[1:]):
        if t <= t1:
            f = (t - t0) / max(t1 - t0, 0.001)
            return a0 + f * (a1 - a0)
    return claves[-1][1]


def main():
    montaje = C.montar()
    mascara = np.asarray(montaje, dtype=np.float32)[..., 3] > 200
    p = S.leer_parametros(C.JSON_CHANGFU)

    ref = M.piel(C.pers, (0, 0) + C.pers.size, None, cuantos=0.15)
    r255 = tuple(int(round(x * 255)) for x in ref[0])
    print("captura del juego: #%02X%02X%02X  rgb%s" % (*r255, str(r255)))
    print("claves de color:", [(round(t, 3), tuple(round(x, 3) for x in c)) for t, c in p["claves_color"]])
    print("claves de alfa :", [(round(t, 3), round(a, 3)) for t, a in p["claves_alfa"]])
    print()

    prem = [(t, tuple(x * alfa_en(p["claves_alfa"], t) for x in c)) for t, c in p["claves_color"]]
    tope = max(max(c) for _, c in prem) or 1.0
    norm = [(t, tuple(x / tope for x in c)) for t, c in prem]

    casos = [
        ("A  colores crudos", p["claves_color"]),
        ("B  color * alfa(t)", prem),
        ("C  color * alfa(t), normalizado", norm),
    ]

    print("%-34s %-22s %-24s %s" % ("variante", "piel", "hsv", "distancia"))
    for nombre, claves in casos:
        q = dict(p)
        q["claves_color"] = claves
        im = S.sombrear_imagen(montaje, q)
        media, hsv, n = M.piel(im, (0, 0) + im.size, mascara, cuantos=0.15)
        m = tuple(int(round(x * 255)) for x in media)
        d = float(np.abs(media - ref[0]).mean() * 255)
        print("%-34s #%02X%02X%02X  rgb%-18s h=%3.0f s=%.2f v=%.2f   %.1f/255  (R %+.1f G %+.1f B %+.1f)"
              % (nombre, *m, str(m), hsv[0] * 360, hsv[1], hsv[2], d, *((media - ref[0]) * 255)))
    return 0


if __name__ == "__main__":
    sys.exit(main())