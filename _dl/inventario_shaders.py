"""Inventario de los shaders del bundle de la shaderlib (431 Shader), via UnityPy.

El motor (AssetStudioMod) no lista los tipos Shader/Material, pero UnityPy si lee la copia extraida
del contenedor vfile. Este script saca, por shader: nombre, tamano, cuantos bloques DXBC lleva y su
path_id. Guarda el inventario completo en JSON para ir al shader que interese sin repetir el parseo.
"""
import json
import re

import UnityPy

B = r"C:\Users\Lukas\p5x-datamining\game_dump\fileContentOut\Bundles\Windows\106\shaders.bundle"
SALIDA = r"C:\Users\Lukas\p5x-datamining\_dl\shaders_del_juego.json"

env = UnityPy.load(B)
filas = []
for o in env.objects:
    if o.type.name not in ("Shader", "ComputeShader"):
        continue
    raw = o.get_raw_data()
    m = re.match(rb"[\x20-\x7e]{2,80}", raw[:80].lstrip(b"\x00"))
    nombre = m.group().decode("ascii", "ignore") if m else "?"
    filas.append({"tipo": o.type.name, "nombre": nombre, "bytes": len(raw),
                  "dxbc": raw.count(b"DXBC"), "pathid": o.path_id})

filas.sort(key=lambda f: f["nombre"])
nombrados = [f for f in filas if f["nombre"] != "?"]
print("objetos shader: %d   con nombre legible: %d" % (len(filas), len(nombrados)))
print()
print("=== los que llevan mas bytecode ===")
for f in sorted(filas, key=lambda f: -f["dxbc"])[:15]:
    print("   %-46s %8d B  %3d dxbc" % (f["nombre"][:46], f["bytes"], f["dxbc"]))
print()
print("=== nombres (hasta 100) ===")
for f in nombrados[:100]:
    print("   %-48s %8d B  %2d" % (f["nombre"][:48], f["bytes"], f["dxbc"]))

with open(SALIDA, "w", encoding="utf-8") as fh:
    json.dump(filas, fh, ensure_ascii=False, indent=1)
print()
print("inventario guardado en", SALIDA)