"""Comprueba que las carpetas de la herramienta se llaman en ingles y que la migracion funciona."""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun  # noqa: E402

sys.path.insert(0, "C:/Users/Lukas/p5x-datamining/p5x_studio")
from p5x_studio import ajustes  # noqa: E402

comun.comprobar(ajustes.SALIDA_HERRAMIENTAS.name == "extracted",
                "la carpeta de salida se llama 'extracted'")

# la migracion, en una raiz de mentira, para no tocar la instalacion de verdad
with tempfile.TemporaryDirectory() as tmp:
    raiz = Path(tmp)
    (raiz / "herramientas_extraidas" / "texturas").mkdir(parents=True)
    (raiz / "herramientas_extraidas" / "texturas" / "a.png").write_text("x")
    (raiz / "motor").mkdir()
    (raiz / "motor" / "m.exe").write_text("x")
    (raiz / "cache" / "herramientas").mkdir(parents=True)
    (raiz / "cache" / "indice_recursos.json").write_text("{}")
    viejo_raiz, viejo_salida = ajustes.RAIZ, ajustes.SALIDA_HERRAMIENTAS
    ajustes.RAIZ = raiz
    ajustes.SALIDA_HERRAMIENTAS = raiz / "extracted"
    try:
        cambios = ajustes.migrar_nombres()
        comun.comprobar((raiz / "extracted" / "textures" / "a.png").is_file(),
                        "la textura de la carpeta vieja acaba en extracted/textures")
        comun.comprobar((raiz / "engine" / "m.exe").is_file(), "el motor acaba en engine/")
        comun.comprobar(not (raiz / "herramientas_extraidas").exists(),
                        "la carpeta vieja ya no esta")
        comun.comprobar((raiz / "cache" / "work").is_dir(), "cache/herramientas pasa a cache/work")
        comun.comprobar((raiz / "cache" / "resource_index.json").is_file(),
                        "indice_recursos.json pasa a resource_index.json")
        comun.comprobar(len(cambios) >= 4, "la migracion informa de lo que hizo (%d cambios)"
                        % len(cambios))
        # no se pisa lo que ya existe
        (raiz / "motor").mkdir()
        (raiz / "motor" / "viejo.exe").write_text("x")
        ajustes.migrar_nombres()
        comun.comprobar((raiz / "motor" / "viejo.exe").is_file(),
                        "si la carpeta nueva ya existe, no se pisa ni se borra la vieja")
    finally:
        ajustes.RAIZ, ajustes.SALIDA_HERRAMIENTAS = viejo_raiz, viejo_salida

comun.resumen()
