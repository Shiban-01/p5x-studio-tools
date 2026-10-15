"""Sonda 5: que layout deja cada opcion de agrupacion (-g) del motor.

Prueba las tres candidatas sobre los mismos bundles (role_ y scn_, que son los de nombres
interesantes) para elegir la que deja las carpetas ya ordenadas sin mover ficheros a mano.
"""
import os
import shutil
import subprocess
from pathlib import Path

RAIZ = Path(r"C:\Users\Lukas\p5x-datamining\p5x_studio")
G = Path(r"C:\Users\Lukas\Downloads\P5X\Client\OuterPackage\Bundles\Windows")
MOTOR = RAIZ / "engine" / "AssetStudioModCLI_net9_win64" / "AssetStudioModCLI.exe"
S = Path(r"C:\Users\Lukas\AppData\Local\hermes\cache\scratch\sonda5")

FAMILIAS = ["role", "scn", "uitex"]
CUANTOS = 2

shutil.rmtree(S, ignore_errors=True)
(S / "entrada").mkdir(parents=True)
for fam in FAMILIAS:
    n = 0
    for p in sorted(G.rglob("%s_*.bundle" % fam)):
        if p.name.split("_")[0] != fam:
            continue
        os.link(p, S / "entrada" / p.name)  # enlace duro: no copia datos
        n += 1
        if n >= CUANTOS:
            break
print("bundles enlazados:", len(list((S / "entrada").glob("*.bundle"))))

for modo in ("none", "container", "fileName"):
    salida = S / ("salida_" + modo)
    r = subprocess.run([str(MOTOR), str(S / "entrada"), "-m", "export", "-t", "tex2d",
                        "-g", modo, "-o", str(salida), "--log-level", "Error",
                        "--unity-version", "2022.3.49f1"],
                       capture_output=True, text=True, timeout=900)
    pngs = sorted(salida.rglob("*.png"))
    print()
    print("=== -g %-10s %d pngs ===" % (modo, len(pngs)))
    for f in pngs[:6]:
        print("     %s" % str(f.relative_to(salida))[:96])
    if len(pngs) > 6:
        print("     ... y %d mas" % (len(pngs) - 6))