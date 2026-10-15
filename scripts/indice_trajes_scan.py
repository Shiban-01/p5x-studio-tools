"""Reabre los bundles del juego para leer la LISTA COMPLETA de recursos que llevan dentro.

El indice de assets (`_dl/indice_assets/assets.json`) ya cataloga los 16.535 bundles, pero su
campo `muestra` esta RECORTADO a 12 nombres por tipo. Para un indice de trajes hace falta la lista
entera: un bundle de modelo puede traer 25 mallas y con 12 no se ven todas las piezas del traje.

Esto no exporta nada: solo pide al motor la lista de recursos (`-m info --export-asset-list xml`),
que tarda ~0,4 s por bundle. Reanudable: los bundles ya leidos se saltan.

Uso:
    python scripts/indice_trajes_scan.py                 # bundles con mallas (Mesh)
    python scripts/indice_trajes_scan.py --todos         # ademas part_ y shared_
    python scripts/indice_trajes_scan.py --hilos 8

Salida: _dl/indice_trajes/assets_full.json
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BUNDLES = Path(r"C:/Users/Lukas/Downloads/P5X/Client/OuterPackage/Bundles/Windows")
MOTOR = RAIZ / "p5x_studio/motor/AssetStudioModCLI_net9_win64/AssetStudioModCLI.exe"
INDICE_ASSETS = RAIZ / "_dl/indice_assets/assets.json"
SALIDA = RAIZ / "_dl/indice_trajes"
ESTADO = SALIDA / "assets_full.json"
TMP = SALIDA / "_tmp"
FLAGS = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def revisar(clave: str) -> tuple[str, dict]:
    """Lee la lista completa de recursos de un bundle (clave = 'carpeta/fichero.bundle')."""
    bundle = BUNDLES / clave.replace("/", "\\")
    with tempfile.TemporaryDirectory(dir=str(TMP)) as tmp:
        orden = [str(MOTOR), str(bundle), "-m", "info", "--export-asset-list", "xml",
                 "-o", tmp, "--log-level", "Error", "--unity-version", "2022.3.49f1"]
        try:
            subprocess.run(orden, capture_output=True, text=True, timeout=300,
                           stdin=subprocess.DEVNULL, creationflags=FLAGS)
        except Exception as e:
            return clave, {"error": "no se pudo abrir: %s" % str(e)[:80]}
        xml = Path(tmp) / "assets.xml"
        if not xml.is_file():
            return clave, {"error": "sin listado"}
        try:
            raiz = ET.parse(xml).getroot()
        except Exception as e:
            return clave, {"error": "listado ilegible: %s" % str(e)[:80]}
        assets: dict[str, list[str]] = {}
        for a in raiz.findall("Asset"):
            n, t = a.find("Name"), a.find("Type")
            if n is None or t is None or not n.text:
                continue
            assets.setdefault(t.text, []).append(n.text)
        return clave, {
            "cuenta": {t: len(v) for t, v in assets.items()},
            "tiene": sorted(assets),
            "nombres": {t: sorted(set(v)) for t, v in assets.items()},
        }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hilos", type=int, default=8)
    ap.add_argument("--todos", action="store_true",
                    help="incluye tambien part_ y shared_ aunque no tengan mallas")
    ap.add_argument("--limite", type=int, default=0)
    args = ap.parse_args()

    SALIDA.mkdir(parents=True, exist_ok=True)
    TMP.mkdir(exist_ok=True)
    datos: dict[str, dict] = {}
    if ESTADO.is_file():
        datos = json.loads(ESTADO.read_text(encoding="utf-8"))

    assets = json.loads(INDICE_ASSETS.read_text(encoding="utf-8"))
    lista = []
    for clave, v in assets.items():
        if "Mesh" in (v.get("tiene") or []):
            lista.append(clave)
        elif args.todos and clave.split("/", 1)[1].startswith(("part_", "shared_")):
            lista.append(clave)
    pend = [c for c in lista if c not in datos]
    if args.limite:
        pend = pend[: args.limite]
    print("   a leer: %d   (ya hechos: %d de %d)" % (len(pend), len(datos), len(lista)),
          flush=True)

    t0, hechos = time.time(), 0
    with ThreadPoolExecutor(max_workers=args.hilos) as pool:
        for clave, cont in pool.map(revisar, pend):
            datos[clave] = cont
            hechos += 1
            if hechos % 100 == 0:
                ESTADO.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
                print("      ... %d/%d  (%.0f s)" % (hechos, len(pend), time.time() - t0),
                      flush=True)
    ESTADO.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
    print("   LISTO: %d bundles leidos en %.0f s" % (len(datos), time.time() - t0))


if __name__ == "__main__":
    main()