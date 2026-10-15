"""Fachada del MOTOR de P5X Studio Tools: toda la logica, sin nada de interfaz.

Esta es la pieza que hace posible tener DOS interfaces (la clasica de tkinter y la nueva de
pywebview/HTML) sobre el MISMO motor. Aqui no se importa `tkinter` ni se sabe nada de colores,
widgets, HTML ni idiomas de presentacion: cada funcion recibe datos simples y devuelve datos
simples (listas de dicts, numeros, cadenas), listos para pintar desde cualquier sitio.

De momento esta fachada se APOYA en las funciones de `herramientas.py`: ese modulo sigue
mezclando logica y panel de tkinter (la clase `PanelHerramientas`), y separarlas del todo es
trabajo de mas de una fase. Lo que ya se ha conseguido aqui es que la interfaz web NO toque
`herramientas` ni la clase del panel: solo habla con estas operaciones, que ademas normalizan la
forma de los datos (una sola forma estable para las dos interfaces). En fases siguientes las
funciones de logica se pueden mover fisicamente aqui sin tocar a quien las llama.

Cobertura de las cinco herramientas:
    1. Explorador de bundles   -> `listar_bundles`, `filtrar_bundles`, `tipos_bundle`, `ficha_bundle`
    2. Inspector de un bundle  -> `abrir_bundle`, `exportar_bundle`
    3. Buscador de recursos    -> `estado_indice`, `construir_indice`, `buscar_recursos`, `tipos_recurso`
    4. Visor de texturas       -> `exportar_texturas`, `imagenes_de`
    5. Video y audio           -> `listar_media`, `extraer_video`, `extraer_audio`

`herramientas.py` no importa este modulo (evita el ciclo): la dependencia va en un solo sentido.
"""
from __future__ import annotations

import json
from pathlib import Path

from . import ajustes, herramientas, idiomas, lote

# --------------------------------------------------------------------------- categorias
# El tipo REAL de un bundle es el prefijo de su fichero (`part_...`, `shared_...`, ...) y hay mas
# de veinte distintos. Para dar color y agrupar en la interfaz se reduce a unas pocas FAMILIAS
# estables. Que una familia sea "character" u "object" es logica de datos (a que se parece un
# prefijo), no presentacion; el color concreto lo decide cada interfaz.
_CATEGORIAS = {
    "part": "character", "char": "character", "avatar": "character", "mc": "character",
    "role": "object", "roletiny": "object",
    "scn": "scene",
    "shared": "shared", "uitex": "shared", "ui": "shared", "uispecial": "shared",
    "atlas": "shared",
    "tl": "anim", "tlm": "anim", "anim": "anim", "animchartiny": "anim", "spinetest": "anim",
}


def categoria_de_tipo(tipo: str) -> str:
    """Familia (`character`/`object`/`scene`/`shared`/`anim`/`other`) de un prefijo de bundle."""
    return _CATEGORIAS.get((tipo or "").lower(), "other")


# --------------------------------------------------------------------------- estado general
def version_ui() -> str:
    return ajustes.VERSION


def idioma() -> str:
    return idiomas.idioma_actual()


def estado() -> dict:
    """Foto de la situacion: juego, bundles, indice del buscador y herramientas externas."""
    juego = ajustes.detectar_juego()
    bundles = herramientas.catalogo_bundles()
    ind = herramientas.indice_recursos_estado()
    from . import dependencias
    return {
        "version": ajustes.VERSION,
        "juego": str(juego) if juego else "",
        "carpeta_bundles": str(herramientas.carpeta_bundles() or ""),
        "n_bundles": len(bundles),
        "origen": (bundles[0].get("origen") if bundles else "") or "",
        "indice": ind,
        "motor": bool(dependencias.ruta_assetstudio()),
        "idioma": idiomas.idioma_actual(),
    }


def estado_herramientas() -> dict:
    """Que herramientas externas hay (wannacri, vgmstream, ffmpeg, motor). No instala nada."""
    est = herramientas.estado_herramientas()
    return {k: bool(v) for k, v in est.items()}


def estado_herramientas_rutas() -> dict:
    """Lo mismo, pero con las rutas en vez de un si/no.

    Hace falta para distinguir una herramienta puesta DENTRO de la carpeta de una que se esta
    usando desde fuera (el escritorio del usuario, el PATH): las dos son "si", pero solo la de
    dentro viaja al copiar la carpeta a otro equipo.
    """
    return {k: (str(v[0] if isinstance(v, list) else v) if v else "")
            for k, v in herramientas.estado_herramientas().items()}


# --------------------------------------------------------------------------- 1) explorador
def _fila(b: dict) -> dict:
    """Normaliza un bundle del catalogo a la forma estable que consumen las interfaces."""
    tipo = b.get("tipo") or ""
    tiene = list(b.get("tiene") or [])
    return {
        "id": b.get("ruta") or "",
        "ruta": b.get("ruta") or "",
        "fichero": b.get("fichero") or "",
        "carpeta": b.get("carpeta") or "",
        "tipo": tipo,
        "cat": categoria_de_tipo(tipo),
        "mb": round(float(b.get("mb") or 0.0), 2),
        "papel": b.get("papel") or "",
        "que_es": b.get("que_es") or "",
        "n_mallas": len(b.get("mallas") or []),
        "n_texturas": len(b.get("texturas") or []),
        "contenido": tiene or ([b.get("que_es")] if b.get("que_es") else []),
        "origen": b.get("origen") or "",
    }


# --------------------------------------------------------------------------- novedades
# Cada vez que el juego se actualiza aparecen bundles nuevos. Para poder ver SOLO esos, se guarda
# un registro de los bundles ya vistos (`cache/bundles_conocidos.json`). La primera vez no hay
# registro, se crea la base con lo que hay ahora y nada se marca como nuevo; a partir de ahí, todo
# bundle que aparezca y no este en el registro es "nuevo" hasta que el usuario lo marca como visto.
_RUTA_CONOCIDOS = ajustes.CACHE / "bundles_conocidos.json"


def _conocidos() -> set[str]:
    try:
        datos = json.loads(_RUTA_CONOCIDOS.read_text(encoding="utf-8"))
        return set(datos.get("rutas") or [])
    except (OSError, ValueError):
        return set()


def _guardar_conocidos(rutas: set[str]) -> None:
    _RUTA_CONOCIDOS.parent.mkdir(parents=True, exist_ok=True)
    _RUTA_CONOCIDOS.write_text(
        json.dumps({"rutas": sorted(r for r in rutas if r)}, ensure_ascii=False),
        encoding="utf-8")


def estado_novedades() -> dict:
    """Los bundles nuevos y modificados desde la ultima vez que se marco como visto."""
    from . import bundles_tracker
    cat = herramientas.catalogo_bundles()
    resultado = bundles_tracker.comparar(cat)
    if not resultado.get("hay_base"):
        return {"hay_base": False, "n_nuevos": 0, "n_modificados": 0,
                "nuevos": [], "modificados": [], "n_total": resultado["n_total"]}
    return resultado


def marcar_novedades_vistas() -> int:
    """Da por vistos los bundles actuales: los deja de contar como nuevos/modificados. Devuelve el total."""
    from . import bundles_tracker
    return bundles_tracker.marcar_vistos(herramientas.catalogo_bundles())


def listar_bundles() -> list[dict]:
    """Los bundles del disco (o del indice si lo hay), normalizados. NO abre ninguno.

    Cada fila lleva `nuevo: bool` y `modificado: bool` — se marcan los bundles anadidos o
    cambiados por una actualizacion reciente del juego (ver `estado_novedades`).
    """
    estado = estado_novedades()
    nuevos = set(estado.get("nuevos") or [])
    modificados = set(estado.get("modificados") or [])
    return [dict(_fila(b),
                 nuevo=(b.get("ruta") or "") in nuevos,
                 modificado=(b.get("ruta") or "") in modificados)
            for b in herramientas.catalogo_bundles()]


def tipos_bundle() -> list[dict]:
    """Los tipos reales presentes, con su recuento y su familia. De mas a menos."""
    cuenta: dict[str, int] = {}
    for b in herramientas.catalogo_bundles():
        tipo = b.get("tipo") or "?"
        cuenta[tipo] = cuenta.get(tipo, 0) + 1
    filas = [{"tipo": t, "n": n, "cat": categoria_de_tipo(t)}
             for t, n in sorted(cuenta.items(), key=lambda x: -x[1])]
    return filas


def filtrar_bundles(tipo: str = "", texto: str = "", mb_min: float = 0.0,
                    actor: str = "", traje: str = "", limite: int | None = None) -> list[dict]:
    """Filtra el catalogo. `tipo` exacto; `texto`/`actor`/`traje` por subcadena; `mb_min` por tamano.

    En modo "solo disco" (sin indices) actor y traje no tienen datos y por tanto no filtran nada:
    se comporta como si estuvieran vacios, sin inventar coincidencias.
    """
    texto = (texto or "").strip().lower()
    actor = (actor or "").strip().lower()
    traje = (traje or "").strip().lower()
    tipo = (tipo or "").strip().lower()
    try:
        mb_min = float(mb_min or 0)
    except (TypeError, ValueError):
        mb_min = 0.0
    salida = []
    for b in herramientas.catalogo_bundles():
        if tipo and (b.get("tipo") or "").lower() != tipo:
            continue
        if mb_min and (b.get("mb") or 0) < mb_min:
            continue
        if texto and texto not in (b.get("fichero") or "").lower() \
                and texto not in (b.get("ruta") or "").lower():
            continue
        if actor and not any(actor in (a or "").lower() for a in (b.get("actores") or [])) \
                and not any(actor in (a or "").lower() for a in (b.get("quien") or [])) \
                and actor not in (b.get("fichero") or "").lower():
            continue
        if traje and not any(traje in (t_ or "").lower() for t_ in (b.get("trajes") or [])) \
                and traje not in (b.get("fichero") or "").lower():
            continue
        salida.append(_fila(b))
        if limite and len(salida) >= limite:
            break
    return salida


def ficha_bundle(ruta_rel: str) -> dict:
    """Datos del catalogo de UN bundle (sin abrirlo). Devuelve {} si no esta."""
    for b in herramientas.catalogo_bundles():
        if (b.get("ruta") or "") == ruta_rel:
            f = _fila(b)
            f["actores"] = list(b.get("actores") or [])
            f["trajes"] = list(b.get("trajes") or [])
            f["quien"] = list(b.get("quien") or [])
            f["cuenta"] = dict(b.get("cuenta") or {})
            f["existe"] = herramientas.ruta_bundle_juego(ruta_rel) is not None
            return f
    return {}


# --------------------------------------------------------------------------- 2) inspector
def abrir_bundle(ruta_rel: str, log=None) -> list[dict]:
    """Abre UN bundle con el motor y devuelve sus recursos (nombre, tipo, contenedor, tamano)."""
    return herramientas.listar_bundle(ruta_rel, log)


def exportar_bundle(ruta_rel: str, tipos: str, destino: str | Path, log=None) -> str:
    """Exporta los recursos de `tipos` (p. ej. 'mesh,tex2d') de UN bundle. Devuelve el destino."""
    return str(herramientas.exportar_bundle(ruta_rel, tipos, Path(destino), log))


def carpeta_herramientas() -> str:
    return str(ajustes.carpeta_herramientas())


def ruta_real(ruta_rel: str) -> str | None:
    """Fichero real de un bundle a partir de su ruta relativa, o None si no esta."""
    p = herramientas.ruta_bundle_juego(ruta_rel)
    return str(p) if p else None


# --------------------------------------------------------------------------- 3) buscador
def estado_indice() -> dict:
    return herramientas.indice_recursos_estado()


def tipos_recurso() -> list[dict]:
    cuenta: dict[str, int] = {}
    for _, t_, _ in herramientas.indice_recursos():
        cuenta[t_] = cuenta.get(t_, 0) + 1
    return [{"tipo": t, "n": n} for t, n in sorted(cuenta.items(), key=lambda x: -x[1])]


def buscar_recursos(texto: str = "", tipo: str = "", limite: int = 1000) -> list[dict]:
    """Busca por nombre (subcadena) y tipo en el indice. Si no hay indice devuelve []."""
    texto = (texto or "").strip().lower()
    tipo = (tipo or "").strip()
    salida = []
    for nombre, tipo_r, bundle in herramientas.indice_recursos():
        if tipo and tipo_r != tipo:
            continue
        if texto and texto not in (nombre or "").lower():
            continue
        salida.append({"nombre": nombre, "tipo": tipo_r, "bundle": bundle})
        if limite and len(salida) >= limite:
            break
    return salida


def construir_indice(progreso=None, cancelar=None, log=None, limite=None) -> list[dict]:
    """Construye el indice del buscador (largo: ~29 min con los 16.535). Devuelve los recursos."""
    filas = herramientas.construir_indice_recursos(progreso=progreso, cancelar=cancelar,
                                                   log=log, limite=limite)
    return [{"nombre": n, "tipo": t_, "bundle": b} for n, t_, b in filas]


# --------------------------------------------------------------------------- 4) texturas
def exportar_texturas(ruta_rel: str, destino: str | Path, log=None,
                      tipos: str = "tex2d") -> str:
    """Exporta las texturas (y sprites) de un bundle. Devuelve el destino."""
    return str(herramientas.exportar_bundle(ruta_rel, tipos, Path(destino), log))


def imagenes_de(carpeta: str | Path) -> list[dict]:
    """Las imagenes que hay (recursivo) en una carpeta de extraccion."""
    return [{"ruta": str(p), "nombre": p.name} for p in herramientas.imagenes_de(Path(carpeta))]


def carpeta_extraidas() -> str:
    return str(ajustes.carpeta_herramientas())


# --------------------------------------------------------------------------- 5) video y audio
def listar_media(carpeta: str | Path | None = None) -> dict:
    """Los .usm y .awb del cliente. Cada .usm lleva su distintivo de audio (`sin_dato` si no hay)."""
    return herramientas.listar_media(Path(carpeta) if carpeta else None)


def extraer_video(ruta_usm: str, destino: str | Path, log=None) -> str:
    """`.usm` -> `.mp4` con TODAS las pistas de audio etiquetadas. Devuelve la ruta del MP4."""
    return str(herramientas.extraer_video(ruta_usm, Path(destino), log))


def extraer_audio(ruta_awb: str, destino: str | Path, log=None) -> list[str]:
    """`.awb` -> `.wav`. Devuelve la lista de WAV generados."""
    return [str(p) for p in herramientas.extraer_audio(ruta_awb, Path(destino), log)]


# --------------------------------------------------------------------------- 6) texturas en bloque
def carpeta_texturas() -> Path:
    """Carpeta donde van las texturas (la misma que usa la extraccion de un solo bundle)."""
    return ajustes.carpeta_herramientas() / "textures"


def bulk_bundles(categorias) -> int:
    """Cuantos bundles caen en las categorias pedidas (para la barra de progreso)."""
    por_cat = lote.catalogo_por_categoria()
    return sum(len(por_cat.get(c) or []) for c in categorias)


def bulk_inventario(filtro: str = "") -> dict:
    """Que se puede sacar: por categoria, bundles, texturas y peso estimado."""
    return lote.inventario(filtro)


def bulk_estado(destino: str | Path | None = None) -> dict:
    """Lo que ya hay en el destino y lo que queda apuntado para reanudar."""
    d = Path(destino) if destino else carpeta_texturas()
    m = lote.manifiesto(d)
    return {"destino": str(d), "libre": lote.espacio_libre(d),
            "hechos": len(m.get("hechos") or []), "categorias_hechas": m.get("categorias") or [],
            "carpetas": lote.carpetas_destino(d)}


def bulk_extraer(categorias, destino: str | Path | None = None, filtro: str = "", sprites: bool = True,
                 por_tipo: bool = False, reanudar: bool = True, progreso=None, log=None,
                 cancelar=None, limite: int | None = None) -> dict:
    """Saca las texturas de las categorias pedidas y las ordena en carpetas."""
    return lote.extraer(list(categorias), Path(destino) if destino else carpeta_texturas(),
                        filtro=filtro, sprites=sprites, por_tipo=por_tipo, reanudar=reanudar,
                        progreso=progreso, log=log, cancelar=cancelar, limite=limite)


def bulk_forzar(destino: str | Path | None = None) -> bool:
    """Olvida lo hecho en ese destino: la proxima pasada lo vuelve a mirar todo."""
    lote.olvidar_manifiesto(Path(destino) if destino else carpeta_texturas())
    return True


# --------------------------------------------------------------------------- visor de bust-ups
def bustups_retratos_estado() -> dict:
    """Que hay para el visor: el extracto de retratos (pequeno) o el bulk entero.

    Solo se cuentan los PNG del extracto de retratos: el bulk son 118.000 ficheros y recorrerlo en
    cada arranque para contar seria tirar el tiempo. De el basta saber si esta.
    """
    from . import bustups, lote
    base = Path(carpeta_extraidas())
    retratos = base / bustups.CARPETA_RETRATOS
    bulk = base / "textures"
    png = mb = 0
    try:
        for f in retratos.rglob("*.png"):
            png += 1
            try:
                mb += f.stat().st_size
            except OSError:
                pass
    except OSError:
        pass
    return {"ok": True, "carpeta": str(bustups.carpeta_texturas()),
            "retratos": str(retratos), "retratos_png": png, "retratos_mb": round(mb / 1e6, 1),
            "retratos_listo": lote.retratos_listos(retratos),
            "bulk": str(bulk), "hay_bulk": bulk.is_dir(),
            "hechos": len(lote.manifiesto(retratos).get("hechos") or []),
            "bundles": lote.bundles_de_retratos(),
            "libre": round(lote.espacio_libre(base) / 1e6, 1)}


def bustups_retratos_extraer(destino: str | Path | None = None, progreso=None, log=None,
                             cancelar=None, reanudar: bool = True,
                             limite: int | None = None) -> dict:
    """Saca SOLO las texturas de los retratos de dialogo (unas 170 MB), sin el bulk entero.

    `limite` es SOLO para pruebas: corta la lista de bundles para probar de punta a punta sin
    esperar a que el motor recorra las 44 familias de texturas de interfaz.
    """
    from . import bustups, lote
    base = Path(destino) if destino else Path(carpeta_extraidas()) / bustups.CARPETA_RETRATOS
    return lote.extraer_retratos(base, bustups.prefijos_retratos(), reanudar=reanudar, progreso=progreso,
                                 log=log, cancelar=cancelar, limite=limite)


def bustups_lista(filtro: str = "", carpeta: str | Path | None = None) -> dict:
    """Los bust-ups que se pueden montar, con sus expresiones y cuantas capas tienen."""
    from . import bustups
    datos = bustups.emparejado().get("emparejados") or {}
    idx = bustups.indice(Path(carpeta) if carpeta else None)
    f = (filtro or "").strip().lower()
    salida = []
    for clave, info in sorted(datos.items()):
        # excluir variantes de shader por capa (-eye/-face/-toufa/-mianju): no son bust-ups
        if any(clave.endswith(s) for s in bustups._SUFIJOS_VARIANTE_SHADER):
            continue
        personaje = info.get("personaje") or ""
        ropa = info.get("ropa") or ""
        if f and f not in clave.lower() and f not in personaje.lower() and f not in ropa.lower():
            continue
        salida.append({"id": clave, "personaje": personaje, "ropa": ropa, "nombre_ingles": info.get("nombre_ingles") or personaje, "thumbnail": info.get("thumbnail") or "",
                       "expresiones": bustups.expresiones(clave, idx),
                       "capas": len(bustups.capas_de(clave, idx))})
    return {"ok": True, "n": len(salida), "bustups": salida, "hay_texturas": bool(idx),
            "carpeta": str(bustups.carpeta_texturas() if not carpeta else carpeta)}


def bustups_ver(clave: str, expresion: str | None = None, carpeta: str | Path | None = None,
                shader: bool = False, sin_tinte: bool = False) -> dict:
    """Monta un bust-up y devuelve el PNG (y el detalle de cada capa).

    Con shader=True el retrato lleva el shader de dialogo del juego (el tono calido de las
    conversaciones); se guarda aparte del montaje limpio, para poder alternar.
    """
    from . import bustups
    return bustups.montar(clave, expresion, Path(carpeta) if carpeta else None, shader=shader,
                           sin_tinte=sin_tinte)


def bustups_exportar(clave: str, expresion: str | None = None, destino: str | Path | None = None,
                     carpeta: str | Path | None = None, shader: bool = False,
                     sin_tinte: bool = False) -> dict:
    """Monta el bust-up y deja el PNG en la carpeta de salida (la que ve el usuario)."""
    import shutil

    from . import bustups
    r = bustups.montar(clave, expresion, Path(carpeta) if carpeta else None, shader=shader,
                        sin_tinte=sin_tinte)
    if not r.get("ok"):
        return r
    d = Path(destino) if destino else carpeta_texturas().parent / "bustups"
    d.mkdir(parents=True, exist_ok=True)
    final = d / Path(r["ruta"]).name
    shutil.copyfile(r["ruta"], final)
    r["destino"] = str(final)
    return r


def bustups_texturas(carpeta: str | Path | None = None) -> bool:
    """Si hay texturas donde el visor las busca (para avisar en vez de dar una lista vacia)."""
    from . import bustups
    try:
        return bool(bustups.indice(Path(carpeta) if carpeta else None))
    except OSError:
        return False


# --------------------------------------------------------------------------- textos de la UI web
def textos() -> dict:
    """Los textos de la interfaz nueva: SOLO en ingles.

    La Tools se publica en ingles y no lleva selector de idioma. El diccionario espanol sigue
    existiendo en `idiomas.py` porque lo usa la app de modelos (esa si es bilingue), pero NO se
    sirve a esta ventana: aqui no hay ninguna frase en espanol a la que se pueda llegar.
    """
    return {
        "idioma": "en",
        "en": {k: v for k, v in idiomas.EN.items() if k.startswith("web_")},
    }
