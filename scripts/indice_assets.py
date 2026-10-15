"""Indice de ASSETS del juego: el nombre de cada cosa que hay dentro de cada bundle.

Este es el indice bueno. El primer intento (`indice_juego.py`) exportaba mallas, que es lento y solo
ve geometria. Este usa `-m info --export-asset-list xml`, que pide al motor la LISTA de recursos de
un bundle sin exportarlos: nombre y tipo de cada uno. Asi salen mallas, texturas, materiales,
animaciones y todo lo demas, en una fraccion del tiempo.

Hace falta porque el nombre del bundle no delata su contenido. Caso real: las mallas del modelo base
`n_GuitarGirl` estan en `part_l_normal`, pero sus TEXTURAS estan en `shared_7aad509` y
`shared_3b8e0d36`. Sin abrir los bundles y leer la lista, eso no hay quien lo adivine.

Uso:
    python scripts/indice_assets.py                    # todos los bundles, 6 procesos
    python scripts/indice_assets.py --prefijos part_,shared_
    python scripts/indice_assets.py --reanudar         # sigue donde lo dejo

Reanudable: los bundles ya revisados se saltan. Escribe el resultado cada pocos bundles.
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
SALIDA = RAIZ / "_dl/indice_assets"
ESTADO = SALIDA / "assets.json"
FLAGS = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def revisar(bundle: Path) -> tuple[str, dict]:
    """Pide al motor la lista de recursos de un bundle. Devuelve su nombre y su contenido."""
    with tempfile.TemporaryDirectory(dir=str(SALIDA / "_tmp")) as tmp:
        orden = [str(MOTOR), str(bundle), "-m", "info", "--export-asset-list", "xml",
                 "-o", tmp, "--log-level", "Error", "--unity-version", "2022.3.49f1"]
        try:
            subprocess.run(orden, capture_output=True, text=True, timeout=180, creationflags=FLAGS)
        except Exception:
            return "", {"error": "no se pudo abrir"}
        xml = Path(tmp) / "assets.xml"
        if not xml.is_file():
            return "", {"error": "sin listado"}
        try:
            raiz = ET.parse(xml).getroot()
        except Exception:
            return "", {"error": "listado ilegible"}

        assets: dict[str, list[str]] = {}
        for a in raiz.findall("Asset"):
            n, t = a.find("Name"), a.find("Type")
            if n is None or t is None or not n.text:
                continue
            assets.setdefault(t.text, []).append(n.text)

        # quien sale en los nombres: `n_GuitarGirl_body_bc` -> n_GuitarGirl
        quien = set()
        for nombres in assets.values():
            for n in nombres:
                m = re.match(r"^(n_[A-Za-z][A-Za-z0-9]*|PC\d{3}(?:_\d{2})?|[a-z]{4,})_", n)
                if m:
                    quien.add(m.group(1))
        return str(bundle), {
            "cuenta": {t: len(v) for t, v in assets.items()},
            "tiene": sorted(assets),
            "quien": sorted(quien)[:40],
            "muestra": {t: v[:12] for t, v in assets.items()},
        }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefijos", default="")
    ap.add_argument("--hilos", type=int, default=6)
    ap.add_argument("--reanudar", action="store_true")
    args = ap.parse_args()

    SALIDA.mkdir(parents=True, exist_ok=True)
    (SALIDA / "_tmp").mkdir(exist_ok=True)
    datos: dict[str, dict] = {}
    if args.reanudar and ESTADO.is_file():
        datos = json.loads(ESTADO.read_text(encoding="utf-8"))

    prefijos = tuple(p.strip() for p in args.prefijos.split(",") if p.strip())
    lista = []
    for carpeta in sorted(BUNDLES.iterdir()):
        if not carpeta.is_dir():
            continue
        for f in sorted(carpeta.glob("*.bundle")):
            if prefijos and not f.name.startswith(prefijos):
                continue
            clave = "%s/%s" % (carpeta.name, f.name)
            if clave not in datos:
                lista.append((clave, f))

    print("   bundles a revisar: %d   (ya hechos: %d)" % (len(lista), len(datos)), flush=True)
    t0, hechos = time.time(), 0
    with ThreadPoolExecutor(max_workers=args.hilos) as pool:
        futuros = {pool.submit(revisar, f): c for c, f in lista}
        for fut in futuros:
            clave = futuros[fut]
            try:
                _, cont = fut.result()
            except Exception as e:
                cont = {"error": str(e)[:80]}
            datos[clave] = cont
            hechos += 1
            if hechos % 50 == 0:
                ESTADO.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
                print("      ... %d/%d  (%.0f s)" % (hechos, len(lista), time.time() - t0), flush=True)

    ESTADO.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
    print("   LISTO: %d bundles catalogados en %.0f s" % (len(datos), time.time() - t0))


if __name__ == "__main__":
    main()