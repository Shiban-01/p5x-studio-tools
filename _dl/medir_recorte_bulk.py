"""Cuantas texturas del bulk estan RECORTADAS de verdad (y no son regiones de un atlas).

Recorre la carpeta del bulk una vez, agrupa por nombre de asset y, en una muestra de los pares
Sprite+Texture2D, comprueba si el pequeno es EXACTAMENTE el contenido del grande recortado:
si `grande.crop(bbox_alfa) == pequeno`, es el recorte de AssetStudio (el que avisa Aaron) y se puede
arreglar reescribiendo el pequeno como el grande. Si no coincide, el pequeno es un sprite distinto
(region de un atlas) y NO hay que tocarlo.

Solo mide: no escribe nada.
"""
import random
import re
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image

TEXTURAS = Path(r"C:\Users\Lukas\Desktop\P5X Studio Tools\extracted\textures")
MUESTRA = 300

print("recorriendo la carpeta del bulk...")
por_nombre = defaultdict(list)
for p in TEXTURAS.rglob("*.png"):
    nombre = re.sub(r"_#\d+$", "", p.stem)
    por_nombre[nombre].append(p)
print("PNG indexados: %d | nombres distintos: %d" % (sum(len(v) for v in por_nombre.values()),
                                                    len(por_nombre)))

pares = {n: v for n, v in por_nombre.items() if len(v) > 1}
print("nombres con mas de un PNG: %d" % len(pares))

# solo los que tienen tamanos distintos
con_tamanos = []
for nombre, rutas in pares.items():
    info = []
    for p in rutas:
        with Image.open(p) as im:
            info.append((im.width * im.height, im.size, p))
    info.sort()
    if info[0][1] != info[-1][1]:
        con_tamanos.append((nombre, info[0], info[-1]))
print("con tamanos distintos (el pequeno podria estar recortado): %d" % len(con_tamanos))

random.seed(7)
muestra = random.sample(con_tamanos, min(MUESTRA, len(con_tamanos)))
recortados = distintos = fallos = 0
ejemplos_recorte = []
for nombre, (a_area, a_tam, a_ruta), (b_area, b_tam, b_ruta) in muestra:
    try:
        with Image.open(a_ruta) as ia, Image.open(b_ruta) as ib:
            pa = ia.convert("RGBA")
            pb = ib.convert("RGBA")
        caja = pa.getbbox()
        if caja is None:
            fallos += 1
            continue
        recorte = pa.crop(caja)
        if recorte.size != pb.size:
            distintos += 1
            continue
        da = np.asarray(recorte, dtype=np.int16)
        db = np.asarray(pb, dtype=np.int16)
        dif = np.abs(da - db).max() if da.size else 0
        if dif <= 2:
            recortados += 1
            if len(ejemplos_recorte) < 6:
                ejemplos_recorte.append((nombre, "%dx%d" % a_tam, "%dx%d" % b_tam))
        else:
            distintos += 1
    except Exception:  # noqa: BLE001
        fallos += 1

print()
print("muestra de %d pares:" % len(muestra))
print("   el pequeno es el grande recortado (recorte de AssetStudio): %d" % recortados)
print("   el pequeno es otro sprite (region de atlas, NO tocar):      %d" % distintos)
print("   no se pudo comprobar:                                       %d" % fallos)
print()
print("ejemplos de recorte:")
for nombre, t1, t2 in ejemplos_recorte:
    print("   %-52s %-12s -> %s" % (nombre[:52], t1, t2))
if muestra:
    print()
    print("estimacion sobre los %d pares: ~%d recortados (~%.0f%%)"
          % (len(con_tamanos), int(len(con_tamanos) * recortados / len(muestra)),
             recortados * 100.0 / len(muestra)))