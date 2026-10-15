"""Inventario completo de los shaders del juego: nombre, propiedades y bloques de bytecode.

UnityPy lee la copia extraida del contenedor vfile (los bundles del juego van cifrados por dentro).
Cada objeto Shader lleva, en crudo: la lista de propiedades (empieza por _MainTex...) y, mas adelante,
el nombre del shader ("UI/UIUnmask", "UIEffect/HuaPing"...). Los bloques compilados se localizan por
la firma DXBC. Todo se guarda en _dl/shaders_del_juego.json para no repetir el parseo.
"""
import json
import re

import UnityPy

B = r"C:\Users\Lukas\p5x-datamining\game_dump\fileContentOut\Bundles\Windows\106\shaders.bundle"
SALIDA = r"C:\Users\Lukas\p5x-datamining\_dl\shaders_del_juego.json"

# candidatos a nombre de shader: algo/algo
PATRON_NOMBRE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_ ]*(/[A-Za-z0-9_][A-Za-z0-9_ ]*)+$")
RUIDO = {"$Globals", "UnityPerDraw", "UnityPerMaterial", "UnityInstancingPerDraw"}


def analizar(raw):
    textos = [s.decode("ascii", "ignore") for s in re.findall(rb"[\x20-\x7e]{4,80}", raw)]
    nombres = [t for t in textos if PATRON_NOMBRE.match(t) and t not in RUIDO
               and not t.startswith(("Assets/", "Packages/", "Library/"))
               and "/" in t and len(t) < 50]
    props = [t for t in textos if re.fullmatch(r"_[A-Za-z][A-Za-z0-9_]{1,28}", t)]
    return nombres, props


env = UnityPy.load(B)
filas = []
for o in env.objects:
    if o.type.name not in ("Shader", "ComputeShader"):
        continue
    raw = o.get_raw_data()
    nombres, props = analizar(raw)
    # el nombre del shader es el ultimo candidato (los tipos de propiedad van antes)
    nombre = nombres[-1] if nombres else "?"
    filas.append({"tipo": o.type.name, "nombre": nombre, "otros_candidatos": nombres[:-1][:6],
                  "props": sorted(set(props)), "bytes": len(raw), "dxbc": raw.count(b"DXBC"),
                  "pathid": o.path_id})

filas.sort(key=lambda f: f["nombre"])
guardar = [{k: v for k, v in f.items() if k != "props"} | {"props": f["props"]} for f in filas]
with open(SALIDA, "w", encoding="utf-8") as fh:
    json.dump(guardar, fh, ensure_ascii=False, indent=1)

nombrados = [f for f in filas if f["nombre"] != "?"]
print("shaders: %d   con nombre: %d" % (len(filas), len(nombrados)))
print()
print("=== TODOS los nombres ===")
for f in nombrados:
    print("   %-44s %8d B  %3d dxbc  props:%2d" % (f["nombre"][:44], f["bytes"], f["dxbc"],
                                                   len(f["props"])))
print()
print("=== los de interfaz (UI / UIEffect / Custom) ===")
for f in nombrados:
    if re.match(r"^(UI|UIEffect|Custom|Hidden)/", f["nombre"]):
        print("   %-44s props: %s" % (f["nombre"][:44], ", ".join(f["props"][:14])))
print()
print("inventario guardado en", SALIDA)