import sys, subprocess, hashlib, wave, array
sys.path.insert(0, r"C:/Users/Lukas/p5x-datamining/p5x_studio")
from p5x_studio import herramientas as H
from pathlib import Path
vgm = H._localiza(H._candidatos_vgmstream(), ("-h",))
mdir = Path(r"C:/Users/Lukas/Downloads/P5X/Client/OuterPackage/Media/Windows")
tmp = Path(r"C:/Users/Lukas/p5x-datamining/_dl/_tmp_hash"); tmp.mkdir(parents=True, exist_ok=True)

def decode(acb, sub, tag):
    w = tmp/(tag+".wav")
    subprocess.run(vgm+["-s",str(sub),"-o",str(w),str(acb)],capture_output=True,text=True,timeout=600)
    if not w.is_file(): return None
    return hashlib.md5(w.read_bytes()).hexdigest(), w.stat().st_size

def flat(w):
    with wave.open(str(w),"rb") as f:
        n=min(f.getnframes(),f.getframerate()*20); d=f.readframes(n)
    a=array.array("h"); a.frombytes(d)
    if not a: return 0.0
    m=sum(a)/len(a); var=sum((x-m)**2 for x in a)/len(a)
    return round(var/ (1e9),3)

# CG_LD_Event_01_13_01 : ja s2, ch s2, base s1
print("=== CG_LD_Event_01_13_01 (buscar: ja s2, ch s2, base s1) ===")
for b,s,t in [("ja_Anim_zx_CLB",2,"ld_ja"),("ch_Anim_zx_CLB",2,"ld_ch"),("Anim_zx_CLB",1,"ld_base")]:
    acb=mdir/(b+".acb")
    h=decode(acb,s,t); print("  %-18s s%d -> %s" % (b,s,h))

print("=== CG_LDP3R_Event_03_01_26_01 (ja s7, ch s7) ===")
for b,s,t in [("ja_Anim_LD_P3R",7,"p3r_ja"),("ch_Anim_LD_P3R",7,"p3r_ch")]:
    acb=mdir/(b+".acb")
    h=decode(acb,s,t); print("  %-18s s%d -> %s" % (b,s,h))

# also decode wrong subsongs to confirm -s is honored
print("=== control: ch_Anim_LD_P3R s1 vs s7 ===")
for s in (1,7):
    h=decode(mdir/"ch_Anim_LD_P3R.acb",s,"ctl_ch_%d"%s); print("  s%d -> %s"%(s,h))
