"""Depura el emparejado: mira que nombres de sprite hay para personajes concretos."""
import json
import re
from pathlib import Path

CENSO = Path(r"C:\Users\Lukas\p5x-datamining\_dl\censo_texturas.json")
filas = json.loads(CENSO.read_text(encoding="utf-8"))["filas"]

for aguja in ("suyu", "aqi", "lizi", "shuangye", "jianajun", "munei", "qianzao"):
    nombres = sorted({f["nombre"] for f in filas if aguja in f["nombre"].lower()})
    print("=== %s: %d nombres ===" % (aguja, len(nombres)))
    for n in nombres[:14]:
        print("   ", n)
    print()