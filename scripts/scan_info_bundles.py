"""Escaneo rapido de bundles: lista assets con '-m info --export-asset-list xml'
(sin convertir texturas, ~0.7 s/bundle) y busca Texture2D por nombre.

Reanudable: guarda bundles ya revisados y hallazgos en _dl/rastreo_texturas/scan_info.json
Uso:
  python scripts/scan_info_bundles.py --terminos chord,guitargirl --prefijos part_,role_,shared_ --hilos 8
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BUNDLES = Path(r"C:/Users/Lukas/Downloads/P5X/Client/OuterPackage/Bundles/Windows")
MOTOR = RAIZ / "p5x_studio/motor/AssetStudioModCLI_net9_win64/AssetStudioModCLI.exe"
TRABAJO = RAIZ / "_dl/rastreo_texturas"
ESTADO = TRABAJO / "scan_info.json"
TMP = TRABAJO / "_tmp_info"

_lock = threading.Lock()


def candidatos(prefijos: list[str]) -> list[Path]:
    salida: list[Path] = []
    for carpeta in sorted(BUNDLES.iterdir()):
        if not carpeta.is_dir():
            continue
        for f in sorted(carpeta.glob("*.bundle")):
            if not prefijos or any(f.name.startswith(p) for p in prefijos):
                salida.append(f)
    return salida


def estado_cargar() -> dict:
    if ESTADO.exists():
        return json.loads(ESTADO.read_text(encoding="utf-8"))
    return {"revisados": [], "hallazgos": {}}


def guardar(est: dict) -> None:
    with _lock:
        tmp = ESTADO.with_suffix(".tmp")
        tmp.write_text(json.dumps(est, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(ESTADO)


import xml.etree.ElementTree as ET


def revisar(bundle: Path, terminos: list[str]) -> tuple[str, list[str], str]:
    clave = str(bundle.relative_to(BUNDLES)).replace("\\", "/")
    out = TMP / bundle.stem
    out.mkdir(parents=True, exist_ok=True)
    orden = [str(MOTOR), str(bundle), "-m", "info", "--export-asset-list", "xml",
             "--load-all", "-o", str(out), "--log-level", "Error", "-r",
             "--unity-version", "2022.3.49f1"]
    try:
        subprocess.run(orden, capture_output=True, text=True, timeout=90,
                       stdin=subprocess.DEVNULL,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except Exception as e:
        return clave, [], "error:%s" % e
    xml = out / "assets.xml"
    if not xml.exists():
        return clave, [], "sin-xml"
    enc = []
    try:
        raiz = ET.parse(str(xml)).getroot()
    except Exception as e:
        return clave, [], "xml-error:%s" % e
    for asset in raiz.findall("Asset"):
        nombre_el = asset.find("Name")
        tipo_el = asset.find("Type")
        if nombre_el is None or tipo_el is None:
            continue
        if (tipo_el.text or "") not in ("Texture2D", "Sprite"):
            continue
        nombre = nombre_el.text or ""
        if any(t in nombre.lower() for t in terminos):
            enc.append("%s (%s)" % (nombre, tipo_el.text))
    return clave, sorted(set(enc)), "ok"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--terminos", required=True)
    ap.add_argument("--prefijos", default="", help="prefijos separados por comas; vacio = todos")
    ap.add_argument("--hilos", type=int, default=1)
    ap.add_argument("--limite", type=int, default=0)
    ap.add_argument("--worker", type=int, default=0)
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--estado", default="scan_info.json")
    args = ap.parse_args()

    terminos = [t.strip().lower() for t in args.terminos.split(",") if t.strip()]
    prefijos = [p.strip() for p in args.prefijos.split(",") if p.strip()]
    global ESTADO
    ESTADO = TRABAJO / args.estado
    TRABAJO.mkdir(parents=True, exist_ok=True)
    TMP.mkdir(parents=True, exist_ok=True)

    lista = candidatos(prefijos)
    if args.workers > 1:
        lista = [b for i, b in enumerate(lista) if i % args.workers == args.worker]
    if args.limite:
        lista = lista[: args.limite]
    est = estado_cargar()
    ya = set(est["revisados"])
    pend = [b for b in lista if str(b.relative_to(BUNDLES)).replace("\\", "/") not in ya]
    print("   a revisar: %d de %d (ya hechos %d)" % (len(pend), len(lista), len(ya)))
    t0 = time.time()
    hechos = 0
    for b in pend:
        clave, enc, nota = revisar(b, terminos)
        hechos += 1
        est["revisados"].append(clave)
        if enc:
            est["hallazgos"][clave] = enc
            print("   >>> HIT %s -> %s" % (clave, "; ".join(enc)), flush=True)
        if hechos % 10 == 0:
            guardar(est)
        if hechos % 100 == 0:
            print("   ... %d/%d  %.0f s" % (hechos, len(pend), time.time() - t0), flush=True)
    guardar(est)
    print()
    print("   HECHOS %d en %.0f s" % (hechos, time.time() - t0))
    print("   HALLAZGOS: %d" % len(est["hallazgos"]))
    for k, v in est["hallazgos"].items():
        print("      %s -> %s" % (k, "; ".join(v)))


if __name__ == "__main__":
    main()