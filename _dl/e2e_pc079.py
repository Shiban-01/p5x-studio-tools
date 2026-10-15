import sys
import time
sys.path.insert(0, r"C:\Users\Lukas\p5x-datamining\p5x_studio")
from p5x_studio import catalogo, extractor

ps = {p["id"]: p for p in catalogo.personajes()}
p = ps["pc079_01"]
opciones = {"mallas": True, "texturas": True, "materiales": True, "esqueleto": True,
            "previas": False, "fbx": False, "armas": True}
t = time.time()
destino = extractor.extraer_personaje(
    p, {}, r"C:\Users\Lukas\p5x-datamining\_dl\p5x_e2e", opciones,
    log=lambda s: print(s, flush=True),
    progreso=lambda v: None,
    estado=lambda s: None)
print("DESTINO:", destino)
print("TIEMPO TOTAL: %.1f s" % (time.time() - t))