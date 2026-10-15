"""Dependencias: crea el entorno de la herramienta, instala lo que falta y avisa de actualizaciones.

La idea es que el usuario final no abra una consola nunca. La herramienta se construye su propio
entorno de Python dentro de su carpeta, instala ahi las librerias que necesita y, en cada arranque,
pregunta a PyPI si hay version nueva. Nada se instala en el Python del sistema.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

from . import ajustes
from .idiomas import t

# librerias necesarias y para que sirve cada una, en lenguaje llano
REQUISITOS = {
    "UnityPy": "reads the game files",
        "Pillow": "builds the model previews",
}

PYPI = "https://pypi.org/pypi/%s/json"


def entorno() -> Path:
    return ajustes.RAIZ / ".venv"


def python_entorno() -> Path | None:
    for rel in ("Scripts/python.exe", "bin/python"):
        p = entorno() / rel
        if p.exists():
            return p
    return None


def _ejecutar(orden: list[str], progreso=None, timeout: int = 120) -> tuple[int, str]:
    """Corre un proceso externo con un tope de tiempo.

    El tope era de 900 segundos, y sin conexion eso dejaba la ventana colgada quince minutos sin
    decir nada. Dos minutos sobran para instalar una dependencia o descargar el motor, y si algo
    se atasca el usuario se entera enseguida en vez de pensar que la app se ha muerto.
    """
    if progreso:
        progreso(t("dep_progreso_cmd", " ".join(orden[:3])))
    try:
        # errors="replace" no es cosmetico: las herramientas de Windows no siempre escriben UTF-8
        # (un simple `ping` en consola espanola mete bytes 0xa1), y sin esto la hebra que lee la
        # salida revienta con UnicodeDecodeError y el resultado se pierde.
        r = subprocess.run(orden, capture_output=True, text=True, errors="replace",
                           timeout=timeout)
        salida = (r.stdout or "") + (r.stderr or "")
        return r.returncode, salida
    except FileNotFoundError:
        return 127, t("dep_no_ejecutable")
    except subprocess.TimeoutExpired:
        return 124, t("dep_tardo")


def _uv_externo() -> str | None:
    """uv que ya hubiera en el equipo (PATH, ~/.local/bin, ~/.cargo/bin). No el nuestro."""
    for candidato in ("uv", str(Path.home() / ".local/bin/uv.exe"),
                      str(Path.home() / ".cargo/bin/uv.exe")):
        codigo, _ = _ejecutar([candidato, "--version"])
        if codigo == 0:
            return candidato
    return None


def _uv() -> str | None:
    """uv, prefiriendo el que viaja en la carpeta (asi no depende del equipo donde se abra)."""
    propio = carpeta_tools() / "uv" / "uv.exe"
    if propio.is_file():
        return str(propio)
    return _uv_externo()


def crear_entorno(progreso=None) -> Path:
    """Crea el entorno de la herramienta si no existe. Devuelve la ruta de su python."""
    ya = python_entorno()
    if ya:
        return ya
    entorno().parent.mkdir(parents=True, exist_ok=True)
    uv = _uv()
    if uv:
        if progreso:
            progreso(t("dep_creando_uv"))
        codigo, salida = _ejecutar([uv, "venv", str(entorno()), "--python", "3.11"], progreso)
        if codigo != 0:
            codigo, salida = _ejecutar([uv, "venv", str(entorno())], progreso)
        if codigo != 0 and progreso:
            progreso(t("dep_uv_fallo"))
    if not python_entorno():
        if progreso:
            progreso(t("dep_creando_sistema"))
        codigo, salida = _ejecutar([sys.executable, "-m", "venv", str(entorno())], progreso)
        if codigo != 0:
            raise RuntimeError(t("dep_err_entorno", salida[-400:]))
    py = python_entorno()
    if not py:
        raise RuntimeError(t("dep_err_python"))
    return py


def _instalar_con(py: Path, paquetes: list[str], progreso=None) -> tuple[int, str]:
    uv = _uv()
    if uv:
        codigo, salida = _ejecutar([uv, "pip", "install", "--python", str(py)] + paquetes, progreso)
        if codigo == 0:
            return 0, salida
    return _ejecutar([str(py), "-m", "pip", "install", "--upgrade"] + paquetes, progreso)


def versiones_instaladas(py: Path) -> dict[str, str]:
    codigo, salida = _ejecutar([str(py), "-c",
        "import json,importlib.metadata as m;"
        "print(json.dumps({n: m.version(n) for n in %r if True}))" % list(REQUISITOS)])
    if codigo != 0:
        # puede que no esten todas: se prueban una a una
        salida = {}
        for nombre in REQUISITOS:
            c, s = _ejecutar([str(py), "-c",
                              "import importlib.metadata as m; print(m.version(%r))" % nombre])
            salida[nombre] = s.strip() if c == 0 else ""
        return salida
    try:
        return json.loads(salida.strip().splitlines()[-1])
    except Exception:
        return {}


def faltantes(py: Path) -> list[str]:
    instaladas = versiones_instaladas(py)
    return [n for n in REQUISITOS if not instaladas.get(n)]


def asegurar_dependencias(progreso=None) -> Path:
    """Deja el entorno listo para trabajar. Es lo primero que llama la interfaz al arrancar.

    Congelada (.exe), UnityPy y Pillow ya viajan dentro del ejecutable, asi que no hay entorno que
    crear ni nada que instalar: se devuelve el propio ejecutable para que la interfaz no intente
    montar un .venv de solo lectura en la carpeta temporal.
    """
    if getattr(sys, "frozen", False):
        if progreso:
            progreso(t("dep_librerias_dentro"))
        return Path(sys.executable)
    py = crear_entorno(progreso)
    falta = faltantes(py)
    if falta:
        if progreso:
            progreso(t("dep_instalando", ", ".join(falta)))
        codigo, salida = _instalar_con(py, falta, progreso)
        if codigo != 0:
            raise RuntimeError(t("dep_err_instalar", salida[-600:]))
        if progreso:
            progreso(t("dep_instaladas"))
    return py


def ultima_version(nombre: str) -> str | None:
    """Version mas reciente publicada en PyPI, o None si no hay red."""
    try:
        with urllib.request.urlopen(PYPI % nombre, timeout=20) as r:
            return json.load(r)["info"]["version"]
    except Exception:
        return None


def _tupla(v: str) -> tuple:
    partes = []
    for trozo in (v or "0").split("."):
        digitos = "".join(c for c in trozo if c.isdigit())
        partes.append(int(digitos) if digitos else 0)
    return tuple(partes)


def revisar_actualizaciones(py: Path, progreso=None) -> list[dict]:
    """Compara lo instalado con lo publicado. Devuelve solo lo que tiene version nueva.

    Congelada no hay nada que actualizar: las librerias van dentro del .exe y se cambian
    reconstruyendolo.
    """
    if getattr(sys, "frozen", False):
        return []
    instaladas = versiones_instaladas(py)
    salida = []
    for nombre, para in REQUISITOS.items():
        actual = instaladas.get(nombre, "")
        ultima = ultima_version(nombre)
        if not ultima:
            continue
        if not actual or _tupla(ultima) > _tupla(actual):
            salida.append({"nombre": nombre, "instalada": actual or t("dep_sin_instalar"),
                           "disponible": ultima, "para": para})
            if progreso:
                progreso(t("dep_nueva", nombre, actual or t("dep_sin_instalar2"), ultima))
    return salida


def actualizar(py: Path, paquetes: list[str], progreso=None) -> None:
    if not paquetes:
        return
    codigo, salida = _instalar_con(py, paquetes, progreso)
    if codigo != 0:
        raise RuntimeError(t("dep_err_actualizar", salida[-600:]))


# --------------------------------------------------------------------------- motor de extraccion
#
# AssetStudioModCLI es el unico programa que abre los bundles cifrados de este juego. No es una
# libreria de Python: es un ejecutable. La herramienta lo descarga sola, lo guarda en su carpeta y
# avisa cuando hay version nueva. Si el usuario ya lo tiene en el escritorio, se aprovecha.

GITHUB_API = "https://api.github.com/repos/aelurum/AssetStudio/releases/latest"
NOMBRE_EXE = "AssetStudioModCLI.exe"


def carpeta_motor() -> Path:
    return ajustes.RAIZ / "engine"


def ruta_assetstudio() -> Path | None:
    """Ejecutable del motor: primero el de la herramienta, luego el que el usuario ya tuviera.

    El zip del motor se descomprime en una subcarpeta con su propio nombre, asi que hay que buscar
    dentro y no solo en la raiz; si no, la herramienta acaba dependiendo de la copia que el usuario
    tuviera en el escritorio sin darse cuenta.
    """
    motor = carpeta_motor()
    propio = motor / NOMBRE_EXE
    if propio.is_file():
        return propio
    if motor.is_dir():
        for hallado in motor.rglob(NOMBRE_EXE):
            if hallado.is_file():
                return hallado
    for candidato in Path.home().joinpath("Desktop").glob("AssetStudioModCLI*/**/" + NOMBRE_EXE):
        if candidato.is_file():
            return candidato
    for candidato in Path.home().glob("Downloads/AssetStudioModCLI*/**/" + NOMBRE_EXE):
        if candidato.is_file():
            return candidato
    return None


def version_assetstudio() -> str:
    """Version instalada, si se puede saber."""
    exe = ruta_assetstudio()
    if not exe:
        return ""
    marca = exe.parent / "version.txt"
    if marca.is_file():
        return marca.read_text(encoding="utf-8").strip()
    return t("dep_version_desconocida")


def _descargar(url: str, destino: Path, progreso=None) -> None:
    import zipfile
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporal = destino.with_suffix(".zip")
    if progreso:
        progreso(t("dep_descargando_motor"))
    with urllib.request.urlopen(url, timeout=300) as r, open(temporal, "wb") as f:
        total = int(r.headers.get("Content-Length") or 0)
        leido = 0
        while True:
            trozo = r.read(262144)
            if not trozo:
                break
            f.write(trozo)
            leido += len(trozo)
            if progreso and total:
                progreso(t("dep_descargando_pct", 100 * leido // total))
    if progreso:
        progreso(t("dep_descomprimiendo"))
    with zipfile.ZipFile(temporal) as z:
        z.extractall(destino)
    temporal.unlink(missing_ok=True)


def ultima_version_assetstudio() -> tuple[str, str] | None:
    """Devuelve (version, url) del ultimo release para Windows, o None sin red."""
    try:
        req = urllib.request.Request(GITHUB_API, headers={"User-Agent": "P5X-Studio"})
        with urllib.request.urlopen(req, timeout=30) as r:
            datos = json.load(r)
    except Exception:
        return None
    for activo in datos.get("assets", []):
        nombre = (activo.get("name") or "").lower()
        if "win64" in nombre and nombre.endswith(".zip") and "net9" in nombre:
            return datos.get("tag_name", ""), activo["browser_download_url"]
    for activo in datos.get("assets", []):
        nombre = (activo.get("name") or "").lower()
        if "win64" in nombre and nombre.endswith(".zip"):
            return datos.get("tag_name", ""), activo["browser_download_url"]
    return None


def asegurar_assetstudio(progreso=None, forzar: bool = False) -> Path:
    """Descarga el motor en NUESTRA carpeta si falta. Devuelve su ruta.

    Se mira primero si el usuario ya tenia su propia copia (escritorio o descargas): sirve para
    trabajar, pero la herramienta se baja la suya igualmente. Si no, la carpeta dejaria de valer
    tal cual en otro equipo en cuanto desapareciera esa copia de fuera, que es justo lo que no
    queremos.
    """
    if not forzar:
        propio = _busca_exe(carpeta_motor(), NOMBRE_EXE)
        if propio:
            return propio
        ajeno = ruta_assetstudio()
        if ajeno and progreso:
            progreso(t("dep_motor_ajeno", ajeno))
    info = ultima_version_assetstudio()
    if not info:
        raise RuntimeError(t("dep_err_descargar"))
    version, url = info
    carpeta = carpeta_motor()
    _descargar(url, carpeta, progreso)
    exe = ruta_assetstudio()
    if not exe:
        raise RuntimeError(t("dep_err_motor_exe"))
    (exe.parent / "version.txt").write_text(version or "", encoding="utf-8")
    if progreso:
        progreso(t("dep_motor_listo", version or t("dep_version_desconocida")))
    return exe


# --------------------------------------------------------------------------- herramientas externas
#
# Lo que NO viaja dentro del .exe, con su peso aproximado en MB (redondeado a lo que ocupa en
# disco). El numero es ORIENTATIVO y sirve para que el usuario sepa cuanto va a tardar y cuanto
# disco va a gastar ANTES de pulsar el boton. Si cambia con una version nueva, se ajusta aqui.
TAMANOS_MB = {"motor": 16, "uv": 40, "wannacri": 5, "vgmstream": 11, "ffmpeg": 105}

VGMSTREAM_REPO = "vgmstream/vgmstream"
FFMPEG_REPO = "BtbN/FFmpeg-Builds"
# paquete "essentials" de gyan.dev: es el que deja menos peso en disco (105 MB en un solo fichero)
FFMPEG_GYAN = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
# uv hace falta para montarle a wannacri su entorno de Python (y sabe bajarse el Python que falte).
# Tenerlo solo en el PATH del equipo no vale: en otro equipo puede no haberlo, y entonces se cae la
# extraccion de video. Se baja a tools/uv/ y a partir de ahi la carpeta se vale sola.
UV_URL = "https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-pc-windows-msvc.zip"


def peso_aproximado_mb() -> int:
    """Cuanto ocupan (mas o menos) las cuatro herramientas juntas."""
    return sum(TAMANOS_MB.values())


def ruta_propia(nombre: str) -> Path | None:
    """Ejecutable de una herramienta DENTRO de nuestra carpeta (None si no esta)."""
    if nombre == "motor":
        return _busca_exe(carpeta_motor(), "AssetStudioModCLI.exe")
    exes = {"uv": "uv.exe", "wannacri": "wannacri.exe", "vgmstream": "vgmstream-cli.exe",
            "ffmpeg": "ffmpeg.exe"}
    if nombre not in exes:
        return None
    return _busca_exe(carpeta_tools() / nombre, exes[nombre])


def dentro_de_carpeta(motor) -> dict:
    """Cual de las herramientas que hay esta FUERA de la carpeta de la herramienta.

    `motor` es `estado_herramientas()` (el de herramientas.py, que tambien las localiza fuera). La
    diferencia importa: la app aprovecha una copia de fuera que el usuario ya tuviera (su
    escritorio, su PATH) para poder trabajar, pero eso NO viaja al copiar la carpeta a otro equipo.
    Decir "instalado" a secas era enganoso.

    Devuelve {nombre: ruta_de_fuera} solo para las que estan fuera; las que faltan no salen (eso ya
    lo dice la propia lista) y las que estan dentro tampoco (no hay nada que avisar).
    """
    salida = {}
    for nombre in ORDEN:
        encontrada = motor.get(nombre)
        if not encontrada or ruta_propia(nombre):
            continue
        salida[nombre] = str(encontrada[0] if isinstance(encontrada, list) else encontrada)
    return salida


def carpeta_tools() -> Path:
    return ajustes.RAIZ / "tools"


def _busca_exe(carpeta: Path, nombre: str) -> Path | None:
    """El ejecutable dentro de una carpeta, aunque venga en subcarpeta propia.

    Los zip de estos programas traen su propia carpeta dentro (`vgmstream-win64/`,
    `ffmpeg-master-latest-win64-gpl/bin/`), asi que buscar solo en la raiz no vale.
    """
    if not carpeta.is_dir():
        return None
    for hallado in carpeta.rglob(nombre):
        if hallado.is_file():
            return hallado
    return None


def _ultimo_release(repo: str) -> dict | None:
    """JSON del ultimo release de un repo de GitHub, o None sin red."""
    try:
        req = urllib.request.Request("https://api.github.com/repos/%s/releases/latest" % repo,
                                     headers={"User-Agent": "P5X-Studio"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except Exception:
        return None


def _asset_por_patron(repo: str, claves: tuple, sobra: tuple = ()) -> tuple[str, str] | None:
    """(version, url) del asset cuyo nombre contiene TODAS las claves y ninguna de `sobra`.

    Se busca por patron y no por nombre exacto a proposito: los assets de estos repos cambian de
    nombre entre versiones, y un nombre fijo se rompe solo. Si no casa ninguno se devuelve None y
    quien llama lo dice con el enlace de la pagina de releases, en vez de fallar en silencio.
    """
    datos = _ultimo_release(repo)
    if not datos:
        return None
    for activo in datos.get("assets", []):
        nombre = (activo.get("name") or "").lower()
        if all(c in nombre for c in claves) and not any(s in nombre for s in sobra):
            return datos.get("tag_name", ""), activo.get("browser_download_url", "")
    return None


def asegurar_vgmstream(progreso=None) -> Path:
    """Descarga vgmstream-cli (lee el audio de los .acb/.awb del juego)."""
    exe = _busca_exe(carpeta_tools() / "vgmstream", "vgmstream-cli.exe")
    if exe:
        if progreso:
            progreso("vgmstream: already there")
        return exe
    info = _asset_por_patron(VGMSTREAM_REPO, ("win64",), ("vst", "foobar", "audacious"))
    if not info:
        raise RuntimeError("I can't find vgmstream for Windows on GitHub. It can be downloaded by "
                                   "hand from https://github.com/vgmstream/vgmstream/releases and dropped "
                                   "in tools/vgmstream/")
    version, url = info
    if progreso:
        progreso("vgmstream %s: downloading" % version)
    _descargar(url, carpeta_tools() / "vgmstream", progreso)
    exe = _busca_exe(carpeta_tools() / "vgmstream", "vgmstream-cli.exe")
    if not exe:
        raise RuntimeError("vgmstream downloaded but I can't find vgmstream-cli.exe")
    if progreso:
        progreso("vgmstream: ready in %s" % exe.parent)
    return exe


def _poda_ffmpeg(carpeta: Path) -> None:
    """Tira lo que no se usa del paquete de ffmpeg (reproductor, sonda, manual y cabeceras).

    Medido en esta maquina: el build estatico completo deja 497 MB en disco y el `lgpl-shared`
    154 MB; de ahi la eleccion de `essentials` (105 MB) mas abajo. La herramienta solo necesita
    `ffmpeg.exe` para montar el MP4. Si el usuario ya tenia su propio ffmpeg esto no le toca nada:
    solo poda lo que ha descargado la herramienta.
    """
    if not carpeta.is_dir():
        return
    for sobra in ("ffplay.exe", "ffprobe.exe"):
        for f in carpeta.rglob(sobra):
            try:
                f.unlink()
            except OSError:
                pass
    for sobra in ("doc", "lib", "include", "presets"):
        for d in carpeta.rglob(sobra):
            if d.is_dir():
                shutil.rmtree(d, ignore_errors=True)


def asegurar_ffmpeg(progreso=None) -> Path:
    """Descarga ffmpeg (monta el MP4 a partir del video y de las pistas de audio).

    Orden de preferencia, con lo que ocupa cada uno MEDIDO (no estimado):

      * gyan.dev `release-essentials`: 115 MB de descarga y 105 MB en disco, en un solo fichero.
      * BtbN `lgpl-shared`: 80 MB de descarga pero 154 MB en disco (el exe va con sus DLL).
      * BtbN `gpl` estatico: 200 MB de descarga y 497 MB en disco. Solo como ultimo recurso.

    Gana `essentials` porque lo que el usuario acaba viendo (y copiando a otro equipo) es el peso
    en disco de la carpeta, no lo que se tarda en bajar una vez.
    """
    exe = _busca_exe(carpeta_tools() / "ffmpeg", "ffmpeg.exe")
    if exe:
        if progreso:
            progreso("ffmpeg: already there")
        return exe
    destino = carpeta_tools() / "ffmpeg"
    problemas = []
    if progreso:
        progreso("ffmpeg: downloading (essentials, ~115 MB)")
    try:
        _descargar(FFMPEG_GYAN, destino, progreso)
        _poda_ffmpeg(destino)
        exe = _busca_exe(destino, "ffmpeg.exe")
        if exe:
            if progreso:
                progreso("ffmpeg: ready in %s" % exe.parent)
            return exe
        problemas.append("no ffmpeg.exe inside the gyan.dev package")
    except Exception as e:  # noqa: BLE001
        problemas.append("gyan.dev: %s" % e)
        if progreso:
            progreso("ffmpeg: gyan.dev did not answer, trying GitHub")
    info = (_asset_por_patron(FFMPEG_REPO, ("win64", "lgpl-shared"), ())
            or _asset_por_patron(FFMPEG_REPO, ("win64", "shared"), ())
            or _asset_por_patron(FFMPEG_REPO, ("win64", "gpl"), ("shared",)))
    if info:
        version, url = info
        if progreso:
            progreso("ffmpeg %s: downloading from GitHub" % version)
        _descargar(url, destino, progreso)
        _poda_ffmpeg(destino)
        exe = _busca_exe(destino, "ffmpeg.exe")
        if exe:
            if progreso:
                progreso("ffmpeg: ready in %s" % exe.parent)
            return exe
        problemas.append("no ffmpeg.exe inside the GitHub package")
    raise RuntimeError("I could not leave ffmpeg in place. %s. It can be downloaded by hand from "
                           "https://www.gyan.dev/ffmpeg/builds/ and dropped in tools/ffmpeg/"
                           % "; ".join(problemas))


def asegurar_uv(progreso=None) -> Path:
    """Deja `uv` dentro de la carpeta.

    wannacri necesita un entorno de Python propio y `uv` es quien lo monta (y quien, si en el
    equipo no hay un Python 3.11, se lo baja). Encontrarlo en el PATH del equipo no basta: la
    carpeta tiene que poder llevarse a otro equipo donde no haya nada instalado. Si no hubiera red,
    se sigue usando el del equipo antes que dejar la extraccion de video sin herramienta.
    """
    propio = carpeta_tools() / "uv" / "uv.exe"
    if propio.is_file():
        if progreso:
            progreso("uv: already there")
        return propio
    if progreso:
        progreso("uv: downloading (the zip is about 18 MB)")
    try:
        _descargar(UV_URL, carpeta_tools() / "uv", progreso)
    except Exception as e:  # noqa: BLE001
        externo = _uv_externo()
        if externo:
            if progreso:
                progreso("uv: could not download it (%s); using the one on this machine (%s)" % (e, externo))
            return Path(externo)
        raise
    # del paquete solo se usa uv.exe: los otros dos (uvx, uvw) son 0,7 MB que no hacen falta
    for sobra in ("uvx.exe", "uvw.exe"):
        (carpeta_tools() / "uv" / sobra).unlink(missing_ok=True)
    exe = _busca_exe(carpeta_tools() / "uv", "uv.exe")
    if not exe:
        raise RuntimeError("uv downloaded but I can't find uv.exe. It can be downloaded by hand from "
                                   "https://github.com/astral-sh/uv/releases and dropped in tools/uv/")
    if progreso:
        progreso("uv: ready in %s" % exe)
    return exe


def asegurar_wannacri(progreso=None) -> Path:
    """Instala wannacri (saca el video de los .usm) en su propio entorno minimo.

    Antes esto era un entorno de Python de 97 MB para una sola herramienta. Se monta uno nuevo y
    pequeno en `tools/wannacri`, con el `uv` que viaja en la carpeta (ver `asegurar_uv`).
    """
    exe = _busca_exe(carpeta_tools() / "wannacri", "wannacri.exe")
    if exe:
        if progreso:
            progreso("wannacri: already there")
        return exe
    destino = carpeta_tools() / "wannacri"
    destino.parent.mkdir(parents=True, exist_ok=True)
    if progreso:
        progreso("wannacri: setting up its environment")
    uv = _uv()
    if uv:
        _ejecutar([uv, "venv", str(destino), "--python", "3.11"], progreso, timeout=600)
    if not (destino / "Scripts" / "python.exe").is_file():
        _ejecutar([sys.executable, "-m", "venv", str(destino)], progreso, timeout=600)
    py = destino / "Scripts" / "python.exe"
    if not py.is_file():
        raise RuntimeError("I could not create the environment for wannacri")
    if progreso:
        progreso("wannacri: installing")
    codigo, salida = _instalar_con(py, ["wannacri"], progreso)
    exe = _busca_exe(destino, "wannacri.exe")
    if codigo != 0 or not exe:
        raise RuntimeError("I could not install wannacri: %s" % (salida or "")[-400:])
    if progreso:
        progreso("wannacri: ready in %s" % exe.parent)
    return exe


ORDEN = ("uv", "motor", "wannacri", "vgmstream", "ffmpeg")


def asegurar_todas(progreso=None) -> dict:
    """Deja la herramienta completa: uv, motor, wannacri, vgmstream y ffmpeg.

    Va en orden y NO se para si una falla: que no haya red para vgmstream no debe impedir que se
    baje el motor. Devuelve {'ok': [...], 'fallos': {nombre: motivo}}.
    """
    # el mapa se arma AQUI (y no al importar) para que se puedan sustituir las funciones en pruebas
    funciones = {"uv": asegurar_uv, "motor": asegurar_assetstudio, "wannacri": asegurar_wannacri,
                 "vgmstream": asegurar_vgmstream, "ffmpeg": asegurar_ffmpeg}
    ok, fallos = [], {}
    for nombre in ORDEN:
        if progreso:
            progreso("--- %s (%d MB approx) ---" % (nombre, TAMANOS_MB[nombre]))
        try:
            funciones[nombre](progreso)
            ok.append(nombre)
            if progreso:
                progreso("%s: ready" % nombre)
        except Exception as e:  # noqa: BLE001
            fallos[nombre] = str(e)
            if progreso:
                progreso("%s: FAILED -> %s" % (nombre, e))
    if progreso:
        progreso("--- done: %d of %d ready ---" % (len(ok), len(ORDEN)))
    return {"ok": ok, "fallos": fallos}


# --------------------------------------------------------------------------- Blender
#
# El motor de extraccion no sabe escribir un FBX del modelo entero, asi que esa parte la hace
# Blender si esta instalado. No es obligatorio: sin el, la herramienta entrega los OBJ y lo dice.

def ruta_blender() -> Path | None:
    """Ejecutable de Blender: primero la ruta fijada por el usuario, luego las instalaciones tipicas."""
    fijada = ajustes._leer_config().get("ruta_blender")
    if fijada and Path(fijada).is_file():
        return Path(fijada)
    raices = [Path(r"C:\Program Files\Blender Foundation"),
              Path(r"C:\Program Files (x86)\Blender Foundation"),
              Path(os.path.expandvars(r"%LOCALAPPDATA%\Programs\Blender Foundation")),
              Path(r"C:\Program Files\Steam\steamapps\common\Blender")]
    candidatos = []
    for raiz in raices:
        if raiz.is_dir():
            candidatos += sorted(raiz.glob("Blender*/blender.exe"), reverse=True)
            if (raiz / "blender.exe").is_file():
                candidatos.append(raiz / "blender.exe")
    for c in candidatos:
        if c.is_file():
            return c
    return None


def revisar_actualizaciones_motor(progreso=None) -> dict | None:
    """Compara el motor instalado con el ultimo publicado."""
    instalada = version_assetstudio()
    info = ultima_version_assetstudio()
    if not info:
        return None
    ultima, url = info
    if instalada and instalada == ultima:
        return None
    return {"instalada": instalada or t("dep_sin_instalar"), "disponible": ultima, "url": url}