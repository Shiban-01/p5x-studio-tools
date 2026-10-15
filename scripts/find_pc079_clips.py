"""Busca AnimationClips de PC079 (Kotone) en los bundles anim_*.

Salida: _dl/pc079_clips.json  {bundle: [nombres de clip]}
Los nombres de clip revelan el rig/atuendo: PC079_uniform@..., PC079_thief@...
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
tmp = pathlib.Path("_dl/_scan.bundle")
bundles = sorted(B.rglob("anim_*.bundle"))
print(f"anim bundles: {len(bundles)}", flush=True)

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
            if o.type.name != "AnimationClip":
                continue
            try:
                n = str(o.read().m_Name)
            except Exception:
                continue
            if "PC079" in n.upper():
                names.append(n)
        if names:
            hits[p.name] = sorted(set(names))
            print(f"  {p.name}: {len(names)} clips", flush=True)
    except Exception as e:
        print(f"  {p.name}: ERROR {str(e)[:40]}", flush=True)
    if i % 25 == 0:
        print(f"  ... {i}/{len(bundles)}", flush=True)

pathlib.Path("_dl/pc079_clips.json").write_text(
    json.dumps(hits, indent=1, ensure_ascii=False), encoding="utf-8")
print(f"TOTAL bundles con clips PC079: {len(hits)}")
for k, v in hits.items():
    print(f"{k}: {v[:10]}")