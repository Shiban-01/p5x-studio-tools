"""Lista TODOS los nombres de objetos de los bundles frost para identificar el actor."""
import pathlib

import UnityPy

UnityPy.config.FALLBACK_UNITY_VERSION = "2022.3.49f1"


def hc(s):
    n = 0
    for c in s:
        n = (n * 131 + ord(c)) & 0xFFFFFFFF
    return n & 0x7FFFFFFF


B = pathlib.Path("C:/Users/Lukas/Downloads/P5X/Client/OuterPackage/Bundles/Windows")
tmp = pathlib.Path("_dl/_frost2.bundle")

cands = sorted({p.name for p in B.rglob("*.bundle")
                if "frost" in p.name.lower() and p.name.startswith(("role_", "part_", "roletiny_", "anim_"))})
print("candidatos:", cands)

for n in cands:
    p = next(B.rglob(n))
    d = p.read_bytes()
    off = hc(p.name) % 32 + 8
    j = d.find(b"UnityFS", max(0, off - 4), off + 8)
    if j > 0:
        d = d[j:]
    tmp.write_bytes(d)
    env = UnityPy.load(str(tmp))
    gos, rigs = [], []
    tipos = {}
    for o in env.objects:
        t = o.type.name
        tipos[t] = tipos.get(t, 0) + 1
        if t == "GameObject":
            try:
                nm = str(o.read().m_Name)
                if nm:
                    gos.append(nm)
            except Exception:
                pass
        elif t == "AnimationClip":
            try:
                nm = str(o.read().m_Name)
                if "@" in nm:
                    rigs.append(nm.split("@")[0])
            except Exception:
                pass
    print(f"\n=== {n} ({p.stat().st_size // 1024} KB) ===")
    print("  tipos:", dict(sorted(tipos.items(), key=lambda x: -x[1])[:6]))
    print("  rigs en clips:", sorted(set(rigs))[:6])
    print("  GameObjects:", sorted(set(gos))[:18])