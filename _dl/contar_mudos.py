#!/usr/bin/env python
"""Cuenta empirica: cuantos .usm resuelven audio con la logica NUEVA y compara con el cache."""
import json, sys, time
sys.path.insert(0, "C:/Users/Lukas/p5x-datamining/p5x_studio")
from pathlib import Path
from p5x_studio import herramientas as H

_MEMO = {}
_orig = H._info_vgm
H._info_vgm = lambda v, a, s: _MEMO.setdefault((str(a), s), _orig(v, a, s))

cache = json.loads(Path("C:/Users/Lukas/p5x-datamining/_dl/estado_audio_video.json").read_text(encoding="utf-8"))
media = H.listar_media()
t0 = time.time()
n_ok = n_no = 0
multis = 0
for i, m in enumerate(media["usm"], 1):
    audios = H.buscar_audios_video(m["ruta"])
    if audios:
        n_ok += 1
        if len(audios) > 1:
            multis += 1
    else:
        n_no += 1
    if i % 25 == 0:
        print("  %d/%d (%.0fs)" % (i, len(media["usm"]), time.time() - t0))
print("resuelven audio: %d   sin audio (mudo): %d   videos con 2+ variantes: %d"
      % (n_ok, n_no, multis))
print("cache dice mudo=%d  audio+silencio=%d"
      % (sum(1 for v in cache.values() if v.get("estado") == "mudo"),
         sum(1 for v in cache.values() if v.get("estado") in ("audio", "silencio"))))
