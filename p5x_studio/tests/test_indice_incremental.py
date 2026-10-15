"""Comprueba que el indice del buscador solo visita los bundles que CAMBIARON.

Recorrer los 16.535 bundles son decenas de minutos: si no ha cambiado nada, volver a recorrerlos
todos es tirar el tiempo del usuario.
"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun  # noqa: E402

sys.path.insert(0, "C:/Users/Lukas/p5x-datamining/p5x_studio")
from p5x_studio import ajustes, herramientas  # noqa: E402

carpeta = Path(tempfile.mkdtemp(prefix="indice_inc_"))
for nombre in ("a.bundle", "b.bundle", "c.bundle"):
    (carpeta / nombre).write_bytes(b"x" * 32)

falsos = [{"nombre": n, "ruta": n} for n in ("a.bundle", "b.bundle", "c.bundle")]
visitas = []
real_catalogo = herramientas.catalogo_bundles
real_listar = herramientas.listar_bundle
real_carpeta = ajustes.carpeta_bundles


def catalogo_falso():
    return list(falsos)


def listar_falso(ruta, a=None, b=None):
    visitas.append(ruta)
    return [{"nombre": "%s_mesh" % Path(ruta).stem, "tipo": "Mesh"}]


# el catalogo real devuelve rutas RELATIVAS a la carpeta del juego, asi que la prueba hace lo mismo
# y de paso prueba la resolucion de rutas de verdad
ajustes.carpeta_bundles = lambda: carpeta
herramientas.catalogo_bundles = catalogo_falso
herramientas.listar_bundle = listar_falso
destino = carpeta / "indice.json"
try:
    r1 = herramientas.construir_indice_recursos(ruta=destino)
    comun.comprobar(sorted(visitas) == ["a.bundle", "b.bundle", "c.bundle"],
                    "la primera vez los visita todos (%s)" % sorted(visitas))
    comun.comprobar(len(r1) == 3, "y anota un recurso de cada uno (%d)" % len(r1))

    visitas.clear()
    r2 = herramientas.construir_indice_recursos(ruta=destino)
    comun.comprobar(visitas == [], "la segunda vez NO visita ninguno (%s)" % visitas)
    comun.comprobar(sorted(r2) == sorted(r1), "y devuelve lo mismo que antes")

    # cambia un bundle: solo ese se vuelve a mirar
    visitas.clear()
    (carpeta / "b.bundle").write_bytes(b"y" * 40)
    r3 = herramientas.construir_indice_recursos(ruta=destino)
    comun.comprobar(visitas == ["b.bundle"], "solo visita el que cambio (%s)" % visitas)
    comun.comprobar(len(r3) == 3, "sigue habiendo un recurso por bundle (%d)" % len(r3))

    # desaparece un bundle: sus recursos se van del indice
    visitas.clear()
    falsos.pop(0)                     # se va a.bundle
    r4 = herramientas.construir_indice_recursos(ruta=destino)
    comun.comprobar([x[2] for x in r4].count("a.bundle") == 0,
                    "los recursos del que se fue no se quedan colgando")
    comun.comprobar(len(r4) == 2, "quedan los de los otros dos (%d)" % len(r4))

    # y queda escrito con que comparar la proxima vez
    datos = json.loads(destino.read_text(encoding="utf-8"))
    comun.comprobar("huellas" in datos, "el indice guarda la huella de cada bundle")
    comun.comprobar(len(datos["huellas"]) == 2, "una por bundle vivo (%d)" % len(datos["huellas"]))
    comun.comprobar(datos["bundles_cubiertos"] == 2,
                    "el indice dice que cubre los 2 bundles que quedan (%s)" % datos["bundles_cubiertos"])
finally:
    ajustes.carpeta_bundles = real_carpeta
    herramientas.catalogo_bundles = real_catalogo
    herramientas.listar_bundle = real_listar

comun.resumen()
