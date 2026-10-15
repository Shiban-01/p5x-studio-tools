"""Sonda 2: nombres y contenedores reales de una muestra de cada familia (un solo proceso).

Copia un bundle de cada familia grande a una carpeta temporal, pide la lista de assets en XML
(rapido: no decodifica) y ensena ordenado por familia que texturas lleva y con que contenedor.
"""
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

RAIZ = Path(r"C:\Users\Lukas\p5x-datamining\p5x_studio")
G = Path(r"C:\Users\Lukas\Downloads\P5X\Client\OuterPackage\Bundles\Windows")
MOTOR = RAIZ / "engine" / "AssetStudioModCLI_net9_win64" / "AssetStudioModCLI.exe"
S = Path(r"C:\Users\Lukas\AppData\Local\hermes\cache\scratch\sonda2")
FAMILIAS = ["shared", "tl", "roletiny", "scn", "uitex", "role", "part", "efx", "atlas", "ui", "char",
            "spinetest", "tlm", "postprocess"]
MUESTRA = 2

shutil.rmtree(S, ignore_errors=True)
(S / "entrada").mkdir(parents=True)

elegidos = []
for fam in FAMILIAS:
    cogidos = 0
    for p in sorted(G.rglob("%s_*.bundle" % fam)):
        if p.name.split("_")[0] != fam:
            continue
        shutil.copy2(p, S / "entrada" / p.name)
        elegidos.append((fam, p.name))
        cogidos += 1
        if cogidos >= MUESTRA:
            break
print("bundles elegidos:", len(elegidos))

r = subprocess.run([str(MOTOR), str(S / "entrada"), "-m", "info", "--export-asset-list", "xml",
                    "-o", str(S / "salida"), "--log-level", "Error", "--unity-version", "2022.3.49f1"],
                   capture_output=True, text=True, timeout=600)
xml = next((S / "salida").rglob("*.xml"), None)
if not xml:
    print("sin XML:", (r.stdout or "")[-500:], (r.stderr or "")[-500:])
    sys.exit(1)

raiz = ET.parse(str(xml)).getroot()
por_bundle = {}
for a in raiz.findall("Asset"):
    cont = (a.findtext("Container") or "").strip()
    nombre = (a.findtext("Name") or "").strip()
    tipo = (a.findtext("Type") or "").strip()
    fichero = (a.findtext("Source") or a.findtext("Path") or "").strip()
    por_bundle.setdefault(fichero or "?", []).append((nombre, tipo, cont))

print("buckets en el XML:", len(por_bundle))
print()
for fam, nombre_bundle in elegidos:
    # el XML agrupa por fichero origen
    clave = next((k for k in por_bundle if nombre_bundle.split(".")[0] in k), None)
    filas = por_bundle.get(clave, [])
    tex = [f for f in filas if f[1] in ("Texture2D", "Sprite")]
    print("=== %-9s %-34s %4d assets, %3d texturas ===" % (fam, nombre_bundle[:34], len(filas), len(tex)))
    for n, t, c in tex[:6]:
        print("      %-34s %-9s cont=%-46s" % (n[:34], t, c[:46] or "(vacio)"))
    if len(tex) > 6:
        print("      ... y %d mas" % (len(tex) - 6))