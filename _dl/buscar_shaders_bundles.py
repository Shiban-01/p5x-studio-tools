"""Busca Shader y Material en TODOS los bundles (escaneo paralelo, modo info).

Los shaders no aparecen ni en resources.assets ni en los ficheros sueltos de P5X_Data, asi que tienen
que estar dentro de algun bundle. Este barrido los encuentra y ademas deja el mapa de que materiales
hay y en que bundle vive cada uno. Guarda solo lo interesante (bundles con Shader o Material) para no
arrastrar 16.535 entradas.
"""
import json
import sys
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, r"C:\Users\Lukas\p5x-datamining\p5x_studio")
from p5x_studio import ajustes, herramientas  # noqa: E402

G = Path(r"C:\Users\Lukas\Downloads\P5X\Client\OuterPackage\Bundles\Windows")
SALIDA = Path(r"C:\Users\Lukas\p5x-datamining\_dl\shaders_materiales.json")
TRABAJADORES = 12

bundles = sorted(str(p.relative_to(G)).replace("\\", "/") for p in G.rglob("*.bundle"))
print("bundles a mirar:", len(bundles), flush=True)

lock = threading.Lock()
hechas = [0]
saltadas = [0]
interesantes = []
fallos = []
tipos_global = Counter()


def una(rel):
    carpeta = ajustes.CACHE / "work" / "shaders" / rel.replace("/", "_")
    # reanudable: si la lista de ese bundle ya esta escrita, no se repite el trabajo
    xml = carpeta / "assets.xml"
    rec = None
    with lock:
        if xml.exists() and xml.stat().st_size > 200:
            saltadas[0] += 1
            if saltadas[0] % 2000 == 0:
                print("  saltadas %d ya hechas" % saltadas[0], flush=True)
            return None
    try:
        rec = herramientas.listar_bundle(rel, destino=carpeta)
    except Exception as e:  # noqa: BLE001
        with lock:
            fallos.append((rel, "%s: %s" % (type(e).__name__, e)))
            hechas[0] += 1
        return None
    cn = Counter(r["tipo"] for r in rec)
    sh = [r["nombre"] for r in rec if r["tipo"].lower() == "shader"]
    ma = [r["nombre"] for r in rec if r["tipo"].lower() == "material"]
    out = None
    if sh or ma:
        out = {"bundle": rel, "recursos": len(rec), "shaders": sh, "materiales": ma,
               "tipos": dict(cn)}
    with lock:
        tipos_global.update(cn)
        if out:
            interesantes.append(out)
        hechas[0] += 1
        if hechas[0] % 500 == 0:
            print("  %d/%d  (con shader o material: %d)" % (hechas[0], len(bundles), len(interesantes)),
                  flush=True)
    return out


t0 = time.time()
with ThreadPoolExecutor(max_workers=TRABAJADORES) as ex:
    list(ex.map(una, bundles))

SALIDA.write_text(json.dumps({"interesantes": interesantes, "fallos": fallos,
                              "tipos_global": dict(tipos_global)}, ensure_ascii=False), encoding="utf-8")

print("\n" + "=" * 78)
print("TIPOS DE ASSET EN LOS 16.535 BUNDLES")
print("=" * 78)
for t, n in tipos_global.most_common(20):
    print("   %-16s %8d" % (t, n))

con_shader = [i for i in interesantes if i["shaders"]]
print()
print("bundles con SHADER: %d" % len(con_shader))
for i in con_shader[:25]:
    print("   %-46s %d shaders: %s" % (i["bundle"], len(i["shaders"]),
                                       ", ".join(i["shaders"][:6])))

con_mat = [i for i in interesantes if i["materiales"]]
print()
print("bundles con MATERIAL: %d (total materiales: %d)"
      % (len(con_mat), sum(len(i["materiales"]) for i in con_mat)))
for i in con_mat[:20]:
    print("   %-46s %d: %s" % (i["bundle"], len(i["materiales"]), ", ".join(i["materiales"][:5])))

print()
print("fallos:", len(fallos), fallos[:5])
print("guardado en %s   (%.1f min)" % (SALIDA, (time.time() - t0) / 60))