import sys, re, json
sys.path.insert(0, r"C:/Users/Lukas/p5x-datamining/p5x_studio")
from p5x_studio import herramientas as H
stem = "CG_LDP3R_Event_03_01_26_01"
norm_idx, an_idx = H._indice_cues()
cands = norm_idx.get(re.sub(r"[^a-z0-9]", "", stem.lower()), [])
print("norm cands:", cands)
k = H._clave_anagrama(stem)
print("anagram key:", k)
print("anagram cands:", an_idx.get(k, []))
mapa = H._mapa_cues()
print("mapa total cues:", len(mapa))
for c in cands:
    print(" ", c, "->", mapa.get(c))
# also search mapa keys containing LD_P3R or 03_01_26
for c in mapa:
    if "LDP3R" in c and "26" in c:
        print("  KEY:", c, mapa[c])
