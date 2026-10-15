"""Comprueba que el montaje NO use nunca un export recortado (aviso de Aaron).

Para cada capa: lo que declara el Texture2D en el dump frente a lo que miden los PNG exportados, y
cual elige el montador. Si en todas las capas hay un PNG del tamano exacto declarado, el recorte de
AssetStudio no nos afecta (se usa la textura entera, no el sprite recortado).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, r"C:\Users\Lukas\p5x-datamining\_dl")
import montar_bustup as M  # noqa: E402
from PIL import Image  # noqa: E402

CLAVES = [
    "UI-DialogShader-changfu01-xiachuanling",
    "UI-DialogShader-guaidaofu01-jianajun",
    "UI-DialogShader-changfu01-aqi",
    "UI-DialogShader-richang01-zhimingyoumei",
]

datos = json.loads((M.DL / "emparejado_bustups.json").read_text(encoding="utf-8"))["emparejados"]
recortadas = completas = 0

for clave in CLAVES:
    info = datos.get(clave)
    if info is None:
        print("%s: no esta emparejado" % clave)
        continue
    print("=== %s  (%s/%s)" % (clave, info["personaje"], info["ropa"]))
    for b in info["bundles"]:
        M.extraer(b)
    dumps = {b: M.volcar(b) for b in info["bundles"]}
    for paso, nombres in M.ORDEN:
        nombre = next((info["capas"][n]["nombre"] for n in nombres if n in info["capas"]), None)
        if nombre is None:
            continue
        b = next(info["capas"][n]["bundle"] for n in nombres if n in info["capas"])
        tex = M.leer_textura(dumps[b], nombre)
        carpeta = M.CACHE / Path(b).stem
        candidatos = (sorted(carpeta.glob("%s.png" % nombre))
                      + sorted(carpeta.glob("%s_#*.png" % nombre)))
        lineas = []
        for p in candidatos:
            with Image.open(p) as im:
                lleno = im.size == tuple(tex["tamano"])
                lineas.append("%s %dx%d%s" % (p.name[-24:], im.width, im.height,
                                              "" if lleno else " RECORTADO"))
                if lleno:
                    completas += 1
                else:
                    recortadas += 1
        print("   %-9s lienzo %dx%d | %s" % (paso, tex["tamano"][0], tex["tamano"][1],
                                             " | ".join(lineas)))
    print()

print("PNG del tamano exacto declarado: %d | PNG recortados (descartados): %d" % (completas, recortadas))