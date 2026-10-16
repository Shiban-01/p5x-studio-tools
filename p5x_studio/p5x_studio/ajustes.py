"""Ajustes y rutas de P5X Studio.

Todo lo que depende del equipo del usuario vive aqui: donde esta el juego, donde se guardan los
modelos extraidos y donde la herramienta guarda su cache. La deteccion del juego es automatica y,
si falla, se le pregunta al usuario desde la interfaz en vez de obligarle a editar ficheros.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

VERSION = "0.0.3-beta"
NOMBRE = "P5X Studio"

# raiz de la herramienta. En modo normal es la carpeta que contiene este paquete; congelada (el .exe)
# no se puede usar __file__, que apunta a una carpeta temporal de solo lectura, asi que se usa la
# carpeta del propio ejecutable. Todo lo que debe persistir (cache, config, modelos, motor) vive ahi.
if getattr(sys, "frozen", False):
    RAIZ = Path(sys.executable).resolve().parent
else:
    RAIZ = Path(__file__).resolve().parent.parent
CACHE = RAIZ / "cache"
SALIDA_POR_DEFECTO = RAIZ / "modelos_extraidos"
# salida de la pestana de herramientas (videos, texturas y exportaciones de bundles). Es su propia
# carpeta para que una version que NO extrae modelos no cree `modelos_extraidos`.
SALIDA_HERRAMIENTAS = RAIZ / "extracted"

# Nombres en INGLES y cortos, igual que los ficheros del juego (que tambien van en ingles: el
# explorador lista `shared_...bundle`, `anim_...`). Antes estaban en espanol y una carpeta llamada
# `herramientas_extraidas` al lado de `Bundles/` cantaba.
RENOMBRES_RAIZ = (
    ("motor", "engine"),
    ("herramientas_extraidas", "extracted"),
)
RENOMBRES_CACHE = (
    ("herramientas", "work"),
    ("indice_recursos.json", "resource_index.json"),
)
# subcarpetas de la salida, dentro de `extracted/`
RENOMBRES_SALIDA = (
    ("texturas", "textures"),
    ("explorador", "explorer"),
    ("recursos", "resources"),
)
# dentro de `tools/`: el entorno de wannacri se llamaba `env`, que no dice nada
RENOMBRES_TOOLS = (
    ("env", "wannacri"),
)


def migrar_nombres(log=None) -> list:
    """Renombra las carpetas de la version anterior a los nombres nuevos (ingles).

    Se llama al arrancar y SOLO si el nombre viejo existe y el nuevo no: asi una instalacion que ya
    tenia el motor o texturas extraidas no pierde nada, y si el usuario ya creo la carpeta nueva a
    mano no se pisa. Devuelve los cambios hechos (para poder dejarlo en el registro).
    """
    cambios = []

    def _mueve(viejo: Path, nuevo: Path):
        if not viejo.exists() or nuevo.exists():
            return
        try:
            nuevo.parent.mkdir(parents=True, exist_ok=True)
            viejo.rename(nuevo)
            cambios.append("%s -> %s" % (viejo.name, nuevo.name))
        except OSError:
            pass

    for viejo, nuevo in RENOMBRES_RAIZ:
        _mueve(RAIZ / viejo, RAIZ / nuevo)
    # la cache se deriva de RAIZ (siempre cuelga de ella) en vez de usar la constante del import:
    # asi la migracion trabaja sobre la raiz que se le pase, no sobre la que habia al arrancar
    raiz_cache = RAIZ / "cache"
    for viejo, nuevo in RENOMBRES_CACHE:
        _mueve(raiz_cache / viejo, raiz_cache / nuevo)
    for viejo, nuevo in RENOMBRES_SALIDA:
        _mueve(SALIDA_HERRAMIENTAS / viejo, SALIDA_HERRAMIENTAS / nuevo)
    for viejo, nuevo in RENOMBRES_TOOLS:
        _mueve(RAIZ / "tools" / viejo, RAIZ / "tools" / nuevo)
    if log and cambios:
        log("carpetas renombradas: " + ", ".join(cambios))
    return cambios
CONFIG = RAIZ / "config.json"

# Sitios donde puede estar instalado el juego, de mas probable a menos. NO se fija la ruta de un
# equipo concreto: la carpeta que elige el usuario se guarda en `config.json` (`carpeta_juego`) y,
# si no hay nada, se prueban estos sitios genericos. Asi el ejecutable vale en cualquier equipo
# (una version publica no puede llevar dentro la ruta de la casa de quien la construyo).
# nombres con los que puede aparecer la carpeta del juego (la china y la global)
NOMBRES_JUEGO = ("P5X", "Persona5ThePhantomX", "Persona 5 The Phantom X", "Persona5X", "PhantomX")


def _candidatos_juego() -> list:
    candidatos = [
        Path(r"C:\Program Files\P5X"),
        Path(r"C:\Program Files (x86)\P5X"),
        Path(r"D:\P5X"),
        Path(r"E:\P5X"),
        Path(r"F:\P5X"),
    ]
    for var in ("%LOCALAPPDATA%", "%APPDATA%"):
        valor = os.path.expandvars(var)
        if valor and "%" not in valor:
            candidatos.append(Path(valor) / "P5X")
    try:
        casa = Path.home()
        candidatos.append(casa / "P5X")
        for sub in ("Downloads", "Desktop", "Documents"):
            candidatos.append(casa / sub / "P5X")
    except Exception:
        pass
    # la version global se distribuye por Steam: la carpeta del juego cuelga de `steamapps/common`
    for comun in _bibliotecas_steam():
        for nombre in NOMBRES_JUEGO:
            candidatos.append(comun / nombre)
    return candidatos


def _bibliotecas_steam() -> list:
    """Carpetas `steamapps/common` de Steam: la instalacion de por defecto y las de otra biblioteca.

    Steam guarda las bibliotecas extra (otro disco, otra carpeta) en `libraryfolders.vdf`, que es un
    fichero de texto con una linea `"path"` por biblioteca. Se leen todas.
    """
    raices = [Path(r"C:\Program Files (x86)\Steam"), Path(r"C:\Program Files\Steam")]
    for var in ("%ProgramFiles(x86)%", "%ProgramFiles%"):
        valor = os.path.expandvars(var)
        if valor and "%" not in valor:
            raices.append(Path(valor) / "Steam")
    comunes = []
    for raiz in raices:
        comunes.append(raiz / "steamapps" / "common")
        try:
            texto = (raiz / "steamapps" / "libraryfolders.vdf").read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for trozo in re.findall(r'"path"\s+"([^"]+)"', texto):
            comunes.append(Path(trozo.replace("\\\\", "\\")) / "steamapps" / "common")
    # sin repetir: varias raices dan la misma carpeta
    vistos, unicos = set(), []
    for c in comunes:
        clave = str(c).lower()
        if clave not in vistos:
            vistos.add(clave)
            unicos.append(c)
    return unicos


CANDIDATOS_JUEGO = _candidatos_juego()

# Subrutas, dentro de la carpeta del juego, donde pueden vivir los bundles. La version china los
# pone en `Client/OuterPackage/Bundles/Windows`; la global (Steam) en `client/OuterPackage/...`, y
# algunas instalaciones cuelgan `OuterPackage` de la propia raiz. Se prueban en orden y vale la
# primera que exista: asi el mismo ejecutable sirve para las dos versiones del juego.
SUBRUTAS_BUNDLES = (
    Path("Client/OuterPackage/Bundles/Windows"),
    Path("client/OuterPackage/Bundles/Windows"),
    Path("OuterPackage/Bundles/Windows"),
    Path("Bundles/Windows"),
)
# la de la version china, por compatibilidad con el codigo que ya la usaba
SUBRUTA_BUNDLES = SUBRUTAS_BUNDLES[0]
# el bundle que contiene el AssetBundleManifest con la lista oficial de bundles
SUBRUTA_MANIFIESTO = Path("083/Windows")


def _leer_config() -> dict:
    if CONFIG.exists():
        try:
            return json.loads(CONFIG.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def guardar_config(**cambios) -> dict:
    datos = _leer_config()
    datos.update(cambios)
    CONFIG.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
    return datos


def idioma() -> str:
    """Idioma de la interfaz guardado en la configuracion. Espanol si no hay nada o no vale."""
    v = _leer_config().get("idioma")
    return v if v in ("es", "en") else "es"


def subruta_bundles(juego: Path) -> Path | None:
    """Subruta de bundles que EXISTE dentro de esa carpeta de juego, o None si esa carpeta no es del
    juego. Se prueban las subrutas conocidas de las dos versiones (china y global)."""
    for sub in SUBRUTAS_BUNDLES:
        try:
            if (juego / sub).is_dir():
                return sub
        except OSError:
            continue
    return None


def detectar_juego() -> Path | None:
    """Devuelve la carpeta del juego si se encuentra sola. Respeta lo que el usuario haya fijado."""
    fijada = _leer_config().get("carpeta_juego")
    if fijada and subruta_bundles(Path(fijada)):
        return Path(fijada)
    for candidato in CANDIDATOS_JUEGO:
        try:
            if subruta_bundles(candidato):
                return candidato
        except OSError:
            continue
    return None


def carpeta_bundles(juego: Path | None = None) -> Path | None:
    juego = juego or detectar_juego()
    if not juego:
        return None
    sub = subruta_bundles(juego)
    return (juego / sub) if sub else None


def resolver_carpeta_juego(ruta) -> tuple[Path | None, Path | None]:
    """Comprueba que una carpeta elegida a mano sea la del juego.

    Acepta dos cosas, porque el usuario puede senalar cualquiera de las dos:
      - la carpeta del juego, que DENTRO lleva `Client/OuterPackage/Bundles/Windows` (o `client/...`
        en la version global de Steam);
      - la propia carpeta de bundles (`.../Bundles/Windows`).

    Devuelve `(carpeta_juego, carpeta_bundles)` si vale, o `(None, None)` si no. No pide que el
    juego este descompilado ni desofuscado: los bundles se leen tal cual, con su nombre ofuscado.
    """
    ruta = Path(ruta)
    if not ruta.is_dir():
        return None, None
    sub = subruta_bundles(ruta)
    if sub:
        return ruta, ruta / sub
    # ¿nos han dado la propia carpeta de bundles? Se compara sin distinguir mayusculas: `Client` en
    # la version china y `client` en la global son la misma carpeta en Windows, pero no en Python.
    partes = [p.lower() for p in SUBRUTA_BUNDLES.parts]
    suyas = [p.lower() for p in ruta.parts]
    if len(suyas) >= len(partes) and suyas[-len(partes):] == partes:
        return ruta.parents[len(partes) - 1], ruta
    return None, None


def contar_bundles(bundles: Path) -> int:
    """Cuenta los ficheros `.bundle` que hay dentro de la carpeta de bundles (incluye subcarpetas)."""
    try:
        return sum(1 for p in Path(bundles).rglob("*.bundle") if p.is_file())
    except OSError:
        return 0


def carpeta_salida() -> Path:
    fijada = _leer_config().get("carpeta_salida")
    ruta = Path(fijada) if fijada else SALIDA_POR_DEFECTO
    ruta.mkdir(parents=True, exist_ok=True)
    return ruta


def carpeta_herramientas() -> Path:
    """Carpeta de salida de la pestana de herramientas (`extracted` por defecto)."""
    fijada = _leer_config().get("carpeta_herramientas")
    ruta = Path(fijada) if fijada else SALIDA_HERRAMIENTAS
    ruta.mkdir(parents=True, exist_ok=True)
    return ruta


def preparar_carpetas() -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    # antes de crear nada: si viene de una instalacion con los nombres viejos, se renombra
    migrar_nombres()
    for c in (CACHE, carpeta_salida()):
        c.mkdir(parents=True, exist_ok=True)