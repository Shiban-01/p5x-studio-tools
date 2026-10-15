"""Abre el bundle de indice (083/Windows) y saca que hay dentro.

Si trae el catalogo del juego como TextAsset, volcarlo da el mapa direccion -> bundle, que es
justo lo que hace falta para saber donde vive cada personaje sin recorrer los 16.535 bundles.
"""
import json
import os
import sys

import UnityPy

BUNDLE = r"C:\Users\Lukas\Downloads\P5X\Client\OuterPackage\Bundles\Windows\083\Windows"
SAL = r"C:\Users\Lukas\p5x-datamining\_dl\indice"
os.makedirs(SAL, exist_ok=True)

env = UnityPy.load(BUNDLE)
print("objetos en el bundle: %d\n" % len(env.objects))

por_tipo = {}
for obj in env.objects:
    por_tipo[obj.type.name] = por_tipo.get(obj.type.name, 0) + 1
for t, n in sorted(por_tipo.items(), key=lambda x: -x[1]):
    print("   %-24s %d" % (t, n))

print()
for obj in env.objects:
    if obj.type.name not in ("TextAsset", "MonoBehaviour"):
        continue
    try:
        datos = obj.read()
    except Exception as e:
        print("   %s: no se pudo leer (%s)" % (obj.type.name, e))
        continue
    nombre = getattr(datos, "m_Name", "") or getattr(datos, "name", "")
    if obj.type.name == "TextAsset":
        crudo = getattr(datos, "m_Script", b"")
        if isinstance(crudo, str):
            crudo = crudo.encode("utf-8", "replace")
        print("   TextAsset '%s'  %d bytes" % (nombre, len(crudo)))
        ruta = os.path.join(SAL, (nombre or "textasset") + ".bin")
        with open(ruta, "wb") as f:
            f.write(crudo)
        print("      volcado a %s" % ruta)
        if crudo[:1] in (b"{", b"["):
            try:
                js = json.loads(crudo)
                print("      JSON valido, claves: %s" % list(js)[:12])
            except Exception:
                print("      parece JSON pero no parsea")
    else:
        print("   MonoBehaviour '%s'" % nombre)
        for campo in ("m_Script", "m_Data", "data", "name"):
            if hasattr(datos, campo):
                v = getattr(datos, campo)
                print("      %s: %s" % (campo, str(v)[:120]))