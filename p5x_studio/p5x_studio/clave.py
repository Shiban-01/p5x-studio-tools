"""Clave de descifrado de los bundles.

Los bundles del juego vienen cifrados con la proteccion de Unity que deriva la clave del
global-metadata.dat del cliente. La clave no cambia entre arranques, asi que se calcula una vez
(puede tardar unos minutos) y se guarda en la cache de la herramienta. Si el juego se actualiza y la
clave deja de servir, se detecta al abrir un bundle y se recalcula sola.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import UnityPy

from . import ajustes
from .idiomas import t

# firmas que UnityPy necesita para reconocer el patron de cifrado del juego
KEY_SIG = b"\n\x00$1#\n\x00$,\xc1\n\x00$7\xd3\n"
DATA_SIG = b"\x00\x01\x00\xc2\x06\xd1\x00\x02\x00\x00\x00\x01\x00\xb8\x00\x03"

# version de Unity del cliente; los bundles no la llevan escrita y UnityPy la necesita
VERSION_UNITY_POR_DEFECTO = "2022.3.49f1"


def ruta_cache() -> Path:
    return ajustes.CACHE / "clave_bundles.json"


def buscar_metadata() -> Path | None:
    """Localiza global-metadata.dat dentro de la instalacion del juego."""
    juego = ajustes.detectar_juego()
    if not juego:
        return None
    candidatos = [
        juego / "Client/pc/P5X_Data/il2cpp_data/Metadata/global-metadata.dat",
        juego / "P5X_Data/il2cpp_data/Metadata/global-metadata.dat",
    ]
    for c in candidatos:
        if c.is_file():
            return c
    # barrido por si la instalacion cambia de estructura
    for raiz, _, ficheros in os.walk(juego):
        if "global-metadata.dat" in ficheros:
            return Path(raiz) / "global-metadata.dat"
    return None


def version_unity() -> str:
    """Lee la version de Unity de la cabecera del bundle de indice, o devuelve la conocida."""
    juego = ajustes.detectar_juego()
    if juego:
        manifiesto = juego / ajustes.SUBRUTA_MANIFIESTO
        if manifiesto.is_file():
            try:
                cabeza = manifiesto.read_bytes()[:200]
                texto = cabeza.decode("latin-1")
                i = texto.find("20")
                if i >= 0:
                    posible = texto[i:i + 12]
                    if posible[:4].isdigit() and "f" in posible:
                        return posible.strip("\x00 ")
            except Exception:
                pass
    return VERSION_UNITY_POR_DEFECTO


def _aplicar(clave, version: str) -> None:
    UnityPy.set_assetbundle_decrypt_key(bytes(clave) if not isinstance(clave, bytes) else clave)
    UnityPy.config.FALLBACK_UNITY_VERSION = version


def cargar(progreso=None) -> tuple[bytes, str]:
    """Devuelve (clave, version). Calcula la clave si no esta en cache."""
    version = version_unity()
    if ruta_cache().exists():
        try:
            datos = json.loads(ruta_cache().read_text(encoding="utf-8"))
            clave = bytes(datos["clave"])
            _aplicar(clave, version)
            if progreso:
                progreso(t("cl_cache"))
            return clave, version
        except Exception:
            pass

    metadata = buscar_metadata()
    if not metadata:
        raise RuntimeError(t("cl_err_metadata"))

    if progreso:
        progreso(t("cl_calculando"))
    from UnityPy.helpers.ArchiveStorageManager import brute_force_key
    with open(metadata, "rb") as fp:
        clave = brute_force_key(fp, KEY_SIG, DATA_SIG)
    if progreso:
        progreso(t("cl_obtenida"))
    ruta_cache().parent.mkdir(parents=True, exist_ok=True)
    ruta_cache().write_text(json.dumps({"clave": list(clave), "metadata": str(metadata)}),
                            encoding="utf-8")
    _aplicar(clave, version)
    return clave, version


def preparar(progreso=None) -> str:
    """Deja UnityPy listo para abrir bundles. Devuelve la version de Unity usada."""
    _, version = cargar(progreso)
    return version


def olvidar() -> None:
    """Borra la clave guardada, para forzar que se recalcule."""
    try:
        ruta_cache().unlink()
    except OSError:
        pass