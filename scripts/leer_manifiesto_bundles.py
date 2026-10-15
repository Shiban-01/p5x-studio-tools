"""Lee el AssetBundleManifest del bundle 083/Windows: la lista oficial de bundles del juego.

Ademas cruza esa lista con los ficheros que hay en disco para saber si estan todos descargados, y
guarda el indice en JSON para que la herramienta no tenga que releerlo cada vez.
"""
import json
import os
import re

import UnityPy

RAIZ = r"C:\Users\Lukas\Downloads\P5X\Client\OuterPackage\Bundles\Windows"
MANIFIESTO = os.path.join(RAIZ, "083", "Windows")
SAL = r"C:\Users\Lukas\p5x-datamining\_dl\indice"
os.makedirs(SAL, exist_ok=True)

env = UnityPy.load(MANIFIESTO)
nombres = []
for obj in env.objects:
    if obj.type.name != "AssetBundleManifest":
        continue
    datos = obj.read()
    crudo = getattr(datos, "m_AssetBundleNames", None)
    if crudo is None:
        # algunas versiones lo exponen distinto
        for campo in dir(datos):
            if "bundle" in campo.lower() and "name" in campo.lower():
                crudo = getattr(datos, campo)
                print("   usando campo alternativo: %s" % campo)
                break
    if crudo is not None:
        nombres = [str(x) for x in crudo]

print("bundles en el manifiesto: %d" % len(nombres))
print("   ejemplos:")
for n in nombres[:8]:
    print("      %s" % n)

# los nombres del manifiesto suelen traer prefijo de carpeta; el fichero real es el ultimo tramo
def fichero_de(nombre):
    base = nombre.replace("\\", "/").split("/")[-1]
    if not base.endswith(".bundle"):
        base += ".bundle"
    return base

# indice de lo que hay en disco: nombre de fichero -> ruta relativa
en_disco = {}
for raiz, _, ficheros in os.walk(RAIZ):
    for f in ficheros:
        if f.endswith(".bundle"):
            en_disco[f] = os.path.relpath(os.path.join(raiz, f), RAIZ)

print("\nficheros .bundle en disco: %d" % len(en_disco))

faltan = [n for n in nombres if fichero_de(n) not in en_disco]
print("del manifiesto, no estan en disco: %d" % len(faltan))
if faltan:
    for n in faltan[:5]:
        print("      %s" % n)

# indice util: nombre de asset -> fichero, sacado del patron <tipo>_<nombre><hash>.bundle
patron = re.compile(r"^(?P<tipo>[a-z0-9]+)_(?P<nombre>.+?)(?P<hash>[0-9a-f]{8,})\.bundle$")
indice = {}
for fichero, rel in en_disco.items():
    m = patron.match(fichero)
    if not m:
        continue
    clave = m.group("nombre")
    indice.setdefault(clave, []).append(rel)

print("\nentradas de indice (nombre logico -> ficheros): %d" % len(indice))
for clave in sorted(k for k in indice if "pc079" in k.lower())[:10]:
    print("   %-40s %s" % (clave, indice[clave]))

ruta_json = os.path.join(SAL, "indice_bundles.json")
with open(ruta_json, "w", encoding="utf-8") as f:
    json.dump({"bundles_en_manifiesto": nombres,
               "en_disco": en_disco,
               "por_nombre": {k: v for k, v in indice.items()}},
              f, ensure_ascii=False, indent=1)
print("\nindice guardado en %s (%.1f MB)" % (ruta_json, os.path.getsize(ruta_json) / 1048576))