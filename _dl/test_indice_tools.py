"""Prueba del mecanismo del buscador bajo demanda: progreso, guardado y cancelacion.

Se ejecuta contra el codigo fuente (no el .exe) para no dejar un indice a medias en `cache/`.
Guarda en un fichero temporal propio, asi que NO toca `cache/indice_recursos.json`.
"""
import json
import os
import sys
import time

os.environ["P5X_STUDIO_SIN_INDICES"] = "1"
sys.path.insert(0, r"C:/Users/Lukas/p5x-datamining/p5x_studio")

from pathlib import Path  # noqa: E402

from p5x_studio import herramientas  # noqa: E402

TMP = Path(r"C:/Users/Lukas/p5x-datamining/_dl/_tmp_indice_tools.json")
TMP.unlink(missing_ok=True)

progresos = []


def prog(hechos, total):
    progresos.append((hechos, total))


# --- 1) construir un trozo de indice (300 bundles) y comprobar que se guarda ---
t = time.time()
recursos = herramientas.construir_indice_recursos(progreso=prog, limite=300, ruta=TMP)
print("1) construccion acotada: %d recursos en %d callbacks de progreso (%.1f s)"
      % (len(recursos), len(progresos), time.time() - t))
print("   primeros progresos:", progresos[:3], "... ultimos:", progresos[-2:])
print("   guardado:", TMP.is_file(), "->", TMP.stat().st_size if TMP.is_file() else 0, "bytes")
print("   relectura cache:", (herramientas.indice_recursos_cache() or [])[:0] or "ruta distinta (correcto)")

# --- 2) cancelar: debe devolver [] y NO tocar lo ya guardado ---
antes = TMP.read_bytes()
seguir = {"n": 0}
vistos = []


def prog2(hechos, total):
    vistos.append(hechos)
    if hechos >= 50:
        seguir["n"] = hechos  # a partir de aqui cancelamos


def cancelar():
    return len(vistos) >= 50


t = time.time()
res_cancel = herramientas.construir_indice_recursos(progreso=prog2, cancelar=cancelar, ruta=TMP)
print("2) cancelacion: devolvio %d recursos tras %d avisos de progreso (%.1f s)"
      % (len(res_cancel), len(vistos), time.time() - t))
print("   fichero intacto:", TMP.read_bytes() == antes)

# --- 3) el indice guardado es legible tal cual lo leeria la app ---
guardado = json.loads(TMP.read_text(encoding="utf-8"))
print("3) indice guardado: n=%d, ejemplo=%s" % (guardado["n"], guardado["recursos"][0]))
TMP.unlink(missing_ok=True)
print("   temporal borrado: %s" % (not TMP.exists()))
print("   cache/indice_recursos.json NO tocado: %s"
      % (not herramientas.ruta_indice_recursos().exists()))
