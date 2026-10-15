import sys, re
sys.path.insert(0, r"C:/Users/Lukas/p5x-datamining/p5x_studio")
from p5x_studio import herramientas as H
from pathlib import Path
media = Path(r"C:/Users/Lukas/Downloads/P5X/Client/OuterPackage/Media/Windows")
mapa=H._mapa_cues(); norm_idx,an_idx=H._indice_cues()
cands1=[]
for p in sorted(media.glob("*.usm")):
    stem=p.stem
    cs=norm_idx.get(re.sub(r"[^a-z0-9]","",stem.lower()),[])
    if not cs:
        k=H._clave_anagrama(stem); cs=an_idx.get(k,[]) if k else []
    for cue in cs[:8]:
        b=mapa.get(cue,[])
        if len(b)==1:
            est=H.estado_audio_de(stem)
            cands1.append((stem,b[0],est)); break
from collections import Counter
print("1-banco total:", len(cands1), Counter(e for _,_,e in cands1))
con=[c for c in cands1 if c[2]=="audio"][:12]
for c in con: print("  ", c)
