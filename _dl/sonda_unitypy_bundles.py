"""Sonda: ¿puede UnityPy leer los bundles INSTALADOS del juego (no solo los del vfile)?

Si puede, de ahi salen los GameObjects con sus RectTransform, que es lo que coloca cada capa del
bust-up. Si no puede (bundle cifrado), habra que ir por el vfile o por la malla del sprite.
"""
import sys
from pathlib import Path

import UnityPy

G = Path(r"C:\Users\Lukas\Downloads\P5X\Client\OuterPackage\Bundles\Windows")

for rel in ("076/uitex_changfu512a3bdb.bundle", "140/ui_lihui_shader.bundle"):
    ruta = G / rel
    print("=== %s (%d MB)" % (rel, ruta.stat().st_size // 1024 // 1024))
    try:
        env = UnityPy.load(str(ruta))
        tipos = {}
        for obj in env.objects:
            tipos[obj.type.name] = tipos.get(obj.type.name, 0) + 1
        print("   objetos: %d" % sum(tipos.values()))
        print("   tipos:", dict(sorted(tipos.items(), key=lambda t: -t[1])[:12]))
        if any(t in tipos for t in ("GameObject", "RectTransform", "Transform")):
            print("   *** HAY TRANSFORMS ***")
    except Exception as e:  # noqa: BLE001
        print("   FALLO: %s: %s" % (type(e).__name__, str(e)[:200]))
    print()