"""Busca en que bundle del juego vive un nombre de malla concreto.

Hace falta porque el nombre del bundle NO delata su contenido: el modelo de `fengbandadi` vive en
`part_n_normal...bundle`, y el de la skin `pc077` se apoya en el base `chord_normal`, que esta en
`part_itargirl...bundle`. Ni el nombre del bundle ni el del personaje lo dicen.

Como funciona: recorre los bundles de modelo (`part_*`), extrae solo las mallas (que son ligeras) y
mira si algun nombre de malla contiene el texto buscado. Nada de recorrer los 16.535 del juego: los
personajes viven en los `part_`.

Uso:  python scripts/buscar_malla.py chord_normal [--todos]
      --todos   mira tambien role_ y tl_ (mas lento)
"""
from __future__ import annotations

import re
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BUNDLES = Path(r"C:/Users/Lukas/Downloads/P5X/Client/OuterPackage/Bundles/Windows")
MOTOR = RAIZ / "p5x_studio/motor/AssetStudioModCLI_net9_win64/AssetStudioModCLI.exe"
TRABAJO = RAIZ / "_dl/rastreo_mallas"


def bundles_a_mirar(todos: bool) -> list[Path]:
    patrones = ("part_*",) if not todos else ("part_*", "role_*", "tl_*")
    salida: list[Path] = []
    for p in patrones:
        salida += sorted(BUNDLES.glob("*/*.bundle")) if False else []
    salida = []
    for carpeta in sorted(BUNDLES.iterdir()):
        if not carpeta.is_dir():
            continue
        for f in sorted(carpeta.glob("*.bundle")):
            if any(f.name.startswith(p.split("*")[0]) for p in patrones):
                salida.append(f)
    return salida


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("uso: buscar_malla.py <texto> [--todos]")
    texto = sys.argv[1].lower()
    todos = "--todos" in sys.argv
    TRABAJO.mkdir(parents=True, exist_ok=True)

    candidatos = bundles_a_mirar(todos)
    print("   bundles a revisar: %d" % len(candidatos))
    encontrados: list[tuple[str, str]] = []
    t0 = time.time()
    for i, bundle in enumerate(candidatos, 1):
        destino = TRABAJO / bundle.stem
        if not destino.exists():
            orden = [str(MOTOR), str(bundle), "-m", "export", "-t", "mesh",
                     "-o", str(destino), "--log-level", "Error", "-r",
                     "--unity-version", "2022.3.49f1"]
            try:
                subprocess.run(orden, capture_output=True, text=True, timeout=600,
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            except Exception:
                continue
        for obj in destino.rglob("*.obj"):
            if texto in obj.name.lower():
                encontrados.append((bundle.name, obj.stem))
                print("   ENCONTRADO en %s -> %s" % (bundle.name, obj.stem))
                break
        if i % 25 == 0:
            print("   ... %d/%d revisados, %.0f s" % (i, len(candidatos), time.time() - t0))

    print()
    print("   RESULTADO: %d bundles con '%s'  (%.0f s)" % (len(encontrados), texto, time.time() - t0))
    for b, m in encontrados:
        print("      %s -> %s" % (b, m))


if __name__ == "__main__":
    main()