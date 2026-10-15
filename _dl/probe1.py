import sys, json
sys.path.insert(0, r"C:/Users/Lukas/p5x-datamining/p5x_studio")
from p5x_studio import herramientas as H
p = r"C:/Users/Lukas/Downloads/P5X/Client/OuterPackage/Media/Windows/CG_LDP3R_Event_03_01_26_01.usm"
import os
print("existe:", os.path.exists(p))
print("mapa cues cargado:", bool(H._mapa_cues()))
infos = H.buscar_audios_video(p, log=lambda s: print("LOG:", s))
for i in infos:
    print(json.dumps(i, ensure_ascii=False))
print("TOTAL:", len(infos))
