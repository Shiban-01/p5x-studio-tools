"""Prueba REAL de descarga: baja las cuatro herramientas a una carpeta de pruebas.

Comprueba que los patrones de GitHub siguen casando y cuanto ocupan de verdad (el numero que la
interfaz ensena al usuario es aproximado; esto dice el real).
"""
import os
import sys
import tempfile
from pathlib import Path

RAIZ_PROYECTO = "C:/Users/Lukas/p5x-datamining/p5x_studio"
sys.path.insert(0, RAIZ_PROYECTO)
os.environ.setdefault("P5X_STUDIO_SIN_INDICES", "1")

from p5x_studio import ajustes, dependencias  # noqa: E402

destino = Path(os.environ.get("CARPETA_PRUEBA") or r"C:\Users\Lukas\p5x-datamining\_dl\deps_prueba")
destino.mkdir(parents=True, exist_ok=True)

viejo = ajustes.RAIZ
ajustes.RAIZ = destino
lineas = []


def progreso(s):
    s = str(s)
    lineas.append(s)
    if "%" not in s:          # los porcentajes cada 256 KB llenarian la salida
        print("   ", s, flush=True)


try:
    print("RAIZ de prueba:", ajustes.RAIZ)
    print("peso que ensena la app:", dependencias.peso_aproximado_mb(), "MB")
    r = dependencias.asegurar_todas(progreso=progreso)
    print("\nresultado:", r)
finally:
    ajustes.RAIZ = viejo

print("\n=== lo que ocupa de verdad ===")
total = 0
for nombre in dependencias.ORDEN:
    carpeta = destino / ("engine" if nombre == "motor" else "tools/" + nombre)
    mb = 0
    if carpeta.is_dir():
        mb = sum(f.stat().st_size for f in carpeta.rglob("*") if f.is_file()) / 1e6
    total += mb
    print("  %-9s %7.1f MB   %s" % (nombre, mb, "OK" if mb else "VACIO"))
print("  TOTAL     %7.1f MB   (la app dice %d MB)" % (total, dependencias.peso_aproximado_mb()))
