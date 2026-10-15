"""Prueba de compatibilidad con la version GLOBAL (Steam) del juego.

Comprueba, contra la instalacion real:
  1. que `detectar_juego()` la encuentra sola, sin configuracion previa;
  2. que `carpeta_bundles()` da la carpeta de bundles;
  3. que el motor lee esos bundles y saca los retratos de los bust-ups;
  4. que los 15 que salian sin cara siguen el mismo camino que en la version china.

Todo escribe en una carpeta temporal: no toca ni el juego ni la salida de la herramienta.
"""
import sys
import time
from pathlib import Path

RAIZ = Path(r"C:/Users/Lukas/p5x-datamining/p5x_studio")
sys.path.insert(0, str(RAIZ))
from p5x_studio import ajustes, bustups, lote  # noqa: E402

BASE = Path(r"C:/Users/Lukas/AppData/Local/hermes/cache/scratch/prueba_global")

print("=== 1. deteccion automatica ===")
juego = ajustes.detectar_juego()
print("   carpeta del juego:", juego)
print("   ¿es la de Steam?:", "steam" in str(juego).lower() if juego else False)
print("   candidatos que existen de los %d probados:" % len(ajustes.CANDIDATOS_JUEGO))
for c in ajustes.CANDIDATOS_JUEGO:
    sub = ajustes.subruta_bundles(c)
    if sub:
        print("      %s  ->  %s" % (c, sub))

print()
print("=== 2. carpeta de bundles ===")
bundles = ajustes.carpeta_bundles()
print("   ", bundles)
print("    bundles en total:", ajustes.contar_bundles(bundles) if bundles else "no hay")

print()
print("=== 3. extraccion desde el juego GLOBAL (carpeta temporal) ===")
t0 = time.time()
def progreso(hechos, total):
    print("   %d/%d" % (hechos, total), flush=True)
n = lote.extraer_retratos(BASE, bustups.prefijos_retratos(), reanudar=False, progreso=progreso)
print("   extracto:", n)
print("   tiempo: %.1f s" % (time.time() - t0))

print()
print("=== 4. los 15 que salian sin cara, desde el extracto GLOBAL ===")
CARPETA = BASE / "portraits"
print("   texturas en:", CARPETA)
print("   indice:", len(bustups.indice(CARPETA, refrescar=True)), "nombres")
SIN_CARA = [
    "guaidao01-bainiao", "guaidao01-longchuanxueshi", "guaidao01-qinyinmianju", "guaidao01-qinyinsp",
    "guaidao01-qinyintoufa", "guaidao01-tengchuanxueshi", "guaidao01-xisenyangcai-face",
    "guaidao01-yemaopengzi01", "guaidao01-yemaopengzi02", "guaidaofu-chibo", "guaidaofu01-qinyin",
    "guaidaofu02-chibo", "sifu01-lizi", "yongzhuang-lizi", "yongzhuang-yemaopengzi",
]
sin_cara = []
for clave in SIN_CARA:
    try:
        r = bustups.montar(clave, carpeta=CARPETA)
    except Exception as e:
        print("   %-30s no monta: %s" % (clave, e))
        continue
    if not r:
        print("   %-30s no monta" % clave)
        continue
    pasos = sorted({c.get("paso") for c in r.get("capas", [])})
    cara = bool({"face", "eyes", "mouth"} & set(pasos))
    print("   %-30s %-2d capas  cara:%s  %s" % (clave, len(r.get("capas", [])), "SI" if cara else "NO",
                                                ",".join(p for p in pasos if p)))
    if not cara:
        sin_cara.append(clave)
print()
print("sin cara con el juego global: %d de %d" % (len(sin_cara), len(SIN_CARA)))
print(sin_cara)