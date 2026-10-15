"""Catalogo del juego: todos los actores que se pueden extraer, no solo los que adivina el nombre.

El indice de bundles solo conoce los ficheros cuyo NOMBRE lleva el codigo del personaje (`pc079_`,
`n040_`). Eso deja fuera a la mayoria: el modelo de `fengbandadi` vive en `part_n_normal`, y el de
la skin `pc077` se apoya en `n_GuitarGirl`, que esta en `part_l_normal`. Nada de eso se ve por el
nombre.

Este modulo usa el indice de CONTENIDO (`_dl/indice_juego/`), que se construyo abriendo los 906
bundles de modelo uno a uno y anotando que mallas lleva cada uno. Con eso el catalogo sabe:

  - que actores existen de verdad (151),
  - en que bundles vive cada uno,
  - que piezas trae (cara, ojos, pelo, cuerpo, armas...),
  - y cuales son SKINS sin cara propia, para poder decirlo en vez de entregar un cuerpo sin cabeza.

Devuelve las mismas entradas que `indice.personajes()`, para que el extractor las acepte sin cambios.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from . import trajes
from .idiomas import t


def _raiz_indice() -> Path:
    """Donde vive el indice de contenido del juego.

    Sin congelar, el modulo esta en p5x-datamining/p5x_studio/p5x_studio/, asi que la raiz del
    proyecto queda tres niveles mas arriba. Congelado, __file__ apunta a una carpeta temporal, asi
    que el indice va EMPAQUETADO dentro del ejecutable (sys._MEIPASS); si por lo que sea no estuviera
    ahi, se busca junto al .exe.
    """
    if getattr(sys, "frozen", False):
        empaquetado = getattr(sys, "_MEIPASS", None)
        if empaquetado:
            cand = Path(empaquetado) / "_dl/indice_juego"
            if (cand / "indice_contenido.json").is_file():
                return cand
        return Path(sys.executable).resolve().parent.parent / "_dl/indice_juego"
    return Path(__file__).resolve().parent.parent.parent / "_dl/indice_juego"


RAIZ = _raiz_indice().parent.parent
INDICE = _raiz_indice()

# Los actores que no son personajes jugables: multitudes, props y restos
NO_PERSONAJE = ("roletiny", "port_rig", "tmpfont", "spinetest")

# Palabras que salen de nombres de malla y NO son personajes. Al abrir los escenarios y los
# timelines, sus props entran al catalogo con nombres como `Obj`, `Part` o `camera`, y hay que
# separarlos o la lista de personajes se llena de sillas y camaras.
NO_ES_GENTE = {
    "bs", "ps", "n", "m", "f", "s", "sd", "pac", "part", "obj", "object", "body", "camera",
    "cam", "scn", "scene", "mod", "prop", "map", "stage", "eff", "efx", "fx", "ui", "tex",
    "weapon", "gun", "bg", "col", "light", "lod", "mat", "mesh", "actor", "null", "none",
    # partes del cuerpo y huesos: salen de nombres de malla como `eye`, `hair` o `b_l_hiza01`
    "eye", "eyeild", "hair", "face", "head", "hand", "foot", "arm", "leg", "spine", "neck",
    "b", "l", "r", "b l", "b r", "hiza", "hiji", "kata", "mune", "mainstory", "story",
    "event", "fan", "common", "default", "test", "temp", "dummy", "empty", "new",
}


def _leer(nombre: str) -> dict:
    ruta = INDICE / nombre
    if not ruta.is_file():
        return {}
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except Exception:
        return {}


def disponible() -> bool:
    """Si el indice del juego esta construido. Si no, la app usa el indice de bundles de siempre."""
    return (INDICE / "indice_contenido.json").is_file() and (INDICE / "actores.json").is_file()


def personajes() -> list[dict]:
    """Todos los actores extraibles, en el mismo formato que `indice.personajes()`."""
    contenido = _leer("indice_contenido.json")
    ficheros = _leer("indice_ficheros.json").get("ficheros", [])
    if not contenido:
        return []

    # que bundle lleva a cada actor, segun su contenido real
    por_actor: dict[str, dict] = {}
    for clave, v in contenido.items():
        for quien in v.get("contiene") or []:
            e = por_actor.setdefault(quien.lower(), {"id": quien.lower(), "ficheros": set(),
                                                     "piezas": set(), "etiqueta": quien})
            e["ficheros"].add(clave.replace("/", "\\"))
            e["piezas"] |= set(v.get("piezas") or [])

    # Y ademas, los bundles cuyo nombre EMPIEZA por el codigo del actor. El emparejamiento tiene
    # que ir anclado al principio: buscar la clave en cualquier posicion hacia que el actor `n`
    # (que sale de mallas como `n_04_1_1_...`) se llevara 5.000 bundles por contener una letra n.
    for f in ficheros:
        nombre = (f.get("nombre") or "").lower()
        for clave in list(por_actor):
            if len(clave) < 3:
                continue
            if nombre == clave or nombre.startswith(clave):
                por_actor[clave]["ficheros"].add("%s\\%s" % (f["carpeta"], f["fichero"]))

    salida = []
    for e in por_actor.values():
        e["categoria"] = clasificar(e["id"], e["piezas"])
        # los codigos de una o dos letras salen de mallas con nombres raros (`n_04_1_1`) y no son
        # personajes: son piezas de escenario o restos
        if len(e["id"]) < 3:
            continue
        piezas = sorted(e["piezas"])
        es_skin = "cara" not in piezas and "cuerpo" in piezas
        etiqueta = e["etiqueta"]
        if es_skin:
            etiqueta += t("ct_skin")
        salida.append({
            "id": e["id"],
            "nombre": e["etiqueta"],
            "ficheros": sorted(e["ficheros"]),
            "tipos": sorted({Path(f).name.split("_", 1)[0] for f in e["ficheros"]}),
            "etiqueta": etiqueta,
            "piezas": piezas,
            "es_skin": es_skin,
            "categoria": e["categoria"],
        })
    salida.sort(key=lambda x: (-len(x["ficheros"]), x["id"]))
    salida = _con_trajes(salida)
    salida.extend(_entradas_del_indice({e["id"] for e in salida}))
    # Los bundles `role_*` que SON el rig del actor pero NO llevan su nombre en el fichero
    # (`role__uniform5f23c883.bundle` para `closer`): sin ellos no hay jerarquia de huesos. Se
    # enganchan antes de apartar props, porque el indice de trajes los marca `escenario` y si no
    # se perderian. Lo mismo con los bundles `shared_*`/`shared_merged_*` de los otros trajes del
    # actor: traen sus texturas (el pelo de `closer` vive en `192/shared_merged_9c38bc5`).
    _unir_rigs(salida)
    _unir_texturas(salida)
    salida = [e for e in salida if not _es_artefacto(e)]
    _apartar_props(salida)
    reclamados = {f for e in salida for f in e["ficheros"]}
    salida.extend(_entradas_del_juego(reclamados))
    salida.sort(key=lambda x: (-len(x["ficheros"]), x["id"]))
    return salida


def _apartar_props(entradas: list[dict]) -> None:
    """Saca de los actores los bundles que NO son suyos: props de escena y escenarios/efectos.

    El emparejamiento por prefijo de nombre metia dentro de un actor cosas que no le pertenecen:
    props de escena (`role_` con papel `escenario`: un `highlight`, un `sword`, una caja), escenarios
    (`scn_`) y efectos (`efx_`). Los tres ya se anaden como entradas propias, asi que aqui se apartan
    a `ficheros_otros` para que no se extraigan junto al personaje.
    """
    if not trajes.disponible():
        return
    bundles = trajes.datos().get("bundles") or {}
    for e in entradas:
        if e.get("categoria") == "efecto":
            continue
        ajenos = [f for f in e["ficheros"] if _no_es_del_actor(f, bundles, e.get("_rigs"))]
        if not ajenos:
            continue
        fuera = set(ajenos)
        e["ficheros"] = [f for f in e["ficheros"] if f not in fuera]
        e.setdefault("ficheros_otros", [])
        e["ficheros_otros"] = sorted(set(e["ficheros_otros"]) | fuera)
        if e.get("trajes"):
            e["trajes"] = [{**T, "ficheros": [f for f in T.get("ficheros", []) if f not in fuera]}
                           for T in e["trajes"]]


def _no_es_del_actor(fichero: str, bundles: dict, rigs: set | None = None) -> bool:
    """Si un bundle no puede ser el modelo de un actor: escenario, efecto o prop de escena.

    Ojo con el papel `escenario`: el indice de trajes se lo pone a CUALQUIER `role_` cuyas mallas no
    sean de personaje, y ahi caen los rigs de actores cuyo prefab solo trae huesos y props
    (`role__uniform` = el rig de `closer`). Por eso se exime a los bundles que el catalogo ya ha
    reconocido como rig del actor (`rigs`).
    """
    if rigs and fichero in rigs:
        return False
    nombre = Path(fichero).name.lower()
    if nombre.startswith(("scn_", "efx_")):
        return True
    return (bundles.get(fichero.replace("\\", "/")) or {}).get("papel") == "escenario"


# --------------------------------------------------------------------------- rigs y texturas sueltas
#
# Dos cosas que el indice de trajes NO puede deducir del nombre y que hay que ir a buscar al indice
# de assets (`_dl/indice_assets/assets.json`, que SI lleva los nombres de los recursos de dentro):
#
#   1. el RIG del actor. El juego no siempre llama `role_<actor>` al prefab: `closer` tiene su rig en
#      `role__uniform5f23c883.bundle` (el token del actor va VACIO) y solo el nombre de su Animator
#      (`closer_uniform`) lo delata. Sin ese bundle no hay jerarquia de huesos y el GLB sale sin
#      esqueleto.
#   2. las TEXTURAS de un traje. El bundle del modelo trae las mallas pero no siempre sus PNG: el
#      pelo de `closer` esta en `192/shared_merged_9c38bc5.bundle`, que el indice asigna al traje
#      `uniform` y no al `normal` que se extrae. Como los `shared_*` no traen mallas de prenda, se
#      pueden sumar a todos los trajes del actor sin meter geometria ajena.

_CACHE_RIGS: dict | None = None


def _assets() -> dict:
    """El indice de assets (bundle -> recursos que lleva). Vacio si no esta."""
    ruta = RAIZ / "_dl/indice_assets/assets.json"
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _rigs_del_indice() -> dict:
    """Mapa `nombre de animator/gameobject` -> [bundles `role_*`] que lo montan.

    Solo se leen los bundles `role_` y, de cada uno, los nombres de sus Animator y GameObject: es el
    nombre del prefab (el del actor con su traje) el que dice a quien pertenece el rig.
    """
    global _CACHE_RIGS
    if _CACHE_RIGS is not None:
        return _CACHE_RIGS
    mapa: dict[str, list[str]] = {}
    for clave, v in _assets().items():
        if not Path(clave).name.lower().startswith("role_"):
            continue
        muestra = (v or {}).get("muestra") or {}
        nombres = list(muestra.get("Animator") or []) + list(muestra.get("GameObject") or [])
        for n in nombres:
            n = (n or "").lower()
            if len(n) < 3:
                continue
            mapa.setdefault(n, []).append(clave.replace("/", "\\"))
    _CACHE_RIGS = mapa
    return mapa


def rigs_de(ident: str, claves_traje=None) -> list[str]:
    """Los bundles `role_*` que son el rig del actor, aunque no lleven su nombre en el fichero.

    Se casa el nombre del prefab (Animator/GameObject) con el id del actor: `closer_uniform` es de
    `closer`. Si se conocen los trajes del actor (`claves_traje`), el trozo que sigue al actor tiene
    que ser uno de ellos: asi `closer_uniform`, `closer_thief` y `closer_thief_swimsuit` entran (son
    su rig) y `closer_ergate` / `closer_dollant` (props del actor, no su esqueleto) se quedan fuera.
    """
    bajo = (ident or "").lower()
    if len(bajo) < 3:
        return []
    claves = {c.lower() for c in (claves_traje or ())}
    salida = set()
    for nombre, bundles in _rigs_del_indice().items():
        if nombre == bajo:
            salida |= set(bundles)
            continue
        if not nombre.startswith(bajo + "_"):
            continue
        if claves:
            resto = nombre[len(bajo) + 1:]
            toks = [t for t in resto.split("_") if t]
            # `closer_thief_swimsuit` -> el traje es la union de los dos primeros trozos
            if resto in claves or (toks and "_".join(toks[:2]) in claves) or (toks and toks[0] in claves):
                salida |= set(bundles)
        else:
            salida |= set(bundles)
    return sorted(salida)


def _unir_rigs(entradas: list[dict]) -> None:
    """Mete el rig de cada actor en su entrada y en TODOS sus trajes."""
    for e in entradas:
        if e.get("categoria") not in (None, "personaje"):
            continue
        claves = [T.get("clave") for T in (e.get("trajes") or [])]
        propios = rigs_de(e["id"], claves)
        if not propios:
            propios = rigs_de(e["id"])
        if not propios:
            continue
        e["_rigs"] = set(propios)
        e["ficheros"] = sorted(set(e["ficheros"]) | set(propios))
        for T in e.get("trajes") or []:
            T["ficheros"] = sorted(set(T.get("ficheros") or []) | set(propios))
        if e.get("ficheros_otros"):
            e["ficheros_otros"] = [f for f in e["ficheros_otros"] if f not in e["_rigs"]]


def _unir_texturas(entradas: list[dict]) -> None:
    """Suma a cada traje los bundles SIN malla de prenda que el actor tiene en sus otros trajes.

    Un `shared_*` solo lleva texturas (y a veces mallas de hueso, que no son prenda). El indice de
    trajes los reparte por traje, asi que al extraer `closer_normal` se quedaba sin las texturas del
    pelo porque viven en el `shared_merged` del traje `uniform`. Se suman a todos los trajes del
    actor: como el enlace textura-malla es por prefijo de rig, no ensucian nada.
    """
    if not trajes.disponible():
        return
    bundles = trajes.datos().get("bundles") or {}
    for e in entradas:
        if e.get("categoria") not in (None, "personaje"):
            continue
        comunes = set()
        for T in e.get("trajes") or []:
            for f in T.get("ficheros") or []:
                b = bundles.get(f.replace("\\", "/")) or {}
                if any("_wholeexport" in (m or "").lower() for m in (b.get("mallas") or [])):
                    continue
                comunes.add(f)
        if not comunes:
            continue
        e["ficheros"] = sorted(set(e["ficheros"]) | comunes)
        for T in e.get("trajes") or []:
            T["ficheros"] = sorted(set(T.get("ficheros") or []) | comunes)


# ids que son un prefijo del nombre de malla, no un actor
ACTORES_IGNORADOS = {"bs", "ps", "wq", "sp", "sd", "obj", "part", "body", "eye", "face",
                     "hair", "camera", "cam", "scn", "scene", "n", "m", "f", "s"}


def _entradas_del_indice(existentes: set) -> list[dict]:
    """Actores que el indice de trajes reconoce y el catalogo no (multitudes, jefes, variantes).

    El catalogo agrupa por el PRIMER trozo del nombre de malla, asi que `n_f_furen_body_...` cae en
    el actor `n_f` y `sd_Gongze_head_...` en `sd`: los dos se descartaban por cortos. El indice de
    trajes los reconoce enteros, asi que se anaden aqui en vez de perderlos.
    """
    if not trajes.disponible():
        return []
    salida = []
    vistos = set(existentes)
    for actor, A in trajes.datos()["actores"].items():
        bajo = actor.lower()
        if bajo in vistos or bajo in ACTORES_IGNORADOS or len(bajo) < 3:
            continue
        if not A.get("trajes"):
            continue
        ficha = trajes.ficha(actor)
        if not ficha:
            continue
        vistos.add(bajo)
        lista = [ficha[c] for c in trajes.orden_trajes(ficha)]
        piezas = sorted({p for T in A["trajes"].values() for p in T["piezas"]})
        ficheros = sorted({f for T in lista for f in T["ficheros"]})
        if not ficheros:
            continue
        es_skin = "cara" not in piezas and "cuerpo" in piezas
        etiqueta = actor + (t("ct_skin") if es_skin else "")
        salida.append({
            "id": bajo, "nombre": actor, "etiqueta": etiqueta,
            "ficheros": ficheros,
            "tipos": sorted({Path(f).name.split("_", 1)[0] for f in ficheros}),
            "piezas": piezas, "es_skin": es_skin,
            "categoria": clasificar(bajo, piezas),
            "trajes": lista, "ficheros_otros": [],
            "traje_por_defecto": lista[0]["clave"] if lista else None,
        })
    return salida


def _es_artefacto(e: dict) -> bool:
    """Entradas que no son un modelo de verdad y solo entraron por coincidencia de prefijo.

    El catalogo agrupa por el primer trozo del nombre de malla, asi que ids genericos como `scn`,
    `part`, `body`, `eye` o `b l hiza01` (un hueso) se llevaban cientos de bundles que no son suyos.
    Se conserva solo lo que el indice de trajes reconoce como actor real.
    """
    cat = e.get("categoria")
    if cat == "escenario":
        return True      # el unico que habia era el cubo `scn`; los de verdad se anaden aparte
    if cat == "objeto":
        return e["id"] not in _actores_conocidos()
    return False


def _actores_conocidos() -> set:
    """Los ids que el indice de trajes reconoce como actores de verdad."""
    if not trajes.disponible():
        return set()
    return {a.lower() for a in (trajes.datos().get("actores") or {})}


# nombre de bundle: <tipo>_<nombre><hash>.bundle. El hash son los ultimos ocho caracteres hex.
_PATRON_BUNDLE = re.compile(r"^(?P<tipo>[a-z0-9]+)_(?P<nombre>.+)(?P<hash>[0-9a-f]{8,})$")

NOMBRES_CATEGORIA = {"escenario": "Escenario", "objeto": "Objeto", "efecto": "Efecto"}


def _nombre_bundle(fichero: str) -> str:
    """Nombre legible de un bundle: quita el prefijo de tipo (`scn_`) y el hash final."""
    stem = Path(fichero).name
    if stem.endswith(".bundle"):
        stem = stem[:-len(".bundle")]
    m = _PATRON_BUNDLE.match(stem)
    if m:
        limpio = m.group("nombre").strip("_")
        if limpio:
            return limpio
    return stem


def _entradas_del_juego(existentes: set) -> list[dict]:
    """Escenarios, objetos/props y efectos con geometria, como entradas de primera clase.

    El catalogo de actores se construye abriendo los bundles de MODELO, asi que los escenarios
    (`scn_`, 1.442 bundles), los props de escena (`role_` con papel `escenario`, 888) y los efectos
    (`efx_`, 398) no aparecen ahi nunca. Aqui se leen del indice de bundles (16.535) cruzado con el
    de trajes, que ya anota que mallas y texturas trae cada uno, y todo bundle con geometria se
    convierte en una entrada extraible con su nombre legible.

    Solo entran los que TRAEN MALLAS: un bundle sin geometria (animacion, manifest) no da ningun
    modelo y solo llenaria la lista de entradas vacias.
    """
    ficheros = _leer("indice_ficheros.json").get("ficheros", [])
    bundles = (trajes.datos().get("bundles") or {}) if trajes.disponible() else {}
    salida = []
    for f in ficheros:
        ruta = "%s\\%s" % (f.get("carpeta", ""), f.get("fichero", ""))
        if ruta in existentes:
            continue
        b = bundles.get(ruta.replace("\\", "/")) or {}
        mallas = b.get("mallas") or []
        if not mallas:
            continue
        tipo = (f.get("tipo") or "").lower()
        if tipo == "scn":
            categoria = "escenario"
        elif tipo == "efx":
            categoria = "efecto"
        elif b.get("papel") == "escenario":
            categoria = "objeto"
        else:
            continue
        nombre = _nombre_bundle(f.get("fichero", ""))
        n_tex = len(b.get("texturas") or [])
        mb = b.get("mb") or 0
        etiqueta = "%s %s   (%d mallas, %d texturas, %.1f MB)" % (
            t("ct_" + categoria), nombre, len(mallas), n_tex, mb)
        salida.append({
            "id": Path(f.get("fichero", "")).stem,
            "nombre": nombre,
            "ficheros": [ruta],
            "tipos": [tipo],
            "etiqueta": etiqueta,
            "piezas": [],
            "es_skin": False,
            "categoria": categoria,
            "trajes": [], "traje_por_defecto": None, "ficheros_otros": [],
            "n_mallas": len(mallas), "n_texturas": n_tex, "mb": mb,
        })
    return salida


def _con_trajes(entradas: list[dict]) -> list[dict]:
    """Reparte los ficheros de cada actor por TRAJE, usando el indice de trajes.

    Antes, la entrada de un actor mezclaba todos sus trajes (y a veces cosas que no eran ni suyas:
    el actor `skull` se llevaba un EDIFICIO llamado `skull`). Aqui cada traje queda con SUS bundles,
    y lo que no es un modelo de personaje (timelines, escenarios, efectos) se aparta a
    `ficheros_otros`, para que no acabe en la extraccion.
    """
    for e in entradas:
        e["trajes"] = []
        e["ficheros_otros"] = []
        e["traje_por_defecto"] = None
    if not trajes.disponible():
        return entradas

    for e in entradas:
        ficha = trajes.ficha(e["id"])
        if not ficha:
            continue
        lista = [ficha[clave] for clave in trajes.orden_trajes(ficha)]
        usados = {f.lower() for T in lista for f in T["ficheros"]}
        montaje, otros = [], []
        for f in e["ficheros"]:
            if f.lower() in usados:
                continue
            b = trajes.bundle(f)
            # el montaje del actor (role_*) no trae mallas, pero se incluye para no perder nada
            if b.get("papel") == "montaje" and e["id"].lower() in f.lower():
                montaje.append(f)
            else:
                otros.append(f)
        for T in lista:
            T["ficheros"] = sorted(set(T["ficheros"]) | set(montaje))
        e["trajes"] = lista
        e["ficheros_otros"] = sorted(otros)
        e["ficheros"] = sorted({f for T in lista for f in T["ficheros"]})
        e["tipos"] = sorted({Path(f).name.split("_", 1)[0] for f in e["ficheros"]})
        if lista:
            e["traje_por_defecto"] = lista[0]["clave"]
    return entradas


def trajes_de(entrada: dict) -> list[dict]:
    """Los trajes de una entrada del catalogo (lista vacia si no se pudo averiguar)."""
    return entrada.get("trajes") or []


def clasificar(ident: str, piezas) -> str:
    """Que es cada cosa: personaje, escenario, objeto o camara.

    El indice no distingue por si solo, porque al abrir los timelines entran props con nombres
    genericos. La regla que funciona: un personaje trae CARA (los 134 de 151 que la tienen), y
    las palabras sueltas de la lista negra son piezas de escena, no gente.
    """
    bajo = ident.lower()
    # un personaje nunca lleva espacios en el codigo; `b l hiza01` es un hueso de la rodilla
    if " " in bajo or bajo in NO_ES_GENTE or len(bajo) < 3:
        if bajo in ("camera", "cam"):
            return "camara"
        if bajo in ("scn", "scene", "map", "stage", "bg"):
            return "escenario"
        return "objeto"
    if "cara" in piezas:
        return "personaje"
    if "cuerpo" in piezas or "pelo" in piezas:
        return "personaje"      # una skin: tiene cuerpo pero su cara vive en el base
    return "objeto"


def por_categoria(categoria: str | None = None) -> list[dict]:
    """Los actores filtrados por categoria, para el menu de la interfaz."""
    gente = personajes()
    if not categoria or categoria == "todo":
        return gente
    return [a for a in gente if a.get("categoria") == categoria]


def cuantas_por_categoria() -> dict:
    cuenta: dict[str, int] = {}
    for a in personajes():
        cuenta[a.get("categoria", "otro")] = cuenta.get(a.get("categoria", "otro"), 0) + 1
    return dict(sorted(cuenta.items(), key=lambda x: -x[1]))


def resumen() -> dict:
    """Cuentas para la cabecera de la interfaz."""
    ficheros = _leer("indice_ficheros.json")
    actores = personajes()
    return {
        "bundles": ficheros.get("total", 0),
        "gb": round((ficheros.get("mb_total") or 0) / 1024, 1),
        "tipos": ficheros.get("por_tipo", {}),
        "actores": len(actores),
        "skins": sum(1 for a in actores if a["es_skin"]),
    }


if __name__ == "__main__":
    r = resumen()
    print("   bundles: %d (%.1f GB)" % (r["bundles"], r["gb"]))
    print("   actores extraibles: %d   de ellos skins sin cara: %d" % (r["actores"], r["skins"]))
    print()
    for a in personajes()[:14]:
        print("   %-20s %3d bundles   %s" % (a["etiqueta"][:34], len(a["ficheros"]),
                                             ", ".join(a["piezas"])))