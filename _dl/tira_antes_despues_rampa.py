"""Tira de antes y despues del arreglo de la rampa de alfa, al lado de la captura del juego.

captura del juego | antes (posiciones de las claves de alfa) | ahora (posiciones de las claves de color)
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, r"C:\Users\Lukas\p5x-datamining\_dl")
import comparar_captura as C  # noqa: E402
import sombreado_lihui as S  # noqa: E402

SALIDA = Path(r"C:\Users\Lukas\p5x-datamining\_dl\prueba_sombreado\antes_despues_rampa.png")


def con_posiciones(p, abajo, arriba):
    """Los parametros con la rampa de alfa mal puesta (posiciones de las claves de alfa)."""
    q = dict(p)
    q["pos_alfa_abajo"] = abajo
    q["pos_alfa_arriba"] = arriba
    return q


def main():
    montaje = C.montar()
    p = S.leer_parametros(C.JSON_CHANGFU)

    antes = S.sombrear_imagen(montaje, con_posiciones(p, float(p["claves_alfa"][0][0]),
                                                      float(p["claves_alfa"][-1][0])))
    ahora = S.sombrear_imagen(montaje, p)

    paneles = [("captura del juego", C.pers), ("antes (paradas de alfa)", antes), ("ahora (paradas de color)", ahora)]
    alto = max(im.height for _, im in paneles)
    ancho = sum(im.width for _, im in paneles) + 8 * (len(paneles) - 1)
    tira = Image.new("RGB", (ancho, alto + 22), (24, 24, 28))
    d = ImageDraw.Draw(tira)
    x = 0
    for nombre, im in paneles:
        tira.paste(im.convert("RGB"), (x, 22))
        d.text((x + 6, 6), nombre, fill=(235, 235, 235))
        x += im.width + 8
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    tira.save(SALIDA)
    print("tira:", SALIDA, tira.size)

    # y el dato, medido con la misma varita
    import medir_piel_captura as M  # noqa: E402
    mascara = np.asarray(montaje, dtype=np.float32)[..., 3] > 200
    ref = M.piel(C.pers, (0, 0) + C.pers.size, None, cuantos=0.15)
    for nombre, im in paneles:
        m = mascara if im is not C.pers else None
        r = M.piel(im, (0, 0) + im.size, m, cuantos=0.15)
        rgb255 = tuple(int(round(v * 255)) for v in r[0])
        print("  %-28s #%02X%02X%02X   R %3d G %3d B %3d   calidez %+5.1f   distancia %.1f/255"
              % (nombre, *rgb255, *rgb255, rgb255[0] - rgb255[2],
                 float(np.abs(r[0] - ref[0]).mean() * 255)))
    return 0


if __name__ == "__main__":
    sys.exit(main())