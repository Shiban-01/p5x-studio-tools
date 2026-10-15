"""Averigua la maqueta de la comparacion del usuario: cuantas mitades, por donde corta y que hay en cada lado."""
from pathlib import Path

import numpy as np
from PIL import Image

ORIGEN = Path(r"C:\Users\Lukas\AppData\Roaming\Hermes\composer-images\image_be4a7c.png")
SALIDA = Path(r"C:\Users\Lukas\p5x-datamining\_dl\prueba_sombreado\comparacion_usuario")
SALIDA.mkdir(parents=True, exist_ok=True)

im = Image.open(ORIGEN).convert("RGB")
a = np.asarray(im, dtype=np.float32)
alto, ancho = a.shape[:2]
print("imagen:", im.size)

# 1) hay una costura vertical? columnas que apenas cambian de color a lo alto
col = np.abs(np.diff(a, axis=1)).mean((0, 2))
print("columnas mas planas (posibles costuras):", sorted(np.argsort(col)[:6].tolist()))
fil = np.abs(np.diff(a, axis=0)).mean((1, 2))
print("filas mas planas:", sorted(np.argsort(fil)[:6].tolist()))

# 2) por donde corta mejor en dos mitades iguales? (se compara cada mitad consigo misma desplazada)
mejor = None
for w in range(int(ancho * 0.3), int(ancho * 0.7)):
    if ancho - w < w:
        continue
    d = np.abs(a[:, :w] - a[:, w:2 * w][:, :w]).mean()
    if mejor is None or d < mejor[1]:
        mejor = (w, d)
print("mejor corte en dos mitades iguales: x=%s con diferencia %.1f" % mejor)

# 3) arriba contra abajo
if alto % 2 == 0:
    print("arriba contra abajo: %.1f" % np.abs(a[:alto // 2] - a[alto // 2:]).mean())

# 4) guarda cada mitad y un par de recortes para mirarlos
im.crop((0, 0, ancho // 2, alto)).save(SALIDA / "mitad_izquierda.png")
im.crop((ancho // 2, 0, ancho, alto)).save(SALIDA / "mitad_derecha.png")
im.crop((0, alto // 4, ancho // 2, alto // 4 + alto // 2)).resize((ancho // 2 * 2, alto)).save(SALIDA / "izq_zoom.png")
im.crop((ancho // 2, alto // 4, ancho, alto // 4 + alto // 2)).resize((ancho // 2 * 2, alto)).save(SALIDA / "der_zoom.png")
print("guardado en", SALIDA)