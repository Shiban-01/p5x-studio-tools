"""Comprueba el gestor de dependencias: tabla de pesos, orden y tolerancia a fallos."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun  # noqa: E402

sys.path.insert(0, "C:/Users/Lukas/p5x-datamining/p5x_studio")
from p5x_studio import dependencias  # noqa: E402

comun.comprobar(isinstance(dependencias.TAMANOS_MB, dict), "hay tabla de tamanos aproximados")
comun.comprobar(sum(dependencias.TAMANOS_MB.values()) <= 200,
                "el peso aproximado total baja de 200 MB (hoy son 289)")
comun.comprobar(set(dependencias.TAMANOS_MB) == {"uv", "motor", "wannacri", "vgmstream", "ffmpeg"},
                "la tabla cubre las cinco piezas que se bajan")
comun.comprobar(set(dependencias.TAMANOS_MB) == set(dependencias.ORDEN),
                "la tabla y el orden de instalacion cuadran (si no, alguna se quedaria sin bajar)")
comun.comprobar(dependencias.ORDEN[0] == "uv",
                "uv va primero: sin el no se puede montar el entorno de wannacri")
comun.comprobar(hasattr(dependencias, "peso_aproximado_mb"), "hay funcion de peso total")

lineas = []


def falso(nombre, falla=False):
    def f(progreso=None):
        if progreso:
            progreso("descargando %s" % nombre)
        if falla:
            raise RuntimeError("sin red (%s)" % nombre)
        return Path("C:/tmp") / nombre
    return f


NOMBRES = ("asegurar_uv", "asegurar_assetstudio", "asegurar_wannacri", "asegurar_vgmstream",
           "asegurar_ffmpeg")
real = {k: getattr(dependencias, k) for k in NOMBRES}
try:
    # 1) todo va bien: se llama a todas y se informa
    dependencias.asegurar_uv = falso("uv")
    dependencias.asegurar_assetstudio = falso("motor")
    dependencias.asegurar_wannacri = falso("wannacri")
    dependencias.asegurar_vgmstream = falso("vgmstream")
    dependencias.asegurar_ffmpeg = falso("ffmpeg")
    res = dependencias.asegurar_todas(progreso=lineas.append)
    comun.comprobar(len(res["ok"]) == len(dependencias.ORDEN),
                    "con todo bien, las %d quedan ok" % len(dependencias.ORDEN))
    comun.comprobar(res["fallos"] == {}, "sin fallos")
    comun.comprobar(any("descargando" in l for l in lineas), "el progreso llega linea a linea")

    # 2) una falla: las otras tres SIGUEN (si no, una caida de red deja la app a medias)
    dependencias.asegurar_vgmstream = falso("vgmstream", falla=True)
    res = dependencias.asegurar_todas(progreso=lineas.append)
    comun.comprobar(set(res["ok"]) == {"uv", "motor", "wannacri", "ffmpeg"},
                    "las otras cuatro si se hicieron (%s)" % sorted(res["ok"]))
    comun.comprobar(set(res["fallos"]) == {"vgmstream"}, "el fallo se apunta, no se esconde")

    # 3) los nombres de las funciones de descarga existen de verdad
    for k in NOMBRES:
        comun.comprobar(callable(real[k]), "%s es llamable" % k)
finally:
    for k, v in real.items():
        setattr(dependencias, k, v)

comun.comprobar(dependencias.peso_aproximado_mb() == sum(dependencias.TAMANOS_MB.values()),
                "el peso total cuadra con la tabla")

# --- de fuera no viaja -------------------------------------------------------------------------
# Nace de la prueba de fuego: con la carpeta recien vaciada, el motor y ffmpeg salian "instalado"
# porque habia copias FUERA (la del escritorio del usuario, la del PATH de la maquina de pruebas).
# La app puede aprovecharlas, pero no viajan al copiar la carpeta: la lista tiene que distinguirlo.
import tempfile
from pathlib import Path as _Path

with tempfile.TemporaryDirectory() as _tmp:
    _reales = (dependencias.carpeta_tools, dependencias.carpeta_motor)
    dependencias.carpeta_tools = lambda: _Path(_tmp) / "tools"
    dependencias.carpeta_motor = lambda: _Path(_tmp) / "engine"
    try:
        # la app las encuentra (existen fuera), pero ninguna esta en nuestra carpeta
        est = {"motor": r"C:\otro\AssetStudioModCLI.exe", "wannacri": None,
               "vgmstream": [r"C:\otro\vgmstream-cli.exe"], "ffmpeg": [r"C:\otro\ffmpeg.exe"]}
        fuera = dependencias.dentro_de_carpeta(est)
        comun.comprobar(set(fuera) == {"motor", "vgmstream", "ffmpeg"},
                        "las que estan fuera se senalan, y solo esas (%s)" % sorted(fuera))
        comun.comprobar("wannacri" not in fuera, "la que falta no se cuenta como de fuera")

        # en cuanto la suya esta dentro, deja de avisar de esa
        (_Path(_tmp) / "tools" / "vgmstream").mkdir(parents=True)
        (_Path(_tmp) / "tools" / "vgmstream" / "vgmstream-cli.exe").write_bytes(b"x")
        fuera = dependencias.dentro_de_carpeta(est)
        comun.comprobar("vgmstream" not in fuera,
                        "con la copia propia dentro, ya no la marca como de fuera")
        comun.comprobar(dependencias.ruta_propia("vgmstream") is not None,
                        "y la encuentra en la carpeta")

        # uv: el de la carpeta manda sobre el que hubiera en el equipo. Es lo que hace que la
        # carpeta sirva en otro equipo: si solo se usara el del PATH, al llevarsela se cae wannacri.
        (_Path(_tmp) / "tools" / "uv").mkdir(parents=True)
        (_Path(_tmp) / "tools" / "uv" / "uv.exe").write_bytes(b"x")
        comun.comprobar(dependencias._uv() == str(_Path(_tmp) / "tools" / "uv" / "uv.exe"),
                        "se prefiere el uv que viaja en la carpeta")
        comun.comprobar(dependencias.ruta_propia("uv") is not None,
                        "y uv cuenta como pieza de la carpeta")
    finally:
        dependencias.carpeta_tools, dependencias.carpeta_motor = _reales

comun.resumen()
