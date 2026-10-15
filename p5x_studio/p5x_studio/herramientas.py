"""Herramientas de P5X Studio: explorar, inspeccionar y extraer cualquier cosa del juego.

La pestana de extraccion saca modelos de personaje. Esta pestana es para todo lo demas: mirar
los 16.535 bundles sin abrir nada (con los indices ya construidos), abrir UNO con el motor y ver
que lleva dentro, buscar un recurso por su nombre en TODO el juego, ver las imagenes que salgan
de una extraccion y sacar los videos y la musica del cliente.

Todo el texto visible sale del modulo `idiomas`; al crear cada widget se registra una funcion que
le vuelve a poner el texto, y cambiar de idioma recorre ese registro sin reconstruir la pestana.

Todo lo pesado (el motor, wannacri, vgmstream, ffmpeg) va en un hilo aparte y se comunica con la
ventana por una cola, para que la interfaz no se congele nunca. Las herramientas externas se
BUSCAN; si falta alguna, se dice con claridad en vez de fallar, y nunca se instala nada solo.

Modulo independiente: no importa `gui` (gui lo importa a el), asi que no puede haber ciclo.
"""
from __future__ import annotations

import json
import hashlib
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import wave
import xml.etree.ElementTree as ET
from array import array
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import ajustes, dependencias, idiomas, trajes
from .idiomas import t

COLOR_FONDO = "#1f2024"
COLOR_PANEL = "#2a2c32"
COLOR_TEXTO = "#e8e8ee"
COLOR_SUAVE = "#a8a8b4"
COLOR_ACENTO = "#e04a5a"
COLOR_OK = "#5fbf7f"
COLOR_AVISO = "#e0a94a"

# version de Unity del juego: el motor la necesita porque los bundles no la traen dentro
UNITY = "2022.3.49f1"
# clave decimal de los .usm (valida en el cliente global, no ha cambiado desde la OBT)
CLAVE_USM = "1729401234202"

# extensiones de imagen que el visor sabe abrir
EXT_IMAGEN = (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tga", ".webp")


# --------------------------------------------------------------------------- rutas y datos
def _raiz_datos() -> Path:
    """La carpeta `_dl` con los indices del juego (empaquetada si el .exe esta congelado)."""
    if getattr(sys, "frozen", False):
        emp = getattr(sys, "_MEIPASS", None)
        if emp and (Path(emp) / "_dl").is_dir():
            return Path(emp) / "_dl"
        return Path(sys.executable).resolve().parent.parent / "_dl"
    return Path(__file__).resolve().parent.parent.parent / "_dl"


def _leer_json(relativo: str) -> dict:
    # Version publica (solo herramientas): no se leen indices en absoluto. El interruptor lo fija
    # `arranque_tools.py`, y garantiza que todo sale de la carpeta del juego (nada de indices
    # empaquetados ni de restos de la carpeta `_dl` del equipo donde se construyo).
    if os.environ.get("P5X_STUDIO_SIN_INDICES"):
        return {}
    ruta = _raiz_datos() / relativo
    if not ruta.is_file():
        return {}
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except Exception:
        return {}


def indice_ficheros() -> dict:
    return _leer_json("indice_juego/indice_ficheros.json")


def indice_assets() -> dict:
    return _leer_json("indice_assets/assets.json")


_CATALOGO: list[dict] | None = None


def olvidar_catalogo() -> None:
    """Tira lo memorizado (al cambiar de carpeta de juego los bundles son otros)."""
    global _CATALOGO
    _CATALOGO = None


def _bundles_del_disco() -> list[dict]:
    """Los bundles tal y como estan en la carpeta del juego, SIN depender de ningun indice.

    El nombre del fichero es el nombre del bundle (`110/shared_...bundle`), asi que basta con
    recorrer la carpeta. El tipo se deduce del prefijo (`part_`), y el tamano del propio fichero.
    Lo que solo sabia el indice (actor, traje, mallas, texturas, contenido) queda vacio y la
    interfaz lo muestra como "-"; nada se inventa.
    """
    carpeta = ajustes.carpeta_bundles()
    if not carpeta:
        return []
    salida: list[dict] = []
    try:
        for p in sorted(carpeta.rglob("*.bundle")):
            if not p.is_file():
                continue
            try:
                rel = p.relative_to(carpeta).as_posix()
            except ValueError:
                continue
            trozos = rel.split("/")
            try:
                mb = p.stat().st_size / 1e6
            except OSError:
                mb = 0.0
            salida.append({
                "ruta": rel,
                "carpeta": "/".join(trozos[:-1]),
                "fichero": p.name,
                "tipo": p.name.split("_", 1)[0].lower(),
                "que_es": "", "nombre": p.name, "mb": mb,
                "papel": "", "actores": [], "trajes": [], "mallas": [], "texturas": [],
                "tiene": [], "cuenta": {}, "quien": [], "origen": "disco",
            })
    except OSError:
        pass
    return salida


def catalogo_bundles() -> list[dict]:
    """Los bundles con todo lo que se sabe de cada uno, sin abrir ninguno.

    Si el indice de ficheros NO esta (p. ej. en una version publica sin indices empaquetados), se
    listan los bundles de la PROPIA CARPETA DEL JUEGO: el explorador sigue funcionando y solo se
    pierden los datos que aportaba el indice (actor, traje, mallas, texturas, contenido). Con el
    indice presente se cruzan las tres fuentes de siempre: ficheros (tipo, tamano), trajes (papel,
    actor, traje, mallas, texturas) y contenido (tipos de recurso que lleva dentro).
    """
    global _CATALOGO
    if _CATALOGO is not None:
        return _CATALOGO
    ficheros = indice_ficheros().get("ficheros", [])
    if not ficheros:
        _CATALOGO = _bundles_del_disco()
        return _CATALOGO
    tb = trajes.datos().get("bundles", {}) if trajes.disponible() else {}
    asx = indice_assets()
    salida = []
    for f in ficheros:
        ruta = "%s/%s" % (f.get("carpeta", ""), f.get("fichero", ""))
        b = tb.get(ruta) or {}
        a = asx.get(ruta) or {}
        salida.append({
            "ruta": ruta,
            "carpeta": f.get("carpeta", ""),
            "fichero": f.get("fichero", ""),
            "tipo": (f.get("tipo") or "").lower(),
            "que_es": f.get("que_es", ""),
            "nombre": f.get("nombre", ""),
            "mb": f.get("mb", 0) or 0,
            "papel": b.get("papel", ""),
            "actores": b.get("actores") or [],
            "trajes": b.get("trajes") or [],
            "mallas": b.get("mallas") or [],
            "texturas": b.get("texturas") or [],
            "tiene": a.get("tiene") or [],
            "cuenta": a.get("cuenta") or {},
            "quien": a.get("quien") or [],
        })
    _CATALOGO = salida
    return salida


def tipos_de_bundle() -> list[str]:
    """Los tipos de bundle que existen de verdad, con su numero, ordenados de mas a menos."""
    cuenta: dict[str, int] = {}
    for b in catalogo_bundles():
        t_ = b["tipo"] or "?"
        cuenta[t_] = cuenta.get(t_, 0) + 1
    return [t_ for t_, _ in sorted(cuenta.items(), key=lambda x: -x[1])]


_RECURSOS: list[tuple] | None = None


def olvidar_recursos() -> None:
    global _RECURSOS
    _RECURSOS = None


def ruta_indice_recursos() -> Path:
    """Donde se guarda el indice de recursos construido bajo demanda (junto al .exe, en cache)."""
    return ajustes.CACHE / "resource_index.json"


def indice_recursos_cache_datos() -> dict | None:
    """El indice construido bajo demanda ENTERO (recursos y de cuantos bundles sale).

    Hace falta el diccionario completo, no solo la lista, porque un indice puede estar a medias:
    si se construyo con `limite` (pruebas) o sobre una carpeta de bundles incompleta, cubre menos
    bundles de los que hay y presentarlo como el indice entero daria resultados enganosos.
    """
    ruta = ruta_indice_recursos()
    if not ruta.is_file():
        return None
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(datos, dict) or "recursos" not in datos:
        return None
    return datos


def indice_recursos_cache() -> list[tuple] | None:
    """Lee el indice construido bajo demanda, o None si todavia no existe / no vale."""
    datos = indice_recursos_cache_datos()
    if datos is None:
        return None
    try:
        return [tuple(x) for x in datos.get("recursos", [])]
    except Exception:
        return None


def indice_recursos_estado() -> dict:
    """Que se sabe del buscador: si hay indice (empaquetado o construido) y de donde sale."""
    if indice_ficheros().get("ficheros") or indice_assets() or (
            trajes.disponible() and trajes.datos().get("bundles")):
        return {"disponible": True, "fuente": "empaquetado", "n": len(indice_recursos()),
                "bundles": len(catalogo_bundles())}
    cache = indice_recursos_cache_datos()
    if cache is not None:
        recursos = cache.get("recursos", [])
        n_bundles = cache.get("bundles_cubiertos", cache.get("bundles", 0)) or 0
        total = len(catalogo_bundles())
        # un indice que cubre menos bundles de los que hay NO es el indice completo: se dice, para
        # que el buscador no prometa mas de lo que tiene.
        parcial = bool(total and n_bundles and n_bundles < total)
        return {"disponible": True, "fuente": "cache", "n": len(recursos), "bundles": total,
                "parcial": parcial, "bundles_cubiertos": n_bundles}
    return {"disponible": False, "fuente": "ninguno", "n": 0,
            "bundles": len(catalogo_bundles()), "parcial": False, "bundles_cubiertos": 0}


def indice_recursos() -> list[tuple]:
    """(nombre, tipo, bundle) de cada recurso conocido del juego.

    Con los indices empaquetados, se arma con los nombres de malla y de textura del indice de
    trajes (listas COMPLETAS) mas la `muestra` del indice de contenido. En una version publica SIN
    indices, se usa el que se haya construido bajo demanda y guardado en cache (ver
    `construir_indice_recursos`); si tampoco hay, devuelve una lista vacia.
    """
    global _RECURSOS
    if _RECURSOS is not None:
        return _RECURSOS
    salida: list[tuple] = []
    vistos: set = set()
    tb = trajes.datos().get("bundles", {}) if trajes.disponible() else {}
    for ruta, b in tb.items():
        for n in (b.get("mallas") or []):
            if (n, "Mesh", ruta) not in vistos:
                vistos.add((n, "Mesh", ruta))
                salida.append((n, "Mesh", ruta))
        for n in (b.get("texturas") or []):
            if (n, "Texture2D", ruta) not in vistos:
                vistos.add((n, "Texture2D", ruta))
                salida.append((n, "Texture2D", ruta))
    for ruta, a in indice_assets().items():
        for tipo, nombres in (a.get("muestra") or {}).items():
            for n in nombres:
                if (n, tipo, ruta) not in vistos:
                    vistos.add((n, tipo, ruta))
                    salida.append((n, tipo, ruta))
    if not salida:
        salida = indice_recursos_cache() or []
    _RECURSOS = salida
    return salida


def _datos_indice(destino: Path | None) -> dict:
    """Lo que hay guardado en el indice: el de verdad, o el que se le pase (pruebas)."""
    if destino is None:
        return indice_recursos_cache_datos() or {}
    try:
        return json.loads(Path(destino).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def huella_bundle(rel: str) -> list:
    """[fecha_de_modificacion, tamano] de un bundle, para saber si cambio SIN abrirlo.

    Devuelve lista vacia si no se puede mirar (fichero que ya no esta, error de disco): asi quien
    llama trata el caso como "no lo puedo comparar, lo visito", que es lo prudente.
    """
    ruta = ruta_bundle_juego(rel)
    try:
        e = ruta.stat()
        return [e.st_mtime_ns, e.st_size]
    except (OSError, AttributeError):
        return []


def construir_indice_recursos(progreso=None, cancelar=None, log=None, limite=None,
                              ruta: Path | None = None, incremental: bool = True) -> list[tuple]:
    """Construye el indice del buscador recorriendo los bundles del juego con el motor.

    Es el trabajo pesado del buscador global: abre cada bundle con `-m info --export-asset-list`
    (~0,2 s cada uno) y anota nombre + tipo + bundle de cada recurso. Con los 16.535 bundles tarda
    decenas de minutos, asi que informa del progreso y se puede cancelar.

    Desde que el indice guarda la huella (fecha y tamano) de cada bundle, la segunda vez **solo
    visita los que cambiaron**: los demas se reutilizan tal cual. Con los bundles del juego, que no
    cambian salvo que se actualice el juego, eso convierte decenas de minutos en segundos.

    `progreso(hechos, total)` se llama desde el hilo de trabajo; `cancelar()` devuelve True para
    parar. Devuelve la lista de recursos (vacia si se cancelo o fallo). `limite` (para pruebas) y
    `ruta` (para no pisar el indice de verdad) son opcionales.
    """
    bundles = catalogo_bundles()
    if limite:
        bundles = bundles[:limite]
    total = len(bundles)
    if not total:
        raise RuntimeError(t("her_sync_sin_bundles"))

    # lo que ya estaba indexado, por bundle, para no volver a abrir lo que no cambio
    destino = Path(ruta) if ruta is not None else (
        ajustes.CACHE / "work" / "indice_prueba.json" if limite else ruta_indice_recursos())
    previo = _datos_indice(None if destino == ruta_indice_recursos() else destino)
    huellas_previas = (previo.get("huellas") or {}) if incremental and previo else {}
    reutilizar: dict[str, list] = {}
    if huellas_previas:
        for fila in (previo.get("recursos") or []):
            try:
                nombre, tipo, rel = fila
            except (TypeError, ValueError):
                continue
            reutilizar.setdefault(str(rel), []).append((nombre, tipo, rel))

    recursos: list[tuple] = []
    vistos: set = set()
    huellas: dict[str, list] = {}
    a_visitar = []
    for b in bundles:
        rel = b["ruta"]
        h = huella_bundle(rel)
        if h and huellas_previas.get(rel) == h and rel in reutilizar:
            huellas[rel] = h
            for clave in reutilizar[rel]:
                if clave not in vistos:
                    vistos.add(clave)
                    recursos.append(clave)
        else:
            if h:
                huellas[rel] = h
            a_visitar.append(b)

    tmp = ajustes.CACHE / "work" / "sync"
    hechos = 0
    tamano_lote = 48
    total_visitar = len(a_visitar)
    with ThreadPoolExecutor(max_workers=6) as pool:
        for inicio in range(0, total_visitar, tamano_lote):
            if cancelar and cancelar():
                if log:
                    log(t("her_sync_cancelado"))
                return []
            lote = a_visitar[inicio:inicio + tamano_lote]
            futuros = {}
            for k, b in enumerate(lote):
                carpeta = tmp / ("%d" % (inicio + k))
                futuros[pool.submit(listar_bundle, b["ruta"], None, carpeta)] = b
            for futuro in as_completed(futuros):
                b = futuros[futuro]
                hechos += 1
                try:
                    filas = futuro.result()
                except Exception:
                    filas = []
                for a in filas:
                    clave = (a["nombre"], a["tipo"], b["ruta"])
                    if clave in vistos:
                        continue
                    vistos.add(clave)
                    recursos.append(clave)
                if progreso:
                    progreso(hechos, total_visitar)
    if cancelar and cancelar():
        return []
    # Con `limite` (pruebas) NO se toca el indice de verdad: si se escribiera, el buscador del
    # usuario quedaria con un indice recortado que se presentaria como completo.
    destino.parent.mkdir(parents=True, exist_ok=True)
    motivo = (t("her_sync_reutilizado", total - total_visitar)
              if total_visitar < total else "")
    destino.write_text(json.dumps({"n": len(recursos), "bundles_cubiertos": total,
                                   "bundles_visitados": total_visitar,
                                   "huellas": huellas,
                                   "recursos": recursos}, ensure_ascii=False),
                       encoding="utf-8")
    olvidar_recursos()
    shutil.rmtree(tmp, ignore_errors=True)
    if log:
        log(t("her_sync_guardado", len(recursos), destino) + motivo)
    return recursos


def tipos_de_recurso() -> list[str]:
    cuenta: dict[str, int] = {}
    for _, t_, _ in indice_recursos():
        cuenta[t_] = cuenta.get(t_, 0) + 1
    return [t_ for t_, _ in sorted(cuenta.items(), key=lambda x: -x[1])]


def carpeta_bundles() -> Path | None:
    return ajustes.carpeta_bundles()


def ruta_bundle_juego(ruta_rel: str) -> Path | None:
    """Fichero real de un bundle a partir de su ruta relativa (`110/shared_...bundle`)."""
    carpeta = carpeta_bundles()
    if not carpeta:
        return None
    p = carpeta / (ruta_rel or "").replace("/", os.sep)
    return p if p.is_file() else None


# --------------------------------------------------------------------------- herramientas externas
def _candidatos_uv() -> list[list[str]]:
    """uv: primero el que viaja en la carpeta, luego el que hubiera en el equipo."""
    raiz = ajustes.RAIZ
    cands = []
    for base in (raiz.parent / "tools", raiz / "tools"):
        exe = base / "uv" / "uv.exe"
        if exe.is_file():
            cands.append([str(exe)])
    cands.append(["uv"])
    for casa in (Path.home() / ".local/bin/uv.exe", Path.home() / ".cargo/bin/uv.exe"):
        if casa.is_file():
            cands.append([str(casa)])
    return cands


def _candidatos_wannacri() -> list[list[str]]:
    raiz = ajustes.RAIZ
    cands = []
    for base in (raiz.parent / "tools", raiz / "tools"):
        # `wannacri` es el nombre nuevo; `env` se sigue mirando porque asi se llamaba el entorno en
        # las instalaciones y en los apuntes del proyecto, y renombrarlo alli romperia esos comandos
        for sub in ("wannacri", "env"):
            exe = base / sub / "Scripts" / "wannacri.exe"
            if exe.is_file():
                cands.append([str(exe)])
            py = base / sub / "Scripts" / "python.exe"
            if py.is_file():
                cands.append([str(py), "-m", "wannacri"])
    cands.append(["wannacri"])
    return cands


def _exe_bajo(base: Path, nombre: str) -> list:
    """Rutas de un ejecutable dentro de una carpeta, aunque venga en subcarpeta propia.

    Los zip de estas herramientas traen su propia carpeta dentro (`ffmpeg-master-...-shared/bin/`,
    `vgmstream-win64/`), asi que mirar solo en la raiz no vale.
    """
    try:
        return [str(p) for p in base.rglob(nombre) if p.is_file()]
    except OSError:
        return []


def _candidatos_vgmstream() -> list[list[str]]:
    raiz = ajustes.RAIZ
    cands = []
    for base in (raiz.parent / "tools", raiz / "tools"):
        exe = base / "vgmstream" / "vgmstream-cli.exe"
        if exe.is_file():
            cands.append([str(exe)])
        for hallado in _exe_bajo(base / "vgmstream", "vgmstream-cli.exe"):
            if [hallado] not in cands:
                cands.append([hallado])
    cands.append(["vgmstream-cli"])
    return cands


def _candidatos_ffmpeg() -> list[list[str]]:
    raiz = ajustes.RAIZ
    cands = [["ffmpeg"]]
    # junto al ejecutable: tools/ffmpeg/bin/ffmpeg.exe (la distribucion publica no lleva ffmpeg
    # dentro, para no engordar el binario; se pone al lado, como wannacri y vgmstream)
    for base in (raiz.parent / "tools", raiz / "tools"):
        for rel in ("ffmpeg/bin/ffmpeg.exe", "ffmpeg/ffmpeg.exe", "ffmpeg.exe"):
            exe = base / rel
            if exe.is_file():
                cands.append([str(exe)])
        # el paquete descargado trae su propia subcarpeta dentro de tools/ffmpeg
        for hallado in _exe_bajo(base / "ffmpeg", "ffmpeg.exe"):
            if [hallado] not in cands:
                cands.append([hallado])
    return cands


def _comprueba(comando: list[str], args=("-version",)) -> bool:
    try:
        r = subprocess.run(comando + list(args), capture_output=True, text=True, timeout=20,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return r.returncode == 0 or bool((r.stdout or "") + (r.stderr or ""))
    except Exception:
        return False


def _localiza(candidatos: list[list[str]], args=("-version",)) -> list[str] | None:
    for c in candidatos:
        if _comprueba(c, args):
            return c
    return None


def estado_herramientas() -> dict:
    """Que herramientas externas hay disponibles. No instala nada: solo mira."""
    return {
        "uv": _localiza(_candidatos_uv(), ("--version",)),
        "wannacri": _localiza(_candidatos_wannacri(), ("-h",)),
        "vgmstream": _localiza(_candidatos_vgmstream(), ("-h",)),
        "ffmpeg": _localiza(_candidatos_ffmpeg(), ("-version",)),
        "motor": dependencias.ruta_assetstudio(),
    }


# --------------------------------------------------------------------------- motor (bundle a bundle)
def _ruta_motor() -> Path:
    exe = dependencias.ruta_assetstudio()
    if not exe:
        raise RuntimeError(t("her_motor_falta"))
    return Path(exe)


def _ejecutar_motor(argumentos: list[str], timeout: int = 600) -> subprocess.CompletedProcess:
    orden = [str(_ruta_motor())] + argumentos
    entorno = dict(os.environ)
    entorno["MSYS_NO_PATHCONV"] = "1"
    return subprocess.run(orden, capture_output=True, text=True, timeout=timeout,
                          env=entorno, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


def listar_bundle(ruta_rel: str, log=None, destino: Path | None = None) -> list[dict]:
    """Abre UN bundle con `-m info --export-asset-list xml` y devuelve sus recursos.

    Es rapido (~0,2 s) porque no decodifica nada: solo escribe la lista de lo que lleva dentro.
    El XML se parsea con ElementTree, NUNCA con regex `.*?` + re.S: un bundle con ~1.400 assets
    hace retroceso catastrofico y el regex se cuelga (parecia un cuelgue del motor).

    `destino` permite dar a cada llamada su propia carpeta (lo usa el indice bajo demanda, que
    abre varios bundles a la vez); por defecto usa la carpeta compartida de siempre.
    """
    fichero = ruta_bundle_juego(ruta_rel)
    if not fichero:
        raise RuntimeError(t("her_err_bundle", ruta_rel))
    destino = Path(destino) if destino is not None else (ajustes.CACHE / "work" / "info")
    destino.mkdir(parents=True, exist_ok=True)
    xml = destino / "assets.xml"
    if xml.exists():
        try:
            xml.unlink()
        except OSError:
            pass
    if log:
        log(t("her_log_abriendo", ruta_rel))
    r = _ejecutar_motor([str(fichero), "-m", "info", "--export-asset-list", "xml",
                         "-o", str(destino), "--log-level", "Error", "--unity-version", UNITY])
    if not xml.is_file():
        raise RuntimeError(t("her_err_sin_lista")
                           % ((r.stdout or "") + (r.stderr or ""))[-600:])
    raiz = ET.parse(str(xml)).getroot()
    filas = []
    for a in raiz.findall("Asset"):
        filas.append({
            "nombre": (a.findtext("Name") or "").strip(),
            "tipo": (a.findtext("Type") or "").strip(),
            "contenedor": (a.findtext("Container") or "").strip(),
            "pathid": (a.findtext("PathID") or "").strip(),
            "tamano": int((a.findtext("Size") or "0").strip() or 0),
        })
    return filas


def exportar_bundle(ruta_rel: str, tipos: str, destino: Path, log=None) -> Path:
    """Exporta los recursos elegidos de UN bundle. `tipos` va en minusculas y con comas."""
    fichero = ruta_bundle_juego(ruta_rel)
    if not fichero:
        raise RuntimeError(t("her_err_bundle", ruta_rel))
    destino = Path(destino)
    destino.mkdir(parents=True, exist_ok=True)
    if log:
        log(t("her_log_exportando", ruta_rel, tipos))
    r = _ejecutar_motor([str(fichero), "-m", "export", "-t", tipos, "-o", str(destino),
                         "--log-level", "Error", "-r", "--unity-version", UNITY], timeout=1800)
    if r.returncode != 0:
        raise RuntimeError(t("her_err_exportar")
                           % ((r.stdout or "") + (r.stderr or ""))[-800:])
    return destino


# --------------------------------------------------------------------------- video y audio
# El sonido de los videos NO viaja dentro del .usm: vive aparte, en los bancos CRIWARE (.acb) que
# llevan las pistas HCA con NOMBRE. El propio juego trae el mapa `CueInfoMap.txt` (cue -> banco);
# emparejando el nombre del .usm con el del cue se llega al banco y, dentro de el, a la pista por su
# nombre. vgmstream abre los .acb directamente y enumera sus subsongs con `-I -s N`.
_AFIJOS_CUE = ("sfx", "anim", "login", "cg", "efx", "se", "v", "p")
_SUFIJOS_IDIOMA = ("jp", "en", "cn", "zh", "ko")

# El juego dobla en chino y en japones, y guarda CADA idioma en su propio banco hermano
# (`ch_Anim_LD_P3R` / `ja_Anim_LD_P3R`, `ch_Closer_Coop` / `ja_Closer_Coop`, ...). Un mismo cue
# apunta a los dos, asi que hasta ahora se cogia siempre el primero que existia (el chino) y se
# perdia la variante japonesa. Orden de preferencia: japones primero (es el doblaje original y,
# en los CG de personajes invitados, el unico que trae voz), luego chino, y por ultimo un banco
# sin prefijo de idioma. El japones queda como pista por defecto del MP4, con el chino detras.
_IDIOMAS_ORDEN = ("ja", "zh", "")
_IDIOMA_META = {"ja": "jpn", "zh": "chi"}
# Una pista SIN prefijo de idioma es la de EFECTOS/SFX puros (sin voces): no es un idioma, asi que
# se etiqueta con `und` (indeterminado) y un titulo explicito para distinguirla de los doblajes.
# Se conserva igual que las de idioma: tener o no voces NUNCA es motivo para descartarla.
_IDIOMA_META_SFX = "und"
_CUE_MAPA: dict | None = None
_CUE_IDX: tuple | None = None


def _idioma_de_banco(banco: str) -> str:
    """Idioma deducido del prefijo del banco CRIWARE: `ja_` -> japones, `ch_`/`zh_` -> chino."""
    b = (banco or "").lower()
    if b.startswith("ja_"):
        return "ja"
    if b.startswith("ch_") or b.startswith("zh_"):
        return "zh"
    return ""


def _etiqueta_idioma(info: dict) -> str:
    """Nombre visible del idioma/rol de una variante (doblaje por idioma, o efectos sin voz)."""
    idi = (info or {}).get("idioma") or ""
    return t("her_idioma_" + idi) if idi in _IDIOMA_META else t("her_pista_sfx")


def _tokens_cue(s: str) -> list[str]:
    return re.findall(r"[a-z]+|[0-9]+", s.lower())


def _nucleo_cue(s: str) -> str:
    """Nombre sin años de 4 digitos ni afijos de rol en los extremos (para comparar cue y .usm)."""
    tks = [x for x in _tokens_cue(s) if not (x.isdigit() and len(x) == 4)]
    cambiado = True
    while cambiado and tks:
        cambiado = False
        if len(tks) > 1 and tks[0] in _AFIJOS_CUE:
            tks = tks[1:]; cambiado = True
        if len(tks) > 1 and tks[-1] in _AFIJOS_CUE:
            tks = tks[:-1]; cambiado = True
    return "".join(tks)


def _clave_anagrama(s: str) -> tuple | None:
    """Clave del nombre INSENSIBLE al orden de las PALABRAS pero sensible al de los numeros.

    Quita años de 4 digitos y afijos de rol en cualquier posicion (no solo extremos) y separa
    palabras de numeros: las palabras se ordenan (multiconjunto), los numeros conservan su orden
    (un 1_2 y un 2_1 no son lo mismo). Caza el caso `CG_P3P_Event_Main_05_3_movie`, cuyo cue real
    es `SFX_CG_Event_P3P_Main_05_3_movie`: 'P3P' y 'Event' van intercambiados entre .usm y cue,
    asi que el nucleo concatenado (sensible al orden) nunca casaba."""
    tks = [x for x in _tokens_cue(s)
           if not (x.isdigit() and len(x) == 4) and x not in _AFIJOS_CUE]
    if len(tks) < 2:
        return None
    palabras = tuple(sorted(x for x in tks if not x.isdigit()))
    numeros = tuple(x for x in tks if x.isdigit())
    return (palabras, numeros)


def _puntua_cue(stem: str, cue: str) -> float:
    ns = re.sub(r"[^a-z0-9]", "", stem.lower())
    nc = re.sub(r"[^a-z0-9]", "", cue.lower())
    if ns == nc:
        return 1.0
    ks, kc = _nucleo_cue(stem), _nucleo_cue(cue)
    if ks and kc and ks == kc:
        return 0.9
    ka, kb = _clave_anagrama(stem), _clave_anagrama(cue)
    if ka and kb and ka == kb:
        return 0.8
    return 0.0


def _carpetas_media() -> list[Path]:
    juego = ajustes.detectar_juego()
    if not juego:
        return []
    salida = []
    for sub in ("Client/OuterPackage/Media/Windows", "Client/bin/Media/Windows"):
        p = juego / sub
        if p.is_dir():
            salida.append(p)
    return salida


def _rutas_cueinfo() -> list[Path]:
    """Todos los CueInfoMap del juego, el principal PRIMERO (prioridad), luego los de idioma.

    El principal solo cubre SFX/BGM de combate y UI; los CG de historia (bancos `ch_`/`ja_`) viven
    en `zh_CueInfoMap.txt` / `ja_CueInfoMap.txt`. Mirar solo el principal dejaba sin audio a 78
    videos que SI lo tienen (p.ej. toda la familia `CG_zx_Event_*`)."""
    juego = ajustes.detectar_juego()
    if not juego:
        return []
    salida = []
    for sub in ("Client/bin/Media/Windows/CueInfoMap.txt",
                "Client/bin/Media/Windows/zh_CueInfoMap.txt",
                "Client/bin/Media/Windows/ja_CueInfoMap.txt",
                "Client/OuterPackage/Media/Windows/CueInfoMap.txt"):
        p = juego / sub
        if p.is_file():
            salida.append(p)
    return salida


def _ruta_cueinfo() -> Path | None:
    """Compatibilidad: el primer CueInfoMap (el principal)."""
    rutas = _rutas_cueinfo()
    return rutas[0] if rutas else None


def _mapa_cues() -> dict:
    """cue -> lista de bancos, leido de TODOS los CueInfoMap del juego (se cachea).

    Un mismo cue puede apuntar a bancos de idioma distintos (`ch_...`, `ja_...`); se conservan
    todos en orden de prioridad (principal primero) y se prueban hasta que uno exista."""
    global _CUE_MAPA
    if _CUE_MAPA is not None:
        return _CUE_MAPA
    mapa: dict = {}
    for ruta in _rutas_cueinfo():
        try:
            for linea in ruta.read_text(encoding="utf-8", errors="replace").splitlines():
                linea = linea.strip()
                if ":" in linea:
                    cue, banco = linea.rsplit(":", 1)
                    cue, banco = cue.strip(), banco.strip()
                    if cue and banco:
                        bancos = mapa.setdefault(cue, [])
                        if banco not in bancos:
                            bancos.append(banco)
        except OSError:
            pass
    _CUE_MAPA = mapa
    return mapa


def _indice_cues() -> tuple:
    """(norm -> [cues], anagrama -> [cues]) precalculado para emparejar sin recorrer el mapa."""
    global _CUE_IDX
    if _CUE_IDX is None:
        norm_idx: dict = {}
        an_idx: dict = {}
        for cue in _mapa_cues():
            norm_idx.setdefault(re.sub(r"[^a-z0-9]", "", cue.lower()), []).append(cue)
            k = _clave_anagrama(cue)
            if k:
                an_idx.setdefault(k, []).append(cue)
        _CUE_IDX = (norm_idx, an_idx)
    return _CUE_IDX


def _busca_acb(banco: str) -> Path | None:
    for carpeta in _carpetas_media():
        p = carpeta / (banco + ".acb")
        if p.is_file():
            return p
    return None


def _info_vgm(vgm: list[str], acb: Path, sub: int) -> dict | None:
    """JSON de UNA pista del .acb. Con `-m` vgmstream solo lee metadatos: sin el volcaria a disco
    un `.wav` por cada subsong consultado (dejaba el `.acb#N.wav` tirado junto a los bancos DEL
    JUEGO en cada emparejamiento)."""
    r = subprocess.run(vgm + ["-I", "-m", "-s", str(sub), str(acb)], capture_output=True, text=True,
                       timeout=120, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    try:
        return json.loads((r.stdout or "").strip().splitlines()[0])
    except Exception:
        return None


def _pista_de_banco(vgm: list[str], acb: Path, cue: str) -> tuple | None:
    """La pista del .acb cuyo nombre casa con el cue. Devuelve (subsong, nombre, segundos).

    Primero el nombre EXACTO; si no, la variante de idioma (cue + `_jp`/`_en`/`_cn`/...). No se
    admiten coincidencias por subcadena sueltas: bancos como `ch_Anim_zx_00.acb` traen pistas de
    nombre truncado (`Anim_zx_Event_00_0`) que enganchaban a varios videos distintos."""
    base = _info_vgm(vgm, acb, 1)
    if not base:
        return None
    total = int(base.get("streamInfo", {}).get("total", 1) or 1)
    ncue = re.sub(r"[^a-z0-9]", "", cue.lower())
    idioma = {ncue + s for s in _SUFIJOS_IDIOMA}
    parecidos = []
    for s in range(1, total + 1):
        d = _info_vgm(vgm, acb, s)
        if not d:
            continue
        si = d.get("streamInfo", {})
        nombre = si.get("name", "") or ""
        sr = float(d.get("sampleRate", 48000) or 48000)
        segs = float(d.get("playSamples", 0) or 0) / sr
        n = re.sub(r"[^a-z0-9]", "", nombre.lower())
        if n == ncue:
            return (s, nombre, segs)
        if n in idioma:
            parecidos.append((s, nombre, segs))
    return parecidos[0] if parecidos else None


def buscar_audios_video(ruta_usm: str, log=None) -> list[dict]:
    """TODAS las pistas de audio distintas de un `.usm` (una por banco), en orden de preferencia.

    Devuelve una lista de `{'acb','banco','cue','subsong','pista','segundos','idioma'}`; la
    primera es la pista que se pone por defecto en el MP4 y las demas van como pistas de audio
    adicionales etiquetadas. Un mismo cue suele existir en un banco chino, en su hermano japones
    y a veces en un tercer banco SIN prefijo de idioma con los EFECTOS puros (sin voces): se
    devuelven LOS TRES. Antes cada idioma se colapsaba a una sola pista y podia perderse la de
    efectos; ahora solo se deduplican pistas con el MISMO audio (por hash, en `extraer_video`).
    """
    mapa = _mapa_cues()
    if not mapa:
        if log:
            log(t("her_log_sin_cueinfo"))
        return []
    stem = Path(ruta_usm).stem
    norm_idx, an_idx = _indice_cues()
    cands = norm_idx.get(re.sub(r"[^a-z0-9]", "", stem.lower()), [])
    if not cands:
        k = _clave_anagrama(stem)
        cands = an_idx.get(k, []) if k else []
    if not cands:
        return []
    vgm = _localiza(_candidatos_vgmstream(), ("-h",))
    if not vgm:
        return []
    orden = {idi: n for n, idi in enumerate(_IDIOMAS_ORDEN)}
    for cue in cands[:8]:
        variantes: dict = {}
        for banco in mapa.get(cue, []):
            acb = _busca_acb(banco)
            if not acb:
                continue
            pista = _pista_de_banco(vgm, acb, cue)
            if not pista:
                continue
            if banco in variantes:       # el mismo banco listado dos veces en los mapas
                continue
            variantes[banco] = {"acb": str(acb), "banco": banco, "cue": cue,
                                "subsong": pista[0], "pista": pista[1],
                                "segundos": round(pista[2], 3),
                                "idioma": _idioma_de_banco(banco)}
        if variantes:
            # Se conservan TODAS las pistas distintas (una por banco): la de efectos puros y cada
            # doblaje. No se descarta ninguna por no llevar voces; los alias (mismo audio con otro
            # nombre) los quita luego `extraer_video` comparando el HASH del WAV, que es la unica
            # deduplicacion fiable. Orden: doblajes primero (japones por defecto), efectos al final.
            return sorted(variantes.values(),
                          key=lambda v: (orden.get(v["idioma"], 9), v["banco"]))
    return []


def buscar_audio_video(ruta_usm: str, log=None) -> dict | None:
    """La pista de audio PRINCIPAL de un `.usm` (la primera variante de idioma), o `None`.

    Se mantiene por compatibilidad (el cache del distintivo y otras pruebas la usan); la
    extraccion usa `buscar_audios_video` para meter TODOS los idiomas en el MP4.
    """
    audios = buscar_audios_video(ruta_usm, log)
    return audios[0] if audios else None


def _wav_es_silencio(ruta: Path, umbral: float = 5.0) -> bool:
    """True si el WAV es practicamente silencio (RMS por debajo del umbral). Sin numpy."""
    try:
        with wave.open(str(ruta), "rb") as w:
            if w.getsampwidth() != 2:
                return False
            n = min(w.getnframes(), w.getframerate() * 10)
            datos = w.readframes(n)
    except Exception:
        return False
    if not datos:
        return True
    a = array("h")
    a.frombytes(datos)
    if not a:
        return True
    rms = (sum(x * x for x in a) / len(a)) ** 0.5
    return rms < umbral


def carpeta_media() -> Path | None:
    """La carpeta con los .usm y .awb del cliente."""
    juego = ajustes.detectar_juego()
    if not juego:
        return None
    for sub in ("Client/OuterPackage/Media/Windows", "Client/bin/Media/Windows"):
        p = juego / sub
        if p.is_dir():
            return p
    return None


def listar_media(carpeta: Path | None = None) -> dict:
    carpeta = carpeta or carpeta_media()
    if not carpeta or not carpeta.is_dir():
        return {"carpeta": None, "usm": [], "awb": []}
    usm, awb = [], []
    for p in carpeta.iterdir():
        if not p.is_file():
            continue
        if p.suffix.lower() == ".usm":
            usm.append({"nombre": p.name, "ruta": str(p), "mb": p.stat().st_size / 1e6,
                        "estado": estado_audio_de(p.stem)})
        elif p.suffix.lower() == ".awb":
            awb.append({"nombre": p.name, "ruta": str(p), "mb": p.stat().st_size / 1e6})
    usm.sort(key=lambda x: x["nombre"].lower())
    awb.sort(key=lambda x: x["nombre"].lower())
    return {"carpeta": str(carpeta), "usm": usm, "awb": awb}


_ESTADO_AUDIO: dict | None = None


def _estados_audio() -> dict:
    """stem -> estado de audio del cache `estado_audio_video.json` (construido aparte, en `_dl`).

    El tercer estado (la pista existe pero es silencio) es caro de calcular en vivo —hay que
    decodificar cada pista con vgmstream y medir su RMS—, asi que se precalculo UNA vez con las
    MISMAS funciones que usa la extraccion (`buscar_audio_video` + `_wav_es_silencio`) y se guarda
    aqui; cargarlo es instantaneo, de modo que la lista se pinta al momento. El cache solo guarda
    el estado y los nombres de banco/cue/pista, nunca rutas absolutas (el ejecutable resuelve las
    rutas en runtime). Si un `.usm` no esta en el cache se deduce barato con el mapa de cues.
    """
    global _ESTADO_AUDIO
    if _ESTADO_AUDIO is None:
        _ESTADO_AUDIO = _leer_json("estado_audio_video.json")
    return _ESTADO_AUDIO


def estado_audio_de(stem: str) -> str:
    """Devuelve `audio`, `silencio`, `mudo` (o `sin_dato` si no se puede deducir sin decodificar).

    El calculo exacto (`audio`/`silencio`) sale del cache medido aparte. Si el cache NO existe en
    absoluto (una version publica sin el indice empaquetado), no se ha medido nada y devolver
    `mudo` seria afirmar de mas: se responde `sin_dato`, que es la verdad ("no lo se").
    """
    cache = _estados_audio()
    reg = cache.get(stem)
    if isinstance(reg, dict) and reg.get("estado"):
        return reg["estado"]
    if not cache:
        return "sin_dato"
    mapa = _mapa_cues()
    if not mapa:
        return "sin_dato"
    if any(_puntua_cue(stem, c) > 0 for c in mapa):
        return "sin_dato"
    return "mudo"


def extraer_video(ruta_usm: str, destino: Path, log=None) -> Path:
    """`.usm` -> `.mp4` CON sonido. Video con wannacri + ffmpeg; audio del banco CRIWARE del juego.

    El video sale a .ivf (VP9), .avi (Sofdec) o alphas/*.sfv. El sonido no vive dentro del .usm:
    se empareja por el nombre con el mapa del juego (CueInfoMap) y se saca del .acb con vgmstream.
    Cuando el cue existe en varios bancos (`ch_*`, `ja_*` y a veces un banco sin prefijo con los
    EFECTOS puros) se meten TODAS las pistas distintas, etiquetadas (doblajes con su idioma,
    efectos como `und`+titulo) y con el japones primero (pista por defecto) y los efectos al
    final; solo se deduplican pistas con el MISMO audio (hash). Si no hay audio emparejado (o la
    pista es silencio) se entrega el video MUDO y se avisa.
    """
    wannacri = _localiza(_candidatos_wannacri(), ("-h",))
    ffmpeg = _localiza(_candidatos_ffmpeg(), ("-version",))
    if not wannacri:
        raise RuntimeError(t("her_err_wannacri"))
    if not ffmpeg:
        raise RuntimeError(t("her_err_ffmpeg"))
    origen = Path(ruta_usm)
    destino = Path(destino)
    destino.mkdir(parents=True, exist_ok=True)
    crudo = destino / (origen.stem + "_crudo")
    if crudo.exists():
        shutil.rmtree(crudo, ignore_errors=True)
    crudo.mkdir(parents=True, exist_ok=True)
    if log:
        log(t("her_log_wannacri", origen.name))

    def _pistas() -> list[Path]:
        return [p for p in crudo.rglob("*") if p.suffix.lower() in (".ivf", ".avi", ".mpg", ".m2v")]

    r = subprocess.run(wannacri + ["extractusm", str(origen), "-k", CLAVE_USM, "-o", str(crudo)],
                       capture_output=True, text=True, timeout=1800,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    piezas = _pistas()
    if not piezas:
        # clips del build CN: literales en GBK, no shift-jis (WannaCRI no senala error con exit-code)
        r = subprocess.run(wannacri + ["extractusm", str(origen), "-k", CLAVE_USM,
                                       "-e", "gbk", "-o", str(crudo)],
                           capture_output=True, text=True, timeout=1800,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        piezas = _pistas()
    if not piezas:
        raise RuntimeError(t("her_err_sin_pista")
                           % ((r.stdout or "") + (r.stderr or ""))[-600:])
    pieza = max(piezas, key=lambda p: p.stat().st_size)
    salida = destino / (origen.stem + ".mp4")

    # --- sonido: TODAS las pistas distintas del banco del juego, cada una como pista ---
    # El japones va primero (pista por defecto), luego el chino y por ultimo la pista de EFECTOS
    # puros (la que no lleva voces), cada una etiquetada para que se puedan elegir en el
    # reproductor. Antes cada idioma se colapsaba a una pista y se perdia la de efectos.
    audios: list[tuple] = []          # (info, wav)
    vistos: dict = {}                 # huella del WAV -> banco que ya aporto esa misma pista
    vgm = _localiza(_candidatos_vgmstream(), ("-h",))
    if vgm:
        infos = buscar_audios_video(ruta_usm, log)
        for info in infos:
            etq = info.get("idioma") or "base"
            wav = destino / ("%s_audio_%s.wav" % (origen.stem, etq))
            subprocess.run(vgm + ["-s", str(info["subsong"]), "-o", str(wav), info["acb"]],
                           capture_output=True, text=True, timeout=600,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            if not (wav.is_file() and not _wav_es_silencio(wav)):
                if log:
                    log(t("her_log_audio_video_mudo", info["banco"], info["pista"]))
                continue
            # Los bancos por idioma comparten pistas por ALIAS (mismo audio con otro nombre): si
            # esta pista ya entro con otra etiqueta, no se duplica en el MP4.
            huella = hashlib.md5(wav.read_bytes()).hexdigest()
            if huella in vistos:
                if log:
                    log(t("her_log_audio_video_repetida", info["banco"], vistos[huella]))
                continue
            vistos[huella] = info["banco"]
            audios.append((info, wav))
            if log:
                log(t("her_log_audio_video", info["banco"], info["pista"]))
        if not infos and log:
            log(t("her_log_audio_video_no_hallado", origen.name))
        if len(audios) > 1 and log:
            log(t("her_log_audio_video_varios", len(audios),
                  ", ".join(_etiqueta_idioma(i) for i, _ in audios)))

    if log:
        log(t("her_log_ffmpeg", pieza.name, salida.name))
    if audios:
        orden = [ffmpeg[0], "-y", "-i", str(pieza)]
        for _, wav in audios:
            orden += ["-i", str(wav)]
        orden += ["-map", "0:v:0"]
        for k in range(len(audios)):
            orden += ["-map", "%d:a:0" % (k + 1)]
        orden += ["-c:v", "copy", "-c:a", "aac", "-b:a", "192k"]
        for k, (info, _) in enumerate(audios):
            # `language` es el codigo (o `und` para los efectos, que no son un idioma). `title` lo
            # pidio el usuario, pero el muxer de MP4 lo tira salvo con `use_metadata_tags`; el
            # nombre que de verdad se ve en el reproductor es `handler_name`, asi que van los dos.
            codigo = _IDIOMA_META.get(info.get("idioma") or "") or _IDIOMA_META_SFX
            etiqueta = _etiqueta_idioma(info)
            orden += ["-metadata:s:a:%d" % k, "language=%s" % codigo,
                      "-metadata:s:a:%d" % k, "title=%s" % etiqueta,
                      "-metadata:s:a:%d" % k, "handler_name=%s" % etiqueta]
        orden += ["-shortest", "-movflags", "+faststart+use_metadata_tags", str(salida)]
    else:
        orden = [ffmpeg[0], "-y", "-i", str(pieza), "-c", "copy", "-f", "mp4", str(salida)]
    r2 = subprocess.run(orden, capture_output=True, text=True, timeout=1800,
                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if r2.returncode != 0 or not salida.is_file():
        raise RuntimeError(t("her_err_ffmpeg_empaquetar")
                           % ((r2.stdout or "") + (r2.stderr or ""))[-600:])
    if log:
        log(t("her_log_video_listo", salida.name, salida.stat().st_size / 1e6))
    return salida


def partir_hca(ruta_awb: str, destino: Path, log=None) -> list[Path]:
    """Los .awb son HCA concatenados EN CLARO: se parten por la magia `HCA\\0`."""
    datos = Path(ruta_awb).read_bytes()
    partes = datos.split(b"HCA\x00")
    destino = Path(destino)
    destino.mkdir(parents=True, exist_ok=True)
    salidas = []
    for i, p in enumerate(partes[1:], 1):
        blob = b"HCA\x00" + p
        f = destino / ("%s_%02d.hca" % (Path(ruta_awb).stem, i))
        f.write_bytes(blob)
        salidas.append(f)
    if log:
        log(t("her_log_hca", len(salidas)))
    return salidas


def extraer_audio(ruta_awb: str, destino: Path, log=None) -> list[Path]:
    """`.awb` -> `.wav` con el troceador HCA + vgmstream."""
    vgm = _localiza(_candidatos_vgmstream(), ("-h",))
    if not vgm:
        raise RuntimeError(t("her_err_vgmstream"))
    destino = Path(destino)
    destino.mkdir(parents=True, exist_ok=True)
    hcas = partir_hca(ruta_awb, destino / (Path(ruta_awb).stem + "_hca"), log)
    salidas = []
    for h in hcas:
        wav = destino / (h.stem + ".wav")
        r = subprocess.run(vgm + ["-o", str(wav), str(h)], capture_output=True, text=True,
                           timeout=600, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if wav.is_file():
            salidas.append(wav)
            if log:
                log(t("her_log_wav", h.name, wav.name, wav.stat().st_size / 1e6))
        elif log:
            log(t("her_log_no_wav", h.name))
    if not salidas:
        raise RuntimeError(t("her_err_sin_audio"))
    return salidas


def imagenes_de(carpeta: Path) -> list[Path]:
    carpeta = Path(carpeta)
    if not carpeta.is_dir():
        return []
    salida = [p for p in carpeta.rglob("*") if p.is_file() and p.suffix.lower() in EXT_IMAGEN]
    salida.sort(key=lambda p: p.name.lower())
    return salida


# =========================================================================== ventana de dependencias
class VentanaDependencias(tk.Toplevel):
    """Ventana con la consola de la descarga de dependencias (interfaz clasica).

    Misma idea que la ventana de la interfaz nueva: el usuario ve el progreso en tiempo real y no
    puede escribir en la consola (el widget esta deshabilitado; `append` lo abre un instante para
    meter la linea y lo vuelve a cerrar). Hace falta tenerla tambien aqui porque en un equipo sin
    WebView2 la interfaz nueva no se abre, y entonces no habria forma de bajar nada.
    """

    MAX_LINEAS = 800

    def __init__(self, maestro):
        super().__init__(maestro)
        self.title(t("her_deps_titulo"))
        self.geometry("720x480")
        self.transient(maestro)
        marco = ttk.Frame(self, padding=14)
        marco.pack(fill="both", expand=True)
        self.peso = ttk.Label(marco, text=t("her_deps_peso", dependencias.peso_aproximado_mb()))
        self.peso.pack(anchor="w", pady=(0, 4))
        # si hay copias de fuera de la carpeta (el escritorio del usuario, el PATH), se dice: la app
        # las usa, pero no viajan al copiar la carpeta a otro equipo
        ajenas = dependencias.dentro_de_carpeta(estado_herramientas())
        if ajenas:
            ttk.Label(marco, text=t("her_deps_fuera", ", ".join(sorted(ajenas))),
                      foreground="#7aa2f7", wraplength=660).pack(anchor="w", pady=(0, 6))
        ttk.Label(marco, text=t("her_deps_solo_ver")).pack(anchor="w", pady=(0, 8))
        barra = ttk.Scrollbar(marco, orient="vertical")
        self.consola = tk.Text(marco, wrap="word", yscrollcommand=barra.set, height=18)
        barra.config(command=self.consola.yview)
        barra.pack(side="right", fill="y")
        self.consola.pack(side="left", fill="both", expand=True)
        self.consola.configure(state="disabled")
        self.cerrar = ttk.Button(self, text=t("her_deps_cerrar"), command=self.destroy)
        self.cerrar.pack(pady=8)

    def append(self, linea):
        """Anade una linea al final. Es lo unico que se puede hacer con la consola."""
        self.consola.configure(state="normal")
        self.consola.insert("end", str(linea) + "\n")
        # si el registro crece mucho se tira del principio, para no comerse la memoria
        if int(self.consola.index("end-1c").split(".")[0]) > self.MAX_LINEAS:
            self.consola.delete("1.0", "%d.0" % (self.MAX_LINEAS // 2))
        self.consola.see("end")
        self.consola.configure(state="disabled")
        self.update_idletasks()


# =========================================================================== panel de la interfaz
class PanelHerramientas(ttk.Frame):
    """La pestana de HERRAMIENTAS. Se empaqueta dentro del Notebook de la ventana principal."""

    def __init__(self, maestro, log=None, cabecera=True):
        super().__init__(maestro, style="TFrame")
        self.log_externo = log
        self._con_cabecera = cabecera
        self.cola: "queue.Queue" = queue.Queue()
        self.trabajando = False
        self._imagen = None                 # referencia viva de la vista previa (si no, se borra)
        self._filas_explorador: list[dict] = []
        self._filas_inspector: list[dict] = []
        self._filas_recursos: list[tuple] = []
        self._media = {"usm": [], "awb": []}
        self._destino_por_defecto = ajustes.carpeta_herramientas()
        self._estilo()
        self._construir()
        self.after(150, self._vaciar_cola)

    # ------------------------------------------------------------------ aspecto
    def _estilo(self):
        st = ttk.Style()
        st.configure("Her.Treeview", background=COLOR_PANEL, fieldbackground=COLOR_PANEL,
                     foreground=COLOR_TEXTO, font=("Consolas", 9), rowheight=20, borderwidth=0)
        st.configure("Her.Treeview.Heading", background=COLOR_FONDO, foreground=COLOR_SUAVE,
                     font=("Segoe UI Semibold", 9))
        st.map("Her.Treeview", background=[("selected", COLOR_ACENTO)],
               foreground=[("selected", "#ffffff")])
        st.configure("Her.TNotebook", background=COLOR_FONDO, borderwidth=0)
        st.configure("Her.TNotebook.Tab", background=COLOR_PANEL, foreground=COLOR_SUAVE,
                     padding=(12, 5), font=("Segoe UI", 9))
        st.map("Her.TNotebook.Tab", background=[("selected", COLOR_FONDO)],
               foreground=[("selected", COLOR_TEXTO)])

    # ------------------------------------------------------------------ idiomas
    def _t(self, widget, clave, *args):
        idiomas.registrar(lambda w=widget, k=clave, a=args: w.config(text=t(k, *a)))
        return widget

    def _t_tab(self, pestana, clave):
        idiomas.registrar(lambda p=pestana, k=clave: self.cuaderno.tab(p, text=t(k)))

    def _construir(self):
        # la version de solo herramientas ya pone su propia cabecera (titulo, lema e idioma), asi
        # que aqui se puede omitir para no gastar alto dos veces
        if self._con_cabecera:
            cab = ttk.Frame(self, padding=(14, 8, 14, 4))
            cab.pack(fill="x")
            self._t(ttk.Label(cab, style="Titulo.TLabel"), "her_titulo").pack(anchor="w")
            self._t(ttk.Label(cab, style="Suave.TLabel"), "her_lema").pack(anchor="w")

        self.cuaderno = ttk.Notebook(self, style="Her.TNotebook")
        self.cuaderno.pack(fill="both", expand=True, padx=14, pady=(4, 10))

        self.tab_explorador = ttk.Frame(self.cuaderno)
        self.tab_inspector = ttk.Frame(self.cuaderno)
        self.tab_buscador = ttk.Frame(self.cuaderno)
        self.tab_texturas = ttk.Frame(self.cuaderno)
        self.tab_media = ttk.Frame(self.cuaderno)
        for pestana, clave in ((self.tab_explorador, "her_tab_explorador"),
                               (self.tab_inspector, "her_tab_inspector"),
                               (self.tab_buscador, "her_tab_buscador"),
                               (self.tab_texturas, "her_tab_texturas"),
                               (self.tab_media, "her_tab_media")):
            self.cuaderno.add(pestana, text=t(clave))
            self._t_tab(pestana, clave)

        self._construir_explorador()
        self._construir_inspector()
        self._construir_buscador()
        self._construir_texturas()
        self._construir_media()

    # ------------------------------------------------------------------ helpers
    def registrar(self, texto):
        if self.log_externo:
            self.log_externo(texto)

    def _arbol(self, maestro, columnas, anchos):
        marco = ttk.Frame(maestro)
        barra = ttk.Scrollbar(marco, orient="vertical")
        tv = ttk.Treeview(marco, columns=columnas, show="headings", style="Her.Treeview",
                          yscrollcommand=barra.set)
        for c, a in zip(columnas, anchos):
            tv.heading(c, text=t(c))
            tv.column(c, width=a, stretch=(c == columnas[0]))
        idiomas.registrar(lambda: [tv.heading(c, text=t(c)) for c in columnas])
        barra.config(command=tv.yview)
        barra.pack(side="right", fill="y")
        tv.pack(side="left", fill="both", expand=True)
        return marco, tv

    def _en_hilo(self, funcion):
        if self.trabajando:
            messagebox.showinfo(ajustes.NOMBRE, t("msg_ocupado"))
            return
        self.trabajando = True

        def envoltorio():
            try:
                funcion()
            except Exception as e:
                self.cola.put(("error", str(e)))
            finally:
                self.cola.put(("ocupado", False))
        threading.Thread(target=envoltorio, daemon=True).start()

    def _vaciar_cola(self):
        try:
            while True:
                tipo, carga = self.cola.get_nowait()
                if tipo == "log":
                    self.registrar(carga)
                elif tipo == "inspector":
                    self._pintar_inspector(carga)
                elif tipo == "recursos":
                    self._pintar_recursos(carga)
                elif tipo == "media":
                    self._pintar_media(carga)
                elif tipo == "indice_progreso":
                    hechos, total = carga
                    self.progreso_indice["value"] = 100.0 * hechos / max(total, 1)
                    self.etiq_indice.config(text=t("her_sync_progreso", hechos, total),
                                            foreground=COLOR_TEXTO)
                elif tipo == "indice_fin":
                    self.progreso_indice["value"] = 100 if carga else 0
                    self.boton_indice_cancelar.config(state="disabled")
                    self._actualizar_estado_indice()
                    self.registrar(t("her_sync_hecho", carga) if carga
                                   else t("her_sync_cancelado"))
                elif tipo == "herr":
                    self._pintar_estado_herr(carga)
                elif tipo == "estado":
                    self.estado.config(text=carga)
                elif tipo == "error":
                    self.registrar("")
                    self.registrar(t("her_err_no_completar", carga))
                    self.estado.config(text=t("msg_no_completar"))
                    messagebox.showerror(ajustes.NOMBRE, str(carga)[:1200])
                elif tipo == "ocupado":
                    self.trabajando = bool(carga)
        except Exception:
            pass
        self.after(150, self._vaciar_cola)

    def _destino(self, sugerido="misc"):
        d = self._destino_por_defecto / sugerido
        d.mkdir(parents=True, exist_ok=True)
        return d

    # ============================================================ EXPLORADOR
    def _construir_explorador(self):
        t_ = self.tab_explorador
        filtros = ttk.Frame(t_, padding=(0, 8, 0, 4))
        filtros.pack(fill="x")

        self._t(ttk.Label(filtros, style="Suave.TLabel"), "her_tipo").pack(side="left")
        self.combo_tipo = ttk.Combobox(filtros, state="readonly", width=12)
        self.combo_tipo.pack(side="left", padx=(4, 12))
        self._preparar_combo_tipo()
        idiomas.registrar(self._preparar_combo_tipo)

        self._t(ttk.Label(filtros, style="Suave.TLabel"), "her_actor").pack(side="left")
        self.ent_actor = ttk.Entry(filtros, width=12)
        self.ent_actor.pack(side="left", padx=(4, 12))

        self._t(ttk.Label(filtros, style="Suave.TLabel"), "her_traje").pack(side="left")
        self.ent_traje = ttk.Entry(filtros, width=12)
        self.ent_traje.pack(side="left", padx=(4, 12))

        self._t(ttk.Label(filtros, style="Suave.TLabel"), "her_min_mb").pack(side="left")
        self.ent_mb = ttk.Entry(filtros, width=6)
        self.ent_mb.pack(side="left", padx=(4, 12))

        self._t(ttk.Button(filtros, command=self.explorar), "her_filtrar").pack(side="left")
        self.etiq_explorador = ttk.Label(filtros, text="", style="Suave.TLabel")
        self.etiq_explorador.pack(side="left", padx=(12, 0))

        cuerpo = ttk.Frame(t_)
        cuerpo.pack(fill="both", expand=True)
        # El panel de detalle se empaqueta ANTES que la tabla: si no, la tabla (cuyo ancho pedido
        # es la suma de sus columnas, ~800 px) se queda el sitio primero y empuja el panel fuera
        # de la ventana. Reservando el panel a la derecha, la tabla se encoge y cabe todo.
        det = ttk.Frame(cuerpo, style="Panel.TFrame", padding=8, width=300)
        det.pack(side="right", fill="y", padx=(10, 0))
        det.pack_propagate(False)
        self.detalle = tk.Text(det, width=34, bg=COLOR_PANEL, fg=COLOR_TEXTO,
                               font=("Consolas", 9), bd=0, highlightthickness=0, wrap="word")
        self.detalle.pack(fill="both", expand=True)
        fila = ttk.Frame(det, style="Panel.TFrame")
        fila.pack(fill="x", pady=(6, 0))
        self._t(ttk.Button(fila, command=self.explorador_al_inspector),
                "her_ver_dentro").pack(side="left", fill="x", expand=True)
        fila2 = ttk.Frame(det, style="Panel.TFrame")
        fila2.pack(fill="x", pady=(4, 0))
        self._t(ttk.Button(fila2, command=self.explorador_exportar),
                "her_exportar_mesh_tex").pack(fill="x")

        marco, self.arbol_explorador = self._arbol(
            cuerpo, ("her_col_bundle", "her_col_tipo", "her_col_papel", "her_col_mb",
                     "her_col_mallas", "her_col_texturas", "her_col_contenido"),
            (260, 70, 80, 60, 60, 70, 200))
        marco.pack(side="left", fill="both", expand=True)
        self.arbol_explorador.bind("<<TreeviewSelect>>", lambda e: self.detalle_explorador())

    def _preparar_combo_tipo(self):
        """(Re)llena el desplegable de tipos conservando lo elegido."""
        actual = self.combo_tipo.get()
        valores = [t("comun_todo")] + tipos_de_bundle()
        self.combo_tipo.config(values=valores)
        self.combo_tipo.set(actual if actual in valores else valores[0])

    def explorar(self):
        filas = catalogo_bundles()
        tipo = self.combo_tipo.get().strip().lower()
        actor = self.ent_actor.get().strip().lower()
        traje = self.ent_traje.get().strip().lower()
        try:
            mb_min = float(self.ent_mb.get().strip() or 0)
        except ValueError:
            mb_min = 0.0
        sel = []
        for b in filas:
            if tipo and tipo != t("comun_todo").lower() and b["tipo"] != tipo:
                continue
            if mb_min and b["mb"] < mb_min:
                continue
            if actor and not any(actor in (a or "").lower() for a in b["actores"]) \
                    and not any(actor in (a or "").lower() for a in b["quien"]) \
                    and actor not in b["fichero"].lower():
                continue
            if traje and not any(traje in (t_ or "").lower() for t_ in b["trajes"]) \
                    and traje not in b["fichero"].lower():
                continue
            sel.append(b)
        self._filas_explorador = sel
        self.arbol_explorador.delete(*self.arbol_explorador.get_children())
        for b in sel[:4000]:
            contenido = ",".join(b["tiene"]) or b["que_es"]
            self.arbol_explorador.insert(
                "", "end", values=(b["ruta"], b["tipo"], b["papel"] or "-",
                                   "%.1f" % b["mb"], len(b["mallas"]), len(b["texturas"]),
                                   contenido))
        self.etiq_explorador.config(
            text=t("her_bundles_de", len(sel), len(filas))
                 + (t("her_solo_4000") if len(sel) > 4000 else "")
                 + (t("her_bundles_disco") if filas and filas[0].get("origen") == "disco" else ""))

    def _bundle_seleccionado(self, arbol, filas):
        sel = arbol.selection()
        if not sel:
            return None
        i = arbol.index(sel[0])
        return filas[i] if 0 <= i < len(filas) else None

    def detalle_explorador(self):
        b = self._bundle_seleccionado(self.arbol_explorador, self._filas_explorador)
        if not b:
            return
        lineas = [
            b["ruta"],
            t("her_det_tipo_papel", b["tipo"], b["papel"] or "-"),
            t("her_det_que_es", b["que_es"] or "-"),
            t("her_det_tamano", b["mb"]),
            "",
            t("her_det_actores", ", ".join(b["actores"]) or "-"),
            t("her_det_trajes", ", ".join(b["trajes"]) or "-"),
            t("her_det_quien", ", ".join(b["quien"]) or "-"),
            "",
            t("her_det_contenido", json.dumps(b["cuenta"], ensure_ascii=False) or "-"),
            t("her_det_mallas", len(b["mallas"]), ", ".join(b["mallas"][:8]) or "-"),
            t("her_det_texturas", len(b["texturas"]), ", ".join(b["texturas"][:8]) or "-"),
        ]
        self.detalle.configure(state="normal")
        self.detalle.delete("1.0", "end")
        self.detalle.insert("1.0", "\n".join(lineas))
        self.detalle.configure(state="disabled")

    def explorador_al_inspector(self):
        b = self._bundle_seleccionado(self.arbol_explorador, self._filas_explorador)
        if not b:
            return
        self.ent_ruta.delete(0, "end")
        self.ent_ruta.insert(0, b["ruta"])
        self.cuaderno.select(self.tab_inspector)
        self.abrir_inspector()

    def explorador_exportar(self):
        b = self._bundle_seleccionado(self.arbol_explorador, self._filas_explorador)
        if not b:
            return
        self._exportar_async(b["ruta"], "mesh,tex2d", "explorer")

    # ============================================================ INSPECTOR
    def _construir_inspector(self):
        t_ = self.tab_inspector
        fila = ttk.Frame(t_, padding=(0, 8, 0, 4))
        fila.pack(fill="x")
        self._t(ttk.Label(fila, style="Suave.TLabel"), "her_bundle").pack(side="left")
        self.ent_ruta = ttk.Entry(fila)
        self.ent_ruta.pack(side="left", fill="x", expand=True, padx=(6, 6))
        self._t(ttk.Button(fila, command=self.elegir_bundle),
                "her_elegir_fichero").pack(side="left")
        self._t(ttk.Button(fila, command=self.abrir_inspector),
                "her_abrir_motor").pack(side="left", padx=(6, 0))

        self.arbol_inspector = None
        marco, self.arbol_inspector = self._arbol(
            t_, ("her_col_nombre", "her_col_tipo2", "her_col_contenedor", "her_col_pathid",
                 "her_col_tamano"), (300, 110, 260, 160, 80))
        marco.pack(fill="both", expand=True)

        pie = ttk.Frame(t_, padding=(0, 6, 0, 0))
        pie.pack(fill="x")
        self._t(ttk.Label(pie, style="Suave.TLabel"), "her_exportar").pack(side="left")
        self._t(ttk.Button(pie, command=lambda: self.exportar_inspector("mesh")),
                "her_mallas").pack(side="left", padx=(6, 0))
        self._t(ttk.Button(pie, command=lambda: self.exportar_inspector("tex2d")),
                "her_texturas").pack(side="left", padx=(4, 0))
        self._t(ttk.Button(pie, command=lambda: self.exportar_inspector("mesh,tex2d")),
                "her_mallas_texturas").pack(side="left", padx=(4, 0))
        self._t(ttk.Button(pie, command=lambda: self.exportar_inspector(
            "mesh,tex2d,mat,anim,mono,font,sprite,text,audio,video")),
            "her_todo_posible").pack(side="left", padx=(4, 0))
        self.estado = ttk.Label(pie, text="", style="Suave.TLabel")
        self.estado.pack(side="left", padx=(12, 0))

    def elegir_bundle(self):
        carpeta = carpeta_bundles()
        ruta = filedialog.askopenfilename(
            title=t("dlg_bundle_titulo"),
            initialdir=str(carpeta) if carpeta else None,
            filetypes=[(t("dlg_bundle_unity"), "*.bundle"), (t("dlg_bundle_todos"), "*.*")])
        if ruta:
            self.ent_ruta.delete(0, "end")
            self.ent_ruta.insert(0, ruta)

    def abrir_inspector(self):
        ruta = self.ent_ruta.get().strip()
        if not ruta:
            messagebox.showinfo(ajustes.NOMBRE, t("her_msg_ruta"))
            return
        self.estado.config(text=t("her_abriendo"))

        def trabajo():
            filas = listar_bundle(ruta, lambda s: self.cola.put(("log", s)))
            self.cola.put(("log", t("her_recursos_dentro", len(filas), Path(ruta).name)))
            self.cola.put(("inspector", filas))
            self.cola.put(("estado", t("her_n_recursos", len(filas))))
        self._en_hilo(trabajo)

    def _pintar_inspector(self, filas):
        self._filas_inspector = filas
        self.arbol_inspector.delete(*self.arbol_inspector.get_children())
        for f in filas:
            self.arbol_inspector.insert(
                "", "end", values=(f["nombre"], f["tipo"], f["contenedor"], f["pathid"],
                                   "%.1f KB" % (f["tamano"] / 1024.0)))

    def exportar_inspector(self, tipos):
        ruta = self.ent_ruta.get().strip()
        if not ruta:
            return
        self._exportar_async(ruta, tipos, "inspector")

    # ============================================================ BUSCADOR
    def _construir_buscador(self):
        t_ = self.tab_buscador
        fila = ttk.Frame(t_, padding=(0, 8, 0, 4))
        fila.pack(fill="x")
        self._t(ttk.Label(fila, style="Suave.TLabel"), "her_recurso").pack(side="left")
        self.ent_recurso = ttk.Entry(fila)
        self.ent_recurso.pack(side="left", fill="x", expand=True, padx=(6, 6))
        self.ent_recurso.bind("<Return>", lambda e: self.buscar_recurso())
        self._t(ttk.Label(fila, style="Suave.TLabel"), "her_tipo").pack(side="left")
        self.combo_tipo_recurso = ttk.Combobox(fila, state="readonly", width=14)
        self.combo_tipo_recurso.pack(side="left", padx=(4, 6))
        self._preparar_combo_tipo_recurso()
        idiomas.registrar(self._preparar_combo_tipo_recurso)
        self._t(ttk.Button(fila, command=self.buscar_recurso), "comun_buscar").pack(side="left")

        # El buscador global es lo unico que necesita un indice grande. Cuando el ejecutable no lo
        # trae empaquetado (version publica), se construye AQUI: avisa de que tarda, muestra el
        # progreso y deja cancelar. Se guarda junto al ejecutable, asi que solo se hace una vez.
        # Se empaqueta ANTES que la tabla (side=bottom) para que la tabla no aplaste estos
        # controles: al ser la tabla la que se estira, no puede robarles el sitio.
        fila_ind = ttk.Frame(t_, style="Panel.TFrame", padding=(10, 6))
        fila_ind.pack(side="bottom", fill="x", pady=(8, 0))
        self.progreso_indice = ttk.Progressbar(fila_ind, mode="determinate", maximum=100,
                                               length=180)
        self.progreso_indice.pack(side="right", padx=(8, 0))
        self.boton_indice = ttk.Button(fila_ind, command=self.construir_indice)
        self._t(self.boton_indice, "her_sync_construir")
        self.boton_indice.pack(side="right", padx=(8, 0))
        self.boton_indice_cancelar = ttk.Button(fila_ind, command=self._cancelar_indice,
                                                state="disabled")
        self._t(self.boton_indice_cancelar, "her_sync_cancelar")
        self.boton_indice_cancelar.pack(side="right")
        self.etiq_indice = ttk.Label(fila_ind, style="Panel.TLabel", wraplength=560,
                                     justify="left")
        self.etiq_indice.pack(side="left")
        self._cancelar_sync = False

        pie = ttk.Frame(t_, padding=(0, 6, 0, 2))
        pie.pack(side="bottom", fill="x")
        self.etiq_recursos = ttk.Label(pie, text="", style="Suave.TLabel")
        self.etiq_recursos.pack(side="left")
        self._t(ttk.Button(pie, command=self.recurso_al_inspector),
                "her_ver_bundle").pack(side="right")
        self._t(ttk.Button(pie, command=lambda: self.recurso_exportar()),
                "her_exportar_bundle").pack(side="right", padx=(0, 6))

        marco, self.arbol_recursos = self._arbol(
            t_, ("her_col_recurso", "her_col_tipo3", "her_col_bundle"), (420, 130, 320))
        marco.pack(fill="both", expand=True)

    def _preparar_combo_tipo_recurso(self):
        actual = self.combo_tipo_recurso.get()
        valores = [t("comun_todo")] + tipos_de_recurso()
        self.combo_tipo_recurso.config(values=valores)
        self.combo_tipo_recurso.set(actual if actual in valores else valores[0])

    def buscar_recurso(self):
        texto = self.ent_recurso.get().strip().lower()
        if len(texto) < 2:
            messagebox.showinfo(ajustes.NOMBRE, t("her_msg_dos_letras"))
            return
        tipo = self.combo_tipo_recurso.get().strip()
        todos = indice_recursos()
        if not todos:
            # sin indice no hay nada que buscar: se ofrece construirlo (es lo honesto)
            if messagebox.askyesno(ajustes.NOMBRE,
                                   t("her_sync_aviso", len(catalogo_bundles()))):
                self.construir_indice()
            return
        sel = []
        for nombre, tip, bundle in todos:
            if tipo and tipo != t("comun_todo") and tip != tipo:
                continue
            if texto in (nombre or "").lower():
                sel.append((nombre, tip, bundle))
            if len(sel) >= 5000:
                break
        self._filas_recursos = sel
        self.arbol_recursos.delete(*self.arbol_recursos.get_children())
        for nombre, tip, bundle in sel:
            self.arbol_recursos.insert("", "end", values=(nombre, tip, bundle))
        self.etiq_recursos.config(
            text=t("her_coincidencias", len(sel), len(todos)))
        self.registrar(t("her_log_buscador", texto, len(sel)))

    # ---------------------------------------------------------------- indice de recursos
    def _actualizar_estado_indice(self):
        """Dice si el buscador ya tiene indice (y de donde sale) o si hay que construirlo."""
        try:
            est = indice_recursos_estado()
        except Exception:
            est = {"disponible": False, "n": 0, "bundles": 0}
        if est.get("disponible") and est.get("parcial"):
            # hay indice, pero recortado: se dice con cuantos bundles cuenta, en vez de dar por
            # bueno un indice que solo mira parte del juego.
            self.etiq_indice.config(
                text=t("her_sync_parcial", est.get("bundles_cubiertos", 0), est.get("bundles", 0),
                       est.get("n", 0)), foreground=COLOR_AVISO)
            self.boton_indice.config(state="normal")
        elif est.get("disponible"):
            self.etiq_indice.config(text=t("her_sync_listo", est["n"], est["bundles"]),
                                    foreground=COLOR_OK)
            self.boton_indice.config(state="disabled")
        else:
            self.etiq_indice.config(text=t("her_sync_aviso_corto", est.get("bundles", 0)),
                                    foreground=COLOR_AVISO)
            self.boton_indice.config(state="normal")

    def construir_indice(self):
        """Lanza la construccion del indice del buscador (avisa, mide y deja cancelar)."""
        if self.trabajando:
            messagebox.showinfo(ajustes.NOMBRE, t("msg_ocupado"))
            return
        try:
            total = len(catalogo_bundles())
        except Exception:
            total = 0
        if not total:
            messagebox.showwarning(ajustes.NOMBRE, t("her_sync_sin_bundles"))
            return
        if not messagebox.askyesno(ajustes.NOMBRE, t("her_sync_confirmar", total)):
            return
        self._cancelar_sync = False
        self.boton_indice.config(state="disabled")
        self.boton_indice_cancelar.config(state="normal")
        self.progreso_indice["value"] = 0
        self.etiq_indice.config(text=t("her_sync_empezando"), foreground=COLOR_TEXTO)

        def progreso(hechos, total_b):
            self.cola.put(("indice_progreso", (hechos, total_b)))

        def trabajo():
            recursos = construir_indice_recursos(
                progreso=progreso, cancelar=lambda: self._cancelar_sync,
                log=lambda s: self.cola.put(("log", s)))
            self.cola.put(("indice_fin", len(recursos)))
        self._en_hilo(trabajo)

    def _cancelar_indice(self):
        self._cancelar_sync = True
        self.boton_indice_cancelar.config(state="disabled")
        self.registrar(t("her_sync_cancelando"))

    def recurso_al_inspector(self):
        sel = self.arbol_recursos.selection()
        if not sel:
            return
        i = self.arbol_recursos.index(sel[0])
        if not (0 <= i < len(self._filas_recursos)):
            return
        _, _, bundle = self._filas_recursos[i]
        self.ent_ruta.delete(0, "end")
        self.ent_ruta.insert(0, bundle)
        self.cuaderno.select(self.tab_inspector)
        self.abrir_inspector()

    def recurso_exportar(self):
        sel = self.arbol_recursos.selection()
        if not sel:
            return
        i = self.arbol_recursos.index(sel[0])
        if not (0 <= i < len(self._filas_recursos)):
            return
        _, tip, bundle = self._filas_recursos[i]
        tipos = {"Mesh": "mesh", "Texture2D": "tex2d"}.get(tip, "mesh,tex2d")
        self._exportar_async(bundle, tipos, "resources")

    # ============================================================ TEXTURAS
    def _construir_texturas(self):
        t_ = self.tab_texturas
        fila = ttk.Frame(t_, padding=(0, 8, 0, 4))
        fila.pack(fill="x")
        self._t(ttk.Label(fila, style="Suave.TLabel"), "her_carpeta").pack(side="left")
        self.ent_carpeta_img = ttk.Entry(fila)
        self.ent_carpeta_img.pack(side="left", fill="x", expand=True, padx=(6, 6))
        self._t(ttk.Button(fila, command=self.elegir_carpeta_imgs),
                "her_elegir_carpeta").pack(side="left")
        self._t(ttk.Button(fila, command=self.listar_imagenes),
                "her_listar_imagenes").pack(side="left", padx=(6, 0))

        cuerpo = ttk.Frame(t_)
        cuerpo.pack(fill="both", expand=True)
        izq = ttk.Frame(cuerpo)
        izq.pack(side="left", fill="y")
        barra = ttk.Scrollbar(izq, orient="vertical")
        self.lista_imgs = tk.Listbox(izq, width=42, bg=COLOR_PANEL, fg=COLOR_TEXTO,
                                     selectbackground=COLOR_ACENTO, selectforeground="#ffffff",
                                     font=("Consolas", 9), bd=0, highlightthickness=0,
                                     yscrollcommand=barra.set, activestyle="none")
        barra.config(command=self.lista_imgs.yview)
        barra.pack(side="right", fill="y")
        self.lista_imgs.pack(side="left", fill="both", expand=True)
        self.lista_imgs.bind("<<ListboxSelect>>", lambda e: self.mostrar_imagen())

        der = ttk.Frame(cuerpo, style="Panel.TFrame", padding=6)
        der.pack(side="right", fill="both", expand=True, padx=(10, 0))
        self.lienzo = tk.Canvas(der, bg=COLOR_PANEL, highlightthickness=0)
        self.lienzo.pack(fill="both", expand=True)
        self.info_img = self._t(ttk.Label(der, style="SuavePanel.TLabel"), "her_elige_imagen")
        self.info_img.pack(anchor="w", pady=(4, 0))

    def elegir_carpeta_imgs(self):
        inicial = self.ent_carpeta_img.get().strip() or str(self._destino())
        carpeta = filedialog.askdirectory(title=t("dlg_carpeta_img_titulo"),
                                          initialdir=inicial)
        if carpeta:
            self.ent_carpeta_img.delete(0, "end")
            self.ent_carpeta_img.insert(0, carpeta)
            self.listar_imagenes()

    def listar_imagenes(self):
        carpeta = self.ent_carpeta_img.get().strip()
        self.lista_imgs.delete(0, "end")
        self._imgs = imagenes_de(carpeta) if carpeta else []
        for p in self._imgs:
            self.lista_imgs.insert("end", "  %s" % p.name)
        self.info_img.config(text=t("her_n_imagenes", len(self._imgs)))
        if not self._imgs:
            self.lienzo.delete("all")
            self.lienzo.create_text(20, 20, anchor="nw", fill=COLOR_SUAVE,
                                    text=t("her_sin_imagenes"))

    def mostrar_imagen(self):
        sel = self.lista_imgs.curselection()
        if not sel or not getattr(self, "_imgs", None):
            return
        ruta = self._imgs[sel[0]]
        try:
            from PIL import Image, ImageTk
        except Exception as e:
            self.info_img.config(text=t("her_sin_pillow", e))
            return
        try:
            img = Image.open(ruta)
            ancho, alto = img.size
            modo = img.mode
            w = max(self.lienzo.winfo_width(), 200)
            h = max(self.lienzo.winfo_height(), 200)
            img.thumbnail((w - 12, h - 12))
            self._imagen = ImageTk.PhotoImage(img)
            self.lienzo.delete("all")
            self.lienzo.create_image(6, 6, anchor="nw", image=self._imagen)
            self.info_img.config(text="%s   %dx%d px   %s   (%.0f KB)"
                                 % (ruta.name, ancho, alto, modo, ruta.stat().st_size / 1024))
        except Exception as e:
            self.lienzo.delete("all")
            self.lienzo.create_text(20, 20, anchor="nw", fill=COLOR_AVISO,
                                    text=t("her_err_imagen", e))

    # ============================================================ VIDEO Y AUDIO
    def _construir_media(self):
        t_ = self.tab_media
        est = ttk.Frame(t_, style="Panel.TFrame", padding=(10, 5))
        est.pack(fill="x", pady=(4, 3))
        fila_herr = ttk.Frame(est, style="Panel.TFrame")
        fila_herr.pack(fill="x")
        self._t(ttk.Label(fila_herr, style="Panel.TLabel", font=("Segoe UI Semibold", 10)),
                "her_herr_externas").pack(side="left", padx=(0, 12))
        # Las cuatro herramientas en UNA fila y con el nombre corto ("wannacri ✓"). Antes eran
        # cuatro filas con la descripcion larga: gastaba ~80 px de alto que aqui no sobran.
        self.etiquetas_herr = {}
        self._clave_texto_herr = {}
        for clave, clave_texto in (("wannacri", "her_wannacri"), ("vgmstream", "her_vgmstream"),
                                   ("ffmpeg", "her_ffmpeg"), ("motor", "her_motor")):
            et = ttk.Label(fila_herr, text=t("comun_comprobando"), style="SuavePanel.TLabel")
            et.pack(side="left", padx=(0, 14))
            self.etiquetas_herr[clave] = et
            self._clave_texto_herr[clave] = clave_texto
        self._estado_herr = None
        idiomas.registrar(self._refrescar_herr)
        # los botones van a la derecha de la cabecera, no en una fila propia: roba alto
        self._t(ttk.Button(fila_herr, command=self.comprobar_herramientas),
                "her_comprobar_herr").pack(side="right")
        # El motor (AssetStudioModCLI) es lo unico que no viaja dentro del ejecutable: pesa 16 MB y
        # engordaria el binario. Se descarga solo, a peticion, y queda en `engine/` junto al
        # programa. Sin el, el inspector y las exportaciones no pueden abrir los bundles.
        self._t(ttk.Button(fila_herr, command=self.descargar_dependencias),
                "her_deps_boton").pack(side="right", padx=(0, 6))
        self._t(ttk.Button(fila_herr, command=self.descargar_motor),
                "her_descargar_motor").pack(side="right", padx=(0, 6))

        fila = ttk.Frame(t_, padding=(0, 2, 0, 4))
        fila.pack(fill="x")
        self._t(ttk.Label(fila, style="Suave.TLabel"), "her_mostrar").pack(side="left")
        self.combo_media = ttk.Combobox(fila, state="readonly", width=16)
        self.combo_media.pack(side="left", padx=(4, 8))
        self._preparar_combo_media()
        idiomas.registrar(self._preparar_combo_media)
        self.combo_media.bind("<<ComboboxSelected>>", lambda e: self.pintar_media())
        self._t(ttk.Button(fila, command=self.listar_media, padding=(8, 3)),
                "her_listar").pack(side="left")
        self.etiq_media = ttk.Label(fila, text="", style="Suave.TLabel")
        self.etiq_media.pack(side="left", padx=(10, 0))
        # el boton de abrir la carpeta va aqui arriba, no en el panel derecho: alli robaba 48 px
        # de alto y dejaba los botones de extraer aplastados a 1 px
        self._t(ttk.Button(fila, command=self.abrir_salida, padding=(8, 3)),
                "her_abrir_salida").pack(side="right")

        self._t(ttk.Label(t_, style="Suave.TLabel", wraplength=760, justify="left"),
                "her_leyenda_audio").pack(anchor="w", pady=(0, 4))

        # El detalle del elegido ocupa una linea al pie de la pestana. Antes vivia en el panel
        # derecho, pero ahi no cabia (la ventana publica es mas baja) y dejaba los botones de
        # extraer aplastados a 1 px.
        self.etiq_sel_media = ttk.Label(t_, text="", style="Suave.TLabel", wraplength=1120,
                                        justify="left")
        self.etiq_sel_media.pack(side="bottom", anchor="w", pady=(4, 0))

        cuerpo = ttk.Frame(t_)
        cuerpo.pack(fill="both", expand=True)
        # el panel derecho se reserva primero, para que la lista no lo empuje fuera (ver explorador)
        der = ttk.Frame(cuerpo, style="Panel.TFrame", padding=10, width=290)
        der.pack(side="right", fill="y", padx=(10, 0))
        der.pack_propagate(False)
        self._t(ttk.Label(der, style="Panel.TLabel", font=("Segoe UI Semibold", 10)),
                "her_extraer_elegido").pack(anchor="w")
        self._t(ttk.Label(der, style="SuavePanel.TLabel", wraplength=266),
                "her_media_ayuda").pack(anchor="w", pady=(4, 6))
        # los dos botones en paralelo (apilados no caben: el panel derecho no da tanto alto)
        par = ttk.Frame(der, style="Panel.TFrame")
        par.pack(fill="x")
        par.columnconfigure(0, weight=1)
        par.columnconfigure(1, weight=1)
        self.boton_video = self._t(ttk.Button(par, command=self.extraer_video_sel,
                                              padding=(8, 3)), "her_extraer_mp4")
        self.boton_video.grid(row=0, column=0, sticky="ew")
        self.boton_audio = self._t(ttk.Button(par, command=self.extraer_audio_sel,
                                              padding=(8, 3)), "her_extraer_wav")
        self.boton_audio.grid(row=0, column=1, sticky="ew", padx=(6, 0))

        izq = ttk.Frame(cuerpo)
        izq.pack(side="left", fill="both", expand=True)
        barra = ttk.Scrollbar(izq, orient="vertical")
        self.lista_media = tk.Listbox(izq, bg=COLOR_PANEL, fg=COLOR_TEXTO,
                                      selectbackground=COLOR_ACENTO, selectforeground="#ffffff",
                                      font=("Consolas", 9), bd=0, highlightthickness=0,
                                      yscrollcommand=barra.set, activestyle="none")
        barra.config(command=self.lista_media.yview)
        barra.pack(side="right", fill="y")
        self.lista_media.pack(side="left", fill="both", expand=True)
        self.lista_media.bind("<<ListboxSelect>>", lambda e: self.detalle_media())

    def _preparar_combo_media(self):
        """(Re)llena el desplegable Videos/Audio conservando la eleccion (por indice)."""
        i = self.combo_media.current()
        self.combo_media.config(values=[t("her_videos"), t("her_audios")])
        self.combo_media.current(i if i >= 0 else 0)

    def comprobar_herramientas(self):
        def trabajo():
            est = estado_herramientas()
            self.cola.put(("herr", est))
        self._en_hilo(trabajo)
        # el resultado llega por cola; se pinta cuando llegue
        self.cola.put(("log", t("her_log_comprobando_herr")))

    def descargar_dependencias(self):
        """Baja TODO lo que la herramienta necesita (motor, wannacri, vgmstream y ffmpeg).

        El progreso se ve en una ventana con consola de solo lectura. Es la version para la
        interfaz clasica del mismo boton que tiene la nueva: en un equipo sin WebView2 esta es la
        unica forma de dejar la herramienta completa.
        """
        if self.trabajando:
            messagebox.showinfo(ajustes.NOMBRE, t("msg_ocupado"))
            return
        if not messagebox.askyesno(ajustes.NOMBRE,
                                   t("her_deps_confirmar", dependencias.peso_aproximado_mb())):
            return
        ventana = VentanaDependencias(self.winfo_toplevel())

        def progreso(linea):
            # desde el hilo no se puede tocar la interfaz: se pide al bucle principal
            try:
                ventana.after(0, ventana.append, linea)
            except Exception:  # noqa: BLE001
                pass
            self.cola.put(("log", str(linea)))

        def trabajo():
            try:
                r = dependencias.asegurar_todas(progreso=progreso)
                if r["fallos"]:
                    progreso(t("her_deps_fallo", "; ".join("%s: %s" % (k, v)
                                                           for k, v in r["fallos"].items())))
                else:
                    progreso(t("her_deps_listo"))
            finally:
                self.cola.put(("herr", estado_herramientas()))

        self._en_hilo(trabajo)

    def descargar_motor(self):
        """Baja el motor AssetStudioModCLI si falta (lo unico que la version publica no lleva)."""
        if self.trabajando:
            messagebox.showinfo(ajustes.NOMBRE, t("msg_ocupado"))
            return
        if dependencias.ruta_assetstudio():
            self.registrar(t("her_motor_ya"))
            self.comprobar_herramientas()
            return
        if not messagebox.askyesno(ajustes.NOMBRE, t("her_motor_confirmar")):
            return

        def trabajo():
            try:
                exe = dependencias.asegurar_assetstudio(
                    progreso=lambda s: self.cola.put(("log", s)))
                self.cola.put(("log", t("her_motor_listo", str(exe))))
            except Exception as e:
                self.cola.put(("error", str(e)))
            self.cola.put(("herr", estado_herramientas()))
        self._en_hilo(trabajo)

    def _pintar_estado_herr(self, est):
        self._estado_herr = est or {}
        self._refrescar_herr()

    def _refrescar_herr(self):
        """Redibuja los distintivos de las herramientas externas (fila unica, nombre corto).

        El nombre corto sale de la propia etiqueta larga: "wannacri (.usm -> video)" -> "wannacri".
        """
        if self._estado_herr is None:
            return
        for clave, et in self.etiquetas_herr.items():
            clave_texto = self._clave_texto_herr.get(clave, clave)
            corto = t(clave_texto).split(" (")[0]
            if self._estado_herr.get(clave):
                et.config(text=t("her_herr_ok", corto), foreground=COLOR_OK)
            else:
                et.config(text=t("her_herr_no", corto), foreground=COLOR_AVISO)

    def listar_media(self):
        datos = listar_media()
        self._media = datos
        if not datos.get("carpeta"):
            self.etiq_media.config(text=t("her_no_carpeta_media"))
            self.lista_media.delete(0, "end")
            self.registrar(t("her_log_no_media"))
            return
        self.pintar_media()

    _COLOR_ESTADO = {"audio": COLOR_OK, "silencio": COLOR_AVISO,
                     "mudo": COLOR_SUAVE, "sin_dato": COLOR_SUAVE}
    _CLAVE_ESTADO = {"audio": "her_video_con_audio", "mudo": "her_video_sin_audio",
                     "silencio": "her_video_silencio", "sin_dato": "her_video_sin_dato"}

    def pintar_media(self):
        es_audio = self.combo_media.current() == 1
        lista = self._media.get("awb" if es_audio else "usm", [])
        self.lista_media.delete(0, "end")
        self._media_sel = lista
        for i, m in enumerate(lista):
            if es_audio:
                self.lista_media.insert("end", "  %-46s %8.1f MB" % (m["nombre"], m["mb"]))
                continue
            estado = m.get("estado", "sin_dato")
            badge = t(self._CLAVE_ESTADO.get(estado, "her_video_sin_dato"))
            self.lista_media.insert("end", "%s %-38s %8.1f MB" % (badge, m["nombre"], m["mb"]))
            self.lista_media.itemconfig(i, foreground=self._COLOR_ESTADO.get(estado, COLOR_SUAVE))
        resumen = ""
        if not es_audio and lista:
            n = {e: sum(1 for m in lista if m.get("estado") == e)
                 for e in ("audio", "silencio", "mudo")}
            resumen = "   —   " + t("her_media_resumen", n["audio"], n["silencio"], n["mudo"])
        self.etiq_media.config(text=t("her_ficheros_en", len(lista),
                                      self._media.get("carpeta", "")) + resumen)

    def detalle_media(self):
        sel = self.lista_media.curselection()
        if not sel or not getattr(self, "_media_sel", None):
            return
        m = self._media_sel[sel[0]]
        texto = "%s\n%.1f MB" % (m["nombre"], m["mb"])
        estado = m.get("estado")
        if estado:
            texto += "\n" + t(self._CLAVE_ESTADO.get(estado, "her_video_sin_dato"))
            reg = _estados_audio().get(Path(m["nombre"]).stem)
            if isinstance(reg, dict) and reg.get("banco"):
                texto += "\n%s / %s" % (reg["banco"], reg.get("pista", ""))
        self.etiq_sel_media.config(text=texto)

    def _media_elegido(self):
        sel = self.lista_media.curselection()
        if not sel or not getattr(self, "_media_sel", None):
            messagebox.showinfo(ajustes.NOMBRE, t("her_msg_elige_fichero"))
            return None
        return self._media_sel[sel[0]]

    def extraer_video_sel(self):
        m = self._media_elegido()
        if not m:
            return
        destino = self._destino("media")

        def trabajo():
            self.cola.put(("log", t("her_log_extrayendo_video", m["nombre"])))
            salida = extraer_video(m["ruta"], destino, lambda s: self.cola.put(("log", s)))
            self.cola.put(("estado", t("her_estado_video_listo", salida.name)))
            self.cola.put(("log", t("her_log_video_extraido", salida)))
        self._en_hilo(trabajo)

    def extraer_audio_sel(self):
        m = self._media_elegido()
        if not m:
            return
        destino = self._destino("media")

        def trabajo():
            self.cola.put(("log", t("her_log_extrayendo_audio", m["nombre"])))
            salidas = extraer_audio(m["ruta"], destino, lambda s: self.cola.put(("log", s)))
            self.cola.put(("estado", t("her_estado_audio_listo", len(salidas))))
        self._en_hilo(trabajo)

    def abrir_salida(self):
        destino = self._destino("media")
        try:
            os.startfile(str(destino))  # type: ignore[attr-defined]
        except Exception:
            subprocess.Popen(["explorer", str(destino)])

    # ============================================================ exportar (comun)
    def _exportar_async(self, ruta_rel, tipos, subcarpeta):
        if not ruta_rel:
            return
        destino = self._destino(subcarpeta)
        self.estado.config(text=t("her_exportando", tipos))

        def trabajo():
            self.cola.put(("log", t("her_log_exportando", ruta_rel, destino)))
            exportar_bundle(ruta_rel, tipos, destino, lambda s: self.cola.put(("log", s)))
            n = sum(1 for _ in Path(destino).rglob("*") if _.is_file())
            self.cola.put(("log", t("her_log_n_ficheros", n)))
            self.cola.put(("estado", t("her_estado_exportado", destino)))
            self.registrar(t("her_log_export_terminada", destino))
        self._en_hilo(trabajo)

    # ------------------------------------------------------------------ primer arranque
    def arrancar(self):
        """Rellena el explorador y comprueba las herramientas la primera vez que se abre."""
        self.explorar()
        self.comprobar_herramientas()
        self._actualizar_estado_indice()
        self.after(600, self.listar_media)