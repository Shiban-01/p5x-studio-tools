"""Extrae personajes por la MISMA ruta que el boton Extraer de la interfaz (extractor.extraer_personaje).

Uso:  python _dl/run_extraer.py closer pc077_01 n_student
Opcional:  <pid>:<traje>   para forzar un traje (closer:normal).
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, r"C:/Users/Lukas/p5x-datamining/p5x_studio")
from p5x_studio import ajustes, bases, catalogo, extractor  # noqa: E402

opciones = {"mallas": True, "texturas": True, "materiales": True, "esqueleto": True,
            "previas": True, "fbx": True, "armas": True}

entradas = {e["id"].lower(): e for e in catalogo.personajes()}

for arg in sys.argv[1:]:
    pid, _, clave = arg.partition(":")
    pid = pid.lower()
    e = entradas.get(pid)
    if not e:
        print("NO ESTA EN EL CATALOGO:", pid, flush=True)
        continue
    trajes = e.get("trajes") or []
    traje = None
    if trajes:
        if clave:
            traje = next((T for T in trajes if T["clave"] == clave), trajes[0])
        else:
            traje = trajes[0]
    print("=" * 78, flush=True)
    print("EXTRAYENDO %s  traje=%s  (%d ficheros)" % (
        pid, (traje or {}).get("clave"), len((traje or {}).get("ficheros") or e["ficheros"])), flush=True)
    for f in (traje or {}).get("ficheros") or e["ficheros"]:
        print("   bundle", f, flush=True)
    t0 = time.time()
    try:
        base = bases.base_de(pid)
    except Exception:
        base = None
    try:
        destino = extractor.extraer_personaje(
            e, {"_": True}, ajustes.carpeta_salida(), opciones,
            lambda s: print("   " + str(s), flush=True), None, None, base=base, traje=traje)
        print("HECHO %s -> %s  (%.0f s)" % (pid, destino, time.time() - t0), flush=True)
    except Exception as ex:
        import traceback
        traceback.print_exc()
        print("FALLO %s: %s" % (pid, ex), flush=True)