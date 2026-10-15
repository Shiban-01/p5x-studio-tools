"""Indice de bundles: sabe en que fichero vive cada personaje sin recorrer el juego entero.

El juego no trae un catalogo de texto: trae un AssetBundleManifest (en 083/Windows) con la lista
oficial de bundles, y los propios nombres de fichero ya codifican el contenido con el patron
<tipo>_<nombre><hash>.bundle. Cruzando las dos cosas se obtiene, en un par de segundos, un mapa
nombre logico -> fichero, y ese mapa se cachea para las siguientes veces.

El indice se invalida solo: si cambia el numero de bundles o la fecha del mas reciente (lo que pasa
cuando el juego se actualiza o se descarga contenido nuevo) se vuelve a construir.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

import UnityPy

from . import ajustes
from .idiomas import t

# El nombre tiene que ser CODICIOSO (`.+`, no `.+?`). Con el no codicioso, el motor busca el hash
# lo antes posible y como las letras de `pc077` tambien son hexadecimales, cortaba por ahi:
# `atlas_on-pc0776e5c4626` quedaba como nombre `on-p` + hash `c0776e5c4626`, y el indice perdia el
# personaje. Codicioso, retrocede desde el final y el hash son los ultimos ocho caracteres.
PATRON = re.compile(r"^(?P<tipo>[a-z0-9]+)_(?P<nombre>.+)(?P<hash>[0-9a-f]{8,})\.bundle$", re.I)
# las claves del indice ya vienen sin el prefijo de tipo: "pc079_" y no "part_pc079_"
# El codigo del personaje no siempre va delante. El juego nombra muchos bundles con el codigo
# detras (`atlas_on-pc077`, `tl_ef_pc077`, `atlas_inkpc079`), y exigir que empiece por `pc077`
# dejaba fuera justo los atlas, que es donde vive parte del trabajo de textura. Se busca el codigo
# en cualquier posicion, protegido para no confundir `pc077` con `pc0771`.
PATRON_PERSONAJE = re.compile(r"(?P<id>pc\d{3}|n\d{3})(?![0-9])", re.I)

# nombres conocidos, para que la lista se lea en lenguaje humano desde el primer arranque
NOMBRES_CONOCIDOS = {
    "pc079": "Kotone Shiomi",
    "n040": "Theo / Theodore",
}


def ruta_cache() -> Path:
    return ajustes.CACHE / "indice_bundles.json"


def huella_bundles(carpeta: Path) -> str:
    """Resumen barato del estado de la carpeta: cuantos bundles hay y cuando se toco el ultimo."""
    n = 0
    ultimo = 0.0
    for raiz, _, ficheros in os.walk(carpeta):
        for f in ficheros:
            if f.endswith(".bundle"):
                n += 1
                try:
                    m = os.path.getmtime(os.path.join(raiz, f))
                    if m > ultimo:
                        ultimo = m
                except OSError:
                    pass
    return "%d:%.0f" % (n, ultimo)


def _nombres_del_manifiesto(ruta: Path) -> list[str]:
    """Lee el AssetBundleManifest. UnityPy lo expone a veces como lista de tuplas (id, nombre).

    Ojo: el manifiesto es en si un bundle y el juego no le escribe la version de Unity dentro, asi
    que si no se fija antes, UnityPy se niega a abrirlo y la lista sale vacia sin dar error.
    """
    from . import clave
    UnityPy.config.FALLBACK_UNITY_VERSION = clave.version_unity()
    env = UnityPy.load(str(ruta))
    for obj in env.objects:
        if obj.type.name != "AssetBundleManifest":
            continue
        datos = obj.read()
        crudo = getattr(datos, "m_AssetBundleNames", None)
        if crudo is None:
            for campo in dir(datos):
                if "bundle" in campo.lower() and "name" in campo.lower():
                    crudo = getattr(datos, campo)
                    break
        if crudo is None:
            continue
        salida = []
        for x in crudo:
            if isinstance(x, (tuple, list)) and len(x) == 2:
                salida.append(str(x[1]))
            else:
                salida.append(str(x))
        return salida
    return []


def construir_indice(progreso=None) -> dict:
    """Reconstruye el indice leyendo el manifiesto y cruzandolo con los ficheros en disco."""
    def avisa(texto):
        if progreso:
            progreso(texto)

    carpeta = ajustes.carpeta_bundles()
    if not carpeta:
        raise RuntimeError(t("ind_err_carpeta"))

    avisa(t("ind_lista_oficial"))
    manifiesto = ajustes.detectar_juego() / ajustes.SUBRUTA_MANIFIESTO
    nombres = _nombres_del_manifiesto(manifiesto) if manifiesto.is_file() else []
    avisa(t("ind_n_bundles", len(nombres)))

    avisa(t("ind_recorriendo"))
    en_disco: dict[str, str] = {}
    for raiz, _, ficheros in os.walk(carpeta):
        for f in ficheros:
            if f.endswith(".bundle"):
                en_disco[f] = os.path.relpath(os.path.join(raiz, f), carpeta)
    avisa(t("ind_n_ficheros", len(en_disco)))

    avisa(t("ind_mapa"))
    por_nombre: dict[str, list[str]] = {}
    for fichero, rel in en_disco.items():
        m = PATRON.match(fichero)
        if not m:
            continue
        por_nombre.setdefault(m.group("nombre").lower(), []).append(rel)
    for v in por_nombre.values():
        v.sort()
    avisa(t("ind_n_nombres", len(por_nombre)))

    datos = {
        "version": ajustes.VERSION,
        "huella": huella_bundles(carpeta),
        "carpeta_bundles": str(carpeta),
        "bundles_en_manifiesto": nombres,
        "en_disco": en_disco,
        "por_nombre": por_nombre,
    }
    ruta_cache().parent.mkdir(parents=True, exist_ok=True)
    ruta_cache().write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
    avisa(t("ind_guardado", ruta_cache()))
    return datos


def cargar_indice(progreso=None, forzar: bool = False) -> dict:
    """Devuelve el indice, reconstruyendolo solo si no existe o si el juego cambio."""
    carpeta = ajustes.carpeta_bundles()
    if not carpeta:
        raise RuntimeError(t("ind_err_carpeta"))
    actual = huella_bundles(carpeta)
    if not forzar and ruta_cache().exists():
        try:
            datos = json.loads(ruta_cache().read_text(encoding="utf-8"))
            if datos.get("huella") == actual:
                return datos
            if progreso:
                progreso(t("ind_reconstruye"))
        except Exception:
            pass
    return construir_indice(progreso)


def _ficheros_de(datos: dict, nombre_logico: str) -> list[str]:
    clave = nombre_logico.lower()
    if clave in datos["por_nombre"]:
        return datos["por_nombre"][clave]
    # el nombre logico puede venir con sufijos (_01, _02...): se busca por prefijo
    salida = []
    for k, v in datos["por_nombre"].items():
        if k.startswith(clave):
            salida.extend(v)
    return sorted(set(salida))


def buscar(texto: str, datos: dict) -> list[dict]:
    """Busca por nombre logico o por id de personaje y devuelve los ficheros candidatos."""
    texto = (texto or "").strip().lower()
    if not texto:
        return []
    resultados = []
    for nombre_logico in sorted(datos["por_nombre"]):
        if texto in nombre_logico:
            resultados.append({
                "nombre": nombre_logico,
                "ficheros": datos["por_nombre"][nombre_logico],
            })
    return resultados


def personajes(datos: dict) -> list[dict]:
    """Lista de personajes con al menos una parte, agrupada por id (pc079, n040...)."""
    agrupados: dict[str, dict] = {}
    for nombre_logico, ficheros in datos["por_nombre"].items():
        m = PATRON_PERSONAJE.search(nombre_logico)
        if not m:
            continue
        # las texturas de interfaz no son del modelo: llenarian la carpeta de ruido
        bajo = nombre_logico.lower()
        if bajo.startswith("uitex") or bajo.startswith("ui_"):
            continue
        pid = m.group("id").lower()
        entrada = agrupados.setdefault(pid, {"id": pid, "nombre": NOMBRES_CONOCIDOS.get(pid, ""),
                                             "ficheros": [], "tipos": set()})
        entrada["ficheros"].extend(ficheros)
        for f in ficheros:
            entrada["tipos"].add(Path(f).name.split("_", 1)[0])
    salida = []
    for pid, e in agrupados.items():
        e["ficheros"] = sorted(set(e["ficheros"]))
        e["tipos"] = sorted(e["tipos"])
        e["etiqueta"] = ("%s - %s" % (pid.upper(), e["nombre"])) if e["nombre"] else pid.upper()
        salida.append(e)
    salida.sort(key=lambda x: x["id"])
    return salida