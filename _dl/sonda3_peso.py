"""Sonda 3: cuanto pesa y cuanto tarda exportar las texturas de una muestra real.

Exporta con una sola pasada del motor (carpeta como entrada, -t tex2d) los bundles de una muestra
de cada familia y mide MB y segundos. Con eso se extrapola el coste real del bulk completo.
"""
import shutil
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(r"C:\Users\Lukas\p5x-datamining\p5x_studio")
G = Path(r"C:\Users\Lukas\Downloads\P5X\Client\OuterPackage\Bundles\Windows")
MOTOR = RAIZ / "engine" / "AssetStudioModCLI_net9_win64" / "AssetStudioModCLI.exe"
S = Path(r"C:\Users\Lukas\AppData\Local\hermes\cache\scratch\sonda3")
FAMILIAS = {"shared": 4, "scn": 4, "role": 3, "roletiny": 3, "uitex": 3, "atlas": 2, "part": 2,
            "tl": 3, "anim": 2, "ui": 2}

shutil.rmtree(S, ignore_errors=True)
(S / "entrada").mkdir(parents=True)

elegidos = {}
for fam, cuantos in FAMILIAS.items():
    cogidos = 0
    for p in sorted(G.rglob("%s_*.bundle" % fam)):
        if p.name.split("_")[0] != fam:
            continue
        shutil.copy2(p, S / "entrada" / p.name)
        elegidos.setdefault(fam, []).append(p.name)
        cogidos += 1
        if cogidos >= cuantos:
            break

mb_entrada = sum(f.stat().st_size for f in (S / "entrada").glob("*.bundle")) / 1e6
print("bundles de la muestra:", sum(len(v) for v in elegidos.values()), "  (%.0f MB de bundles)" % mb_entrada)

t0 = time.time()
r = subprocess.run([str(MOTOR), str(S / "entrada"), "-m", "export", "-t", "tex2d",
                    "-g", "none", "-o", str(S / "salida"),
                    "--log-level", "Error", "--unity-version", "2022.3.49f1"],
                   capture_output=True, text=True, timeout=1800)
segundos = time.time() - t0

salida = S / "salida"
pngs = list(salida.rglob("*.png"))
mb = sum(f.stat().st_size for f in pngs) / 1e6
print("salida:", (r.stdout or "").strip().splitlines()[-1][:90] if r.stdout else (r.stderr or "")[-90:])
print()
print("  texturas exportadas: %d" % len(pngs))
print("  MB en disco:         %.1f MB" % mb)
print("  segundos:            %.1f s" % segundos)
print("  por bundle:          %.2f s  /  %.2f MB" % (segundos / 28, mb / 28))
print()
print("=== las 8 mas grandes ===")
for f in sorted(pngs, key=lambda x: -x.stat().st_size)[:8]:
    print("   %8.2f MB  %s" % (f.stat().st_size / 1e6, f.name[:70]))
print()
print("=== extensiones ===")
from collections import Counter
print(Counter(f.suffix for f in salida.rglob("*") if f.is_file()))