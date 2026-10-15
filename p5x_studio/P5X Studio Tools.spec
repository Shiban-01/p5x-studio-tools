# -*- mode: python ; coding: utf-8 -*-
"""Spec de PyInstaller para P5X Studio Tools (version publica, SOLO herramientas).

Es un ejecutable PARALELO al de P5X Studio: no lo sustituye ni comparte su spec. Genera un unico
.exe de ventana (sin consola) con la pestana de herramientas (explorador de bundles, inspector,
buscador de recursos, visor de texturas y video/audio).

A diferencia del de modelos, este NO lleva:
  - el motor de modelos (extractor, unity, rig_unitypy, glb_rig, fbx_blender, sesion_unity);
  - UnityPy (solo hace falta para montar mallas/esqueletos);
  - ningun indice del juego (`_dl`): el explorador lista la carpeta del juego y el buscador
    construye su indice bajo demanda (cache/indice_recursos.json).

Por eso el binario es bastante mas pequeno. Lo que si necesita:
  - Pillow (visor de texturas, ya dentro);
  - el motor AssetStudioModCLI y las herramientas wannacri/vgmstream/ffmpeg, que NO se empaquetan
    (16 MB + dependencias engordarian el binario): se descargan o se ponen en `tools/` al lado.
"""
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

# relativa al propio spec: asi el build no depende de la ruta de ningun equipo concreto.
# (PyInstaller no define __file__ dentro del spec; el directorio del spec esta en SPECPATH)
PROYECTO = Path(SPECPATH)

# --------------------------------------------------------------------------- datos y binarios
# La PAGINA de la interfaz nueva. `ui_web._pagina()` la busca como `<paquete>/ui_web/index.html`,
# que al estar congelado cae dentro de _MEIPASS: sin esta linea la ventana nueva abriria en blanco.
origen_web = PROYECTO / "p5x_studio" / "ui_web"
datas = [(str(origen_web), "p5x_studio/ui_web")]

# El mapa de bust-ups (JSON del shader -> capas y expresiones) viaja DENTRO del ejecutable: el visor
# no depende de tener `_dl` al lado. `bustups._datos_empaquetados` lo busca en `_MEIPASS`.
origen_datos = PROYECTO / "p5x_studio" / "datos"
if origen_datos.exists():
    datas.append((str(origen_datos), "p5x_studio/datos"))

# pywebview y pythonnet: no basta con los imports, hacen falta sus DLL nativas (WebView2Loader.dll
# y Microsoft.Web.WebView2.Core.dll entre ellas), que es lo que recolecta `collect_all`.
hiddenimports = [
    "PIL._tkinter_finder",
    "webview",
    "webview.platforms.winforms",
    "webview.platforms.edgechromium",
    "clr",
    "clr_loader",
    "pythonnet",
]
binaries = []
for paquete in ("webview", "pythonnet", "clr_loader"):
    try:
        d, b, h = collect_all(paquete)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception as e:  # noqa: BLE001
        print("aviso: no se pudo recolectar %s: %r" % (paquete, e))

# modulo del apartado de MODELOS que NO debe entrar ni por descuido (PyInstaller no los sigue
# porque nadie los importa, pero se excluyen a proposito para que no vuelvan por una dependencia)
EXCLUIDOS = [
    "UnityPy",
    "numpy",
    "p5x_studio.extractor",
    "p5x_studio.extractor_viejo",
    "p5x_studio.unity",
    "p5x_studio.rig_unitypy",
    "p5x_studio.glb_rig",
    "p5x_studio.fbx_blender",
    "p5x_studio.sesion_unity",
    "p5x_studio.clave",
    "p5x_studio.indice",
    "p5x_studio.preview",
    "p5x_studio.bases",
    "p5x_studio.catalogo",
    "p5x_studio.gui",
]

a = Analysis(
    [str(PROYECTO / "arranque_tools.py")],
    pathex=[str(PROYECTO)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUIDOS,
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
    name="P5X Studio Tools",
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
