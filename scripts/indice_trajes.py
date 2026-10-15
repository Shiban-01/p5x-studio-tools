"""Indice de TRAJES del juego: para cada bundle, que es, de que actor, de que traje y que lleva.

El indice de bundles solo conoce el nombre del fichero, y el de assets solo la lista de recursos.
Ninguno de los dos mira el nombre de las MALLAS, que es donde el juego escribe el traje:

    <actor>_<traje>_<pieza>_wholeexport_rig_<prefijo_textura>_<pieza>

Ejemplos reales:
    skull_thief_body_wholeexport_rig_skull_thief_body
    n_GuitarGirl_normal_body_wholeexport_rig_chord_normal_body
    PC079_01_face_wholeexport_rig_PC079_01_face

Por eso la herramienta agrupaba por actor y metia TODOS sus trajes en la misma entrada: extraer
`skull` devolvia a la vez el traje de ladron, el uniforme y hasta un EDIFICIO llamado `skull`
(`role_other_ht_skull`: mallas skull_lunchuan, skull_wuding, skull_paodao...).

Este indice lee los nombres de malla de los 16.535 bundles (listas completas de `assets_full.json`
cuando existen; si no, la `muestra` del indice de assets) y deduce, bundle a bundle:

  - `papel`: modelo de personaje, montaje (rig), escenario, timeline, animacion, textura, interfaz...
  - `actor` y `traje` de cada malla de personaje,
  - `piezas` (cara, ojos, pelo, cuerpo, arma, accesorio),
  - y separa las variantes que NO son trajes:
      * calidad   -> lod, lodlow, lodhigh, low, high, shadow
      * expresion -> bs, ps

Uso:
    python scripts/indice_trajes.py

Salidas en _dl/indice_trajes/:
    trajes.json   para la app
    TRAJES.md     legible, actor por actor
    REGLAS.md     el criterio, documentado
"""
from __future__ import annotations

import json
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
IND = RAIZ / "_dl"
FICHEROS = IND / "indice_juego/indice_ficheros.json"
ASSETS = IND / "indice_assets/assets.json"
ASSETS_FULL = IND / "indice_trajes/assets_full.json"
CONTENIDO = IND / "indice_juego/indice_contenido.json"
SALIDA = IND / "indice_trajes"

# --- piezas del personaje. El orden importa: la primera que encaje gana. -------------------
PIEZAS = [
    ("cara", ("face", "kao")),
    ("ojos", ("eye", "eyelid", "eyeild", "yan")),
    ("pelo", ("hair", "toufa", "kami", "highlight")),
    ("arma", ("weapon", "gun", "pistol", "qiang", "sword", "blade", "wq_", "wp_", "wq")),
    ("accesorio", ("headwear", "headset", "hat", "cap", "glasses", "mask", "bag", "backpack",
                   "auricular", "sombrero", "headphone", "scarf", "tie", "belt", "guitar",
                   "guitar2", "umbrella", "earring", "necklace", "ring", "watch", "wing",
                   "tail", "book", "phone", "key", "card", "fan")),
    ("cuerpo", ("body", "head", "cloth", "uniform", "skin", "shenti", "xiuzhang", "dress",
                "top", "bottom", "shoes", "shoe", "foot", "hand", "leg", "arm", "boot", "boots",
                "glove", "gloves", "sock", "socks", "skirt", "shirt", "pants", "coat", "jacket",
                "hoodie", "suit", "tie", "kaitou", "whole")),
]
# Palabras que son una PIEZA inequivoca (no un traje). Ojo: NO se incluyen `uniform`, `dress`,
# `top`, `coat`... porque son nombres de traje en este juego (`skull_uniform_*`, `changweiaizhu_dress_*`).
TOKENS_PIEZA = {
    "body", "head", "face", "kao", "hair", "toufa", "kami", "highlight", "eye", "eyelid",
    "eyeild", "yan", "weapon", "gun", "pistol", "qiang", "qiangtao", "sword", "blade", "wq",
    "wp", "hand", "hands", "foot", "feet", "shoe", "shoes", "boot", "boots", "leg", "arm",
    "top", "bottom", "skirt", "shirt", "pants", "sock", "socks", "glove", "gloves", "mask",
    "cap", "hat", "headwear", "headset", "bag", "backpack", "guitar", "guitar2", "kaitou",
    "whole", "tongue", "key", "card", "book", "umbrella", "shi",
} | {"wholeexport", "rig", "mesh", "lod", "lodlow", "lodhigh", "low", "high", "shadow", "bs",
     "ps", "sp", "obj", "part", "mod", "actor", "null", "none", "dummy", "replaced"}
# variantes de calidad: la MISMA ropa con menos detalle. No son trajes distintos.
CALIDAD = {"lod", "lodlow", "lodhigh", "low", "high", "shadow", "shade", "yinying", "op", "lodbake"}
# variantes de expresion: la misma ropa, cara con morphs. No son trajes distintos.
EXPRESION = {"bs", "ps"}
# modificadores que se pegan al traje anterior: `closer_uniform_swimsuit_body` es el BANADOR, no el
# uniforme (`uniform_swimsuit` = banador). Sin esto, dos prendas distintas caerian en el mismo grupo.
MODIFICADORES = {"swimsuit", "sports", "summer", "winter", "autumn", "spring", "casual", "fashion",
                 "school", "formal", "battle", "soccer", "party", "wedding", "beach", "kokatsu"}
# nombres de traje con faltas o variantes -> forma canonica
ALIAS_TRAJE = {
    "unifom": "uniform", "unifrom": "uniform", "swim": "swimsuit", "binghao": "binghaofu",
    "maid": "maidsuit",
}
# que es cada traje, en castellano
NOMBRES_TRAJE = {
    "normal": "Ropa normal", "thief": "Traje de ladron", "uniform": "Uniforme",
    "swimsuit": "Banador", "dress": "Vestido", "catbag": "Disfraz de gato",
    "autumn": "Ropa de otono", "office": "Ropa de oficina", "sports": "Ropa deportiva",
    "maidsuit": "Traje de doncella", "binghaofu": "Bata de hospital", "wheelchair": "Silla de ruedas",
    "gamer": "Ropa de gamer", "doctor": "Bata de medico", "student": "Uniforme escolar",
    "velvet": "Terciopelo", "heize": "Ropa negra", "weiqun": "Falda", "manwu": "Traje de baile",
    "chushifu": "Bata de cocina", "kimono": "Kimono", "yukata": "Yukata", "pajama": "Pijama",
    "unreal": "Variante unreal", "sp": "Variante SP", "kokatsu": "Uniforme escolar",
    "guitar": "Con guitarra", "seeker": "Seeker", "itargirl": "Variante itargirl",
}
# como se llama cada pieza en castellano
NOMBRES_PIEZA = {"cara": "cara", "ojos": "ojos", "pelo": "pelo", "cuerpo": "cuerpo",
                 "arma": "arma", "accesorio": "accesorio"}

PAPEL = {
    "part": "modelo de personaje o pieza", "role": "montaje del actor (huesos y manifiesto del rig)",
    "tl": "timeline o escena de historia", "scn": "escenario", "anim": "animaciones",
    "atlas": "atlas de texturas (arte 2D)", "uitex": "texturas de interfaz", "ui": "interfaz",
    "efx": "efectos", "shared": "recursos compartidos", "shaders": "shaders",
    "i18n": "traducciones", "spinetest": "pruebas de Spine", "roletiny": "actor reducido",
    "tlm": "timeline (marcador)", "postprocess": "post-proceso", "avatar": "avatar",
    "char": "personaje (datos)", "cinemachine": "camara virtual", "uispecial": "interfaz especial",
    "mc": "mini-cine", "tmpfontmat": "fuentes temporales",
}


def actor_y_traje(nombre: str):
    """De un nombre de malla saca (actor, traje, pieza). None si no es una malla de personaje.

    Solo se consideran mallas de personaje las que llevan `_wholeexport` (asi exporta el juego las
    prendas del actor). El resto son props, escenarios o huesos.

    `traje` sale None para las armas y los props: no definen un traje, se reparten entre los que
    traiga el mismo bundle (una pistola vale para el uniforme y para el traje de ladron).
    """
    bajo = nombre.lower()
    if "_wholeexport" not in bajo:
        return None
    base = nombre.split("_wholeexport")[0]
    t = base.split("_")
    if not t:
        return None
    a = _len_actor(t)
    actor = "_".join(t[:a])
    resto = t[a:]
    # la pieza sale del prefijo de textura (lo que va tras `_rig_`), que termina en la pieza
    pieza = _pieza_de(nombre)
    if pieza in ("arma", "otro"):
        return actor, None, pieza
    traje = _traje_de(resto, actor)
    return actor, traje, pieza


def _len_actor(t: list[str]) -> int:
    """Cuantos trozos ocupa el actor al principio del nombre de malla."""
    if re.match(r"^PC\d{3}$", t[0], re.I):
        return 2 if len(t) > 1 and re.match(r"^\d{2}$", t[1]) else 1
    if t[0].lower() in ("n", "m", "f", "s", "sd") and len(t) > 1:
        return 2
    return 1


def _traje_de(resto: list[str], actor: str) -> str:
    """El traje es el primer trozo tras el actor, salvo si es una pieza o una variante.

    Si el trozo siguiente es un modificador (`swimsuit`, `sports`...), se pega: `uniform_swimsuit`
    es el banador, que es otra prenda distinta del uniforme.
    """
    i = 0
    while i < len(resto) and resto[i].lower() in (EXPRESION | CALIDAD):
        i += 1
    if i >= len(resto):
        return "normal"
    tok = resto[i].lower()
    if tok in TOKENS_PIEZA or re.match(r"^\d+$", tok) or len(tok) <= 1:
        return "normal"         # el nombre no lleva traje: es la ropa base
    if i + 1 < len(resto) and resto[i + 1].lower() in MODIFICADORES:
        tok = tok + "_" + resto[i + 1].lower()
    return ALIAS_TRAJE.get(tok, tok)


def _pieza_de(nombre: str) -> str:
    """Que parte del personaje es la malla (cara, ojos, pelo, cuerpo, arma, accesorio)."""
    bajo = nombre.lower()
    # primero el prefijo de textura tras `_rig_`, que es el mas fiable
    i = bajo.find("_rig_")
    zona = bajo[i + 5:] if i >= 0 else bajo
    for parte, pistas in PIEZAS:
        if any(p in zona for p in pistas):
            return parte
    for parte, pistas in PIEZAS:
        if any(p in bajo for p in pistas):
            return parte
    return "otro"


def _prefijo_rig(nombre: str) -> str | None:
    """Prefijo de textura de una malla: `..._wholeexport_rig_chord_normal_body` -> `chord_normal_body`.

    Es justo el nombre con el que empiezan sus texturas (`chord_normal_body_bc`), asi que sirve para
    enlazar malla y textura sin depender del material del juego.
    """
    bajo = nombre.lower()
    i = bajo.find("_rig_")
    if i < 0:
        return None
    toks = [t for t in bajo[i + 5:].split("_") if t]
    while toks and toks[0] in ("bs", "ps", "b"):
        toks = toks[1:]
    return "_".join(toks) if len(toks) >= 2 else None


def _papel(tipo: str, mallas: list[str], es_personaje: bool) -> str:
    if es_personaje:
        return "modelo"
    if tipo == "part" or tipo == "role":
        # un `part_` o `role_` sin mallas de personaje: es un escenario o un prop con nombre de actor
        if mallas:
            return "escenario"
        return "montaje"
    return "otro"


def _cargar(ruta: Path) -> dict:
    if not ruta.is_file():
        return {}
    return json.loads(ruta.read_text(encoding="utf-8"))


def construir() -> dict:
    ficheros = _cargar(FICHEROS).get("ficheros", [])
    assets = _cargar(ASSETS)
    full = _cargar(ASSETS_FULL)
    contenido = _cargar(CONTENIDO)

    bundles: dict[str, dict] = {}
    actores: dict[str, dict] = {}
    prefijos: dict[tuple, set] = {}      # (actor, traje) -> prefijos de textura de sus mallas

    for f in ficheros:
        clave = "%s/%s" % (f["carpeta"], f["fichero"])
        tipo = f.get("tipo", "?")
        info_a = assets.get(clave) or {}
        info_f = full.get(clave) or {}
        cont = contenido.get(clave) or {}

        # lista de nombres por tipo: la completa si existe, si no la muestra recortada
        nombres = info_f.get("nombres") or info_a.get("muestra") or {}
        mallas = sorted(nombres.get("Mesh") or cont.get("mallas") or [])
        texturas = sorted(nombres.get("Texture2D") or [])

        por_actor: dict[str, dict] = {}
        armas: dict[str, set] = {}
        armas_mallas: dict[str, list] = {}
        for m in mallas:
            r = actor_y_traje(m)
            if not r:
                continue
            actor, traje, pieza = r
            e = por_actor.setdefault(actor, {"trajes": {}, "piezas": set(),
                                             "mallas": {}, "n": {}})
            if traje is None:
                # arma o prop: no define traje, se reparte luego entre los del bundle
                armas.setdefault(actor, set()).add(pieza)
                armas_mallas.setdefault(actor, []).append(m)
                continue
            e["trajes"].setdefault(traje, set()).add(pieza)
            e["piezas"].add(pieza)
            e["mallas"].setdefault(traje, []).append(m)
            e["n"][traje] = e["n"].get(traje, 0) + 1
            p = _prefijo_rig(m)
            if p:
                prefijos.setdefault((actor, traje), set()).add(p)
        for actor, pzs in armas.items():
            e = por_actor.setdefault(actor, {"trajes": {}, "piezas": set(),
                                             "mallas": {}, "n": {}})
            for traje in (list(e["trajes"]) or ["normal"]):
                e["trajes"].setdefault(traje, set()).update(pzs)
                # el prefijo de las armas tambien vale para el traje (sus texturas son suyas)
                for m in armas_mallas.get(actor, []):
                    p = _prefijo_rig(m)
                    if p:
                        prefijos.setdefault((actor, traje), set()).add(p)
            e["piezas"] |= pzs

        # un bundle puede traer mallas de varios actores (p.ej. `part_port_rig`). Se guardan todos.
        actor_trajes = []
        for actor, e in sorted(por_actor.items()):
            for traje, pz in sorted(e["trajes"].items()):
                actor_trajes.append({"actor": actor, "traje": traje, "piezas": sorted(pz),
                                     "n_mallas": e["n"].get(traje, 0)})
        es_personaje = bool(actor_trajes)
        papel = _papel(tipo, mallas, es_personaje)

        bundles[clave] = {
            "tipo": tipo, "nombre": f.get("nombre", ""), "que_es": PAPEL.get(tipo, "sin clasificar"),
            "papel": papel, "mb": f.get("mb", 0),
            "actor_trajes": actor_trajes,
            "actores": sorted(por_actor),
            "trajes": sorted({a["traje"] for a in actor_trajes}),
            "piezas": sorted({p for a in actor_trajes for p in a["piezas"]}),
            "cuenta": info_f.get("cuenta") or info_a.get("cuenta") or {},
            "mallas": mallas, "texturas": texturas,
        }

        for actor, e in por_actor.items():
            A = actores.setdefault(actor, {"actor": actor, "trajes": {}, "bundles": [],
                                           "piezas": set()})
            A["bundles"].append(clave)
            A["piezas"] |= e["piezas"]
            for traje, pz in e["trajes"].items():
                T = A["trajes"].setdefault(traje, {"bundles": [], "piezas": set(),
                                                   "mallas": [], "texturas": [], "mb": 0.0})
                T["bundles"].append(clave)
                T["piezas"] |= pz
                T["mb"] = round(T["mb"] + f.get("mb", 0), 2)
                T["mallas"].extend(e["mallas"].get(traje, []))
                T["n_mallas"] = T.get("n_mallas", 0) + e["n"].get(traje, 0)

    # --- mallas por traje, y separacion de las variantes de calidad y de expresion
    for actor, A in actores.items():
        for traje, T in A["trajes"].items():
            T["piezas"] = sorted(T["piezas"])
            T["bundles"] = sorted(set(T["bundles"]))
            T["mallas"] = sorted(set(T["mallas"]))
            variantes = {"calidad": [], "expresion": []}
            for m in T["mallas"]:
                bajo = m.lower()
                for var, conjunto in (("calidad", CALIDAD), ("expresion", EXPRESION)):
                    if any(("_%s_" % v) in bajo or bajo.endswith("_" + v) for v in conjunto):
                        variantes[var].append(m)
            T["variantes"] = variantes
        A["bundles"] = sorted(set(A["bundles"]))
        A["piezas"] = sorted(A["piezas"])

    # --- fase 2: enlazar las TEXTURAS. Una textura pertenece al traje cuya malla pide su prefijo:
    # `chord_normal_body_bc` -> prefijo `chord_normal_body` -> traje `normal` de `n_GuitarGirl`.
    # Esto es lo que descubre que las texturas de un actor pueden vivir en bundles `shared_`
    # (las de `n_GuitarGirl` estan en `shared_*`, no en su bundle de mallas).
    mapa_prefijos: dict[str, list] = {}
    for (actor, traje), ps in prefijos.items():
        for p in ps:
            mapa_prefijos.setdefault(p, []).append((actor, traje))

    def dueno(textura: str):
        """A que (actor, traje) pertenece una textura.

        Primero por el prefijo de rig mas largo que encaje; si no, leyendo la propia textura con las
        mismas reglas que una malla (`skull_uniform_body_bc` -> traje `uniform`). El prefijo de las
        mallas de algunos trajes es generico (`c0002_02_body_low`), y sin este respaldo sus texturas
        quedarian sin dueno.
        """
        toks = textura.lower().split("_")
        for i in range(len(toks) - 1, 1, -1):      # del prefijo mas largo al mas corto
            cand = "_".join(toks[:i])
            if cand in mapa_prefijos:
                return mapa_prefijos[cand][0]
        if len(toks) > 1:
            a = _len_actor(toks)
            actor = "_".join(toks[:a])
            if actor in actores:
                traje = _traje_de(toks[a:], actor)
                if traje in actores[actor]["trajes"]:
                    return (actor, traje)
        return None

    # Un bundle `shared_` puede traer texturas de varios personajes. Las texturas de los bundles de
    # MALLA del traje siempre cuentan; un bundle solo de texturas se enlaza si la MAYORIA son suyas
    # (>=70%): asi `193/shared_7aad509` (todo `chord_normal_*`) entra, pero un atlas mezclado no
    # llena la extraccion de texturas ajenas.
    for clave, b in bundles.items():
        if not b["texturas"]:
            continue
        total = len(b["texturas"])
        suyas: dict[tuple, list] = {}
        for t in b["texturas"]:
            d = dueno(t)
            if d:
                suyas.setdefault(d, []).append(t)
        for (actor, traje), ts in suyas.items():
            A = actores.get(actor)
            if not A or traje not in A["trajes"]:
                continue
            T = A["trajes"][traje]
            es_modelo = clave in T["bundles"]
            if not es_modelo and len(ts) / total < 0.7:
                continue
            if not es_modelo:
                T.setdefault("bundles_texturas", set()).add(clave)
            for t in ts:
                if t not in T["texturas"]:
                    T["texturas"].append(t)

    # --- cierre: listas ordenadas y bundles finales (mallas + texturas)
    for actor, A in actores.items():
        for traje, T in A["trajes"].items():
            T["bundles_modelo"] = T["bundles"]
            T["bundles_texturas"] = sorted(T.get("bundles_texturas", set()))
            T["bundles"] = sorted(set(T["bundles"]) | set(T["bundles_texturas"]))
            T["texturas"] = sorted(T["texturas"])
            T["mb"] = round(T["mb"] + sum(bundles[c]["mb"] for c in T["bundles_texturas"]), 2)
        A["bundles"] = sorted(set(A["bundles"]) | {c for T in A["trajes"].values()
                                                   for c in T["bundles"]})

    return {"bundles": bundles, "actores": actores}


def escribir(datos: dict) -> None:
    bundles, actores = datos["bundles"], datos["actores"]
    SALIDA.mkdir(parents=True, exist_ok=True)
    (SALIDA / "trajes.json").write_text(
        json.dumps({"version": 1, "reglas": {
            "malla": "<actor>_<traje>_<pieza>_wholeexport_rig_<prefijo_textura>_<pieza>",
            "traje": "primer trozo tras el actor; las variantes de calidad (lod, lodlow, shadow) "
                     "y de expresion (bs, ps) NO son trajes aparte",
        }, "bundles": bundles, "actores": actores}, ensure_ascii=False),
        encoding="utf-8")

    # --- documento legible
    L = ["# Indice de trajes del juego", "",
         "Para cada bundle: que es, de que actor, de que traje y que lleva dentro.", "",
         "El traje sale del nombre de la malla (`<actor>_<traje>_<pieza>_wholeexport_rig_...`).",
         "Las variantes de calidad (`lodlow`) y de expresion (`bs`) no cuentan como traje.", "",
         "## Actores con mas de un traje", ""]
    multi = [(a, A) for a, A in actores.items() if len(A["trajes"]) > 1]
    multi.sort(key=lambda x: (-len(x[1]["trajes"]), x[0]))
    L += ["| actor | trajes | bundles |", "|---|---|---|"]
    for a, A in multi[:120]:
        L.append("| `%s` | %s | %d |" % (a, ", ".join(sorted(A["trajes"])), len(A["bundles"])))
    L += ["", "Total actores: **%d**, con mas de un traje: **%d**." % (len(actores), len(multi)), "",
          "## Actor por actor", ""]
    for a in sorted(actores):
        A = actores[a]
        L.append("### `%s`" % a)
        L.append("")
        for traje in sorted(A["trajes"]):
            T = A["trajes"][traje]
            nombre = NOMBRES_TRAJE.get(traje, traje)
            L.append("- **%s** (%s): %d bundles, %d mallas; piezas: %s"
                     % (traje, nombre, len(T["bundles"]), T.get("n_mallas", 0),
                        ", ".join(NOMBRES_PIEZA.get(p, p) for p in T["piezas"]) or "-"))
            for b in T["bundles"]:
                L.append("  - `%s` (%s, %.1f MB)" % (b, bundles[b]["nombre"], bundles[b]["mb"]))
        L.append("")
    (SALIDA / "TRAJES.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    _escribir_reglas(bundles, actores)


def _escribir_reglas(bundles: dict, actores: dict) -> None:
    """Documento con el criterio: que es traje, que es calidad y que es expresion."""
    modelos = [c for c, b in bundles.items() if b["papel"] == "modelo"]
    escenarios = [c for c, b in bundles.items() if b["papel"] == "escenario"]
    montaje = [c for c, b in bundles.items() if b["papel"] == "montaje"]
    variantes = sum(len(T["variantes"]["calidad"]) + len(T["variantes"]["expresion"])
                    for A in actores.values() for T in A["trajes"].values())
    L = [
        "# Reglas del indice de trajes",
        "",
        "Como se decide a que actor y a que traje pertenece cada bundle, y que NO cuenta como traje.",
        "Se aplica a los 16.535 bundles del juego; las listas completas de recursos se leyeron",
        "reabriendo los 8.121 que traen mallas (`scripts/indice_trajes_scan.py`).",
        "",
        "## 1. El nombre de la malla delata el traje",
        "",
        "Las prendas de un actor se exportan con este nombre:",
        "",
        "```",
        "<actor>_<traje>[_<modificador>]_<pieza>_wholeexport_rig_<prefijo_textura>_<pieza>",
        "```",
        "",
        "Ejemplos reales:",
        "",
        "| malla | actor | traje | pieza |",
        "|---|---|---|---|",
        "| `skull_thief_body_wholeexport_rig_skull_thief_body` | `skull` | `thief` | cuerpo |",
        "| `skull_uniform_body_wholeexport_rig_c0002_02_body_low` | `skull` | `uniform` | cuerpo |",
        "| `n_GuitarGirl_normal_body_wholeexport_rig_chord_normal_body` | `n_GuitarGirl` | `normal` | cuerpo |",
        "| `PC079_01_face_wholeexport_rig_PC079_01_face` | `PC079_01` | `normal` | cara |",
        "| `closer_uniform_swimsuit_body_...` | `closer` | `uniform_swimsuit` | cuerpo |",
        "",
        "Solo se miran las mallas con `_wholeexport`: asi exporta el juego las prendas del actor. El",
        "resto de mallas de un bundle son props, escenarios o huesos y no definen traje.",
        "",
        "## 2. Que es el actor",
        "",
        "- `PC###` (o `PC###_##`): los personajes jugables (`PC079_01`).",
        "- `n_<Nombre>` / `m_<Nombre>` / `f_<Nombre>`: actores del mundo (`n_GuitarGirl`).",
        "- una sola palabra (`skull`, `chord`, `kotomo`...): los demas.",
        "",
        "## 3. Que NO es un traje",
        "",
        "El juego mete en el mismo nombre variantes que NO son ropa distinta. Se separan y se",
        "guardan aparte (`variantes`), pero no crean una entrada nueva:",
        "",
        "| tipo | marcas | ejemplo | por que no es un traje |",
        "|---|---|---|---|",
        "| calidad | `lod`, `lodlow`, `lodhigh`, `low`, `high`, `shadow` | `..._body_lodlow` | la MISMA ropa con menos detalle |",
        "| expresion | `bs`, `ps` | `..._rig_bs_chord_normal_face` | la misma cara, con morphs de expresion |",
        "",
        "Los numeros y las letras sueltas (`body_02`, `weapon_03`, `normal_10`) tampoco son trajes:",
        "son variantes internas de la misma prenda.",
        "",
        "En cambio, un MODIFICADOR si se conserva pegado al traje, porque es ropa distinta:",
        "`uniform_swimsuit` es el banador (no el uniforme), y `thief_swimsuit` el banador con base de",
        "ladron. Sin esto, dos prendas distintas caerian en el mismo grupo.",
        "",
        "## 4. Que es cada bundle (`papel`)",
        "",
        "| papel | cuantos | que es |",
        "|---|---|---|",
        "| `modelo` | %d | trae mallas de personaje (`_wholeexport`): el modelo |" % len(modelos),
        "| `montaje` | %d | `role_*` del actor: huesos y manifiesto del rig, sin mallas |" % len(montaje),
        "| `escenario` | %d | `part_*`/`role_*` con mallas que NO son de personaje |" % len(escenarios),
        "| `otro` | %d | timeline, animacion, textura, interfaz, efecto... |"
        % (len(bundles) - len(modelos) - len(escenarios) - len(montaje)),
        "",
        "El papel `escenario` es el que arregla el error reportado: el actor `skull` se llevaba",
        "tambien `032/role_other_ht_skull7f0c9b07.bundle`, que NO es el personaje, sino un EDIFICIO",
        "llamado `skull` (mallas `skull_lunchuan02`, `skull_wuding`, `skull_paodao`...).",
        "",
        "## 5. Donde estan las texturas",
        "",
        "Las texturas se enlazan a un traje por el PREFIJO DE TEXTURA de sus mallas (lo que va tras",
        "`_rig_`): `chord_normal_body_bc` empieza por `chord_normal_body`, que es el prefijo de",
        "`n_GuitarGirl_normal_body_wholeexport_rig_chord_normal_body`. Asi se descubre que las",
        "texturas de `n_GuitarGirl` NO estan en su bundle de mallas (`089/part_l_normal`), sino en",
        "cuatro bundles `shared_*`.",
        "",
        "Un bundle `shared_` que mezcla texturas de varios personajes solo se enlaza a un traje si la",
        "MAYORIA (>=70%%) de sus texturas son suyas. De este modo la extraccion no se llena de",
        "texturas ajenas.",
        "",
        "## 6. Numeros",
        "",
        "- bundles catalogados: **%d**" % len(bundles),
        "- actores con trajes identificados: **%d**" % len(actores),
        "- actores con mas de un traje: **%d**" % sum(1 for A in actores.values() if len(A["trajes"]) > 1),
        "- bundles de modelo de personaje: **%d**" % len(modelos),
        "- mallas marcadas como variante de calidad o expresion: **%d**" % variantes,
        "",
    ]
    (SALIDA / "REGLAS.md").write_text("\n".join(L) + "\n", encoding="utf-8")


def main() -> None:
    t0 = time.time()
    datos = construir()
    escribir(datos)
    bundles, actores = datos["bundles"], datos["actores"]
    papeles = Counter(b["papel"] for b in bundles.values())
    multi = sum(1 for A in actores.values() if len(A["trajes"]) > 1)
    print("   bundles: %d   actores: %d   con mas de un traje: %d   (%.0f s)"
          % (len(bundles), len(actores), multi, time.time() - t0))
    print("   papeles:", dict(papeles.most_common()))
    print("   top actores por trajes:")
    for a, A in sorted(actores.items(), key=lambda x: -len(x[1]["trajes"]))[:15]:
        print("      %-18s %d trajes: %s" % (a, len(A["trajes"]),
                                             ", ".join(sorted(A["trajes"]))[:90]))


if __name__ == "__main__":
    main()