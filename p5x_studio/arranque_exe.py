"""Punto de entrada del ejecutable congelado de P5X Studio.

A diferencia de `lanzar.pyw`, aqui NO se crea ningun entorno ni se instala nada: UnityPy y Pillow
viajan dentro del propio ejecutable. Se abre la interfaz directamente.

Se usa desde el .spec de PyInstaller. Fuera del ejecutable tambien funciona:

    python arranque_exe.py

Si se define la variable de entorno P5X_STUDIO_DIAGNOSTICO=1, en vez de abrir la ventana escribe un
informe (rutas, si el indice va empaquetado y cuantos actores ve) en `diagnostico_congelado.txt`, al
lado del ejecutable, y termina. Sirve para verificar el empaquetado sin depender de la interfaz.

Con P5X_STUDIO_EXTRAER=<id> extrae ese personaje sin abrir la ventana, con las mismas opciones por
defecto que la interfaz, y escribe el registro por la salida estandar; P5X_STUDIO_DESTINO=<carpeta>
elige donde (por defecto, la carpeta de modelos configurada). Util para extraer en lote y para
comprobar que el ejecutable monta bien el esqueleto.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# sin congelar hace falta que el paquete p5x_studio (que esta al lado) se vea
if not getattr(sys, "frozen", False):
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from p5x_studio import ajustes, catalogo  # noqa: E402


def _diagnostico() -> None:
    """Comprobacion interna del empaquetado: deja por escrito lo que ve el ejecutable."""
    actores = catalogo.personajes()
    lineas = [
        "frozen=%s" % getattr(sys, "frozen", False),
        "executable=%s" % sys.executable,
        "meipass=%s" % getattr(sys, "_MEIPASS", ""),
        "raiz_datos=%s" % ajustes.RAIZ,
        "indice=%s" % catalogo.INDICE,
        "indice_disponible=%s" % catalogo.disponible(),
        "actores=%d" % len(actores),
        "primero=%s" % (actores[0]["etiqueta"] if actores else ""),
    ]
    (ajustes.RAIZ / "diagnostico_congelado.txt").write_text("\n".join(lineas) + "\n",
                                                            encoding="utf-8")


def _extraer_sin_ventana(pid: str) -> int:
    """Extrae un personaje con el mismo camino que la interfaz, pero sin abrir ventana."""
    from p5x_studio import bases, extractor

    personas = {e["id"].lower(): e for e in catalogo.personajes()}
    p = personas.get(pid.lower())
    if not p:
        print("no encuentro el id %s" % pid)
        return 1
    opciones = {"mallas": True, "texturas": True, "materiales": True, "esqueleto": True,
                "previas": True, "fbx": True, "armas": True}
    if p.get("categoria", "personaje") != "personaje":
        opciones["esqueleto"] = False
    base = None
    try:
        base = bases.base_de(p["id"])
    except Exception:
        base = None
    traje = None
    lista_trajes = p.get("trajes") or []
    if lista_trajes:
        traje = lista_trajes[0]
    destino = Path(os.environ.get("P5X_STUDIO_DESTINO") or ajustes.carpeta_salida())
    # la ventana del ejecutable no tiene consola: el registro se puede volcar a un fichero
    registro = os.environ.get("P5X_STUDIO_LOG")
    lineas = []

    def anota(s):
        lineas.append(s)
        if registro:
            Path(registro).write_text("\n".join(lineas) + "\n", encoding="utf-8")
        else:
            print("  " + s, flush=True)

    salida = extractor.extraer_personaje(
        p, {}, destino, opciones, anota, None, None, base=base, traje=traje)
    print("LISTO %s" % salida)
    return 0


if __name__ == "__main__":
    if getattr(sys, "frozen", False):
        if os.environ.get("P5X_STUDIO_DIAGNOSTICO"):
            _diagnostico()
            raise SystemExit(0)
        if os.environ.get("P5X_STUDIO_EXTRAER"):
            raise SystemExit(_extraer_sin_ventana(os.environ["P5X_STUDIO_EXTRAER"]))

    from p5x_studio.gui import arrancar
    arrancar()