"""Modelo base de una skin: declarar de que personaje hereda la cara, los ojos y el pelo.

Por que existe este modulo
--------------------------
Media docena de los personajes del catalogo son SKINS: el juego solo trae su cuerpo y su ropa, no su
cara. La cara vive en un MODELO BASE distinto, que son otros bundles y, ademas, el juego no guarda
en ningun sitio la relacion skin -> base. El nombre del fichero tampoco lo dice: la skin `pc077_01`
se apoya en `n_GuitarGirl`, que aparece en `part_l_normal` y en los bundles `shared_*` con texturas
`chord_normal_*`.

Como el vinculo no esta en los datos, la herramienta deja DECLARARLO y lo guarda en `config.json`,
asociado al personaje. Con la declaracion hecha, el extractor sabe que bundles mirar para traer la
cara, los ojos, los parpados y el pelo del base.

Ademas, este modulo intenta PROPONER el base cuando los propios datos dejan una pista: los bundles
de la skin suelen llevar mallas `bs_<base>_replaced` con el nombre del base dentro (en PC077 aparece
`bs_guitar_chord_replaced`, que delata al personaje interno `chord`). Si la pista no es concluyente,
la herramienta pide que se declare a mano en vez de adivinar.

Todo lo que necesita saber de bundles lo saca del indice de assets (`_dl/indice_assets/assets.json`),
que anota, para cada uno de los 16.535 bundles, que recursos lleva y que personajes aparecen.
"""
from __future__ import annotations

import difflib
import json
import re
import sys
from pathlib import Path

from . import ajustes, catalogo
from .idiomas import t

# que piezas del base se traen al extraer una skin: la cara, los ojos (incluye parpados) y el pelo
PIEZAS_BASE = ("face", "eyes", "hair")
# el catalogo nombra las piezas en castellano; las carpetas y los ficheros, en ingles
PIEZA_CATALOGO = {"face": "cara", "eyes": "ojos", "hair": "pelo"}
NOMBRES_PIEZA = {"face": "Cara", "eyes": "Ojos", "hair": "Pelo"}

# tipos de bundle que pueden llevar geometria o texturas de un personaje. Los timelines, escenarios,
# efectos e interfaz se descartan: arrastrarian miles de recursos de otros personajes.
TIPOS_MODELO = ("part", "shared")

# ids que salen de nombres de malla y no son personajes; nunca se proponen como base
GENERICOS = set(catalogo.NO_ES_GENTE) | {
    "bs", "matcap", "obj", "other", "wholeexport", "normal", "thief", "body02",
    "eyel", "yanpi", "eyeild", "eye l", "eye r", "hair01", "head",
}


def _menciona(nombre: str, ident: str) -> bool:
    """Si el id aparece en el nombre como palabra completa (`chord` en `bs_guitar_chord_replaced`).

    Se exige frontera: si no, `eyel` (un actor basura que sale de un hueso) casaria dentro de
    `eyelid` y se propondria como base de cualquier personaje con parpados.
    """
    return re.search(r"(?<![A-Za-z0-9])" + re.escape(ident) + r"(?![A-Za-z0-9])", nombre) is not None


# --------------------------------------------------------------------------- rutas e indices
def _raiz_datos() -> Path:
    """La carpeta `_dl` del proyecto, con los indices. Dentro del .exe va empaquetada."""
    if getattr(sys, "frozen", False):
        empaquetado = getattr(sys, "_MEIPASS", None)
        if empaquetado:
            cand = Path(empaquetado) / "_dl"
            if (cand / "indice_assets/assets.json").is_file():
                return cand
        return Path(sys.executable).resolve().parent.parent / "_dl"
    return Path(__file__).resolve().parent.parent.parent / "_dl"


_CACHE_ASSETS: dict | None = None
_CACHE_TIPOS: dict | None = None
_CACHE_CATALOGO: list[dict] | None = None
_CACHE_BUSQUEDA: list[tuple[str, str, bool]] | None = None


def _assets() -> dict:
    global _CACHE_ASSETS
    if _CACHE_ASSETS is None:
        ruta = _raiz_datos() / "indice_assets/assets.json"
        try:
            _CACHE_ASSETS = json.loads(ruta.read_text(encoding="utf-8"))
        except Exception:
            _CACHE_ASSETS = {}
    return _CACHE_ASSETS


def _tipos_fichero() -> dict[str, str]:
    """Mapa `carpeta/fichero` -> tipo de bundle (part, shared, tl...).

    El tipo se saca del propio nombre del fichero (`part_...`, `shared_...`), no del indice de
    ficheros: alli los `shared_<hash>` salen como `?` porque el nombre no lleva texto entre el tipo
    y el hash, y quedarian fuera bundles con las texturas que mas falta hacen.
    """
    global _CACHE_TIPOS
    if _CACHE_TIPOS is None:
        _CACHE_TIPOS = {}
        for clave in _assets():
            _CACHE_TIPOS[clave] = Path(clave).name.split("_", 1)[0].lower()
    return _CACHE_TIPOS


def _catalogo_personajes(forzar: bool = False) -> list[dict]:
    global _CACHE_CATALOGO
    if _CACHE_CATALOGO is None or forzar:
        try:
            _CACHE_CATALOGO = catalogo.personajes()
        except Exception:
            _CACHE_CATALOGO = []
    return _CACHE_CATALOGO


def indice_disponible() -> bool:
    """Si estan los indices que hacen falta para buscar y proponer un base."""
    return bool(_assets()) and bool(_catalogo_personajes())


def entrada(ident: str) -> dict | None:
    """La entrada del catalogo de un personaje, por id."""
    return _entradas().get((ident or "").lower())


_CACHE_ENTRADAS: dict[str, dict] | None = None


def _entradas() -> dict[str, dict]:
    global _CACHE_ENTRADAS
    if _CACHE_ENTRADAS is None:
        _CACHE_ENTRADAS = {a["id"]: a for a in _catalogo_personajes()}
    return _CACHE_ENTRADAS


# --------------------------------------------------------------------------- declaraciones
def _clave_config() -> str:
    return "modelos_base"


def declaraciones() -> dict[str, dict]:
    """Todas las relaciones skin -> base declaradas, tal cual estan en `config.json`."""
    datos = ajustes._leer_config().get(_clave_config()) or {}
    return {k: v for k, v in datos.items() if isinstance(v, dict) and v.get("base")}


def declarar(skin_id: str, base_id: str, nota: str = "", origen: str = "usuario") -> dict:
    """Declara que `skin_id` es una skin de `base_id`. Se guarda en la configuracion."""
    skin_id = (skin_id or "").lower().strip()
    base_id = (base_id or "").lower().strip()
    if not skin_id or not base_id:
        raise ValueError(t("base_err_faltan"))
    if skin_id == base_id:
        raise ValueError(t("base_err_propio"))
    decl = declaraciones()
    b = entrada(base_id)
    decl[skin_id] = {
        "base": base_id,
        "nombre": (b or {}).get("nombre") or base_id,
        "nota": nota or "",
        "origen": origen,
    }
    ajustes.guardar_config(**{_clave_config(): decl})
    return decl[skin_id]


def quitar(skin_id: str) -> bool:
    """Borra la declaracion de un personaje. Devuelve si habia algo que borrar."""
    skin_id = (skin_id or "").lower().strip()
    decl = declaraciones()
    if skin_id not in decl:
        return False
    del decl[skin_id]
    ajustes.guardar_config(**{_clave_config(): decl})
    return True


def base_de(skin_id: str) -> str | None:
    """El id del modelo base declarado para un personaje, o None."""
    d = declaraciones().get((skin_id or "").lower().strip())
    return d.get("base") if d else None


# --------------------------------------------------------------------------- bundles de un actor
def _quien(bundle: str) -> list[str]:
    return [str(x).lower() for x in (_assets().get(bundle) or {}).get("quien", [])]


def bundles_de_actor(ident: str, tipos=TIPOS_MODELO, con_datos: bool = True) -> list[str]:
    """Bundles donde aparece un actor, con ruta relativa a `Bundles/Windows`.

    Se queda solo con los tipos que llevan modelo o texturas (part, shared), para no arrastrar
    timelines ni atlas de interfaz. Si `con_datos`, exige que el bundle traiga malla o textura.
    """
    ident = (ident or "").lower()
    tipos = tuple(tipos)
    tipos_fichero = _tipos_fichero()
    salida = []
    for clave, v in _assets().items():
        if tipos_fichero.get(clave) not in tipos:
            continue
        if con_datos and not ({"Mesh", "Texture2D"} & set(v.get("tiene") or [])):
            continue
        if ident in _quien(clave):
            salida.append(clave.replace("/", "\\"))
    return sorted(salida)


def grupo(ident: str, limite: int = 12) -> list[str]:
    """El actor y sus alias: el mismo personaje con dos nombres en el juego.

    `n_GuitarGirl` y `chord` son la misma chica; no hay ningun campo que lo diga, pero si comparten
    un bundle (`180/part_itargirl...`, que lleva mallas de n_GuitarGirl y texturas `chord_normal_*`)
    o el nombre de una malla. Eso basta para unirlos y no dejar fuera ni una textura.
    """
    ident = (ident or "").lower()
    if not ident:
        return []
    conocidos = {a["id"] for a in _catalogo_personajes()}
    ids = {ident}
    for _ in range(4):
        nuevos = set()
        for clave in list(_assets()):
            if _tipos_fichero().get(clave) not in TIPOS_MODELO:
                continue
            quien = set(_quien(clave))
            if quien & ids:
                for otro in quien:
                    if otro in conocidos and otro not in ids and len(otro) >= 4:
                        nuevos.add(otro)
        if not nuevos:
            break
        ids |= nuevos
        if len(ids) >= limite:
            break
    return sorted(ids)


def info_base(base_id: str) -> dict:
    """Todo lo que hay que saber del base para extraerlo: su grupo, sus bundles y sus piezas."""
    base_id = (base_id or "").lower()
    grupo_ids = grupo(base_id) or [base_id]
    bundles: list[str] = []
    for gid in grupo_ids:
        for b in bundles_de_actor(gid):
            if b not in bundles:
                bundles.append(b)
    entradas = [entrada(g) for g in grupo_ids]
    entradas = [e for e in entradas if e]
    piezas = sorted({p for e in entradas for p in e.get("piezas") or []})
    return {
        "id": base_id,
        "nombre": (entrada(base_id) or {}).get("nombre") or base_id,
        "grupo": grupo_ids,
        "entradas": entradas,
        "bundles": bundles,
        "piezas": piezas,
        "trae": [p for p in PIEZAS_BASE if PIEZA_CATALOGO[p] in piezas],
    }


# --------------------------------------------------------------------------- buscar candidatos
def _blob_actor(a: dict) -> str:
    """Texto sobre el que se busca un actor: su id, su etiqueta, sus bundles y nombres de recurso."""
    partes = [a["id"], a.get("nombre") or "", a.get("etiqueta") or ""]
    for f in a.get("ficheros") or []:
        partes.append(Path(f).name)
    assets = _assets()
    for f in a.get("ficheros") or []:
        clave = f.replace("\\", "/")
        muestra = (assets.get(clave) or {}).get("muestra") or {}
        for nombres in muestra.values():
            partes.extend(str(n) for n in (nombres or [])[:40])
    return " ".join(partes).lower()


def _indice_busqueda() -> list[tuple[str, str, bool]]:
    global _CACHE_BUSQUEDA
    if _CACHE_BUSQUEDA is None:
        _CACHE_BUSQUEDA = []
        for a in _catalogo_personajes():
            tiene_cara = "cara" in (a.get("piezas") or [])
            _CACHE_BUSQUEDA.append((a["id"], _blob_actor(a), tiene_cara))
    return _CACHE_BUSQUEDA


def _puntua(consulta: str, blob: str, ident: str) -> float:
    """Puntuacion difusa: subcadena directa vale mas; si no, parecido de palabras (tolera erratas)."""
    if consulta in ident:
        return 100.0 + len(consulta)
    if consulta in blob:
        return 60.0 + len(consulta)
    mejor = 0.0
    for palabra in list(set(blob.split()))[:600]:
        if abs(len(palabra) - len(consulta)) > 4:
            continue
        r = difflib.SequenceMatcher(None, consulta, palabra).ratio()
        if r > mejor:
            mejor = r
    return mejor * 30.0 if mejor > 0.72 else 0.0


def buscar(texto: str, limite: int = 25, solo_con_cara: bool = False) -> list[dict]:
    """Buscador difuso de personajes sobre el catalogo y los nombres de bundle/recurso.

    Permite elegir un modelo base escribiendo un trozo del nombre (`chord`, `guitar`, `kotone`)
    aunque no se sepa el id exacto.
    """
    consulta = (texto or "").strip().lower()
    if len(consulta) < 2:
        return []
    salida = []
    for ident, blob, tiene_cara in _indice_busqueda():
        if solo_con_cara and not tiene_cara:
            continue
        punto = _puntua(consulta, blob, ident)
        if punto <= 0:
            continue
        a = entrada(ident) or {}
        # los restos de escenario (obj, huesos, props) entran al catalogo pero no son un base util:
        # solo se dejan pasar cuando la busqueda coincide con su id mismo.
        if a.get("categoria") != "personaje" and punto < 100:
            continue
        salida.append({
            "id": ident,
            "etiqueta": a.get("etiqueta") or ident,
            "nombre": a.get("nombre") or ident,
            "tiene_cara": tiene_cara,
            "es_skin": bool(a.get("es_skin")),
            "ficheros": len(a.get("ficheros") or []),
            "puntuacion": round(punto, 1),
        })
    salida.sort(key=lambda x: (-x["puntuacion"], x["id"]))
    return salida[:limite]


def _personajes_con_cara() -> list[dict]:
    return [a for a in _catalogo_personajes() if "cara" in (a.get("piezas") or [])]


def sugerencias(skin_id: str, limite: int = 6) -> list[dict]:
    """Propone modelos base para una skin, si los datos dejan una pista clara.

    La pista real: los bundles de la skin llevan mallas `bs_<base>_replaced` o comparten bundle con
    el base. En PC077 aparece `bs_guitar_chord_replaced`, que senala al personaje interno `chord`
    (el mismo que `n_GuitarGirl`). Sin pista, la lista sale vacia y hay que declararlo a mano.
    """
    skin_id = (skin_id or "").lower().strip()
    skin = entrada(skin_id)
    if not skin:
        return []
    # nombres de todo lo que llevan los bundles de la skin (bundles + recursos por tipo)
    bundles = set(skin.get("ficheros") or [])
    bundles |= set(b.lower() for b in bundles_de_actor(skin_id))
    assets = _assets()
    blob = []
    for f in bundles:
        clave = f.replace("\\", "/")
        blob.append(Path(clave).name.lower())
        muestra = (assets.get(clave) or {}).get("muestra") or {}
        for nombres in muestra.values():
            blob.extend(str(n).lower() for n in (nombres or []))
    blob_txt = " ".join(blob)

    puntuaciones: dict[str, dict] = {}
    for a in _personajes_con_cara():
        ident = a["id"]
        if ident == skin_id or ident in GENERICOS or len(ident) < 4:
            continue
        if ident.isdigit():
            continue
        # que el id del actor aparezca como palabra completa dentro de los nombres de la skin
        donde = [n for n in blob if _menciona(n, ident)]
        if not donde:
            continue
        g = grupo(ident)
        puntuaciones[ident] = {
            "id": ident,
            "nombre": a.get("nombre") or ident,
            "grupo": g,
            "puntuacion": len(donde),
            "motivo": t("base_motivo", ", ".join(sorted({d for d in donde})[:3])),
            "tiene_cara": True,
        }
    ordenados = sorted(puntuaciones.values(), key=lambda x: (-x["puntuacion"], x["id"]))
    return ordenados[:limite]


def proponer(skin_id: str) -> dict | None:
    """El base mas probable para una skin, si hay uno solo claro. Si hay varios o ninguno, None."""
    cand = sugerencias(skin_id)
    if not cand:
        return None
    if len(cand) == 1:
        return cand[0]
    # claro solo si el primero destaca sobre el segundo
    if cand[0]["puntuacion"] >= 2 and cand[0]["puntuacion"] > cand[1]["puntuacion"]:
        return cand[0]
    return None


def resumen() -> dict:
    """Cuentas para la interfaz."""
    decl = declaraciones()
    skins = [a for a in _catalogo_personajes() if a.get("es_skin")]
    return {
        "con_cara": len(_personajes_con_cara()),
        "skins": len(skins),
        "declaradas": len(decl),
        "declaraciones": decl,
    }


if __name__ == "__main__":  # pequena utilidad de linea de ordenes, sin interfaz
    import argparse
    ap = argparse.ArgumentParser(description="Modelos base de las skins (P5X Studio)")
    sub = ap.add_subparsers(dest="orden", required=True)
    p_ver = sub.add_parser("listar")
    p_bus = sub.add_parser("buscar"); p_bus.add_argument("texto")
    p_sug = sub.add_parser("sugerir"); p_sug.add_argument("skin")
    p_dec = sub.add_parser("declarar"); p_dec.add_argument("skin"); p_dec.add_argument("base")
    p_dec.add_argument("--nota", default="")
    p_qui = sub.add_parser("quitar"); p_qui.add_argument("skin")
    p_info = sub.add_parser("info"); p_info.add_argument("base")
    args = ap.parse_args()
    if args.orden == "listar":
        for skin, d in sorted(declaraciones().items()):
            print("  %-14s -> %-16s (%s)" % (skin, d.get("base"), d.get("origen", "")))
    elif args.orden == "buscar":
        for c in buscar(args.texto):
            print("  %-16s %-34s cara=%s punt=%s" % (c["id"], c["etiqueta"][:34],
                                                     c["tiene_cara"], c["puntuacion"]))
    elif args.orden == "sugerir":
        for c in sugerencias(args.skin):
            print("  %-16s (grupo %s) punt=%s  %s" % (c["id"], ",".join(c["grupo"]),
                                                      c["puntuacion"], c["motivo"]))
    elif args.orden == "declarar":
        print(declarar(args.skin, args.base, args.nota))
    elif args.orden == "quitar":
        print("quitado" if quitar(args.skin) else "no habia nada")
    elif args.orden == "info":
        print(json.dumps(info_base(args.base), ensure_ascii=False, indent=1))