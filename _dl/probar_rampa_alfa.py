"""Prueba como se mezcla el degradado (la rampa de alfa), midiendo contra la captura del juego.

El JSON trae tres cosas distintas que se pueden confundir:
  - `claves_alfa`: la CURVA de alfa del Gradient de Unity (sus propias paradas).
  - `GradientAlphaBottom` / `GradientAlphaTop`: dos numeros aparte.
Mi version usaba solo los numeros, repartiendo una recta entre la primera y la ultima parada de la
curva: eso ignora las paradas de en medio (105 de los 216 JSON tienen 3 o mas) y, cuando la curva
vale 1.0 en todo su recorrido, mete mucho menos degradado del que toca. Aqui se comparan las
variantes contra la captura para ver cual clava el color.
"""
import sys

import numpy as np

sys.path.insert(0, r"C:\Users\Lukas\p5x-datamining\_dl")
import comparar_captura as C  # noqa: E402
import medir_piel_captura as M  # noqa: E402
import sombreado_lihui as S  # noqa: E402


def ga_variantes(p, coord):
    """(nombre, ramp) para cada manera de sacar el factor de mezcla del degradado."""
    ca = p["claves_alfa"]
    btm_pos, top_pos = float(ca[0][0]), float(ca[-1][0])
    abajo, arriba = p["alfa_abajo"], p["alfa_arriba"]

    # 1) la actual: una recta entre los numeros, repartida por el tramo de la curva
    t = np.minimum(np.maximum(coord - btm_pos, 0.001) / max(top_pos - btm_pos, 0.001), 1.0)
    recta = t * (arriba - abajo) + abajo
    recta = np.where(coord <= btm_pos, abajo, np.where(coord >= top_pos, arriba, recta))

    # 2) la curva de alfa de verdad, escalada entre los dos numeros
    curva = S.evaluar_degradado(ca, np.clip(coord, 0.0, 1.0))
    curva = curva * (arriba - abajo) + abajo

    # 3) la curva cruda, sin los numeros
    cruda = S.evaluar_degradado(ca, np.clip(coord, 0.0, 1.0))

    # 4) el degradado a plena fuerza
    plena = np.ones_like(coord)

    return [("1 recta (actual)", recta), ("2 curva escalada", curva),
            ("3 curva cruda", cruda), ("4 degradado pleno", plena)]


def con_ramp(p, ramp):
    """Devuelve los parametros con una rampa de alfa impuesta (para reusar sombrear_imagen)."""
    q = dict(p)
    q["_ramp"] = ramp
    return q


def main():
    montaje = C.montar()
    mascara = np.asarray(montaje, dtype=np.float32)[..., 3] > 200
    p = S.leer_parametros(C.JSON_CHANGFU)

    ref = M.piel(C.pers, (0, 0) + C.pers.size, None, cuantos=0.15)
    print("captura del juego: #%02X%02X%02X  rgb%s  h=%3.0f s=%.2f v=%.2f"
          % (*[int(round(x * 255)) for x in ref[0]], str(tuple(int(round(x * 255)) for x in ref[0])),
             ref[1][0] * 360, ref[1][1], ref[1][2]))
    print()
    print("%-22s %-22s %-26s %s" % ("variante", "piel media", "hsv", "distancia a la captura"))

    # la rampa se calcula igual que dentro de sombrear_imagen: hay que repetir aqui la coordenada
    ancho, alto = montaje.size
    u = (np.arange(ancho, dtype=np.float32) + 0.5) / ancho
    v = 1.0 - (np.arange(alto, dtype=np.float32) + 0.5) / alto
    U, V = np.meshgrid(u, v)
    a = np.radians(p["angulo"])
    lin = (U - 0.5) * np.sin(-a) + (V - 0.5) * np.cos(a) + 0.5
    radial = np.sqrt(((U - p["centro"][0]) * p["proporcion"][0]) ** 2
                     + ((V - p["centro"][1]) * p["proporcion"][1]) ** 2) * 2.0
    coord = lin + p["modo"] * (radial - lin)

    for nombre, ramp in ga_variantes(p, coord):
        q = con_ramp(p, ramp)
        im = S.sombrear_imagen(montaje, q)
        r = M.piel(im, (0, 0) + im.size, mascara, cuantos=0.15)
        if not r:
            print("%-22s (sin pixeles)" % nombre)
            continue
        media, hsv, n = r
        rgb255 = tuple(int(round(x * 255)) for x in media)
        d = float(np.abs(media - ref[0]).mean() * 255)
        print("%-22s #%02X%02X%02X  rgb%-18s h=%3.0f s=%.2f v=%.2f   %.1f/255   (R %+.1f G %+.1f B %+.1f)"
              % (nombre, *rgb255, str(rgb255), hsv[0] * 360, hsv[1], hsv[2], d,
                 *((media - ref[0]) * 255)))
    return 0


if __name__ == "__main__":
    sys.exit(main())