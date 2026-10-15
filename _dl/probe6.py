import sys, json
sys.path.insert(0, r"C:/Users/Lukas/p5x-datamining/p5x_studio")
from p5x_studio import herramientas as H
from pathlib import Path
media = Path(r"C:/Users/Lukas/Downloads/P5X/Client/OuterPackage/Media/Windows")
for stem in ("CG_LD_Event_01_13_01","CG_zx_Event_04_31_01_1","CG_zx_Event_05_28_03","CG_LDP3R_Event_03_01_26_01","gacha_first_00_new"):
    p = media/(stem+".usm")
    if not p.exists():
        print(stem, "NO EXISTE"); continue
    infos = H.buscar_audios_video(str(p))
    print("=== %s -> %d pistas" % (stem, len(infos)))
    for i in infos:
        print("   %-6s %-22s s%-2d %8.3fs  %s" % (i["idioma"] or "base", i["banco"], i["subsong"], i["segundos"], i["pista"]))
