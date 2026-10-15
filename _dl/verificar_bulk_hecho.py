"""Verifica la corrida completa del bulk: disco contra censo, categoria por categoria.

El censo (censo_texturas.json) tiene las 118.425 texturas con su bundle, su nombre, su tipo y el
fichero contenedor del que salen. Aqui se reconstruye lo que DEBERIA haber quedado en cada carpeta y
se compara con lo que hay de verdad, para poder decir exactamente que falta y por que.
"""
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, r"C:\Users\Lukas\p5x-datamining\p5x_studio")
from p5x_studio import lote  # noqa: E402

DEST = Path(r"C:\Users\Lukas\Desktop\P5X Studio Tools\extracted\textures")
CENSO = Path(r"C:\Users\Lukas\p5x-datamining\_dl\censo_texturas.json")

# ------------------------------------------------------------------ 1) lo que hay en el disco
disco = defaultdict(set)          # (categoria, conjunto) -> {ficheros}
vacios = []
colisiones = Counter()
total_disco = 0
otros = []
for raiz, carpetas, ficheros in os.walk(DEST):
    rel = Path(raiz).relative_to(DEST)
    for f in ficheros:
        if not f.lower().endswith(".png"):
            otros.append(str(rel / f))
            continue
        if len(rel.parts) == 0:
            otros.append(f)        # suelto en la raiz: lo deja la OTRA herramienta, no el bulk
            continue
        categoria = rel.parts[0]
        conjunto = rel.parts[1] if len(rel.parts) > 1 else "(suelto)"
        disco[(categoria, conjunto)].add(f)
        total_disco += 1
        if (Path(raiz) / f).stat().st_size == 0:
            vacios.append(str(rel / f))
        if "_2.png" in f or "_3.png" in f:
            colisiones[categoria] += 1

# ------------------------------------------------------------------ 2) lo que DEBERIA haber
filas = json.loads(CENSO.read_text(encoding="utf-8"))["filas"]
esperado = defaultdict(set)           # (categoria, conjunto) -> {contenedores}
esperado_nombre = defaultdict(set)    # idem, por nombre de asset
sin_contenedor = 0
for r in filas:
    cat = lote.etiqueta(lote.categoria_de(r["bundle"]))
    conj = lote.nombre_conjunto(r["bundle"])
    if r["cont"]:
        esperado[(cat, conj)].add(r["cont"])
    else:
        sin_contenedor += 1
        esperado[(cat, conj)].add(r["nombre"] + ".png")
    esperado_nombre[(cat, conj)].add(r["nombre"])

# ------------------------------------------------------------------ 3) la comparacion
print("=" * 78)
print("LO QUE HAY EN EL DISCO")
print("=" * 78)
print("PNG totales:", total_disco)
print("ficheros que no son PNG o estan sueltos en la raiz:", len(otros))
print("PNG de 0 bytes:", len(vacios))
print("colisiones resueltas con _2/_3:", sum(colisiones.values()), dict(colisiones))

print()
print("%-18s %9s %9s %9s %8s %8s" % ("categoria", "censo", "unicos", "en disco", "faltan", "sobran"))
print("-" * 70)
tot = Counter()
por_categoria = defaultdict(lambda: Counter())
for cat in sorted({c for c, _ in esperado} | {c for c, _ in disco}):
    esp = set()
    for (c, j), v in esperado.items():
        if c == cat:
            esp |= v
    esp_nombre = set()
    for (c, j), v in esperado_nombre.items():
        if c == cat:
            esp_nombre |= v
    hay = set()
    for (c, j), v in disco.items():
        if c == cat:
            hay |= v
    faltan = esp - hay
    sobran = hay - esp
    # ¿casan mejor los nombres de asset que los contenedores?
    faltan_n = esp_nombre - hay
    por_categoria[cat] = Counter(censo=sum(1 for r in filas
                                          if lote.etiqueta(lote.categoria_de(r["bundle"])) == cat),
                                 unicos=len(esp), disco=len(hay),
                                 faltan=len(faltan), sobran=len(sobran),
                                 faltan_nombre=len(faltan_n))
    print("%-18s %9d %9d %9d %8d %8d" % (cat, por_categoria[cat]["censo"], len(esp), len(hay),
                                         len(faltan), len(sobran)))
    tot["censo"] += por_categoria[cat]["censo"]
    tot["unicos"] += len(esp)
    tot["disco"] += len(hay)
    tot["faltan"] += len(faltan)
    tot["sobran"] += len(sobran)
print("-" * 70)
print("%-18s %9d %9d %9d %8d %8d" % ("TOTAL", tot["censo"], tot["unicos"], tot["disco"],
                                     tot["faltan"], tot["sobran"]))
print()
print("texturas del censo sin fichero contenedor:", sin_contenedor)

# ------------------------------------------------------------------ 4) detalle de lo que falta
print()
print("=" * 78)
print("DETALLE (primeras 15 de lo que el censo dice y no esta)")
print("=" * 78)
faltan_todas = []
for (cat, conj), v in esperado.items():
    hay = disco.get((cat, conj), set())
    for f in sorted(v - hay):
        faltan_todas.append("%s/%s/%s" % (cat, conj, f))
print("total que falta:", len(faltan_todas))
for x in faltan_todas[:15]:
    print("   ", x)

print()
print("=" * 78)
print("CONJUNTOS VACIOS (censo dice que hay texturas y la carpeta no existe o esta vacia)")
print("=" * 78)
vacios_conj = [k for k, v in esperado.items() if v and not disco.get(k)]
print("conjuntos esperados con texturas y sin nada:", len(vacios_conj))
for k in sorted(vacios_conj)[:15]:
    print("   ", k, "->", len(esperado[k]), "esperadas")
print()
print("conjuntos en disco:", len(disco), "| conjuntos esperados:", len(esperado))

# ------------------------------------------------------------------ 5) muestras de integridad
print()
print("=" * 78)
print("INTEGRIDAD: se abren de verdad unas cuantas al azar")
print("=" * 78)
import random
from PIL import Image
aleatorias = []
for k, v in disco.items():
    for f in v:
        aleatorias.append(k[0] / k[1] / f)
random.seed(7)
malas = []
for rel in random.sample(aleatorias, min(25, len(aleatorias))):
    try:
        with Image.open(DEST / rel) as im:
            im.verify()
    except Exception as e:  # noqa: BLE001
        malas.append("%s (%s)" % (rel, e))
print("abiertas 25 al azar, fallan:", len(malas), malas[:3])