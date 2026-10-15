import sys, os, traceback, io
sys.path.insert(0, r'C:\Users\Lukas\p5x-datamining\p5x_studio')
from p5x_studio import ajustes, indice, extractor, idiomas

idioma = sys.argv[1] if len(sys.argv) > 1 else "en"
pid = sys.argv[2] if len(sys.argv) > 2 else "pc055"
idiomas.activar(idioma)
print("### IDIOMA ACTIVO:", idiomas.idioma_actual(), "| config:", ajustes.idioma())

datos = indice.cargar_indice()
p = [x for x in indice.personajes(datos) if x["id"] == pid][0]
opciones = {"mallas": True, "texturas": True, "materiales": True, "esqueleto": False,
            "previas": True, "fbx": False, "armas": True, "traje": True, "base": True}
try:
    dest = extractor.extraer_personaje(
        p, datos, ajustes.carpeta_salida(), opciones,
        lambda s: print("  LOG", s), base=None, traje=None)
    print("### OK ->", dest)
except Exception:
    print("### FALLO ###")
    traceback.print_exc()
    sys.exit(1)
