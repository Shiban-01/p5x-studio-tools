"""Verificacion final del bulk completo: cobertura, peso, integridad y rarezas.

Tres pasadas sobre el mismo arbol (una sola lectura del disco):
  1) cobertura EXACTA   -> el fichero se llama igual que el asset (sin extension ni mayusculas)
  2) cobertura TOLERANTE-> ademas vale si el fichero empieza por el nombre del asset (el motor anade
     cosas: `.tga.png`, `.png.png`, `_#1288`, `_001`...)
  3) peso, integridad y rarezas
"""
import os
import random
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, r"C:\Users\Lukas\p5x-datamining\p5x_studio")
from p5x_studio import lote  # noqa: E402

DEST = Path(r"C:\Users\Lukas\Desktop\P5X Studio Tools\extracted\textures")
filas = __import__("json").loads(Path(r"C:\Users\Lukas\p5x-datamining\_dl\censo_texturas.json")
                                 .read_text(encoding="utf-8"))["filas"]
EXT = (".png", ".tga", ".jpg", ".jpeg", ".dds", ".bmp", ".exr", ".tif", ".psd", ".tga.png")


def norm(s):
    if not s:
        return ""
    s = s.strip().lower()
    for e in EXT:
        if s.endswith(e):
            return s[: -len(e)]
    return s


# ------------------------------------------------------------------ una sola lectura del disco
disco = defaultdict(list)        # (cat, conj) -> [(nombre_normalizado, tamano, nombre_real)]
peso = Counter()
cuenta = Counter()
vacios = []
sueltos = []
colisiones = Counter()
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
        conjunto = rel.parts[1] if len(rel.parts) > 1 else "(suelto)"
        disco[(cat, conjunto)].append((norm(f), n, str(rel / f)))
        peso[cat] += n
        cuenta[cat] += 1
        if n == 0:
            vacios.append(str(rel / f))
        if "_#" in f or f.lower().endswith("_2.png"):
            colisiones[cat] += 1

# ------------------------------------------------------------------ cobertura
res = defaultdict(Counter)
residual = defaultdict(list)
for r in filas:
    cat = lote.etiqueta(lote.categoria_de(r["bundle"]))
    conj = lote.nombre_conjunto(r["bundle"])
    objetivo = norm(r["nombre"])
    lista = disco.get((cat, conj), [])
    res[cat]["censo"] += 1
    if any(n == objetivo for n, _, _ in lista):
        res[cat]["exacta"] += 1
    elif any(n.startswith(objetivo) or objetivo in n for n, _, _ in lista):
        res[cat]["tolerante"] += 1
    else:
        res[cat]["fuera"] += 1
        if len(residual[cat]) < 6:
            residual[cat].append("%s -> %s" % (r["nombre"], r["bundle"]))

print("=" * 92)
print("COBERTURA DE LAS 118.425 TEXTURAS DEL CENSO")
print("=" * 92)
print("%-18s %9s %9s %10s %7s" % ("categoria", "censo", "exactas", "tolerantes", "fuera"))
print("-" * 84)
t = Counter()
for cat in sorted(res):
    d = res[cat]
    print("%-18s %9d %9d %10d %7d" % (cat, d["censo"], d["exacta"], d["tolerante"], d["fuera"]))
    for k in d:
        t[k] += d[k]
print("-" * 84)
print("%-18s %9d %9d %10d %7d" % ("TOTAL", t["censo"], t["exacta"], t["tolerante"], t["fuera"]))
print("cobertura: %.3f%%  (%d de %d)" % (100.0 * (t["exacta"] + t["tolerante"]) / t["censo"],
                                         t["exacta"] + t["tolerante"], t["censo"]))

print()
print("=" * 92)
print("PESO Y CONTEO EN DISCO")
print("=" * 92)
for cat in sorted(cuenta):
    print("%-18s %8d PNG %11.2f GB" % (cat, cuenta[cat], peso[cat] / 1e9))
print("-" * 84)
print("%-18s %8d PNG %11.2f GB" % ("TOTAL", sum(cuenta.values()), sum(peso.values()) / 1e9))
print("libre en C: %.1f GB" % (shutil.disk_usage("C:/").free / 1e9))

print()
print("conjuntos en disco:", len(disco), "| conjuntos que el censo pide:",
      len({(lote.etiqueta(lote.categoria_de(r["bundle"])), lote.nombre_conjunto(r["bundle"]))
           for r in filas}))
print("conjuntos vacios:", sum(1 for k, v in disco.items() if not v))
print("PNG de 0 bytes:", len(vacios), vacios[:4])
print("ficheros sueltos en la raiz o no-PNG:", len(sueltos), sueltos[:14])
print("nombres con sufijo de desempate (_#, _2):", sum(colisiones.values()), dict(colisiones))

print()
print("=" * 92)
print("LO QUE NO APARECE NI TOLERANDO (%d)" % t["fuera"])
print("=" * 92)
for cat in sorted(residual):
    if not residual[cat]:
        continue
    print("[%s]" % cat)
    for x in residual[cat]:
        print("   ", x)

print()
print("=" * 92)
print("INTEGRIDAD: 30 PNG AL AZAR ABIERTOS CON PIL")
print("=" * 92)
from PIL import Image  # noqa: E402

todas = [(cat, conj, real) for (cat, conj), v in disco.items() for _, _, real in v]
random.seed(11)
sample = random.sample(todas, min(30, len(todas)))
malos = []
for _, _, real in sample:
    try:
        with Image.open(DEST / real) as im:
            im.verify()
    except Exception as e:  # noqa: BLE001
        malos.append("%s (%s)" % (real, e))
print("abiertas %d, ilegibles: %d %s" % (len(sample), len(malos), malos[:3]))
tam = [(os.path.getsize(DEST / real), real) for _, _, real in sample]
tam.sort()
print("la mas pequena: %s (%.0f KB)" % (tam[0][1], tam[0][0] / 1024))
print("la mas grande : %s (%.1f MB)" % (tam[-1][1], tam[-1][0] / 1e6))