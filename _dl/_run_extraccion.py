"""Lanza una extraccion real desde linea de comandos, igual que hace la interfaz.

Uso:
  python _run_extraccion.py <id> [<carpeta_salida>] [clave=valor ...]

Opciones: base=<id_base>, traje=<clave>, sin_armas=1, sin_fbx=1, sin_previas=1
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, r"C:/Users/Lukas/p5x-datamining/p5x_studio")
from p5x_studio import ajustes, bases, catalogo, extractor  # noqa: E402


def main():
    pid = sys.argv[1]
    salida = Path(sys.argv[2]) if len(sys.argv) > 2 and "=" not in sys.argv[2] \
        else ajustes.carpeta_salida()
    opciones_cli = {}
    for a in sys.argv[2:]:
        if "=" in a:
            k, v = a.split("=", 1)
            opciones_cli[k] = v

    personas = {e["id"].lower(): e for e in catalogo.personajes()}
    e = personas.get(pid.lower())
    if not e:
        print("no encuentro el id %s" % pid)
        print("ids de ejemplo:", [x for x in list(personas)[:15]])
        return 1
    print("entrada:", json.dumps({k: e[k] for k in e if k != "ficheros"}, ensure_ascii=False)[:400])
    print("categoria:", e.get("categoria"), "es_skin:", e.get("es_skin"), "ficheros:", len(e["ficheros"]))

    opciones = {"mallas": True, "texturas": True, "materiales": True, "esqueleto": True,
                "previas": True, "fbx": True, "armas": True}
    if opciones_cli.get("sin_armas"):
        opciones["armas"] = False
    if opciones_cli.get("sin_fbx"):
        opciones["fbx"] = False
    if opciones_cli.get("sin_previas"):
        opciones["previas"] = False
    if opciones_cli.get("sin_esqueleto"):
        opciones["esqueleto"] = False

    base = opciones_cli.get("base")
    if base is None:
        try:
            base = bases.base_de(pid)
        except Exception:
            base = None
    traje = opciones_cli.get("traje")

    t0 = time.time()
    destino = extractor.extraer_personaje(e, {}, salida, opciones,
                                          lambda s: print("  " + s, flush=True),
                                          None, None, base=base, traje=traje)
    print("LISTO %s en %.1fs" % (destino, time.time() - t0))
    return 0


if __name__ == "__main__":
    sys.exit(main())