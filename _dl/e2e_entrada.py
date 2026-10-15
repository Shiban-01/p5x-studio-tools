"""Extrae una entrada del catalogo (escenario, objeto o personaje) fuera de la interfaz.

Uso: python e2e_entrada.py <id_entrada> [carpeta_salida]
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, r"C:/Users/Lukas/p5x-datamining/p5x_studio")
from p5x_studio import ajustes, catalogo, extractor  # noqa: E402


def main():
    ident = sys.argv[1]
    destino = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(r"C:/Users/Lukas/p5x-datamining/_dl/prueba_escenario")
    ent = [e for e in catalogo.personajes() if e["id"] == ident]
    if not ent:
        print("NO EXISTE la entrada", ident)
        sys.exit(1)
    p = ent[0]
    print("ENTRADA:", p["etiqueta"])
    print("  categoria:", p["categoria"], "ficheros:", p["ficheros"])
    opciones = {"mallas": True, "texturas": True, "materiales": True,
                "esqueleto": p["categoria"] == "personaje", "previas": True, "fbx": True}
    t0 = time.time()
    salida = extractor.extraer_personaje(
        p, None, destino, opciones,
        log=lambda s: print("   ", s),
        progreso=lambda v: None,
        estado=lambda s: None)
    print("SALIDA:", salida)
    print("DURACION total: %.1fs" % (time.time() - t0))
    res = json.loads((salida / "SUMMARY.json").read_text(encoding="utf-8"))
    nm = sum(len(v["mallas"]) for v in res["partes"].values())
    nt = sum(len(v["texturas"]) for v in res["partes"].values())
    print("RESUMEN: %d mallas, %d texturas, fbx=%s" % (nm, nt, res.get("fbx")))
    prev = list((salida / "preview").glob("*.png"))
    print("previews:", len(prev), "lamina:", (salida / "preview/lamina_completa.png").is_file())
    mb = sum(f.stat().st_size for f in salida.rglob("*") if f.is_file()) / 1048576
    print("OCUPA: %.1f MB" % mb)


if __name__ == "__main__":
    main()