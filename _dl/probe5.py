import sys
sys.path.insert(0, r"C:/Users/Lukas/p5x-datamining/p5x_studio")
from p5x_studio import herramientas as H
from pathlib import Path
mapa = H._mapa_cues()
# 1) base bank for LD_P3R?
for b in ("Anim_LD_P3R","ch_Anim_LD_P3R","ja_Anim_LD_P3R"):
    p = Path(r"C:/Users/Lukas/Downloads/P5X/Client/OuterPackage/Media/Windows")/(b+".acb")
    print("ACB", b, p.exists())
# 2) usm stems that map to 3-bank cues
media = Path(r"C:/Users/Lukas/Downloads/P5X/Client/OuterPackage/Media/Windows")
usms = [p.stem for p in media.glob("*.usm")]
norm_idx, an_idx = H._indice_cues()
import re
hits3=[]
for stem in usms:
    cands = norm_idx.get(re.sub(r"[^a-z0-9]","",stem.lower()),[])
    if not cands:
        k=H._clave_anagrama(stem); cands=an_idx.get(k,[]) if k else []
    for cue in cands[:8]:
        bancos = mapa.get(cue,[])
        if len(bancos)>=3:
            hits3.append((stem,cue,bancos)); break
print("USM con >=3 bancos:", len(hits3))
for h in hits3[:25]: print("  ", h)
