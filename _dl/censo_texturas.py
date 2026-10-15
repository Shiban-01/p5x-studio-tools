"""Censo de texturas: cuantas hay, de que familia y cuanto pesan.

Recorre los 16.535 bundles en paralelo con el motor en modo info (no decodifica nada, ~0,2 s por
bundle) y guarda un JSON con cada textura: familia, nombre, tipo y tamano. Es la medida que hace
falta para saber si un bulk de TODAS las texturas es viable y como se pueden agrupar por carpetas.
"""
import json
import re
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, r"C:\Users\Lukas\p5x-datamining\p5x_studio")
from p5x_studio import ajustes, herramientas

G = Path(r"C:\Users\Lukas\Downloads\P5X\Client\OuterPackage\Bundles\Windows")
SALIDA = Path(r"C:\Users\Lukas\p5x-datamining\_dl\censo_texturas.json")
TRABAJADORES = 8

bundles = sorted(str(p.relative_to(G)).replace("\\", "/") for p in G.rglob("*.bundle"))
print("bundles a mirar:", len(bundles), flush=True)

lock = __import__("threading").Lock()
hechas = [0]
filas = []
fallos = []


def una(rel):
    carpeta = ajustes.CACHE / "work" / "censo" / rel.replace("/", "_")
    try:
        recursos = herramientas.listar_bundle(rel, destino=carpeta)
        out = []
        for r in recursos:
            tipo = r["tipo"]
            if tipo in ("Texture2D", "Sprite"):
                out.append({"bundle": rel, "nombre": r["nombre"], "tipo": tipo,
                            "cont": r["contenedor"], "bytes": r["tamano"]})
        return out
    except Exception as e:  # noqa: BLE001
        with lock:
            fallos.append((rel, "%s: %s" % (type(e).__name__, e)))
        return []


t0 = time.time()
with ThreadPoolExecutor(max_workers=TRABAJADORES) as ex:
    for i, res in enumerate(ex.map(una, bundles), 1):
        filas.extend(res)
        if i % 500 == 0:
            print("  %5d/%d  %6.1fs  texturas=%d" % (i, len(bundles), time.time() - t0, len(filas)),
                  flush=True)

print()
print("=== RESULTADO ===")
print("texturas y sprites:", len(filas))
print("bundles sin texturas:", len(bundles) - len({f["bundle"] for f in filas}))
print("fallos:", len(fallos))
for rel, e in fallos[:5]:
    print("   ", rel, e)

fam = Counter(f["bundle"].split("/")[1].split("_")[0] for f in filas)
peso = defaultdict(int)
for f in filas:
    peso[f["bundle"].split("/")[1].split("_")[0]] += f["bytes"]
print()
print("%-14s %8s %12s" % ("familia", "texturas", "MB"))
for k, n in fam.most_common():
    print("%-14s %8d %12.1f" % (k, n, peso[k] / 1e6))
print("%-14s %8d %12.1f" % ("TOTAL", len(filas), sum(f["bytes"] for f in filas) / 1e6))

print()
print("=== tipos ===", Counter(f["tipo"] for f in filas))
print("=== contenedores rellenos ===", sum(1 for f in filas if f["cont"]), "de", len(filas))

# que pinta tienen los nombres: primeros dos trozos
trozos = Counter("_".join(f["nombre"].split("_")[:2]) for f in filas)
print()
print("=== 30 prefijos de nombre mas comunes ===")
for k, n in trozos.most_common(30):
    print("   %-24s %6d" % (k, n))

# sufijos mas comunes (lo que suele decir el tipo de mapa: _nmas, _em...) 
sufijos = Counter(f["nombre"].rsplit("_", 1)[-1] for f in filas if "_" in f["nombre"])
print()
print("=== 20 sufijos mas comunes ===")
for k, n in sufijos.most_common(20):
    print("   %-16s %6d" % (k, n))

SALIDA.write_text(json.dumps({"filas": filas, "fallos": fallos}, ensure_ascii=False), encoding="utf-8")
print()
print("guardado en", SALIDA, "%.1f MB" % (SALIDA.stat().st_size / 1e6))