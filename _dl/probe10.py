import sys, subprocess, hashlib, re
sys.path.insert(0, r"C:/Users/Lukas/p5x-datamining/p5x_studio")
from p5x_studio import herramientas as H
from pathlib import Path
vgm = H._localiza(H._candidatos_vgmstream(), ("-h",))
mdir = Path(r"C:/Users/Lukas/Downloads/P5X/Client/OuterPackage/Media/Windows")
tmp = Path(r"C:/Users/Lukas/p5x-datamining/_dl/_tmp_hash"); tmp.mkdir(parents=True, exist_ok=True)
mapa=H._mapa_cues(); norm_idx,an_idx=H._indice_cues()
def hashsub(acb,sub,tag):
    w=tmp/(tag+".wav")
    subprocess.run(vgm+["-s",str(sub),"-o",str(w),str(acb)],capture_output=True,text=True,timeout=600)
    return hashlib.md5(w.read_bytes()).hexdigest() if w.is_file() else None
tres=[s for s in [p.stem for p in mdir.glob("*.usm")] if True]
from collections import Counter
for p in sorted(mdir.glob("*.usm")):
    stem=p.stem
    infos=H.buscar_audios_video(str(p))
    if len(infos)<3: continue
    hs=[hashsub(Path(i["acb"]),i["subsong"],stem+"_"+str(k)) for k,i in enumerate(infos)]
    uniq=len(set(hs))
    print("%-32s buscar=%d unicos=%d  %s" % (stem, len(infos), uniq, [ (i["idioma"] or "base") for i in infos]))
