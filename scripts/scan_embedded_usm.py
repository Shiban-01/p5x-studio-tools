#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
¿Hay vídeos USM ESCONDIDOS dentro de otros ficheros del cliente (bundles, .acb, vfileContent...)?

Un `grep "CRID"` da muchísimos falsos positivos: "CRID" aparece como subcadena suelta dentro de
datos binarios/comprimidos. La firma de un USM de verdad es la cabecera `CRID` seguida de un bloque
`@UTF` (el tablero de metadatos de Sofdec) a los pocos bytes — en los USM del juego, `@UTF` está en
el offset 0x20.

Este script recorre los ficheros del cliente (excluyendo los .usm ya conocidos) en bloques, busca
`CRID` y comprueba si `@UTF` aparece dentro de los 64 bytes siguientes. Solo esos son candidatos
reales a vídeo embebido.

Uso:
    python scripts/scan_embedded_usm.py [--limit N] [--json salida.json]
"""
import argparse
import json
import os
import sys
import time

CLIENTE = r"C:\Users\Lukas\Downloads\P5X\Client"
BLOQUE = 4 << 20          # 4 MB
VENTANA = 64              # bytes tras CRID donde debe caer @UTF

ap = argparse.ArgumentParser()
ap.add_argument("--limit", type=int, default=0)
ap.add_argument("--json", default=r"C:\Users\Lukas\p5x-datamining\_dl\embedded_usm.json")
a = ap.parse_args()


def main():
    objetivo = []
    for raiz, dirs, fs in os.walk(CLIENTE):
        for f in fs:
            if f.lower().endswith(".usm"):
                continue
            p = os.path.join(raiz, f)
            try:
                if os.path.getsize(p) < 4096:
                    continue
            except OSError:
                continue
            objetivo.append(p)
    if a.limit:
        objetivo = objetivo[:a.limit]
    total_gb = sum(os.path.getsize(p) for p in objetivo) / 1e9
    print(f"ficheros a revisar: {len(objetivo)}  ({total_gb:.1f} GB)")
    t0 = time.time()

    hallazgos = []
    sospechosos = []
    for i, p in enumerate(objetivo, 1):
        try:
            with open(p, "rb") as fh:
                cola = b""
                off = 0
                while True:
                    b = fh.read(BLOQUE)
                    if not b:
                        break
                    buf = cola + b
                    base = off - len(cola)
                    j = buf.find(b"CRID")
                    while j >= 0:
                        abs_off = base + j
                        # @UTF dentro de la ventana siguiente?
                        if b"@UTF" in buf[j + 4: j + 4 + VENTANA]:
                            hallazgos.append({"fichero": os.path.relpath(p, CLIENTE),
                                              "offset": abs_off})
                        else:
                            sospechosos.append(os.path.relpath(p, CLIENTE))
                        j = buf.find(b"CRID", j + 1)
                    cola = buf[-(VENTANA - 1):]
                    off += len(b)
        except Exception as e:
            print(f"  error en {p}: {type(e).__name__}")
        if i % 200 == 0:
            print(f"  ... {i}/{len(objetivo)}  ({time.time()-t0:.0f}s)  candidatos reales: {len(hallazgos)}")

    print(f"\n=== fin ({time.time()-t0:.0f}s) ===")
    print(f"coincidencias con firma de USM real (CRID+@UTF): {len(hallazgos)}")
    for h in hallazgos[:40]:
        print(f"   {h['fichero']}  @ {h['offset']}")
    print(f"\nficheros con 'CRID' suelto (falsos positivos): {len(set(sospechosos))}")
    for s in sorted(set(sospechosos))[:25]:
        print(f"   {s}")
    json.dump({"reales": hallazgos, "falsos": sorted(set(sospechosos))},
              open(a.json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\ninforme: {a.json}")


if __name__ == "__main__":
    sys.exit(main() or 0)