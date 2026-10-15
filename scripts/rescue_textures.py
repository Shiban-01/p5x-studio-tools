#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Rescata texturas de personaje que AssetRipper no exporto (quedan como "sin textura"
en el capturador -> caras/pelo/ropa planos).

Recorre un conjunto de bundles candidatos del cliente, los desofusca en un stage
temporal y exporta a PNG toda Texture2D cuyo nombre empiece por alguno de los
prefijos pedidos y que AUN NO exista en Assets/Texture2D.

Uso: python rescue_textures.py [prefijo ...]
  (por defecto: PC079_01 wonder_uniform)
"""
import os, re, shutil, subprocess, sys, glob
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUNDLES = Path(r"C:/Users/Lukas/Downloads/P5X/Client/OuterPackage/Bundles/Windows")
STAGE = ROOT / "_dl" / "tex_stage"
DEST = ROOT / "unity_projects" / "kotone" / "ExportedProject" / "Assets" / "Texture2D"
PREFIJOS = sys.argv[1:] or ["PC079_01", "wonder_uniform"]

import UnityPy
UnityPy.config.FALLBACK_UNITY_VERSION = "2022.3.49f1"


def candidatos():
    patrones = ["*wonder*", "*uniform*", "*pc079*"]
    vistos, out = set(), []
    for p in patrones:
        for f in BUNDLES.rglob(p):
            if f.suffix != ".bundle" or f in vistos:
                continue
            vistos.add(f)
            out.append(f)
    return out


def main():
    STAGE.mkdir(parents=True, exist_ok=True)
    DEST.mkdir(parents=True, exist_ok=True)
    cands = candidatos()
    print(f"candidatos: {len(cands)}")
    copiados = 0
    for c in cands:
        dst = STAGE / c.name
        if not dst.exists():
            try:
                shutil.copy2(c, dst); copiados += 1
            except Exception as e:
                print(f"  [!] no copiado {c.name}: {e}")
    print(f"copiados al stage: {copiados} (total stage: {len(list(STAGE.glob('*.bundle')))})")

    # desofuscado in-place
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "deobfuscate_bundles.py"), str(STAGE)],
                       capture_output=True, text=True)
    print("deofuscado:", (r.stdout or r.stderr).strip().splitlines()[-1] if (r.stdout or r.stderr) else "?")

    ya = {p.stem for p in DEST.glob("*.png")}
    print(f"PNG ya presentes en el proyecto: {len(ya)}")
    nuevos, fallos = [], 0
    for b in sorted(STAGE.glob("*.bundle")):
        try:
            env = UnityPy.load(str(b))
        except Exception:
            fallos += 1
            continue
        for obj in env.objects:
            if obj.type.name != "Texture2D":
                continue
            try:
                data = obj.read()
                nombre = data.m_Name
            except Exception:
                continue
            if not any(nombre.startswith(p) for p in PREFIJOS):
                continue
            if nombre in ya:
                continue
            try:
                img = data.image
                if isinstance(img, bytes):
                    from PIL import Image
                    import io
                    img = Image.open(io.BytesIO(img))
                dst = DEST / f"{nombre}.png"
                img.save(dst)
                nuevos.append((nombre, dst.stat().st_size))
                ya.add(nombre)
            except Exception as e:
                print(f"  [!] {nombre}: {str(e)[:70]}")
    print(f"\n=== texturas nuevas: {len(nuevos)} (bundles ilegibles: {fallos}) ===")
    for n, s in sorted(nuevos):
        print(f"   {n:46} {s // 1024:5} KB")


if __name__ == "__main__":
    main()