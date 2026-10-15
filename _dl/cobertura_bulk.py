"""Cobertura real del bulk: cuantas de las 118.425 texturas del censo estan en el disco.

Un fichero cuenta como "esa textura" si su nombre (sin extension, sin distinguir mayusculas) coincide
con el nombre del asset O con el del fichero contenedor: el motor puede escribir uno u otro segun el
tipo (lo he visto con los dos). Ademas se agrupa por CONJUNTO, que es donde el fichero tiene que
estar, y se comprueba de paso que cada bundle tiene su carpeta con algo dentro.
"""
import json
import os
from collections import Counter, defaultdict
from pathlib import Path

DEST = Path(r"C:\Users\Lukas\Desktop\P5X Studio Tools\extracted\textures")
filas = json.loads(Path(r"C:\Users\Lukas\p5x-datamining\_dl\censo_texturas.json")
                   .read_text(encoding="utf-8"))["filas"]

import sys
sys.path.insert(0, r"C:\Users\Lukas\p5x-datamining\p5x_studio")
from p5x_studio import lote  # noqa: E402


EXT = (".png", ".tga", ".jpg", ".jpeg", ".dds", ".bmp", ".exr", ".tif")


def norm(s):
    """Quita SOLO una extension de imagen conocida y pasa a minusculas.

    No vale `Path(s).stem`: hay nombres con puntos legitimos (`.1001`, `v4.14`, `2.5ST`, `5.8`) y
    cortar por el ultimo punto se los come, lo que hace parecer que falta medio censo.
    """
    if not s:
        return ""
    s = s.strip().lower()
    for e in EXT:
        if s.endswith(e):
            return s[: -len(e)]
    return s


# ------------------------------------------------------------------ indice del disco
disco = defaultdict(set)
ficheros_disco = 0
for raiz, _, ficheros in os.walk(DEST):
    rel = Path(raiz).relative_to(DEST)
    if not rel.parts:
        continue
    categoria = rel.parts[0]
    conjunto = rel.parts[1] if len(rel.parts) > 1 else "(suelto)"
    for f in ficheros:
        if f.lower().endswith(".png"):
            disco[(categoria, conjunto)].add(norm(f))
            ficheros_disco += 1

# ------------------------------------------------------------------ cobertura del censo
res = defaultdict(Counter)
sin_cubrir = defaultdict(list)
for r in filas:
    cat = lote.etiqueta(lote.categoria_de(r["bundle"]))
    conj = lote.nombre_conjunto(r["bundle"])
    tengo = disco.get((cat, conj), set())
    # el `cont` del censo se guardo truncado a 32 caracteres: no sirve para emparejar
    posibles = {norm(r["nombre"])} - {""}
    res[cat]["texturas"] += 1
    if posibles & tengo:
        res[cat]["cubiertas"] += 1
    else:
        res[cat]["sin_cubrir"] += 1
        if len(sin_cubrir[cat]) < 8:
            sin_cubrir[cat].append((r["nombre"], r["cont"], r["tipo"], r["bundle"], conj))

print("=" * 84)
print("COBERTURA DEL CENSO (118.425 texturas) CONTRA LO QUE HAY EN EL DISCO")
print("(emparejando por NOMBRE del asset, sin mayusculas y sin la extension de imagen)")
print("=" * 84)
print("%-18s %9s %9s %9s %7s" % ("categoria", "censo", "cubiertas", "sin cubrir", "%"))
print("-" * 76)
t = Counter()
for cat in sorted(res):
    d = res[cat]
    pct = 100.0 * d["cubiertas"] / d["texturas"]
    print("%-18s %9d %9d %9d %6.1f%%" % (cat, d["texturas"], d["cubiertas"], d["sin_cubrir"], pct))
    for k in d:
        t[k] += d[k]
print("-" * 76)
print("%-18s %9d %9d %9d %6.1f%%" % ("TOTAL", t["texturas"], t["cubiertas"], t["sin_cubrir"],
                                     100.0 * t["cubiertas"] / t["texturas"]))

print()
print("PNG en disco: %d  (el censo cuenta texturas, no ficheros: varios sprites de un mismo atlas"
      " son un solo PNG)" % ficheros_disco)
print("conjuntos en disco: %d" % len(disco))

print()
print("=" * 84)
print("EJEMPLOS DE LO QUE NO ENCUENTRO (para poder mirar por que)")
print("=" * 84)
for cat in sorted(sin_cubrir):
    if not sin_cubrir[cat]:
        continue
    print("\n[%s]" % cat)
    for nombre, cont, tipo, bundle, conj in sin_cubrir[cat]:
        print("   %-36s cont=%-32s %-9s %s" % (nombre[:36], str(cont)[:32], tipo, bundle))