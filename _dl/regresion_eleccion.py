#!/usr/bin/env python
"""Compara la eleccion ANTIGUA (primer banco que case, en orden de mapa) con la NUEVA
(japones > chino > base) para los 347 .usm, y lista las diferencias. Sin decodificar audio.
"""
import sys, time
sys.path.insert(0, "C:/Users/Lukas/p5x-datamining/p5x_studio")
from pathlib import Path
from p5x_studio import herramientas as H

media = H.listar_media()
vgm = H._localiza(H._candidatos_vgmstream(), ("-h",))
mapa = H._mapa_cues()
norm_idx, an_idx = H._indice_cues()


def antiguo(stem):
    cands = norm_idx.get(H.re.sub(r"[^a-z0-9]", "", stem.lower()), [])
    if not cands:
        k = H._clave_anagrama(stem)
        cands = an_idx.get(k, []) if k else []
    for cue in cands[:8]:
        for banco in mapa.get(cue, []):
            acb = H._busca_acb(banco)
            if not acb:
                continue
            p = H._pista_de_banco(vgm, acb, cue)
            if p:
                return (banco, cue, p[0])
    return None


dif = []
t0 = time.time()
for i, m in enumerate(media["usm"], 1):
    stem = Path(m["nombre"]).stem
    a = antiguo(stem)
    n = H.buscar_audio_video(m["ruta"])
    nb = n["banco"] if n else None
    ab = a[0] if a else None
    if ab != nb:
        dif.append((stem, ab, nb, a[2] if a else None, n["subsong"] if n else None))
    if i % 50 == 0:
        print("  %d/%d (%.1fs)" % (i, len(media["usm"]), time.time() - t0))

print("\ntotal videos:", len(media["usm"]))
print("cambian de banco:", len(dif))
for stem, ab, nb, asub, nsub in dif:
    print("  %-44s %-26s -> %-26s (sub %s -> %s)" % (stem, ab, nb, asub, nsub))
