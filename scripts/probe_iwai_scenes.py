"""Inspecciona los candidatos de escenario visual (iwatodai / zone1)."""
import pathlib

import UnityPy

UnityPy.config.FALLBACK_UNITY_VERSION = "2022.3.49f1"


def hc(s):
    n = 0
    for c in s:
        n = (n * 131 + ord(c)) & 0xFFFFFFFF
    return n & 0x7FFFFFFF


B = pathlib.Path("C:/Users/Lukas/Downloads/P5X/Client/OuterPackage/Bundles/Windows")
tmp = pathlib.Path("_dl/_scn2.bundle")

for n in ["scn_iwai_wyc718eb6dc", "scn_os_zone12d10ce94", "scn_os_zone11d5cc2da"]:
    hits = list(B.rglob(n + ".bundle"))
    if not hits:
        print(f"{n}: NO ENCONTRADO")
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
    gos = []
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
    print(f"\n=== {p.name} ({p.stat().st_size // 1024 // 1024} MB) ===")
    print("  tipos:", dict(sorted(tipos.items(), key=lambda x: -x[1])[:9]))
    print(f"  {len(gos)} GameObjects:")
    for nm in gos[:30]:
        print("   -", nm)