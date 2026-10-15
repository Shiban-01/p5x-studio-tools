"""Empareja cada material de arma con su textura, leyendo los GUID de los .mat y de los .meta.

Los .mat del juego guardan las texturas por GUID, no por nombre. El nombre esta en el .meta de
cada Texture2D. Asi se sabe que textura lleva cada arma sin adivinar nada.
"""
import os
import re

RAIZ = r"C:\Users\Lukas\p5x-datamining\unity_com\RipperProj\ExportedProject\Assets"
MAT = os.path.join(RAIZ, "Material")
TEX = os.path.join(RAIZ, "Texture2D")

# guid -> fichero de textura
guid_a_textura = {}
for f in os.listdir(TEX):
    if f.endswith(".png.meta"):
        t = open(os.path.join(TEX, f), encoding="utf-8", errors="replace").read()
        m = re.search(r"guid:\s*([a-f0-9]{32})", t)
        if m:
            guid_a_textura[m.group(1)] = f[:-5]      # quita ".meta"

print("texturas con guid: %d" % len(guid_a_textura))

for f in sorted(os.listdir(MAT)):
    if not f.startswith("PC079_01_weapon") or not f.endswith(".mat"):
        continue
    t = open(os.path.join(MAT, f), encoding="utf-8", errors="replace").read()
    # las ranuras van como "- _NombreTex:" y despues "m_Texture: {fileID: ..., guid: ..., type: ...}"
    ranuras = re.findall(r"- (_[A-Za-z0-9]+):\s*\n\s*m_Texture:\s*\{fileID: (\d+), guid: ([a-f0-9]{32})",
                         t)
    print("\n%s" % f)
    if not ranuras:
        print("   (sin texturas asignadas)")
    for ranura, fid, guid in ranuras:
        if fid == "0":
            continue
        nombre = guid_a_textura.get(guid, "GUID desconocido " + guid[:8])
        print("   %-22s %s" % (ranura, nombre))