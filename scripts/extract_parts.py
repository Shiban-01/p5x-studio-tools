#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Extrae texturas de personaje que faltan en el proyecto exportado (las que dejan materiales
planos: eyelid, cheekred, eye, hair, shoes, bottom...).

Localizadas con un grep -a sobre los 16.535 bundles del cliente: viven en la familia
`part_s_port_rig*` (34 bundles, ~136 MB), no en los bundles de UI ni en `part__uniform*`
(esos son de otros personajes: noir, okyann, kotomo...).

Uso:
    python scripts/extract_parts.py [--familia part_s_port_rig] [--prefijos PC079_01,wonder_uniform]
                                    [--seco]

Deja los PNG en unity_projects/kotone/ExportedProject/Assets/Texture2D/ (sin .meta: los genera
Unity). Luego hay que re-ejecutar P5XFixTextures.Run para que los materiales los tomen.
"""
import argparse
import glob
import os
import re
import shutil
import sys

BUNDLES = r"C:\Users\Lukas\Downloads\P5X\Client\OuterPackage\Bundles\Windows"
RAIZ = r"C:\Users\Lukas\p5x-datamining"
STAGE = os.path.join(RAIZ, "_dl", "tex_stage2")
DESTINO = os.path.join(RAIZ, "unity_projects", "kotone", "ExportedProject", "Assets", "Texture2D")

ap = argparse.ArgumentParser()
ap.add_argument("--familia", default="part_s_port_rig")
ap.add_argument("--prefijos", default="PC079_01,wonder_uniform")
ap.add_argument("--seco", action="store_true")
a = ap.parse_args()
prefijos = [p.strip() for p in a.prefijos.split(",") if p.strip()]

import UnityPy
UnityPy.config.FALLBACK_UNITY_VERSION = "2022.3.49f1"


def carga(ruta):
    """UnityPy sobre el bundle tal cual; si falla, lo entiende como ofuscado."""
    try:
        env = UnityPy.load(ruta)
        if list(env.objects):
            return env
    except Exception:
        pass
    return None


def main():
    os.makedirs(STAGE, exist_ok=True)
    fam = sorted(glob.glob(os.path.join(BUNDLES, "**", a.familia + "*.bundle"), recursive=True))
    print(f"bundles de la familia {a.familia}*: {len(fam)}")
    ya = {os.path.splitext(f)[0] for f in os.listdir(DESTINO) if f.endswith(".png")}
    print(f"texturas ya en el proyecto: {len(ya)}")

    n_copiados = n_export = n_saltadas = n_ilegibles = 0
    exportadas = []
    for i, src in enumerate(fam, 1):
        dst = os.path.join(STAGE, os.path.basename(src))
        if not os.path.exists(dst):
            shutil.copy2(src, dst)
            n_copiados += 1
        env = carga(dst)
        if env is None:
            n_ilegibles += 1
            print(f"  [{i:2}/{len(fam)}] ILEGIBLE {os.path.basename(src)}")
            continue
        sacadas = 0
        for o in env.objects:
            if o.type.name != "Texture2D":
                continue
            try:
                d = o.read()
                nom = d.m_name
            except Exception:
                continue
            if not any(nom.startswith(p) for p in prefijos):
                continue
            if nom in ya:
                n_saltadas += 1
                continue
            if a.seco:
                exportadas.append(nom)
                continue
            try:
                img = d.image
                p = os.path.join(DESTINO, nom + ".png")
                img.save(p)
                ya.add(nom)
                n_export += 1
                sacadas += 1
                exportadas.append(nom)
            except Exception as e:
                print(f"      fallo al exportar {nom}: {type(e).__name__}")
        if sacadas:
            print(f"  [{i:2}/{len(fam)}] {os.path.basename(src)[:34]:34} -> {sacadas} nuevas")

    print(f"\n=== resumen ===")
    print(f"  bundles copiados a stage : {n_copiados}")
    print(f"  bundles ilegibles        : {n_ilegibles}")
    print(f"  texturas ya presentes    : {n_saltadas}")
    print(f"  texturas exportadas      : {n_export}" + (" (simulacion)" if a.seco else ""))
    for n in sorted(set(exportadas))[:40]:
        print(f"     {n}")
    if len(set(exportadas)) > 40:
        print(f"     ... y {len(set(exportadas)) - 40} mas")


if __name__ == "__main__":
    main()