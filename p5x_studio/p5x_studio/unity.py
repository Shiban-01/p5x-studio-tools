"""Ruta de Unity: el modelo completo, con esqueleto y expresiones.

Por que hace falta una segunda ruta: los bundles del juego traen las mallas por un lado y el
esqueleto por otro, **sin jerarquia de renderers**. Los SkinnedMeshRenderer se montan en tiempo de
ejecucion desde el manifiesto del rig, asi que ningun exportador externo (ni el motor de extraccion
que usa el resto de la herramienta) puede producir un FBX ya riggeado: solo ve piezas sueltas.

Unity si tiene esa piel montada. Por eso el modelo con huesos, pesos y expresiones faciales se saca
cargando el proyecto decompilado en el Editor y volcando los datos desde ahi.

Esta ruta NO es obligatoria: sin ella la herramienta entrega geometria, texturas y materiales, que
es todo lo que hace falta para esculpir, renderizar o retocar. Con ella, ademas, el modelo se puede
animar.

Requisitos, y conviene decirlo claro: el usuario necesita el juego decompilado a un proyecto de
Unity (AssetRipper lo hace) y el Editor instalado. No se instala solo.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from . import ajustes
from .idiomas import t

# Los nombres de las piezas de un rig, tal como los deja el decompilador.
SUFIJOS_RIG = ("body_wholeexport_rig", "face_wholeexport_rig", "hair_wholeexport_rig",
               "face_wholeexport_rig_bs", "weapon_wholeexport_rig")


# --------------------------------------------------------------------------- localizar Unity

def ruta_unity() -> Path | None:
    """Ejecutable del Editor de Unity.

    Se mira primero la ruta que fije el usuario, luego las instalaciones habituales. Ojo: el Hub
    instala por defecto en `C:\\Program Files\\Unity\\Hub\\Editor`, pero tambien se puede instalar
    suelto en `C:\\Users\\<usuario>\\Unity\\<version>\\Editor`, que es donde acaba a menudo.
    """
    fijada = ajustes._leer_config().get("ruta_unity")
    if fijada and Path(fijada).is_file():
        return Path(fijada)

    candidatos: list[Path] = []
    hogar = Path(os.path.expanduser("~"))
    for raiz in (Path(r"C:\Program Files\Unity\Hub\Editor"),
                 Path(r"C:\Program Files\Unity"),
                 hogar / "Unity",
                 Path(os.path.expandvars(r"%LOCALAPPDATA%\Unity"))):
        if raiz.is_dir():
            candidatos += sorted(raiz.glob("*/Editor/Unity.exe"), reverse=True)
            candidatos += sorted(raiz.glob("Editor/Unity.exe"), reverse=True)
    for c in candidatos:
        if c.is_file():
            return c
    return None


# --------------------------------------------------------------------------- localizar el proyecto

def _es_proyecto_unity(ruta: Path) -> bool:
    return (ruta / "Assets").is_dir() and (ruta / "ProjectSettings").is_dir()


def buscar_proyecto() -> Path | None:
    """Proyecto de Unity decompilado, si la herramienta sabe donde esta.

    Se acepta tanto el proyecto entero como su carpeta `ExportedProject`, que es lo que deja
    AssetRipper dentro de una carpeta propia. Se mira, por orden: lo que fije la configuracion, la
    variable de entorno `P5X_PROYECTO_UNITY`, y las carpetas habituales de este proyecto (debajo de
    `p5x-datamining/unity_com` y `unity_projects`), para no obligar a escribirlo a mano.
    """
    fijado = ajustes._leer_config().get("proyecto_unity") or os.environ.get("P5X_PROYECTO_UNITY")
    candidatos: list[Path] = []
    if fijado:
        p = Path(fijado)
        candidatos += [p, p / "ExportedProject"]
    hogar = Path(os.path.expanduser("~"))
    for raiz in (hogar / "p5x-datamining/unity_com", hogar / "p5x-datamining/unity_projects",
                 hogar / "p5x-datamining/unity_com/RipperProj"):
        if raiz.is_dir():
            candidatos.append(raiz)
            candidatos.append(raiz / "ExportedProject")
            candidatos += sorted(raiz.glob("*/ExportedProject"))
    for cand in candidatos:
        if _es_proyecto_unity(cand):
            return cand
    return None


# --------------------------------------------------------------------------- rigs del personaje

def rigs_del_personaje(proyecto: Path, personaje: str) -> list[str]:
    """Nombres de los prefabs de rig del personaje dentro del proyecto decompilado.

    Esto sustituye a la lista que en el capturador original estaba escrita a mano para un solo
    personaje: se pregunta al propio proyecto que rigs tiene, buscando los prefabs cuyo nombre
    empieza por el identificador del personaje (`PC079_01`) y termina en uno de los sufijos de rig.
    """
    assets = proyecto / "Assets"
    if not assets.is_dir():
        return []
    prefijo = personaje.lower()
    encontrados: set[str] = set()
    for p in assets.rglob("*.prefab"):
        nombre = p.stem
        bajo = nombre.lower()
        if not bajo.startswith(prefijo):
            continue
        if any(s in bajo for s in SUFIJOS_RIG):
            encontrados.add(nombre)
    return sorted(encontrados)


def resumen_de_ruta(proyecto: Path | None = None, personaje: str | None = None) -> dict:
    """Estado de la ruta de Unity, para que la interfaz lo pueda contar sin sorpresas."""
    unity = ruta_unity()
    proy = proyecto or buscar_proyecto()
    datos = {
        "unity": str(unity) if unity else None,
        "proyecto": str(proy) if proy else None,
        "rigs": [],
        "listo": bool(unity and proy),
    }
    if proy and personaje:
        datos["rigs"] = rigs_del_personaje(proy, personaje)
        datos["listo"] = bool(unity and datos["rigs"])
    return datos


# --------------------------------------------------------------------------- capturador en lote

# El capturador que se copia al proyecto: es el que monta la piel (que los bundles traen sin
# jerarquia de renderers) y vuelca huesos, pesos e inversas de bind.
SCRIPT_CAPTURADOR = "P5XSkeletonExport.cs"
CLASE_CAPTURADOR = "P5XSkeletonExport"
# Unity tarda en arrancar y compilar; el volcado en si es rapido. 15 min es techo de sobra.
ESPERA_UNITY = 900


def _ruta_recurso(nombre: str) -> Path:
    if getattr(sys, "frozen", False) and getattr(sys, "_MEIPASS", None):
        return Path(sys._MEIPASS) / "p5x_studio" / nombre
    return Path(__file__).resolve().parent / nombre


def instalar_capturador(proyecto: Path) -> Path:
    """Copia el script del capturador dentro de `Assets/Editor/` del proyecto decompilado.

    Hay que hacerlo porque el script tiene que estar en el proyecto para que Unity lo compile y lo
    pueda ejecutar con `-executeMethod`; no se puede pasar desde fuera. Se copia solo si falta o si
    ha cambiado, para no ensuciar el proyecto en cada extraccion.
    """
    origen = _ruta_recurso(SCRIPT_CAPTURADOR)
    if not origen.is_file():
        raise RuntimeError(t("un_err_capturador", SCRIPT_CAPTURADOR))
    destino = Path(proyecto) / "Assets/Editor" / SCRIPT_CAPTURADOR
    destino.parent.mkdir(parents=True, exist_ok=True)
    nuevo = origen.read_bytes()
    if not destino.is_file() or destino.read_bytes() != nuevo:
        destino.write_bytes(nuevo)
    return destino


def exportar_esqueleto(proyecto: Path, personaje: str, dump: Path, log=None,
                       timeout: int = ESPERA_UNITY) -> dict:
    """Lanza Unity en lote para volcar el modelo con esqueleto y pesos de piel.

    Es el unico paso que no se puede hacer desde fuera de Unity: los bundles traen las mallas y el
    esqueleto por separado, sin jerarquia de renderers, asi que la piel solo existe montada dentro
    del Editor. El capturador recibe el personaje por variables de entorno (un script de
    `Assets/Editor` no acepta argumentos de linea de comandos) y deja el volcado en `dump`.

    Devuelve el resumen que escribio el capturador, o levanta RuntimeError con el log real.
    """
    def di(t):
        if log:
            log(t)

    unity = ruta_unity()
    if not unity:
        raise RuntimeError(t("un_err_no_editor"))
    proyecto = Path(proyecto)
    if not _es_proyecto_unity(proyecto):
        raise RuntimeError(t("un_err_proyecto", proyecto))

    di(t("un_copiando"))
    instalar_capturador(proyecto)

    dump = Path(dump)
    if dump.exists():
        shutil.rmtree(dump, ignore_errors=True)
    dump.mkdir(parents=True, exist_ok=True)
    ruta_log_unity = dump / "unity_editor.log"

    entorno = dict(os.environ)
    entorno.update({
        "P5X_ACTOR": personaje.upper(),
        "P5X_DUMP": str(dump),
        "P5X_LOG": str(dump / "log.txt"),
    })
    orden = [str(unity), "-batchmode", "-quit", "-nographics",
             "-projectPath", str(proyecto),
             "-executeMethod", "%s.Run" % CLASE_CAPTURADOR,
             "-logFile", str(ruta_log_unity)]
    di(t("un_arrancando"))
    r = subprocess.run(orden, capture_output=True, text=True, timeout=timeout,
                       env=entorno, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))

    resumen_json = dump / "resumen.json"
    log_unity = ruta_log_unity.read_text(encoding="utf-8", errors="replace") \
        if ruta_log_unity.is_file() else ""
    if not resumen_json.is_file():
        compilacion = "Scripts have compiler errors" in log_unity
        pista = t("un_err_compila") if compilacion else t("un_revisa_log", ruta_log_unity)
        raise RuntimeError(t("un_err_volcado", r.returncode, pista))

    datos = json.loads(resumen_json.read_text(encoding="utf-8"))
    datos["dump"] = str(dump)
    di(t("un_volcado_listo", datos.get("partes", 0), datos.get("mallas_con_pesos", 0),
         datos.get("huesos_unicos", 0)))
    if datos.get("partes", 0) == 0:
        raise RuntimeError(t("un_err_malla", personaje, ruta_log_unity))
    return datos


if __name__ == "__main__":
    # uso: python -m p5x_studio.unity [PC079_01]
    quien = sys.argv[1] if len(sys.argv) > 1 else None
    info = resumen_de_ruta(personaje=quien)
    print(json.dumps(info, indent=2, ensure_ascii=False))