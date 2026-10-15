"""Comprobacion directa de los pares que sabemos que son recorte (xiachuanling, jianajun).

Si el test no los detecta, el test esta mal; si los detecta, entonces en el bulk casi no hay recortes
y la conclusion de la muestra (0%) es real. Se busca cada pareja en la carpeta del bulk y se compara
la caja de alfa del grande con el pequeno.
"""
import json
import re
from pathlib import Path

import numpy as np
from PIL import Image

DL = Path(r"C:\Users\Lukas\p5x-datamining\_dl")
TEXTURAS = Path(r"C:\Users\Lukas\Desktop\P5X Studio Tools\extracted\textures")
idx = json.loads((DL / "indice_bulk.json").read_text(encoding="utf-8"))

CLAVES = [
    "xiachuanling-changfu-benti", "xiachuanling-changfu-benti-lunkuo",
    "xiachuanling-changfu-tongchang-zui1", "xiachuanling-changfu-benti-yifu",
    "jianajun-guaidaofu-benti-tongchang-long", "jianajun-guaidaofu-tongchang-yan1",
]

for clave in CLAVES:
    rutas = idx.get(clave)
    if not rutas:
        print("%-46s no esta en el indice (un solo PNG o nombre distinto)" % clave)
        continue
    info = []
    for r in rutas:
        with Image.open(r) as im:
            info.append((im.width * im.height, im.size, r))
    info.sort()
    print("%s" % clave)
    for area, tam, r in info:
        print("      %-52s %dx%d" % (Path(r).name, tam[0], tam[1]))
    if len(info) >= 2 and info[0][1] != info[-1][1]:
        with Image.open(info[-1][2]) as ib, Image.open(info[0][2]) as ia:
            grande = ib.convert("RGBA")
            pequeno = ia.convert("RGBA")
        caja = grande.getbbox()
        print("      caja de alfa del grande: %s (%dx%d)"
              % (caja, caja[2] - caja[0], caja[3] - caja[1]))
        for crecer in (0, 1, 2, 3, 4):
            c = (max(0, caja[0] - crecer), max(0, caja[1] - crecer),
                 min(grande.width, caja[2] + crecer), min(grande.height, caja[3] + crecer))
            recorte = grande.crop(c)
            if recorte.size == pequeno.size:
                da = np.asarray(recorte, dtype=np.int16)
                db = np.asarray(pequeno, dtype=np.int16)
                d = int(np.abs(da - db).max()) if da.size else -1
                print("      con crecer=%d los tamanos COINCIDEN, diferencia max de pixel: %d"
                      % (crecer, d))
                break
        else:
            print("      el recorte no cuadra con el pequeno en ningun crecer 0..4")
    print()