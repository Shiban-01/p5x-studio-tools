import sys
sys.path.insert(0, r"C:/Users/Lukas/p5x-datamining/p5x_studio")
from p5x_studio import herramientas as H
from pathlib import Path
media = Path(r"C:/Users/Lukas/Downloads/P5X/Client/OuterPackage/Media/Windows")
dest = Path(r"C:/Users/Lukas/p5x-datamining/_dl/v3")
stem = sys.argv[1]
p = media/(stem+".usm")
print("###", stem, "existe:", p.exists())
infos = H.buscar_audios_video(str(p))
print("  buscar_audios_video -> %d pistas: %s" % (len(infos), [ (i["idioma"] or "efectos", i["banco"], i["subsong"]) for i in infos]))
try:
    out = H.extraer_video(str(p), dest, log=lambda s: print("  LOG:", s))
    print("  ->", out.name, round(out.stat().st_size/1e6,2), "MB")
except Exception as e:
    print("  ERROR:", repr(e))
