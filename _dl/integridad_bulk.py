"""Peso, integridad y rarezas del resultado del bulk.

- tamano y numero de PNG por categoria
- ficheros de 0 bytes (un PNG truncado por un corte de luz, por ejemplo)
- 30 PNG al azar abiertos de verdad con PIL (no basta con que el fichero exista)
- ficheros sueltos en la raiz de `textures/` (los deja la OTRA herramienta, no el bulk)
- colisiones resueltas con `_2`/`_3`
"""
import os
import random
from collections import Counter, defaultdict
from pathlib import Path

DEST = Path(r"C:\Users\Lukas\Desktop\P5X Studio Tools\extracted\textures")

peso = Counter()
cuenta = Counter()
vacios = []
sueltos = []
colisiones = Counter()
por_categoria = defaultdict(list)
for raiz, _, ficheros in os.walk(DEST):
    rel = Path(raiz).relative_to(DEST)
    for f in ficheros:
        p = Path(raiz) / f
        if not rel.parts:
            sueltos.append(f)
            continue
        cat = rel.parts[0]
        if not f.lower().endswith(".png"):
            sueltos.append(str(rel / f))
            continue
        try:
            n = p.stat().st_size
        except OSError:
            continue
        peso[cat] += n
        cuenta[cat] += 1
        if n == 0:
            vacios.append(str(rel / f))
        if "_2.png" in f.lower() or "_3.png" in f.lower():
            colisiones[cat] += 1
        por_categoria[cat].append(rel / f)

print("=" * 74)
print("%-18s %8s %14s" % ("categoria", "PNG", "peso"))
print("-" * 74)
for cat in sorted(cuenta):
    print("%-18s %8d %11.2f GB" % (cat, cuenta[cat], peso[cat] / 1e9))
print("-" * 74)
print("%-18s %8d %11.2f GB" % ("TOTAL", sum(cuenta.values()), sum(peso.values()) / 1e9))
print()
print("PNG de 0 bytes:", len(vacios), vacios[:5])
print("ficheros sueltos en la raiz o no-PNG:", len(sueltos), sueltos[:16])
print("colisiones _2/_3:", sum(colisiones.values()), dict(colisiones))
print("espacio libre ahora mismo:")
import shutil
print("   %.1f GB en C:" % (shutil.disk_usage("C:/").free / 1e9))

print()
print("=" * 74)
print("30 PNG AL AZAR ABIERTOS CON PIL")
print("=" * 74)
from PIL import Image  # noqa: E402

todas = [f for v in por_categoria.values() for f in v]
random.seed(11)
sample = random.sample(todas, min(30, len(todas)))
malos = []
detalle = []
for rel in sample:
    try:
        with Image.open(DEST / rel) as im:
            detalle.append("%s %sx%s %s" % (rel.name, im.width, im.height, im.mode))
    except Exception as e:  # noqa: BLE001
        malos.append("%s (%s)" % (rel, e))
print("abiertas %d, no se pudieron leer: %d" % (len(sample), len(malos)))
for x in malos[:5]:
    print("   ", x)
print("muestra de lo que hay dentro:")
for x in detalle[:8]:
    print("   ", x)