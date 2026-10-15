"""Mide la comparacion que mando el usuario: mitad izquierda (juego) contra mitad derecha (nuestra).

Saca el color medio de la piel de cada figura (los pixeles claros dentro de la silueta, que es lo que
cambia entre las dos) y el desplazamiento de calidez, para saber cuanto hemos de bajar el shader.
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ORIGEN = Path(r"C:\Users\Lukas\AppData\Roaming\Hermes\composer-images\image_be4a7c.png")
SALIDA = Path(r"C:\Users\Lukas\p5x-datamining\_dl\prueba_sombreado\comparacion_usuario")

im = Image.open(ORIGEN).convert("RGB")
a = np.asarray(im, dtype=np.float32)
alto, ancho = a.shape[:2]
print("imagen:", im.size)

# el usuario dice que la figura nuestra esta en la derecha
mitad = ancho // 2
izq = a[:, :mitad]
der = a[:, mitad:mitad * 2]

# donde cambia: la silueta de la figura (mismo encuadre en las dos mitades)
dif = np.abs(izq - der).mean(-1)
umbral = np.percentile(dif, 99)
cambia = dif > max(umbral, 12)
print("pixeles que cambian: %d (%.1f%% del area comparable), umbral %.1f"
      % (cambia.sum(), 100.0 * cambia.sum() / cambia.size, umbral))

def resumen(bloque, sel, nombre):
    rgb = bloque[sel]
    if not len(rgb):
        print("  %-22s (nada)" % nombre)
        return None
    lum = rgb @ np.array([0.2125, 0.7154, 0.0721])
    claro = rgb[lum > np.percentile(lum, 70)]
    media = claro.mean(0)
    print("  %-22s piel #%02X%02X%02X   calidez (R-B) %+.3f   R %3d G %3d B %3d"
          % (nombre, int(media[0]), int(media[1]), int(media[2]),
             float((claro[:, 0] - claro[:, 2]).mean()),
             int(claro[:, 0].mean()), int(claro[:, 1].mean()), int(claro[:, 2].mean())))
    return claro

print("\ndentro de la silueta (lo que cambia entre las dos):")
c_izq = resumen(izq, cambia, "izquierda (juego)")
c_der = resumen(der, cambia, "derecha (nuestra)")

if c_izq is not None and c_der is not None:
    mi, md = c_izq.mean(0), c_der.mean(0)
    print("\n  desplazamiento nuestra - juego: R %+.1f  G %+.1f  B %+.1f  |  calidez %+.3f  |  distancia %.1f/255"
          % (md[0] - mi[0], md[1] - mi[1], md[2] - mi[2],
             float((c_der[:, 0] - c_der[:, 2]).mean() - (c_izq[:, 0] - c_izq[:, 2]).mean()),
             float(np.abs(md - mi).mean())))

SALIDA.mkdir(parents=True, exist_ok=True)
# recorte de las dos caras, para mirarlas
caja = np.argwhere(cambia)
y0, x0 = caja.min(0)
y1, x1 = caja.max(0)
print("\nsilueta (en la mitad): x %d..%d  y %d..%d" % (x0, x1, y0, y1))
rec_izq = izq[y0:y1, x0:x1]
rec_der = der[y0:y1, x0:x1]
pega = np.concatenate([rec_izq, np.full((rec_izq.shape[0], 6, 3), 255, np.float32), rec_der], axis=1)
Image.fromarray(pega.astype(np.uint8)).save(SALIDA / "caras_juego_vs_nuestra.png")
print("recorte guardado en", SALIDA / "caras_juego_vs_nuestra.png")