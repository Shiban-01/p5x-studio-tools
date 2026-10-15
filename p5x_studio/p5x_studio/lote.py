"""Bulk de texturas: saca TODAS las del juego y las ordena en carpetas por categoria.

QUE HACE
--------
Coge los bundles por FAMILIAS (con enlaces duros, sin copiar los 72 GB), le pide al motor que
exporte las texturas de cada familia en UNA pasada (`-m export -t tex2d,sprite -g fileName`) y mueve
cada PNG a `<destino>/<Categoria>/<conjunto>/`. Va por lotes de bundles y apunta lo hecho, asi que
si se corta a mitad se puede relanzar y sigue donde estaba.

POR QUE ASI (medido, no supuesto)
---------------------------------
- Clasificar por el NOMBRE de la textura no sirve: son pinyin y abreviaturas (`yjs_jz_912_nmas`,
  `sb_niudan`, `wonder_normal_13_bc`). La FAMILIA del bundle SI es fiable, sobre los 16.535:
  `uitex`=interfaz, `scn`=escenarios, `part`=particulas, `role`=personajes, `efx`=efectos,
  `roletiny`=iconos, `shared`/`tl`=compartido.
- Los personajes (`PC0xx`) estan REPARTIDOS entre familias (3.409 en `uitex`, 841 en `part`, 414 en
  `atlas`, y solo 43 en `role`), asi que "todo lo de un personaje" se saca con el FILTRO de texto
  (`PC079`), no con una categoria.
- El motor acepta una CARPETA como entrada, y con `-g fileName` deja cada textura bajo su bundle de
  origen: eso es lo que permite saber de donde viene cada PNG sin abrir los bundles de uno en uno.
- Enlaces duros = cero copia. Si el temporal y el juego estan en discos distintos, se copia y se
  borra al terminar cada lote.
- Coste real medido: 0,69 s y 4,24 MB por bundle en la muestra -> 118.425 texturas ~ 36 GB y ~3 h.
"""
from __future__ import annotations

import json
import os
import re
import shutil
from collections import Counter, defaultdict
from pathlib import Path

from . import ajustes, herramientas
from .idiomas import t

# --------------------------------------------------------------------------- categorias
# El orden importa: es el que se ensena en la ventana y el que siguen las carpetas.
CATEGORIAS = (
    {"id": "ui", "label": "UI", "familias": ("uitex", "ui", "atlas", "uispecial", "i18n")},
    {"id": "scenery", "label": "Scenery", "familias": ("scn",)},
    {"id": "characters", "label": "Characters", "familias": ("role", "char")},
    {"id": "icons", "label": "Character icons", "familias": ("roletiny", "spinetest", "animchartiny")},
    {"id": "particles", "label": "Particles", "familias": ("part",)},
    {"id": "effects", "label": "Effects", "familias": ("efx", "postprocess")},
    {"id": "shared", "label": "Shared", "familias": ("shared", "tl", "tlm", "program", "ring", "mc")},
    {"id": "other", "label": "Other", "familias": ()},   # lo que no sea de las anteriores
)

# Lo que hay DENTRO de cada familia, medido con el censo de los 16.535 bundles (3-oct):
# (texturas y sprites, MB que declara el motor). Sirve para estimar ANTES de arrancar, sin tener que
# abrir nada. Si el juego se actualiza, siguen valiendo como orden de magnitud.
_FAMILIAS_MEDIDAS = {
    "uitex": (53256, 22036.4), "shared": (20443, 44423.0), "atlas": (15263, 717.2),
    "scn": (9058, 13916.1), "part": (6121, 26982.3), "role": (4302, 15020.4),
    "efx": (3787, 1510.7), "ui": (2622, 1490.3), "roletiny": (2145, 6554.0),
    "tl": (826, 864.0), "spinetest": (301, 315.0), "program": (186, 101.8),
    "char": (101, 139.9), "uispecial": (9, 8.3), "ring": (4, 5.6), "postprocess": (1, 1.4),
}
# Factor medido entre lo que declara el motor y el PNG que acaba en disco: se exportaron 28 bundles
# de verdad (178 PNG, 118,7 MB) y el censo declaraba 441,8 MB para ellos -> 0,27x.
_FACTOR_PNG = 0.27

# Tipos de mapa por el sufijo del nombre (los que se ven en el juego, contados sobre los 118.425).
_TIPOS_MAPA = (
    ("Color", ("bc", "bcm", "darkcolor", "diffuse", "albedo")),
    ("Normal", ("nm", "nmas", "normal")),
    ("Emission", ("em", "emission")),
    ("Lightmap", ("light", "lightmap")),
    ("Shadow", ("shadow",)),
    ("Mask", ("mask",)),
    ("Packed", ("pk", "packed")),
    ("Stroke", ("stroke",)),
    ("Data", ("staticpoint",)),
)

# Cuantos bundles se le pasan al motor de una vez. Lote pequeno = progreso fino y se puede cancelar
# sin perder casi nada; el motor, ademas, paraleliza dentro de cada lote.
TAMANO_LOTE = 120


def _familias_de(rel: str) -> str:
    """Familia de un bundle por su nombre de fichero: `scn_...` -> `scn`."""
    nombre = rel.replace("\\", "/").rsplit("/", 1)[-1]
    return nombre.split("_")[0].split(".")[0].lower()


def categoria_de(rel: str) -> str:
    """Categoria (id) a la que va un bundle."""
    fam = _familias_de(rel)
    for c in CATEGORIAS:
        if fam in c["familias"]:
            return c["id"]
    return "other"


def etiqueta(cat: str) -> str:
    for c in CATEGORIAS:
        if c["id"] == cat:
            return c["label"]
    return cat


def nombre_conjunto(rel: str) -> str:
    """Carpeta "conjunto" de un bundle: su nombre sin el hash del final.

    El hash mide entre 7 y 13 caracteres y a veces empieza por una letra que SI es del nombre
    (`anim_battle` + `726bfea9`), asi que no vale cortar un numero fijo: se quitan 8 como maximo y
    solo si el tramo hex final mide 7 o mas. Lo que quede muy corto se deja entero, y si el nombre
    se queda vacio se usa el original: el nombre feo es mejor que una carpeta sin nombre.
    """
    nombre = rel.replace("\\", "/").rsplit("/", 1)[-1]
    if nombre.lower().endswith(".bundle"):
        nombre = nombre[: -len(".bundle")]
    m = re.search(r"[0-9a-f]+$", nombre)
    if m and len(m.group(0)) >= 7:
        corte = nombre[: len(nombre) - min(len(m.group(0)), 8)]
        if len(corte.strip("_- ")) >= 3:
            nombre = corte
    nombre = re.sub(r"[-_]{2,}", "_", nombre).strip("_- ")
    return nombre or rel.replace("\\", "/").rsplit("/", 1)[-1][:-len(".bundle")]


def tipo_mapa(nombre: str) -> str:
    """Tipo de mapa por el sufijo del nombre (`_bc` -> Color, `_nmas` -> Normal...)."""
    suf = re.split(r"[_\-]", nombre)[-1].lower() if re.search(r"[_\-]", nombre) else ""
    if not suf:
        return "Other"
    for etiqueta_mapa, sufijos in _TIPOS_MAPA:
        if suf in sufijos:
            return etiqueta_mapa
    for etiqueta_mapa, sufijos in _TIPOS_MAPA:
        if any(suf.startswith(s) for s in sufijos):
            return etiqueta_mapa
    return "Other"


# --------------------------------------------------------------------------- inventario
def catalogo_por_categoria(filtro: str = "") -> dict[str, list[str]]:
    """Bundles del juego (relativos) agrupados por categoria, en el orden de `CATEGORIAS`."""
    fuera: dict[str, list[str]] = {c["id"]: [] for c in CATEGORIAS}
    for b in herramientas.catalogo_bundles():
        fuera[categoria_de(b["ruta"])].append(b["ruta"])
    return fuera


def _estimado(familias) -> tuple[int, float]:
    tex = mb = 0.0
    for fam in familias:
        n, m = _FAMILIAS_MEDIDAS.get(fam, (0, 0.0))
        tex += n
        mb += m
    return tex, mb * _FACTOR_PNG


def inventario(filtro: str = "") -> dict:
    """Que se puede sacar: por categoria, bundles / texturas / peso estimado.

    Los bundles son exactos (salen del catalogo de ficheros del juego). Las texturas y el peso son
    los medidos en el censo de esta version del juego: sirven para decidir antes de arrancar. Con un
    filtro de texto puesto no se pueden saber de antemano, asi que se devuelven a None.
    """
    agrupados = catalogo_por_categoria()
    salida = []
    total_tex = total_mb = 0.0
    for c in CATEGORIAS:
        bundles = agrupados.get(c["id"]) or []
        tex, mb = (None, None) if filtro else _estimado(c["familias"])
        salida.append({"id": c["id"], "label": c["label"], "bundles": len(bundles),
                       "texturas": tex, "mb": None if mb is None else round(mb, 1)})
        if not filtro and c["id"] != "other":
            total_tex += tex or 0
            total_mb += mb or 0
    # la bolsa "other" no se estima: es lo que sobra, y ahi casi no hay texturas
    otros = agrupados.get("other") or []
    return {"categorias": salida,
            "total_bundles": sum(len(v) for v in agrupados.values()),
            "total_texturas": None if filtro else int(total_tex),
            "total_mb": None if filtro else round(total_mb, 1),
            "filtro": filtro,
            "otros_bundles": len(otros)}


def espacio_libre(destino: Path | str) -> int:
    """Bytes libres en el disco del destino (0 si no se puede mirar)."""
    p = Path(destino)
    while not p.exists() and p.parent != p:
        p = p.parent
    try:
        return shutil.disk_usage(str(p)).free
    except OSError:
        return 0


# --------------------------------------------------------------------------- manifiesto
def _manifiesto_ruta() -> Path:
    return ajustes.CACHE / "work" / "bulk_texturas.json"


def manifiesto(destino: Path | str | None = None) -> dict:
    """Lo ya hecho, por carpeta destino (así reanudar en otro sitio no se salta nada)."""
    try:
        datos = json.loads(_manifiesto_ruta().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        datos = {}
    if destino is None:
        return datos
    return datos.get(str(Path(destino).resolve()), {}) or {}


def _manifiesto_guardar(datos: dict) -> None:
    ruta = _manifiesto_ruta()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    try:
        ruta.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass


def olvidar_manifiesto(destino: Path | str) -> None:
    """Tira lo apuntado para un destino: la proxima pasada lo vuelve a mirar todo."""
    datos = manifiesto()
    datos.pop(str(Path(destino).resolve()), None)
    _manifiesto_guardar(datos)


def _apuntar(destino: Path, hechos) -> None:
    datos = manifiesto()
    clave = str(Path(destino).resolve())
    entrada = datos.setdefault(clave, {"hechos": [], "categorias": []})
    vistos = set(entrada["hechos"])
    vistos.update(hechos)
    entrada["hechos"] = sorted(vistos)
    _manifiesto_guardar(datos)      # sin esto no se apuntaba nada y reanudar no servia de nada


# --------------------------------------------------------------------------- enlaces duros
def enlazar(bundles: list[str], carpeta: Path) -> int:
    """Deja los bundles en `carpeta` con enlaces duros (sin copiar). Devuelve cuantos enlazo.

    Si el enlace no se puede (otro volumen, sistema de ficheros sin soporte), se copia. La copia se
    borra con la carpeta del lote al terminar, asi que no se acumula.
    """
    carpeta.mkdir(parents=True, exist_ok=True)
    enlazados = 0
    for rel in bundles:
        origen = herramientas.ruta_bundle_juego(rel)
        if not origen or not origen.is_file():
            continue
        destino = carpeta / origen.name
        if destino.exists():
            enlazados += 1
            continue
        try:
            os.link(origen, destino)
        except OSError:
            try:
                shutil.copy2(origen, destino)
            except OSError:
                continue
        enlazados += 1
    return enlazados


# --------------------------------------------------------------------------- motor
def exportar_lote(carpeta_entrada: Path, carpeta_salida: Path, filtro: str = "",
                  sprites: bool = True, log=None) -> None:
    """Una pasada del motor: exporta las texturas de una carpeta entera de bundles."""
    tipos = "tex2d,sprite" if sprites else "tex2d"
    orden = [str(carpeta_entrada), "-m", "export", "-t", tipos, "-g", "fileName",
             "-o", str(carpeta_salida), "--log-level", "Error", "-r",
             "--unity-version", herramientas.UNITY]
    if filtro:
        orden += ["--filter-by-text", filtro]
    if log:
        log(t("bulk_log_pasada", carpeta_entrada.name, len(list(carpeta_entrada.glob("*.bundle")))))
    r = herramientas._ejecutar_motor(orden, timeout=6 * 3600)
    if r.returncode != 0:
        raise RuntimeError(t("bulk_err_motor")
                           % ((r.stdout or "") + (r.stderr or ""))[-600:])


# --------------------------------------------------------------------------- organizar
def _bundle_de_carpeta(nombre_carpeta: str) -> str:
    """`role__weiyang40b9bdc8.bundle_export` -> `role__weiyang40b9bdc8.bundle`.

    El motor llama a la carpeta de cada bundle `<nombre>.bundle_export`, asi que al quitar `_export`
    YA vuelve a quedar el `.bundle`. Poner un `.bundle` de mas dejaba nombres como
    `role__weiyang40b9bdc8.bundle.bundle` (y de ahi salian carpetas con `.bundle` dentro).
    """
    nombre = nombre_carpeta
    if nombre.endswith("_export"):
        nombre = nombre[: -len("_export")]
    if not nombre.lower().endswith(".bundle"):
        nombre += ".bundle"
    return nombre


def organizar(carpeta_salida: Path, destino: Path, categoria: str, por_tipo: bool = False,
              solo=None) -> int:
    """Mueve los PNG de un lote a `<destino>/<Categoria>/<conjunto>[/<Tipo>]/`.

    Devuelve cuantos movio. Si el fichero ya esta y mide lo mismo, se salta (eso es lo que hace que
    relanzar no repita trabajo); si ya esta pero mide distinto, se guarda con `_2`, `_3`... para no
    tirar nada.

    `solo` es un filtro por nombre (los prefijos de los retratos de dialogo): lo que no encaja se
    BORRA en vez de guardarse. Es lo que hace que el extracto de retratos acabe en ~170 MB y no en
    los 10 GB que ocupa la familia entera de texturas de interfaz.
    """
    movidos = 0
    base = destino / etiqueta(categoria)
    for png in sorted(carpeta_salida.rglob("*.png")):
        if solo and not es_de_retrato(png.name, solo):
            try:
                png.unlink()
            except OSError:
                pass
            continue
        rel = png.relative_to(carpeta_salida)
        if len(rel.parts) < 2:
            conjunto = "suelto"
        else:
            bundle = _bundle_de_carpeta(rel.parts[0])
            # solo lo que es de ESTA categoria: si en la salida del motor hubiera algo de otra
            # (lote mal preparado, un resto de la pasada anterior), se queda donde esta en vez de
            # acabar en la carpeta equivocada
            if categoria_de(bundle) != categoria:
                continue
            conjunto = nombre_conjunto(bundle)
        final = base / conjunto
        if por_tipo:
            final = final / tipo_mapa(png.stem)
        final.mkdir(parents=True, exist_ok=True)
        objeto = final / png.name
        if objeto.exists():
            try:
                if objeto.stat().st_size == png.stat().st_size:
                    png.unlink()
                    continue
            except OSError:
                pass
            n = 2
            while (final / ("%s_%d%s" % (png.stem, n, png.suffix))).exists() and n < 500:
                n += 1
            objeto = final / ("%s_%d%s" % (png.stem, n, png.suffix))
        try:
            shutil.move(str(png), str(objeto))
            movidos += 1
        except OSError:
            pass
    return movidos


# --------------------------------------------------------------------------- retratos de dialogo
# El visor de bust-ups monta los retratos de dialogo. TODO lo que usa (los lienzos grandes, los
# recortes de ojos y boca, el pelo, la ropa, el contorno) vive en los bundles `uitex_*`, asi que se
# puede sacar sin pasar por el bulk entero: son ~170 MB frente a los 63 GB del bulk.
FAMILIA_RETRATOS = "uitex"
LOTE_RETRATOS = 40      # mas corto que el del bulk: el pico de disco es una sola pasada de export


def bundles_de_retratos() -> list[str]:
    """Bundles donde viven las texturas de los retratos de dialogo.

    El mapa de bust-ups apunta el bundle de cada capa (se midio al emparejar), asi que la extraccion
    va a tiro hecho: 80 bundles, no los 1.506 de texturas de interfaz. Si el mapa no los trajera (un
    mapa viejo), se cae a la familia `uitex` entera, que los contiene todos.
    """
    from . import bustups

    medidos = bustups.bundles_retratos()
    if medidos:
        return sorted(medidos)
    vistos = set()
    for info in (bustups.emparejado().get("emparejados") or {}).values():
        for b in (info.get("bundles") or []):
            if isinstance(b, str) and b:
                vistos.add(b)
        for capa in (info.get("capas") or {}).values():
            if isinstance(capa, dict) and capa.get("bundle"):
                vistos.add(capa["bundle"])
    if vistos:
        return sorted(vistos)
    return [b["ruta"] for b in herramientas.catalogo_bundles()
            if _familias_de(b["ruta"]) == FAMILIA_RETRATOS]


def es_de_retrato(nombre: str, prefijos) -> bool:
    """Si un PNG es de algun bust-up. El motor recorta los sprites y deja `..._#NN`, que no cuenta.

    Es lo que decide que se queda el extracto de retratos: el nombre del asset manda, no el fichero.
    """
    tallo = re.sub(r"_#\d+$", "", Path(nombre).stem)
    return tallo.startswith(tuple(prefijos))


def extraer_retratos(destino: Path | str, prefijos, sprites: bool = True, reanudar: bool = True,
                     progreso=None, log=None, cancelar=None, limite: int | None = None) -> dict:
    """Saca SOLO las texturas de los retratos de dialogo: el visor queda autosuficiente.

    Es el mismo motor que el bulk (mismo reanudar, misma cancelacion, mismo progreso), pero en lotes
    cortos y tirando los PNG que no son de ningun bust-up ANTES de ordenarlos: si no, el disco
    tendria que aguantar los 10 GB de la familia `uitex` entera a mitad de camino.

    `limite` es SOLO para pruebas: corta la lista de bundles.
    """
    destino = Path(destino)
    destino.mkdir(parents=True, exist_ok=True)
    bundles = bundles_de_retratos()
    if limite:
        bundles = bundles[:limite]
    total = len(bundles)
    hechos = ficheros = 0
    fallos: list[str] = []
    tmp = ajustes.CACHE / "work" / "retratos"
    ya = set(manifiesto(destino).get("hechos") or []) if reanudar else set()

    if log:
        log(t("retr_log_arranca", total))

    for i in range(0, total, LOTE_RETRATOS):
        lote = bundles[i:i + LOTE_RETRATOS]
        if cancelar and cancelar():
            if log:
                log(t("bulk_log_cancelado", hechos, total))
            return {"bundles": hechos, "total": total, "ficheros": ficheros, "fallos": fallos,
                    "cancelado": True}
        if reanudar and all(b in ya for b in lote):
            hechos += len(lote)
            if progreso:
                progreso(hechos, total)
            continue
        entrada = tmp / "entrada"
        salida = tmp / "salida"
        shutil.rmtree(entrada, ignore_errors=True)
        shutil.rmtree(salida, ignore_errors=True)
        try:
            if not enlazar(lote, entrada):
                fallos.append(t("bulk_err_lote_vacio", "UI"))
                hechos += len(lote)
                continue
            exportar_lote(entrada, salida, sprites=sprites, log=log)
            ficheros += organizar(salida, destino, "ui", solo=prefijos)
            _apuntar(destino, lote)
            ya.update(lote)
            if log:
                log(t("retr_log_lote", hechos + len(lote), total, ficheros))
        except Exception as e:  # noqa: BLE001
            fallos.append("UI: %s" % e)
            if log:
                log(t("bulk_log_fallo", "UI", e))
        finally:
            shutil.rmtree(entrada, ignore_errors=True)
            shutil.rmtree(salida, ignore_errors=True)
        hechos += len(lote)
        if progreso:
            progreso(hechos, total)

    # la marca de "completo" solo la deja una pasada entera y sin fallos (y nunca la de prueba)
    # el recuento se mide sobre la carpeta: al reanudar, los lotes ya hechos no vuelven a contar
    try:
        ficheros = sum(1 for _ in destino.rglob("*.png"))
    except OSError:
        pass
    if not fallos and not limite:
        marcar_retratos_listos(destino, ficheros)
    return {"bundles": hechos, "total": total, "ficheros": ficheros, "fallos": fallos,
            "cancelado": False}


def marcar_retratos_listos(destino: Path | str, ficheros: int = 0) -> None:
    """Deja la marca de que el extracto de retratos esta COMPLETO.

    Importa: con media extraccion hecha, el visor tiene que seguir usando el bulk (que esta entero) en
    vez de una carpeta a medias. La marca solo la escribe una pasada terminada y sin fallos.
    """
    try:
        (Path(destino) / "_listo.json").write_text(
            json.dumps({"completo": True, "png": ficheros}, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass


def retratos_listos(destino: Path | str) -> bool:
    """Si el extracto de retratos de esa carpeta esta completo."""
    return (Path(destino) / "_listo.json").is_file()


# --------------------------------------------------------------------------- el trabajo
def extraer(categorias: list[str], destino: Path | str, filtro: str = "", sprites: bool = True,
            por_tipo: bool = False, reanudar: bool = True, progreso=None, log=None,
            cancelar=None, limite: int | None = None) -> dict:
    """Saca las texturas de las categorias pedidas. Devuelve el resumen.

    `progreso(hechos, total)` va en BUNDLES. `cancelar()` devuelve True para parar; lo ya exportado
    queda apuntado, asi que volver a llamar continua donde se quedo. `limite` es SOLO para pruebas:
    corta los bundles por categoria (como el `limite` del indice) para poder probar de punta a punta
    sin lanzar las tres horas.
    """
    destino = Path(destino)
    destino.mkdir(parents=True, exist_ok=True)
    agrupados = catalogo_por_categoria(filtro)
    elegidas = [c for c in categorias if c in agrupados]
    if not elegidas:
        raise RuntimeError(t("bulk_err_sin_categoria"))

    if limite:
        agrupados = {k: v[:limite] for k, v in agrupados.items()}
    total = sum(len(agrupados[c]) for c in elegidas)
    hechos = 0
    ficheros = 0
    fallos: list[str] = []
    tmp = ajustes.CACHE / "work" / "bulk"
    ya = set(manifiesto(destino).get("hechos") or []) if reanudar else set()

    # margen antes de llenar el disco: si no cabe, mejor saberlo AHORA que en la hora dos
    if not filtro:
        inv = inventario("")
        pedido = sum((c["mb"] or 0) for c in inv["categorias"] if c["id"] in elegidas)
        libre = espacio_libre(destino) / 1e6
        if pedido and libre and libre < pedido * 1.15:
            raise RuntimeError(t("bulk_err_espacio", round(pedido * 1.15), round(libre)))

    if log:
        log(t("bulk_log_arranca", total, ", ".join(etiqueta(c) for c in elegidas)))

    for cat in elegidas:
        pendientes = agrupados[cat]
        for i in range(0, len(pendientes), TAMANO_LOTE):
            lote = pendientes[i:i + TAMANO_LOTE]
            if cancelar and cancelar():
                if log:
                    log(t("bulk_log_cancelado", hechos, total))
                return {"bundles": hechos, "total": total, "ficheros": ficheros,
                        "fallos": fallos, "cancelado": True}
            if reanudar and all(b in ya for b in lote):
                hechos += len(lote)
                if progreso:
                    progreso(hechos, total)
                continue
            entrada = tmp / "entrada"
            salida = tmp / "salida"
            shutil.rmtree(entrada, ignore_errors=True)
            shutil.rmtree(salida, ignore_errors=True)
            try:
                enlazados = enlazar(lote, entrada)
                if not enlazados:
                    fallos.append(t("bulk_err_lote_vacio", etiqueta(cat)))
                    hechos += len(lote)
                    continue
                exportar_lote(entrada, salida, filtro=filtro, sprites=sprites, log=log)
                n = organizar(salida, destino, cat, por_tipo=por_tipo)
                ficheros += n
                _apuntar(destino, lote)
                ya.update(lote)
                if log:
                    log(t("bulk_log_lote", etiqueta(cat), hechos + len(lote), total, n))
            except Exception as e:  # noqa: BLE001
                fallos.append("%s: %s" % (etiqueta(cat), e))
                if log:
                    log(t("bulk_log_fallo", etiqueta(cat), e))
            finally:
                shutil.rmtree(entrada, ignore_errors=True)
                shutil.rmtree(salida, ignore_errors=True)
            hechos += len(lote)
            if progreso:
                progreso(hechos, total)

    datos = manifiesto()
    clave = str(destino.resolve())
    entradas = datos.setdefault(clave, {"hechos": [], "categorias": []})
    entradas["categorias"] = sorted(set(entradas["categorias"] + elegidas))
    _manifiesto_guardar(datos)
    if log:
        log(t("bulk_log_fin", ficheros))
    return {"bundles": hechos, "total": total, "ficheros": ficheros, "fallos": fallos,
            "cancelado": False}


def carpetas_destino(destino: Path | str, categorias=None) -> list[dict]:
    """Que hay ya en el destino, por categoria: ficheros y MB (para ensenarlo al abrir)."""
    destino = Path(destino)
    salida = []
    for c in CATEGORIAS:
        if categorias and c["id"] not in categorias:
            continue
        d = destino / c["label"]
        if not d.is_dir():
            salida.append({"id": c["id"], "label": c["label"], "ficheros": 0, "mb": 0.0})
            continue
        n = mb = 0
        for f in d.rglob("*"):
            if f.is_file():
                n += 1
                try:
                    mb += f.stat().st_size
                except OSError:
                    pass
        salida.append({"id": c["id"], "label": c["label"], "ficheros": n,
                       "mb": round(mb / 1e6, 1)})
    return salida


def por_tipo_disponibles() -> list[str]:
    """Los nombres de carpeta que usa la opcion "separar por tipo de mapa"."""
    return [e for e, _ in _TIPOS_MAPA] + ["Other"]