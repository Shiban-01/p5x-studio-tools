#!/usr/bin/env python
"""Extrae UN video con la app real (herramientas.extraer_video) y volca el log.
Uso: python probar_extraccion.py <stem> [carpeta_salida]
"""
import sys, time
sys.path.insert(0, "C:/Users/Lukas/p5x-datamining/p5x_studio")
from pathlib import Path
from p5x_studio import herramientas as H

stem = sys.argv[1]
destino = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("C:/Users/Lukas/p5x-datamining/_dl/verif_video")
media = H.listar_media()
usm = [m for m in media["usm"] if Path(m["nombre"]).stem == stem]
if not usm:
    print("NO ENCONTRADO:", stem)
    sys.exit(1)
t0 = time.time()
print("extrayendo %s -> %s" % (stem, destino))
try:
    out = H.extraer_video(usm[0]["ruta"], destino, lambda s: print("  [log]", s))
    print("OK ->", out, "(%.1f MB)  en %.1fs" % (out.stat().st_size / 1e6, time.time() - t0))
except Exception as e:
    print("ERROR:", e)
    sys.exit(1)
