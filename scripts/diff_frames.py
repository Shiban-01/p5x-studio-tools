#!/usr/bin/env python3
"""Compara PNGs de una secuencia tl_* y dice si hay movimiento real.

Uso: python diff_frames.py media/cinematics_capture/tl_*.png
"""
import sys
from pathlib import Path
import numpy as np

try:
    from PIL import Image
except ImportError:
    sys.exit("falta pillow: uv pip install pillow")

paths = sorted(Path(p) for p in sys.argv[1:])
if len(paths) < 2:
    sys.exit("necesito >=2 pngs")

base = np.asarray(Image.open(paths[0]).convert("RGB"), dtype=np.float32)
print(f"{paths[0].name}: {base.shape} base")
prev = base
changed = 0
for p in paths[1:]:
    im = np.asarray(Image.open(p).convert("RGB"), dtype=np.float32)
    d = np.abs(im - prev).mean()
    # percentil 99 del pixel-diff para ignorar ruido JPEG-like
    dd = np.abs(im - prev).max(axis=2)
    pct = (dd > 8).mean() * 100
    tag = "MOV" if pct > 0.5 else "."
    print(f"{p.name:44s} meandiff={d:6.2f} pixcambiados={pct:5.1f}% {tag}")
    if pct > 0.5: changed += 1
    prev = im
print(f"\n=> {changed}/{len(paths)-1} transiciones con movimiento")
