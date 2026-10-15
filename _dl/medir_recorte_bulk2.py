"""Recorte del bulk, segunda vuelta: con tolerancia por el extrude de Unity.

Unity recorta el sprite a su malla ajustada MAS 1 px de extrude (`m_Extrude = 1`), asi que el PNG
recortado mide 2 px mas que la caja de alfa del grande. La comparacion exacta falla y da falsos
negativos: hay que permitir unos pixeles de diferencia y comparar la zona comun.

Uso:  medir_recorte_bulk2.py [n_muestra]
"""
import json
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image

DL = Path(r"C:\Users\Lukas\p5x-datamining\_dl")
TEXTURAS = Path(r"C:\Users\Lukas\Desktop\P5X Studio Tools\extracted\textures")
INDICE = DL / "indice_bulk.json"
TOL = 6
MUESTRA = int(sys.argv[1]) if len(sys.argv) > 1 else 300

if INDICE.exists():
    idx = json.loads(INDICE.read_text(encoding="utf-8"))
    print("indice cacheado: %d nombres" % len(idx))
else:
    print("indexando la carpeta del bulk (una vez)...")
    por_nombre = defaultdict(list)
    for p in TEXTURAS.rglob("*.png"):
        por_nombre[re.sub(r"_#\d+$", "", p.stem)].append(str(p))
    idx = {n: v for n, v in por_nombre.items() if len(v) > 1}
    INDICE.write_text(json.dumps(idx), encoding="utf-8")
    print("nombres con mas de un PNG: %d (indice guardado)" % len(idx))

pares = []
for nombre, rutas in idx.items():
    info = []
    for r in rutas:
        with Image.open(r) as im:
            info.append((im.width * im.height, im.size, r))
    info.sort()
    if info[0][1] != info[-1][1]:
        pares.append((nombre, info[0], info[-1]))
print("con tamanos distintos: %d" % len(pares))

random.seed(7)
muestra = random.sample(pares, min(MUESTRA, len(pares)))
recortados = distintos = 0
ejemplos = []
for nombre, (a_area, a_tam, a_ruta), (b_area, b_tam, b_ruta) in muestra:
    with Image.open(a_ruta) as ia, Image.open(b_ruta) as ib:
        pa = ia.convert("RGBA")
        pb = ib.convert("RGBA")
    caja = pa.getbbox()
    if caja is None:
        distintos += 1
        continue
    # se prueba la caja de alfa y sus versiones ampliadas por el extrude
    acierto = False
    for crecer in (0, 1, 2, 3, 4, TOL // 2):
        c = (max(0, caja[0] - crecer), max(0, caja[1] - crecer),
             min(pa.width, caja[2] + crecer), min(pa.height, caja[3] + crecer))
        recorte = pa.crop(c)
        if recorte.size != pb.size:
            continue
        da = np.asarray(recorte, dtype=np.int16)
        db = np.asarray(pb, dtype=np.int16)
        if da.size and np.abs(da - db).max() <= 3:
            acierto = True
            break
    if acierto:
        recortados += 1
        if len(ejemplos) < 8:
            ejemplos.append((nombre, "%dx%d" % a_tam, "%dx%d" % b_tam))
    else:
        distintos += 1

print()
print("muestra de %d pares:" % len(muestra))
print("   recorte de AssetStudio (el pequeno = el grande recortado): %d" % recortados)
print("   otro sprite distinto (region de atlas, NO tocar):         %d" % distintos)
print()
for nombre, t1, t2 in ejemplos:
    print("   %-52s %-12s -> %s" % (nombre[:52], t1, t2))
if muestra:
    print()
    print("estimacion sobre %d pares: ~%d recortados (~%.0f%%)"
          % (len(pares), int(len(pares) * recortados / len(muestra)),
             recortados * 100.0 / len(muestra)))