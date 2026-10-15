"""Busca las texturas de cuerpo que faltan en bundles candidatos (atlas/uitex/role/p_*)."""
import pathlib

import UnityPy

UnityPy.config.FALLBACK_UNITY_VERSION = "2022.3.49f1"


def hc(s):
    n = 0
    for c in s:
        n = (n * 131 + ord(c)) & 0xFFFFFFFF
    return n & 0x7FFFFFFF


B = pathlib.Path("C:/Users/Lukas/Downloads/P5X/Client/OuterPackage/Bundles/Windows")
OBJETIVOS = ["pc063", "63_02", "63_thief", "wonder"]
PATRONES = ["atlas_", "uitex_", "role_", "p_", "mat_", "tex"]

cands = []
for p in B.rglob("*.bundle"):
    ln = p.name.lower()
    if any(o in ln for o in OBJETIVOS):
        cands.append(p)
    elif any(ln.startswith(q) for q in PATRONES) and ("63" in ln or "wonder" in ln):
        cands.append(p)

print(f"candidatos: {len(cands)}")
tmp = pathlib.Path("_dl/_probe.bundle")
for p in sorted(set(cands)):
    try:
        d = p.read_bytes()
        off = hc(p.name) % 32 + 8
        i = d.find(b"UnityFS", max(0, off - 4), off + 8)
        if i > 0:
            d = d[i:]
        tmp.write_bytes(d)
        env = UnityPy.load(str(tmp))
        texs = []
        for o in env.objects:
            if o.type.name == "Texture2D":
                try:
                    n = str(o.read().m_Name)
                except Exception:
                    continue
                if "bc" in n and ("body" in n or "uniform" in n):
                    texs.append(n)
        if texs:
            print(f"  {p.name}: {texs[:6]}")
    except Exception as e:
        print(f"  {p.name}: error {str(e)[:40]}")