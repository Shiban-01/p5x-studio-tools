# -*- mode: python ; coding: utf-8 -*-
"""Spec de PyInstaller para P5X Studio.

Genera un unico ejecutable de ventana (sin consola) que lleva dentro el paquete p5x_studio, las
librerias (UnityPy, Pillow) y el indice de contenido del juego, para que la lista de personajes
funcione nada mas abrir. Lo que debe persistir (cache, config, modelos, motor) se escribe junto al
.exe, no aqui dentro.
"""
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

PROYECTO = Path(r"C:/Users/Lukas/p5x-datamining/p5x_studio")
INDICE = Path(r"C:/Users/Lukas/p5x-datamining/_dl/indice_juego")
INDICE_TRAJES = Path(r"C:/Users/Lukas/p5x-datamining/_dl/indice_trajes")
# indice de contenido por bundle: la pestana de HERRAMIENTAS lo usa para el explorador (tipos de
# recurso que lleva cada bundle) y para el buscador global de recursos
INDICE_ASSETS = Path(r"C:/Users/Lukas/p5x-datamining/_dl/indice_assets")
# cache del distintivo de audio de la lista de videos (con audio / silencio / sin audio). Se
# precalculo con vgmstream + RMS; sin el, el ejecutable solo puede deducir un estado aproximado.
ESTADO_AUDIO = Path(r"C:/Users/Lukas/p5x-datamining/_dl/estado_audio_video.json")

datas = [
    (str(INDICE / "actores.json"), "_dl/indice_juego"),
    (str(INDICE / "indice_contenido.json"), "_dl/indice_juego"),
    (str(INDICE / "indice_ficheros.json"), "_dl/indice_juego"),
    # indice de trajes: sin el, el catalogo no sabe separar los trajes de un personaje
    (str(INDICE_TRAJES / "trajes.json"), "_dl/indice_trajes"),
    (str(INDICE_ASSETS / "assets.json"), "_dl/indice_assets"),
    (str(ESTADO_AUDIO), "_dl"),
    (str(PROYECTO / "p5x_studio" / "fbx_blender.py"), "p5x_studio"),
]

# UnityPy trae datos (arboles de tipos) y una extension compilada: hay que arrastrarlo entero
datos_unitypy, binarios_unitypy, ocultos_unitypy = collect_all("UnityPy")

a = Analysis(
    [str(PROYECTO / "arranque_exe.py")],
    pathex=[str(PROYECTO)],
    binaries=binarios_unitypy,
    datas=datas + datos_unitypy,
    hiddenimports=ocultos_unitypy,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="P5X Studio",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)