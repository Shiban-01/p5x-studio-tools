import sys
sys.path.insert(0, r"C:/Users/Lukas/p5x-datamining/p5x_studio")
from p5x_studio import herramientas as H
vgm = H._localiza(H._candidatos_vgmstream(), ("-h",))
from pathlib import Path
for b in ("ch_Anim_LD_P3R","ja_Anim_LD_P3R"):
    acb = Path(r"C:/Users/Lukas/Downloads/P5X/Client/OuterPackage/Media/Windows")/(b+".acb")
    base = H._info_vgm(vgm, acb, 1)
    total = int(base.get("streamInfo",{}).get("total",1) or 1)
    print("===", b, "total:", total)
    for s in range(1, total+1):
        d = H._info_vgm(vgm, acb, s)
        si = d.get("streamInfo",{}) if d else {}
        sr = float(d.get("sampleRate",48000) or 48000) if d else 0
        segs = float(d.get("playSamples",0) or 0)/sr if d else 0
        print("  s%02d %6.3fs  %s" % (s, segs, si.get("name","")))
