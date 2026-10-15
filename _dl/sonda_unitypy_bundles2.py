"""Sonda 2: con la version de Unity forzada, ¿salen GameObjects/RectTransform del bundle de sprites?

El bundle no esta cifrado (el error era solo que la cabecera no lleva la version). Si aqui salen los
GameObject con RectTransform, el montaje exacto esta en el propio bundle del bust-up.
"""
from pathlib import Path

import UnityPy

UnityPy.config.FALLBACK_UNITY_VERSION = "2022.3.49f1"

G = Path(r"C:\Users\Lukas\Downloads\P5X\Client\OuterPackage\Bundles\Windows")

for rel in ("076/uitex_changfu512a3bdb.bundle", "043/uitex_yinying39b40dd6.bundle"):
    ruta = G / rel
    print("=== %s (%.1f MB)" % (rel, ruta.stat().st_size / 1048576))
    try:
        env = UnityPy.load(str(ruta))
        tipos = {}
        for obj in env.objects:
            tipos[obj.type.name] = tipos.get(obj.type.name, 0) + 1
        print("   objetos: %d" % sum(tipos.values()))
        for t, n in sorted(tipos.items(), key=lambda t: -t[1]):
            print("      %-22s %d" % (t, n))
        gos = [o for o in env.objects if o.type.name == "GameObject"]
        if gos:
            print("   *** %d GameObjects ***" % len(gos))
            for o in gos[:6]:
                d = o.read()
                print("      - %s" % d.m_Name)
        else:
            print("   (sin GameObjects)")
    except Exception as e:  # noqa: BLE001
        print("   FALLO: %s: %s" % (type(e).__name__, str(e)[:160]))
    print()