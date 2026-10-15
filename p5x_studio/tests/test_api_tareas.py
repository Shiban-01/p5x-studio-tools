"""Comprueba que el puente guarda el registro de una tarea linea a linea, lo acota, y ofrece
la instalacion de dependencias."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun  # noqa: E402

sys.path.insert(0, "C:/Users/Lukas/p5x-datamining/p5x_studio")
from p5x_studio import ui_web  # noqa: E402

api = ui_web.Api()
api._nueva_tarea("dependencias")
log = api._log("dependencias")
for i in range(600):
    log("linea %d" % i)
est = api.estado_tarea()
comun.comprobar(est["lineas"][-1] == "linea 599", "el registro guarda la ultima linea")
comun.comprobar(len(est["lineas"]) <= 400,
                "el registro NO crece sin limite (%d)" % len(est["lineas"]))
comun.comprobar(est["lineas"][0].startswith("linea "), "el registro conserva el principio recortado")
comun.comprobar(est["ultimo"] == "linea 599", "la ultima linea sigue en 'ultimo' (lo usa el sondeo)")

api._fin_tarea(resultado="4")
comun.comprobar(api.estado_tarea()["terminada"] is True, "la tarea se cierra")

comun.comprobar(hasattr(api, "instalar_dependencias"), "el puente ofrece instalar_dependencias")
est_dep = api.estado_dependencias()
comun.comprobar("peso_mb" in est_dep, "el estado dice el peso aproximado")
comun.comprobar(set(est_dep["tamanos"]) == {"uv", "motor", "wannacri", "vgmstream", "ffmpeg"},
                "el estado detalla las cinco piezas que se pueden bajar")
comun.comprobar("fuera" in est_dep,
                "el estado distingue lo que se usa desde fuera de la carpeta")

# una tarea nueva NO arrastra el registro de la anterior
api._nueva_tarea("video")
comun.comprobar(api.estado_tarea()["lineas"] == [], "cada tarea empieza con el registro vacio")

comun.resumen()
