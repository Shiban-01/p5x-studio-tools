"""Modo lote: saca sombreado cada bust-up de los 216 JSON usando los sprites del juego.

Flujo por cada JSON emparejado:
  1. extrae el bundle del personaje (con el motor, cacheado: no se repite si ya esta)
  2. apila sus capas (cuerpo, brazos, ropa, pelo, ojos, boca)
  3. aplica el sombreado con los parametros de ESE JSON
  4. guarda el PNG

Es reanudable: si la salida ya existe, no la repite. El emparejado JSON<->sprites lo hace
emparejar_jsons.py; aqui se puede sobrescribir con _dl/alias_bustups.json, por ejemplo:

    {"UI-DialogShader-changfu01-suyu": {"personaje": "xinjingsuyu", "ropa": "changfu"}}

Uso:  lote_bustups.py [--limite N] [--solo <trozo de nombre>]
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, r"C:\Users\Lukas\p5x-datamining\_dl")
import sombreado_lihui as S  # noqa: E402
import montar_bustup as MB  # noqa: E402

RAIZ = Path(r"C:\Users\Lukas\p5x-datamining")
DL = RAIZ / "_dl"
JUEGO = Path(r"C:\Users\Lukas\Downloads\P5X\Client\OuterPackage\Bundles\Windows")
MOTOR = RAIZ / "p5x_studio/engine/AssetStudioModCLI_net9_win64/AssetStudioModCLI.exe"
CACHE = DL / "bustups_cache"
SALIDA = DL / "bustups_sombreados"
INFORME = DL / "lote_bustups_informe.json"
ALIAS = DL / "alias_bustups.json"

# orden de apilado; cada paso admite varios nombres porque el juego no es constante.
# El PELO va ARRIBA de todo: el flequillo tapa el borde de los ojos y de la piel (si va debajo, se
# ven pixeles de piel sobre el negro del pelo).
ORDEN = [
    ("contorno", ["benti-lunkuo", "shenti-lunkuo", "lunkuo"]),
    ("cuerpo", ["benti", "shenti", "zhengti"]),
    ("brazos", ["benti-zhi", "shenti-zhi", "zhi"]),
    ("ropa", ["benti-yifu", "shenti-yifu", "yifu"]),
    ("ojos", ["tongchang-yan1"]),
    ("boca", ["tongchang-zui1"]),
    ("pelo", ["benti-toufa", "shenti-toufa", "toufa"]),
]


def extraer(bundle):
    """Extrae el bundle (si no esta ya) y devuelve la carpeta con los PNG."""
    destino = CACHE / Path(bundle).stem
    if destino.exists() and any(destino.rglob("*.png")):
        return destino
    if destino.exists():
        shutil.rmtree(destino, ignore_errors=True)
    destino.mkdir(parents=True, exist_ok=True)
    subprocess.run([str(MOTOR), str(JUEGO / bundle), "-t", "all", "-o", str(destino),
                    "-g", "none", "--unity-version", "2022.3.49f1"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=600)
    return destino


def capa_de(entrada):
    """Lee una capa con sus COORDENADAS (sprite recortado + rect de la malla).

    Devuelve dict con la imagen, el tamano de su textura, su rect de malla y si la imagen es la hoja
    entera. Se apoya en montar_bustup.py, que es quien sabe leer el dump.
    """
    carpeta = MB.extraer(entrada["bundle"])
    dumps = MB.volcar(entrada["bundle"])
    nombre = entrada["nombre"]
    spr = MB.leer_sprite(dumps, nombre)
    tex = MB.leer_textura(dumps, nombre)
    if spr is None or tex is None:
        return None
    png, im, es_lienzo = MB.buscar_png(carpeta, nombre, tex["tamano"], preferir_recortado=True)
    if im is None:
        return None
    return {"im": im, "textura": tex["tamano"], "sprite_textura": spr["textura"],
            "rect": spr["rect"], "malla": MB.leer_malla(dumps, nombre, im.size), "es_lienzo": es_lienzo}


def montar(capas):
    """Apila las capas con sus coordenadas.

    El lienzo lo marca el CUERPO (su textura). Cada capa se coloca en el rect de su malla, que es la
    posicion real del recorte dentro de su hoja; si no hubiera rect de malla y su textura fuese el
    lienzo, se pega la hoja entera en (0,0). Lo que no encaje se avisa y se salta.
    """
    leidas = []
    for _, nombres in ORDEN:
        for n in nombres:
            if n in capas:
                info = capa_de(capas[n])
                if info is not None:
                    leidas.append((n, info))
                break
    if not leidas:
        return None, ["no hay ninguna capa"]
    cuerpo = next((i for n, i in leidas if n in ("benti", "shenti", "zhengti")), None)
    if cuerpo is None:
        return None, ["no hay capa de cuerpo (solo contorno/ojos)"]
    lienzo = tuple(cuerpo["textura"])

    avisos, lona = [], Image.new("RGBA", lienzo, (0, 0, 0, 0))
    for n, info in leidas:
        im, malla = info["im"], info["malla"]
        if malla and abs(malla[2] - im.width) <= 1.5 and abs(malla[3] - im.height) <= 1.5:
            # rect de la malla: Unity mide la Y desde abajo, en el PNG es desde arriba
            alto = info["textura"][1]
            lona.alpha_composite(im, dest=(round(malla[0]), round(alto - malla[1] - malla[3])))
        elif info["es_lienzo"] and tuple(info["textura"]) == lienzo:
            lona.alpha_composite(im, dest=(0, 0))
            avisos.append("capa %s sin rect de malla: pegada la hoja entera" % n)
        else:
            avisos.append("capa %s saltada: mide %s, su textura %s y el lienzo %s"
                          % (n, im.size, info["textura"], lienzo))
    return lona, avisos


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limite", type=int, default=0)
    ap.add_argument("--solo", default="")
    args = ap.parse_args()

    datos = json.loads((DL / "emparejado_bustups.json").read_text(encoding="utf-8"))
    emparejados = datos["emparejados"]
    # los alias (personaje+ropa forzados) ya los aplica emparejar_jsons.py

    SALIDA.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)

    lista = sorted(emparejados.items())
    if args.solo:
        lista = [(n, v) for n, v in lista if args.solo in n]
    if args.limite:
        lista = lista[:args.limite]

    print("bust-ups a sacar: %d" % len(lista))
    hechos, saltados, fallos = 0, 0, []
    for i, (nombre_json, info) in enumerate(lista, 1):
        personaje, ropa = info.get("personaje"), info.get("ropa")
        etiqueta = "%s_%s_%s" % (nombre_json.replace("UI-DialogShader-", ""), personaje, ropa)
        destino = SALIDA / ("%s.png" % etiqueta)
        if destino.exists():
            saltados += 1
            continue
        try:
            montaje, avisos = montar(info.get("capas") or {})
            if montaje is None:
                fallos.append((nombre_json, "; ".join(avisos)))
                continue
            p = S.leer_parametros(DL / "lihui_shader_json" / ("%s.json" % nombre_json))
            sombreado = S.sombrear_imagen(montaje, p)
            sombreado.save(destino)
            if avisos:
                fallos.append((nombre_json, "AVISO: " + "; ".join(avisos)))
            hechos += 1
        except Exception as e:  # noqa: BLE001
            fallos.append((nombre_json, "%s: %s" % (type(e).__name__, e)))
        if i % 10 == 0 or i == len(lista):
            print("   %d/%d  hechos %d | saltados %d | fallos %d"
                  % (i, len(lista), hechos, saltados, len(fallos)), flush=True)

    INFORME.write_text(json.dumps({"hechos": hechos, "saltados": saltados, "fallos": fallos},
                                  ensure_ascii=False, indent=1), encoding="utf-8")
    print()
    print("hechos: %d | ya estaban: %d | fallos: %d" % (hechos, saltados, len(fallos)))
    for nombre, motivo in fallos[:20]:
        print("   %-52s %s" % (nombre, motivo[:80]))
    print("informe:", INFORME)


if __name__ == "__main__":
    raise SystemExit(main())