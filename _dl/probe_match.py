#!/usr/bin/env python
"""Prueba el emparejamiento (herramientas.py) y lista TODAS las variantes de idioma.
Uso: python probe_match.py <stem1> <stem2> ...
"""
import sys, json
sys.path.insert(0, "C:/Users/Lukas/p5x-datamining/p5x_studio")
from p5x_studio import herramientas as H

vgm = H._localiza(H._candidatos_vgmstream(), ("-h",))
print("vgmstream:", vgm)
mapa = H._mapa_cues()
print("cues en el mapa:", len(mapa))
print()

for stem in sys.argv[1:]:
    print("===== %s =====" % stem)
    norm_idx, an_idx = H._indice_cues()
    cands = norm_idx.get(H.re.sub(r"[^a-z0-9]", "", stem.lower()), [])
    if not cands:
        k = H._clave_anagrama(stem)
        cands = an_idx.get(k, []) if k else []
    print("  cues candidatos:", cands[:8])
    for cue in cands[:8]:
        bancos = mapa.get(cue, [])
        print("   cue %s -> bancos %s" % (cue, bancos))
        for banco in bancos:
            acb = H._busca_acb(banco)
            if not acb:
                print("      %-28s (no existe el .acb)" % banco)
                continue
            p = H._pista_de_banco(vgm, acb, cue)
            print("      %-28s -> %s" % (banco, p))
    print()
