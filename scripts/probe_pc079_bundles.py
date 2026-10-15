"""Lista los nombres de objetos de los bundles de PC079 (tl, role, part)."""
import pathlib

import UnityPy

UnityPy.config.FALLBACK_UNITY_VERSION = "2022.3.49f1"


def hc(s):
    n = 0
    for c in s:
        n = (n * 131 + ord(c)) & 0xFFFFFFFF
    return n & 0x7FFFFFFF


B = pathlib.Path("C:/Users/Lukas/Downloads/P5X/Client/OuterPackage/Bundles/Windows")
OBJETIVOS = ["tl_pc079_01d91df0.bundle", "tl_p3p5e6d9136.bundle",
             "role_pc079_0113713867.bundle", "part_pc079_011ef29087.bundle"]
tmp = pathlib.Path("_dl/_probe3.bundle")

for nombre in OBJETIVOS:
    hits = list(B.rglob(nombre))
    if not hits:
        print(f"{nombre}: NO ENCONTRADO")
        continue
    p = hits[0]
    d = p.read_bytes()
    off = hc(p.name) % 32 + 8
    j = d.find(b"UnityFS", max(0, off - 4), off + 8)
    if j > 0:
        d = d[j:]
    tmp.write_bytes(d)
    env = UnityPy.load(str(tmp))
    tipos = {}
    nombres = []
    for o in env.objects:
        t = o.type.name
        tipos[t] = tipos.get(t, 0) + 1
        if t in ("GameObject", "AnimationClip", "MonoBehaviour"):
            try:
                nm = str(o.read().m_Name)
                if nm:
                    nombres.append(nm)
            except Exception:
                pass
    print(f"\n=== {p.name} ({p.stat().st_size // 1024} KB) ===")
    print("  tipos:", dict(sorted(tipos.items(), key=lambda x: -x[1])[:8]))
    print("  nombres:", sorted(set(nombres))[:25])