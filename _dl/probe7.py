import sys, re, json
sys.path.insert(0, r"C:/Users/Lukas/p5x-datamining/p5x_studio")
from p5x_studio import herramientas as H
from pathlib import Path
media = Path(r"C:/Users/Lukas/Downloads/P5X/Client/OuterPackage/Media/Windows")
mapa = H._mapa_cues(); norm_idx, an_idx = H._indice_cues()
from collections import Counter
cnt = Counter(); ej = {}
for p in sorted(media.glob("*.usm")):
    stem = p.stem
    cands = norm_idx.get(re.sub(r"[^a-z0-9]","",stem.lower()),[])
    if not cands:
        k=H._clave_anagrama(stem); cands=an_idx.get(k,[]) if k else []
    n = 0
    for cue in cands[:8]:
        bancos = mapa.get(cue,[])
        if bancos: n = len(bancos); break
    cnt[n]+=1; ej.setdefault(n,[]).append(stem)
print("bancos -> nº videos:", dict(cnt))
for n in sorted(ej): print(" ", n, "bancos:", ej[n][:6])
