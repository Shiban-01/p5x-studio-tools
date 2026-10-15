"""Punto de entrada del ejecutable de P5X Studio Tools (version publica, solo herramientas).

Igual que `arranque_exe.py`, pero para la version publica: NO importa el motor de modelos
(`extractor`, `unity`, `rig_unitypy`, `glb_rig`, `fbx_blender`, `sesion_unity`) ni lee indices
empaquetados. Todo lo que necesita sale de la carpeta del juego (que elige quien usa el programa)
y, para el buscador global, de un indice que se construye bajo demanda y se guarda en `cache/`.

Fija `P5X_STUDIO_SIN_INDICES=1` ANTES de importar el paquete: asi el explorador, el buscador y el
distintivo de audio no pueden apoyarse en `_dl` aunque exista en el equipo donde se construyo (en
un equipo ajeno no existe). Eso es lo que hace la version autosuficiente de verdad, no de palabra.

Modos SIN ventana (para verificar el empaquetado sin abrir la interfaz):
  - P5X_STUDIO_TOOLS_DIAGNOSTICO=1  -> escribe `autotest_tools.txt` con lo que ve el ejecutable.
  - P5X_STUDIO_TOOLS_SELFTEST=1     -> prueba las herramientas de verdad (explorador, inspector,
                                       texturas y video) y escribe `autotest_tools.txt` + un log.
      P5X_STUDIO_TOOLS_SIN_VIDEO=1  -> omite la extraccion de video (es la parte lenta).

Con `python arranque_tools.py` tambien funciona (sin congelar).
"""
from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

# la version publica no lee NINGUN indice empaquetado: todo sale de la carpeta del juego
os.environ.setdefault("P5X_STUDIO_SIN_INDICES", "1")

# sin congelar hace falta que el paquete p5x_studio (que esta al lado) se vea
if not getattr(sys, "frozen", False):
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from p5x_studio import ajustes, dependencias, herramientas  # noqa: E402

INFORME = "autotest_tools.txt"
LOG = "autotest_tools.log"

# estos son los modulos del apartado de MODELOS: si alguno aparece aqui, el binario los arrastra
MODULOS_MODELOS = ("p5x_studio.extractor", "p5x_studio.unity", "p5x_studio.rig_unitypy",
                   "p5x_studio.glb_rig", "p5x_studio.fbx_blender", "p5x_studio.sesion_unity")


def _escribir(lineas) -> Path:
    ruta = ajustes.RAIZ / INFORME
    ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    return ruta


def _presencia_modelos() -> list[str]:
    """Dice si los modulos de MODELOS estan dentro del binario (no deberian)."""
    salida = []
    for nombre in MODULOS_MODELOS:
        try:
            importlib.import_module(nombre)
            salida.append("%s=PRESENTE" % nombre)
        except Exception:
            salida.append("%s=ausente" % nombre)
    return salida


def _herramientas_externas() -> list[str]:
    """Que herramientas de fuera tiene a mano el ejecutable y cuales le faltan.

    Son las que NO viajan dentro del binario (el motor son 16 MB y wannacri/vgmstream/ffmpeg otros
    tantos). Que falte alguna no rompe lo demas: el explorador y el buscador son Python puro. Lo que
    hace es acotar QUE se puede hacer en este equipo, y por eso se apunta en el informe.
    """
    buscar = (
        ("wannacri", herramientas._candidatos_wannacri, ("-h",)),
        ("vgmstream", herramientas._candidatos_vgmstream, ("-h",)),
        ("ffmpeg", herramientas._candidatos_ffmpeg, ("-version",)),
    )
    salida = []
    for nombre, candidatos, sonda in buscar:
        try:
            orden = herramientas._localiza(candidatos(), sonda)
        except Exception as e:  # noqa: BLE001
            salida.append("%s=error(%s)" % (nombre, e))
            continue
        salida.append("%s=%s" % (nombre, "si" if orden else "FALTA"))
    try:
        motor = dependencias.ruta_assetstudio()
    except Exception:  # noqa: BLE001
        motor = None
    salida.append("motor=%s" % ("si" if motor else "FALTA"))
    return salida


def _diagnostico() -> int:
    bundles = herramientas.catalogo_bundles()
    est = herramientas.indice_recursos_estado()
    lineas = [
        "P5X Studio Tools - diagnostico",
        "frozen=%s" % getattr(sys, "frozen", False),
        "executable=%s" % sys.executable,
        "meipass=%s" % getattr(sys, "_MEIPASS", ""),
        "raiz=%s" % ajustes.RAIZ,
        "sin_indices=%s" % os.environ.get("P5X_STUDIO_SIN_INDICES"),
        "juego=%s" % ajustes.detectar_juego(),
        "bundles=%d" % len(bundles),
        "origen_catalogo=%s" % (bundles[0].get("origen") if bundles else "-"),
        "buscador_disponible=%s" % est["disponible"],
        "buscador_fuente=%s" % est["fuente"],
        "buscador_recursos=%d" % est["n"],
    ] + _presencia_modelos() + _herramientas_externas()
    ruta = _escribir(lineas)
    print("informe: %s" % ruta)
    return 0


def _selftest() -> int:
    lineas: list[str] = []
    registro: list[str] = []

    def anota(s):
        registro.append(str(s))

    lineas.append("P5X Studio Tools - autotest de autosuficiencia")
    lineas.append("frozen=%s" % getattr(sys, "frozen", False))
    lineas.append("executable=%s" % sys.executable)
    lineas.append("sin_indices=%s" % os.environ.get("P5X_STUDIO_SIN_INDICES"))
    lineas.extend(_presencia_modelos())
    lineas.extend(_herramientas_externas())
    juego = ajustes.detectar_juego()
    lineas.append("juego=%s" % juego)
    if not juego:
        lineas.append("FALLO: no encuentro la carpeta del juego")
        _escribir(lineas)
        return 2

    # 1) EXPLORADOR: lista los bundles del sistema de ficheros, sin ningun indice
    bundles = herramientas.catalogo_bundles()
    lineas.append("1) explorador: bundles=%d  origen=%s"
                  % (len(bundles), bundles[0].get("origen") if bundles else "-"))
    if bundles:
        lineas.append("   primera=%s  tipo=%s  %.2f MB"
                      % (bundles[0]["ruta"], bundles[0]["tipo"], bundles[0]["mb"]))
        lineas.append("   tipos=%s" % ",".join(herramientas.tipos_de_bundle()[:10]))

    # 2) INSPECTOR: abre UN bundle con el motor (misma llamada que el boton "Abrir con el motor").
    # Se prueban los mas grandes (los que seguro llevan algo); el primero que devuelve recursos es
    # el que se informa.
    elegido, recursos, intentos = "", [], 0
    for b in sorted(bundles, key=lambda x: -x["mb"])[:12]:
        intentos += 1
        try:
            f = herramientas.listar_bundle(b["ruta"], anota)
        except Exception as e:
            anota("info fallo %s: %s" % (b["ruta"], e))
            continue
        if f:
            elegido, recursos = b["ruta"], f
            break
    lineas.append("2) inspector: %d bundles probados; %s -> %d recursos"
                  % (intentos, elegido or "-", len(recursos)))
    lineas.append("   tipos dentro=%s"
                  % ",".join(sorted({r["tipo"] for r in recursos})[:10]))

    # 3) VISOR DE TEXTURAS: exporta tex2d de un bundle y abre la primera imagen con Pillow
    destino_tx = ajustes.carpeta_herramientas() / "autotest_texturas"
    candidatos = sorted([b for b in bundles
                         if b["fichero"].startswith("shared") and b["mb"] >= 1.0],
                        key=lambda b: b["mb"])
    imagenes, usado = [], ""
    for b in candidatos[:10]:
        try:
            herramientas.exportar_bundle(b["ruta"], "tex2d", destino_tx, anota)
        except Exception as e:
            anota("export fallo %s: %s" % (b["ruta"], e))
            continue
        imagenes = herramientas.imagenes_de(destino_tx)
        if imagenes:
            usado = b["ruta"]
            break
    lineas.append("3) texturas: %d imagenes (bundle %s)" % (len(imagenes), usado or "-"))
    if imagenes:
        from PIL import Image
        with Image.open(imagenes[0]) as im:
            lineas.append("   abierta con Pillow: %s  %s  %s"
                          % (imagenes[0].name, im.size, im.mode))

    # 4) VIDEO/AUDIO: extrae un .usm pequeno a MP4 y mira el distintivo de audio (honesto)
    if os.environ.get("P5X_STUDIO_TOOLS_SIN_VIDEO"):
        lineas.append("4) video: omitido (P5X_STUDIO_TOOLS_SIN_VIDEO=1)")
    else:
        media = herramientas.listar_media()
        usms = sorted([m for m in media.get("usm", []) if m["mb"] >= 0.05],
                      key=lambda m: m["mb"])
        lineas.append("4) media: %d .usm, %d .awb  carpeta=%s"
                      % (len(usms), len(media.get("awb", [])), media.get("carpeta")))
        if usms:
            chico = usms[0]
            lineas.append("   distintivo de audio de %s: %s"
                          % (chico["nombre"], chico["estado"]))
            destino_v = ajustes.carpeta_herramientas() / "autotest_video"
            # extraer_video necesita wannacri y ffmpeg, que NO viajan dentro del ejecutable: en un
            # equipo sin ellos esto falla con un mensaje claro y el autotest debe seguir, no morir.
            try:
                salida = herramientas.extraer_video(chico["ruta"], destino_v, anota)
            except Exception as e:  # noqa: BLE001
                lineas.append("   FALLO al extraer: %s: %s" % (type(e).__name__, e))
                anota("video fallo: %r" % (e,))
            else:
                lineas.append("   %s -> %s (%.1f MB)"
                              % (chico["nombre"], salida.name, salida.stat().st_size / 1e6))

    # 5) BUSCADOR: dice si tiene indice (se construye bajo demanda) — no se lanza el barrido largo
    est = herramientas.indice_recursos_estado()
    aviso = ""
    if est.get("parcial"):
        aviso = "  PARCIAL (cubre %d de %d)" % (est.get("bundles_cubiertos", 0), est["bundles"])
    lineas.append("5) buscador: disponible=%s fuente=%s recursos=%d bundles=%d%s"
                  % (est["disponible"], est["fuente"], est["n"], est["bundles"], aviso))

    lineas.append("--- log ---")
    lineas.extend(registro)
    ruta = _escribir(lineas)
    (ajustes.RAIZ / LOG).write_text("\n".join(registro) + "\n", encoding="utf-8")
    print("informe: %s" % ruta)
    print("\n".join(lineas))
    return 0


if __name__ == "__main__":
    if getattr(sys, "frozen", False):
        if os.environ.get("P5X_STUDIO_TOOLS_DIAGNOSTICO"):
            raise SystemExit(_diagnostico())
        if os.environ.get("P5X_STUDIO_TOOLS_SELFTEST"):
            raise SystemExit(_selftest())
    from p5x_studio.ui import arrancar
    arrancar()
