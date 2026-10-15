"""Busca en que bundle viven las TEXTURAS de un personaje.

Recorre bundles de modelo abriendolos con AssetStudioModCLI (los .bundle estan
cifrados; no vale grep) y exporta solo tex2d, mirando los .png cuyo nombre
contenga alguno de los terminos buscados.

Reanudable: guarda en ESTADO los bundles ya revisados y no repite.

Uso:
  python scripts/buscar_textura_chord.py --terminos chord,guitargirl --patron part_normal,part_itargirl
  python scripts/buscar_textura_chord.py --terminos chord --patron part --limite 806
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BUNDLES = Path(r"C:/Users/Lukas/Downloads/P5X/Client/OuterPackage/Bundles/Windows")
MOTOR = RAIZ / "p5x_studio/motor/AssetStudioModCLI_net9_win64/AssetStudioModCLI.exe"
TRABAJO = RAIZ / "_dl/rastreo_texturas"
ESTADO = TRABAJO / "estado.json"


def candidatos(patrones: list[str]) -> list[Path]:
    salida: list[Path] = []
    for carpeta in sorted(BUNDLES.iterdir()):
        if not carpeta.is_dir():
            continue
        for f in sorted(carpeta.glob("*.bundle")):
            if any(f.name.startswith(p) for p in patrones):
                salida.append(f)
    return salida


def cargar_estado(ruta: Path) -> dict:
    if ruta.exists():
        return json.loads(ruta.read_text(encoding="utf-8"))
    return {"revisados": [], "hallazgos": {}}


def guardar_estado(est: dict, ruta: Path) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(est, ensure_ascii=False, indent=1), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--terminos", required=True, help="lista separada por comas, minusculas")
    ap.add_argument("--patron", required=True, help="prefijos de bundle separados por comas")
    ap.add_argument("--nombre-contiene", default="", help="subcadenas separadas por comas que debe tener el nombre del bundle")
    ap.add_argument("--limite", type=int, default=0)
    ap.add_argument("--worker", type=int, default=0)
    ap.add_argument("--workers", type=int, default=1)
    args = ap.parse_args()

    terminos = [t.strip().lower() for t in args.terminos.split(",") if t.strip()]
    patrones = [p.strip() for p in args.patron.split(",") if p.strip()]
    nom = [s.strip().lower() for s in args.nombre_contiene.split(",") if s.strip()]
    TRABAJO.mkdir(parents=True, exist_ok=True)

    lista = candidatos(patrones)
    if nom:
        lista = [b for b in lista if any(s in b.name.lower() for s in nom)]
    if args.workers > 1:
        lista = [b for i, b in enumerate(lista) if i % args.workers == args.worker]
    if args.limite:
        lista = lista[: args.limite]
    est_ruta = TRABAJO / ("estado_w%d.json" % args.worker)
    est = cargar_estado(est_ruta)
    revisados = set(est["revisados"])

    print("   bundles a revisar: %d (ya revisados: %d)" % (len(lista), len(revisados)))
    t0 = time.time()
    n = 0
    for bundle in lista:
        clave = str(bundle.relative_to(BUNDLES)).replace("\\", "/")
        if clave in revisados:
            continue
        n += 1
        destino = TRABAJO / ("ex_" + bundle.stem)
        if not destino.exists():
            orden = [str(MOTOR), str(bundle), "-m", "export", "-t", "tex2d",
                     "-o", str(destino), "--log-level", "Error", "-r",
                     "--unity-version", "2022.3.49f1"]
            try:
                subprocess.run(orden, capture_output=True, text=True, timeout=600,
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            except Exception:
                pass
        pngs = [p.name for p in destino.rglob("*.png")] if destino.exists() else []
        enc = [p for p in pngs if any(t in p.lower() for t in terminos)]
        est["revisados"].append(clave)
        if enc:
            est["hallazgos"][clave] = sorted(enc)
            print("   >>> HIT %s  (%d png): %s" % (clave, len(pngs), ", ".join(sorted(enc))))
        elif pngs:
            print("   %s: %d png, ninguno coincide (%s)" % (clave, len(pngs), ", ".join(sorted(pngs)[:3])))
        else:
            print("   %s: 0 png" % clave)
        if n % 10 == 0:
            guardar_estado(est, est_ruta)
            print("   ... %d revisados en esta pasada, %.0f s" % (n, time.time() - t0))
    guardar_estado(est, est_ruta)
    print()
    print("   HECHOS %d bundles en %.0f s" % (n, time.time() - t0))
    print("   HALLAZGOS: %d bundles" % len(est["hallazgos"]))
    for k, v in est["hallazgos"].items():
        print("      %s -> %s" % (k, ", ".join(v)))


if __name__ == "__main__":
    main()