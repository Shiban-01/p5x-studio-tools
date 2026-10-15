"""Extrae el rig COMPLETO de Kotone (PC079) con la cadena ya probada, sin optimizar nada.

Contexto: cuando se optimizo el rig para el maniqui, el script bajo de 334 a 252 huesos y por el
camino desaparecio un hueso llamado IK Ring. Ese hueso nunca dejo de estar en los bundles: lo quito
la optimizacion. Asi que esta extraccion va directa, sin poda, y comprueba si vuelve.

Usa la cadena entera: bundles -> mallas y texturas, y Unity en modo lote -> esqueleto y pesos.
"""
from __future__ import annotations

import json
import struct
import sys
import time
from pathlib import Path

sys.path.insert(0, r"C:\Users\Lukas\p5x-datamining\p5x_studio")
from p5x_studio import catalogo, extractor, indice   # noqa: E402

DESTINO = Path(r"C:\Users\Lukas\p5x-datamining\_dl\kotone_rig_completo")
OPCIONES = {"mallas": True, "texturas": True, "materiales": True,
            "esqueleto": True, "previas": True, "fbx": True, "armas": True}


def huesos_del_glb(ruta: Path) -> list[str]:
    """Lee los nombres de hueso de un GLB sin depender de ninguna libreria."""
    d = ruta.read_bytes()
    if d[:4] != b"glTF":
        return []
    n = struct.unpack("<I", d[12:16])[0]
    j = json.loads(d[20:20 + n])
    nombres = [nd.get("name", "") for nd in j.get("nodes", [])]
    return [x for x in nombres if x]


def main() -> None:
    entradas = [a for a in catalogo.personajes() if a["id"].lower().startswith("pc079")]
    if not entradas:
        print("   no encuentro a PC079 en el catalogo")
        return
    p = entradas[0]
    print("   actor: %s   trajes: %s   ficheros: %d" % (p["id"], p.get("trajes"), len(p["ficheros"])))

    datos = indice.cargar_indice(print)
    t0 = time.time()
    carpeta = extractor.extraer_personaje(p, datos, DESTINO, OPCIONES, log=lambda m: print("   ", m))
    print("   extraccion terminada en %.0f s: %s" % (time.time() - t0, carpeta))

    # el hueso que se perdio al optimizar
    print()
    print("   --- buscando el IK Ring ---")
    for glb in Path(carpeta).rglob("*.glb"):
        nombres = huesos_del_glb(glb)
        if not nombres:
            continue
        print("   %s: %d nodos" % (glb.name, len(nombres)))
        interesantes = [n for n in nombres if "ik" in n.lower() or "ring" in n.lower()]
        print("      con IK o Ring en el nombre: %d" % len(interesantes))
        for n in interesantes[:20]:
            print("         %s" % n)
    # y la lista completa, para poder compararla con la del paquete viejo
    for glb in Path(carpeta).rglob("*.glb"):
        nombres = huesos_del_glb(glb)
        if nombres:
            salida = DESTINO / "huesos_completos.txt"
            salida.write_text("\n".join(sorted(nombres)), encoding="utf-8")
            print("   lista de los %d nombres -> %s" % (len(nombres), salida))
            break


if __name__ == "__main__":
    main()