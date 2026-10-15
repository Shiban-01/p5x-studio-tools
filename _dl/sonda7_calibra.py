"""Calibra el peso: relacion entre el tamano que declara el censo y los PNG reales medidos.

En la sonda 3 se exportaron 28 bundles (170 MB de bundles) y salieron 118,7 MB de PNG. Aqui se
suma lo que el censo declara para ESOS bundles y se saca el factor, para poder estimar el bulk
completo con datos y no a ojo.
"""
import json
from pathlib import Path

CENSO = Path(r"C:\Users\Lukas\p5x-datamining\_dl\censo_texturas.json")
SONDA = Path(r"C:\Users\Lukas\AppData\Local\hermes\cache\scratch\sonda3")

D = json.loads(CENSO.read_text(encoding="utf-8"))
filas = D["filas"]

nombres = {p.name for p in (SONDA / "entrada").glob("*.bundle")}
muestra = [f for f in filas if f["bundle"].split("/")[-1] in nombres]

declarado = sum(f["bytes"] for f in muestra) / 1e6
real = 118.7
print("bundles de la muestra:", len(nombres))
print("texturas en la muestra:", len(muestra))
print("MB declarados por el censo: %.1f" % declarado)
print("MB reales de PNG:           %.1f" % real)
print("factor PNG/declarado:       %.2fx" % (real / declarado))

total_declarado = sum(f["bytes"] for f in filas) / 1e6
print()
print("declarado en TODO el juego: %.0f MB" % total_declarado)
print("estimacion de PNG total:    %.0f MB (%.0f GB)" % (total_declarado * real / declarado,
                                                        total_declarado * real / declarado / 1024))

# y por categoria, con el mismo factor
fam = {}
for f in filas:
    k = f["bundle"].split("/")[1].split("_")[0]
    a = fam.setdefault(k, [0, 0])
    a[0] += 1
    a[1] += f["bytes"]
factor = real / declarado
print()
print("%-12s %8s %10s %12s" % ("familia", "texturas", "declarado", "PNG estim."))
for k, (n, b) in sorted(fam.items(), key=lambda x: -x[1][1]):
    print("%-12s %8d %9.0f MB %9.1f GB" % (k, n, b / 1e6, b * factor / 1e9))