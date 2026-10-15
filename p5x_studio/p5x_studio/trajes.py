"""Indice de TRAJES: de cada bundle del juego, que es, de que actor, de que traje y que lleva.

Lee `_dl/indice_trajes/trajes.json`, que construye `scripts/indice_trajes.py` leyendo los nombres de
malla de los 16.535 bundles. El nombre de la malla delata el traje:

    <actor>_<traje>[_<modificador>]_<pieza>_wholeexport_rig_<prefijo_textura>_<pieza>

Sin este indice, el catalogo agrupaba por actor y metia en la misma entrada todos sus trajes: pedir
`skull` devolvia a la vez el traje de ladron, el uniforme y hasta un EDIFICIO llamado `skull`.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from .idiomas import t

_CACHE: dict = {}


def _raiz_indice() -> Path:
    """Donde vive el indice de trajes (igual que el de contenido: empaquetado si esta congelado)."""
    if getattr(sys, "frozen", False):
        empaquetado = getattr(sys, "_MEIPASS", None)
        if empaquetado:
            cand = Path(empaquetado) / "_dl/indice_trajes"
            if (cand / "trajes.json").is_file():
                return cand
        return Path(sys.executable).resolve().parent.parent / "_dl/indice_trajes"
    return Path(__file__).resolve().parent.parent.parent / "_dl/indice_trajes"


RAIZ = _raiz_indice()

# como se lee cada traje en castellano (lo que no este aqui se muestra tal cual)
NOMBRES = {
    "normal": "Ropa normal", "thief": "Traje de ladron", "uniform": "Uniforme",
    "uniform_swimsuit": "Banador (base uniforme)", "thief_swimsuit": "Banador (base ladron)",
    "swimsuit": "Banador", "dress": "Vestido", "catbag": "Disfraz de gato",
    "autumn": "Ropa de otono", "office": "Ropa de oficina", "sports": "Ropa deportiva",
    "maidsuit": "Traje de doncella", "binghaofu": "Bata de hospital",
    "wheelchair": "Silla de ruedas", "gamer": "Ropa de gamer", "doctor": "Bata de medico",
    "student": "Uniforme escolar", "velvet": "Terciopelo", "heize": "Ropa negra",
    "weiqun": "Falda", "manwu": "Traje de baile", "chushifu": "Bata de cocina",
    "kokatsu": "Uniforme escolar", "unreal": "Variante unreal", "sp": "Variante SP",
}
# orden de preferencia del traje que sale elegido por defecto
PREFERENCIA = ["normal", "thief", "uniform", "swimsuit"]


def disponible() -> bool:
    # la version publica de herramientas no usa el indice de trajes (ver herramientas._leer_json)
    if os.environ.get("P5X_STUDIO_SIN_INDICES"):
        return False
    return (RAIZ / "trajes.json").is_file()


def datos() -> dict:
    if "d" not in _CACHE:
        try:
            _CACHE["d"] = json.loads((RAIZ / "trajes.json").read_text(encoding="utf-8"))
        except Exception:
            _CACHE["d"] = {"bundles": {}, "actores": {}}
    return _CACHE["d"]


def nombre_traje(clave: str) -> str:
    """Nombre legible de un traje en el idioma activo (`thief` -> `Traje de ladron`)."""
    from .idiomas import t
    clave = clave or ""
    texto = t("tr_" + clave)
    # si no hay traduccion, `t` devuelve la propia clave ("tr_xxx"): se cae al mapa de siempre
    return texto if texto != "tr_" + clave else NOMBRES.get(clave, clave)


def bundle(ruta: str) -> dict:
    """La ficha de un bundle del juego. Acepta la ruta con barra normal o invertida."""
    return datos()["bundles"].get((ruta or "").replace("\\", "/"), {})


def actor_por_id(ident: str) -> dict:
    """La ficha de un actor por su id del catalogo (`pc079_01`, `skull`). Vacia si no esta."""
    for clave, A in datos()["actores"].items():
        if clave.lower() == (ident or "").lower():
            return A
    return {}


def orden_trajes(trajes) -> list:
    """Ordena los trajes para la interfaz: primero los habituales, luego el resto por nombre."""
    def clave(t):
        return (PREFERENCIA.index(t) if t in PREFERENCIA else len(PREFERENCIA), t)
    return sorted(trajes, key=clave)


def ficha(ident: str) -> dict:
    """Los trajes de un actor, listos para el catalogo.

    Devuelve {clave_traje: {clave, nombre, ficheros, piezas, n_mallas, n_texturas, mb}}.
    """
    A = actor_por_id(ident)
    salida = {}
    for clave, T in (A.get("trajes") or {}).items():
        salida[clave] = {
            "clave": clave,
            "nombre": nombre_traje(clave),
            "ficheros": [c.replace("/", "\\") for c in T.get("bundles", [])],
            "ficheros_modelo": [c.replace("/", "\\") for c in T.get("bundles_modelo", [])],
            "piezas": list(T.get("piezas", [])),
            "n_mallas": T.get("n_mallas", 0),
            "n_texturas": len(T.get("texturas", [])),
            "mb": T.get("mb", 0),
        }
    return salida