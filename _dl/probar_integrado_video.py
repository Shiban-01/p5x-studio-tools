# -*- coding: utf-8 -*-
"""Prueba la integracion real: importa herramientas de la app y usa extraer_video."""
import sys, os, json
sys.path.insert(0, r"C:/Users/Lukas/p5x-datamining/p5x_studio")
from p5x_studio import herramientas as H

MEDIA = r"C:/Users/Lukas/Downloads/P5X/Client/OuterPackage/Media/Windows"
DEST = r"C:/Users/Lukas/p5x-datamining/_dl/integrado"
os.makedirs(DEST, exist_ok=True)

print("estado_herramientas:", H.estado_herramientas())
print("cueinfo:", H._ruta_cueinfo())
print("mapa cues:", len(H._mapa_cues()))

for stem in ["CG_wonder_swimsuit", "PC068_transition", "CG_zx_Event_05_28_03",
             "Activity_2025zhounian_1", "1_jinru"]:
    usm = os.path.join(MEDIA, stem + ".usm")
    print("\n=== %s ===" % stem)
    info = H.buscar_audio_video(usm, lambda s: print("   [log]", s))
    print("   buscar_audio_video ->", info)
    try:
        out = H.extraer_video(usm, DEST, lambda s: print("   [log]", s))
        print("   MP4:", out, "%.2f MB" % (out.stat().st_size / 1e6))
    except Exception as e:
        print("   ERROR:", e)