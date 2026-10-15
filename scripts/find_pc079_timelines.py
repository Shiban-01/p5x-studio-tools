"""Escanea TODOS los tl_* buscando timelines que usen PC079 (Kotone).

Los playables exponen nombres tipo 'AnimationPlayableAsset of PC079_01@attack',
asi que basta con leer los m_Name de los objetos.
Salida: _dl/pc079_timelines.json
"""
import json
import pathlib

import UnityPy

UnityPy.config.FALLBACK_UNITY_VERSION = "2022.3.49f1"


def hc(s):
    n = 0
    for c in s:
        n = (n * 131 + ord(c)) & 0xFFFFFFFF
    return n & 0x7FFFFFFF


B = pathlib.Path("C:/Users/Lukas/Downloads/P5X/Client/OuterPackage/Bundles/Windows")
tmp = pathlib.Path("_dl/_scan_tl.bundle")
bundles = sorted(B.rglob("tl_*.bundle"))
print(f"tl bundles: {len(bundles)}", flush=True)

hits = {}
for i, p in enumerate(bundles):
    try:
        d = p.read_bytes()
        off = hc(p.name) % 32 + 8
        j = d.find(b"UnityFS", max(0, off - 4), off + 8)
        if j > 0:
            d = d[j:]
        tmp.write_bytes(d)
        env = UnityPy.load(str(tmp))
        names = []
        for o in env.objects:
            if o.type.name not in ("MonoBehaviour", "GameObject", "AnimationClip"):
                continue
            try:
                nm = str(o.read().m_Name)
            except Exception:
                continue
            if "PC079" in nm.upper():
                names.append(nm)
        if names:
            hits[p.name] = sorted(set(names))
            print(f"  {p.name}: {len(names)} refs", flush=True)
    except Exception as e:
        print(f"  {p.name}: ERROR {str(e)[:40]}", flush=True)
    if i % 50 == 0:
        print(f"  ... {i}/{len(bundles)}", flush=True)

pathlib.Path("_dl/pc079_timelines.json").write_text(
    json.dumps(hits, indent=1, ensure_ascii=False), encoding="utf-8")
print(f"\nTOTAL timelines con PC079: {len(hits)}")
for k, v in hits.items():
    print(f"{k}: {v[:8]}")