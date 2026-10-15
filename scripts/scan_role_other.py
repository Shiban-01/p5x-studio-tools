"""Escanea los role_other_* buscando las texturas de cuerpo de PC063 (thief) y wonder."""
import pathlib

import UnityPy

UnityPy.config.FALLBACK_UNITY_VERSION = "2022.3.49f1"


def hc(s):
    n = 0
    for c in s:
        n = (n * 131 + ord(c)) & 0xFFFFFFFF
    return n & 0x7FFFFFFF


B = pathlib.Path("C:/Users/Lukas/Downloads/P5X/Client/OuterPackage/Bundles/Windows")
cands = sorted(B.rglob("role_other_*.bundle"))
print(f"role_other_* : {len(cands)} bundles")

tmp = pathlib.Path("_dl/_probe2.bundle")
hits = {}
for p in cands:
    try:
        d = p.read_bytes()
        off = hc(p.name) % 32 + 8
        i = d.find(b"UnityFS", max(0, off - 4), off + 8)
        if i > 0:
            d = d[i:]
        tmp.write_bytes(d)
        env = UnityPy.load(str(tmp))
        for o in env.objects:
            if o.type.name != "Texture2D":
                continue
            try:
                n = str(o.read().m_Name)
            except Exception:
                continue
            if ("PC063" in n or "wonder_uniform" in n) and "_bc" in n:
                hits.setdefault(p.name, []).append(n)
    except Exception:
        pass

for k, v in hits.items():
    print(f"  {k}: {sorted(set(v))[:8]}")
print("total bundles con aciertos:", len(hits))