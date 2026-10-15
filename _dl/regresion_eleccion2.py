#!/usr/bin/env python
"""Como regresion_eleccion.py pero solo donde el cue apunta a >=2 bancos existentes
(ahi es donde el orden japones/chino puede cambiar la eleccion)."""
import sys, time
sys.path.insert(0, "C:/Users/Lukas/p5x-datamining/p5x_studio")
from pathlib import Path
from p5x_studio import herramientas as H

media = H.listar_media()
vgm = H._localiza(H._candidatos_vgmstream(), ("-h",))
mapa = H._mapa_cues()
norm_idx, an_idx = H._indice_cues()

# memoiza vgmstream -I (el cuello de botella): el mismo (acb, subsong) se pide muchas veces
_MEMO = {}
_orig_info = H._info_vgm


def _info_memo(vgm_, acb, sub):
    clave = (str(acb), sub)
    if clave not in _MEMO:
        _MEMO[clave] = _orig_info(vgm_, acb, sub)
    return _MEMO[clave]


H._info_vgm = _info_memo


def cues_de(stem):
    c = norm_idx.get(H.re.sub(r"[^a-z0-9]", "", stem.lower()), [])
    if not c:
        k = H._clave_anagrama(stem)
        c = an_idx.get(k, []) if k else []
    return c[:8]


def bancos_vivos(cands):
    vivos = []
    for cue in cands:
        for banco in mapa.get(cue, []):
            if H._busca_acb(banco):
                vivos.append(banco)
    return vivos


def antiguo(cands):
    for cue in cands:
        for banco in mapa.get(cue, []):
            acb = H._busca_acb(banco)
            if not acb:
                continue
            p = H._pista_de_banco(vgm, acb, cue)
            if p:
                return (banco, cue, p[0])
    return None


dif, multi, t0 = [], 0, time.time()
for i, m in enumerate(media["usm"], 1):
    stem = Path(m["nombre"]).stem
    cands = cues_de(stem)
    bancos = bancos_vivos(cands)
    if len(bancos) < 2:
        continue
    multi += 1
    a = antiguo(cands)
    n = H.buscar_audio_video(m["ruta"])
    ab = a[0] if a else None
    nb = n["banco"] if n else None
    if ab != nb:
        dif.append((stem, ab, nb, a[2] if a else None, n["subsong"] if n else None))
    if i % 25 == 0:
        print("  %d/%d (%.1fs)" % (i, len(media["usm"]), time.time() - t0))

print("\nvideos con >=2 bancos vivos:", multi)
print("cambian de banco:", len(dif))
for stem, ab, nb, asub, nsub in dif:
    print("  %-44s %-26s -> %-26s (sub %s -> %s)" % (stem, ab, nb, asub, nsub))
