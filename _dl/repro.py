import sys, traceback
sys.path.insert(0, r'C:\Users\Lukas\p5x-datamining\p5x_studio')
from p5x_studio import ajustes, indice, extractor, bases

print("idioma:", ajustes.idioma())
datos = indice.cargar_indice()
pjs = indice.personajes(datos)
pid = sys.argv[1] if len(sys.argv) > 1 else "pc069"
cands = [x for x in pjs if x["id"] == pid]
print("candidatos:", [c["id"] for c in cands])
p = cands[0]
print("id:", p["id"], "ficheros:", len(p["ficheros"]))

opciones = {"mallas": True, "texturas": True, "materiales": True, "esqueleto": False,
            "previas": True, "fbx": False, "armas": True, "traje": True, "base": True}
try:
    dest = extractor.extraer_personaje(
        p, datos, ajustes.carpeta_salida(), opciones,
        lambda s: print("LOG", s), base=None, traje=None)
    print("OK ->", dest)
except Exception:
    print("=== TRACEBACK ===")
    traceback.print_exc()
