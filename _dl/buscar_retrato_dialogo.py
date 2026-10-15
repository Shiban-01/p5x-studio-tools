"""Localiza en el assetmap el retrato de dialogo de un personaje concreto y lo extrae.

El assetmap da pares (nombre de asset, bundle). Aqui se busca un nombre que contenga changfu01 y el
personaje pedido, y se saca la textura de su bundle con el motor.
"""
import re
import subprocess
import sys
from pathlib import Path

MAPA = Path(r"C:\Users\Lukas\p5x-datamining\game_dump\fileContentOut\Bundles\Windows\105\assetMapName.txt")
G = Path(r"C:\Users\Lukas\Downloads\P5X\Client\OuterPackage\Bundles\Windows")
MOTOR = Path(r"C:\Users\Lukas\p5x-datamining\p5x_studio\engine\AssetStudioModCLI_net9_win64\AssetStudioModCLI.exe")
SALIDA = Path(r"C:\Users\Lukas\AppData\Local\hermes\cache\scratch\retrato_dialogo")

d = MAPA.read_bytes()
cadenas = [s.decode("ascii", "ignore") for s in re.findall(rb"[\x20-\x7e]{3,120}", d)]

buscado = sys.argv[1] if len(sys.argv) > 1 else "changfu01-aqi"
print("buscando:", buscado)
encontrados = []
for i, s in enumerate(cadenas):
    if buscado in s:
        encontrados.append((i, s, cadenas[i - 1] if i else "", cadenas[i + 1] if i + 1 < len(cadenas) else ""))
print("coincidencias exactas:", len(encontrados))
for i, s, ant, sig in encontrados[:10]:
    print("   %-40s | antes: %-34s | despues: %-34s" % (s, ant[:34], sig[:34]))

clave = buscado.replace("-", "")
parcial = [(i, s) for i, s in enumerate(cadenas) if clave in s.replace("-", "")]
print()
print("coincidencias laxas (%s): %d" % (clave, len(parcial)))
for i, s in parcial[:12]:
    print("   %-56s | vecino: %s" % (s[:56], cadenas[i + 1][:38] if i + 1 < len(cadenas) else ""))

# si aparece el bundle, se extrae su textura con nombre parecido
bundle = next((cadenas[i + 1] for i, s in parcial if cadenas[i + 1].endswith(".bundle")), None)
if not bundle:
    bundle = next((s for s in cadenas if "ichangfu" in s and s.endswith(".bundle")), None)
print()
print("bundle candidato:", bundle)
if bundle:
    rutas = list(G.rglob(bundle))
    print("   en disco:", rutas[:1])
    if rutas:
        SALIDA.mkdir(parents=True, exist_ok=True)
        subprocess.run([str(MOTOR), str(rutas[0]), "-t", "tex2d", "-o", str(SALIDA), "-g", "fileName",
                        "--log-level", "Error", "--unity-version", "2022.3.49f1"], capture_output=True)
        pngs = sorted(SALIDA.rglob("*.png"))
        print("   png extraidos:", len(pngs))
        for p in pngs[:12]:
            print("      ", p.name, p.stat().st_size // 1024, "KB")