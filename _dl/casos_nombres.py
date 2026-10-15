"""Mira casos concretos para deducir como nombra el motor lo que exporta.

El censo guarda el fichero CONTENEDOR tal cual aparece en el bundle (puede ser `.tga`, `.prefab`...)
y el motor escribe PNG. Antes de contar "lo que falta" hay que entender la regla, no suponerla.
"""
import json
import os
from collections import Counter, defaultdict
from pathlib import Path

DEST = Path(r"C:\Users\Lukas\Desktop\P5X Studio Tools\extracted\textures")
filas = json.loads(Path(r"C:\Users\Lukas\p5x-datamining\_dl\censo_texturas.json").read_text(encoding="utf-8"))["filas"]

por_bundle = defaultdict(list)
for r in filas:
    por_bundle[r["bundle"]].append(r)

CASOS = [
    ("Effects", "efx_bugs"),
    ("Effects", "efx_vasuki"),
    ("Particles", "part_port_rig"),
    ("UI", "atlas_nzhimoni"),
]
for cat, conj in CASOS:
    print("=" * 78)
    print("%s / %s" % (cat, conj))
    print("=" * 78)
    carpeta = DEST / cat / conj
    en_disco = sorted(p.name for p in carpeta.iterdir()) if carpeta.exists() else []
    print("EN DISCO (%d):" % len(en_disco))
    for n in en_disco[:12]:
        print("    %s" % n)
    if len(en_disco) > 12:
        print("    ... y %d mas" % (len(en_disco) - 12))
    # el bundle de ese conjunto
    pares = [(b, v) for b, v in por_bundle.items() if conj in b.split("/")[-1].split("_")[0:3]]
    bundle = None
    for b, v in pares:
        candidato = b.split("/")[-1][:-len(".bundle")]
        # el conjunto es el nombre del bundle sin el hash
        if candidato.startswith(conj.split("_")[0]):
            bundle = b
            break
    print()
    print("EN EL CENSO:")
    if bundle:
        rs = por_bundle[bundle]
        print("    bundle: %s  (%d texturas)" % (bundle, len(rs)))
        conts = Counter(r["cont"] for r in rs)
        print("    contenedores distintos: %d" % len(conts))
        print("    extensiones de contenedor:", Counter(Path(c).suffix.lower() for c in conts if c))
        print("    12 ejemplos (nombre del asset -> contenedor):")
        for r in rs[:12]:
            print("        %-34s -> %s  [%s]" % (r["nombre"], r["cont"] or "(vacio)", r["tipo"]))
    else:
        print("    (no localice el bundle)")
    print()