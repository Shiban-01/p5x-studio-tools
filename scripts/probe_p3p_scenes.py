"""Inspecciona los escenarios del evento P3P (scn_1_p3p_0X)."""
import pathlib

import UnityPy

UnityPy.config.FALLBACK_UNITY_VERSION = "2022.3.49f1"


def hc(s):
    n = 0
    for c in s:
        n = (n * 131 + ord(c)) & 0xFFFFFFFF
    return n & 0x7FFFFFFF


B = pathlib.Path("C:/Users/Lukas/Downloads/P5X/Client/OuterPackage/Bundles/Windows")
tmp = pathlib.Path("_dl/_scn.bundle")

for n in ["scn_1_p3p_013c97ac6c", "scn_1_p3p_023c97ac6d", "scn_1_p3p_033c97ac6e",
          "scn_1_p3p_043c97ac6f", "scn_1_p3p_053c97ac70"]:
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
    raiz, hijos = [], []
    for o in env.objects:
        t = o.type.name
        tipos[t] = tipos.get(t, 0) + 1
        if t == "GameObject":
            try:
                nm = str(o.read().m_Name)
            except Exception:
                continue
            if nm:
                hijos.append(nm)
    print(f"\n=== {p.name} ({p.stat().st_size // 1024 // 1024} MB) ===")
    print("  tipos:", dict(sorted(tipos.items(), key=lambda x: -x[1])[:7]))
    print(f"  {len(hijos)} GameObjects. Muestra:")
    for nm in hijos[:22]:
        print("   -", nm)