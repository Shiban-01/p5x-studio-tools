"""Parsea assetMapName.txt (FlatBuffer AssetMapBundleFB) -> lista (path, bundle).

Esquema IL2CPP:
  AssetMapBundleFB: H2b:[AssetHashMapBundleFB], P2b:[AssetPathMapBundleFB]
  AssetHashMapBundleFB: Hash:uint, Bundle:string
  AssetPathMapBundleFB: Path:string, Bundle:string
"""
import json
import struct
import sys
from pathlib import Path

P = Path(sys.argv[1] if len(sys.argv) > 1 else
         r"C:\Users\Lukas\Downloads\P5X\Client\OuterPackage\Bundles\Windows\105\assetMapName.txt")
b = P.read_bytes()
print("bytes:", len(b))


def u32(p): return struct.unpack_from("<I", b, p)[0]
def i32(p): return struct.unpack_from("<i", b, p)[0]
def i16(p): return struct.unpack_from("<h", b, p)[0]


def campo(tab, f):
    vt = tab - i32(tab)
    if 4 + 2 * f >= i16(vt):
        return 0
    off = i16(vt + 4 + 2 * f)
    return tab + off if off else 0


def texto(voff):
    p = voff + u32(voff)
    n = u32(p)
    return b[p + 4:p + 4 + n].decode("utf-8", "replace")


root = u32(0)
print("root @", root)
for nombre, f in (("H2b", 0), ("P2b", 1)):
    vf = campo(root, f)
    if not vf:
        print(nombre, "ausente"); continue
    vec = vf + u32(vf)
    n = u32(vec)
    print(nombre, ":", n)
    if n and f == 1:
        for i in range(min(n, 5)):
            ep = vec + 4 + 4 * i
            tab = ep + u32(ep)
            path = texto(campo(tab, 0)) if campo(tab, 0) else "?"
            bun = texto(campo(tab, 1)) if campo(tab, 1) else "?"
            print("   ", path, "->", bun)

# volcar P2b completo si es razonable
vf = campo(root, 1)
vec = vf + u32(vf)
n = u32(vec)
pares = []
for i in range(n):
    ep = vec + 4 + 4 * i
    tab = ep + u32(ep)
    path = texto(campo(tab, 0)) if campo(tab, 0) else ""
    bun = texto(campo(tab, 1)) if campo(tab, 1) else ""
    pares.append((path, bun))
print("total pares path->bundle:", len(pares))
out = Path(r"C:\Users\Lukas\p5x-datamining\_dl\assetmap_pairs.json")
out.write_text(json.dumps(pares, ensure_ascii=False), encoding="utf-8")
print("guardado", out)

# que pinta tienen los paths y prefabs
import re
pref = [p for p, _ in pares if re.search(r"prefab", p, re.I)]
print("paths con 'prefab':", len(pref), pref[:10])
bust = [(p, b_) for p, b_ in pares if re.search(r"(changfu|lihui|bust)", p, re.I)]
print("paths con changfu/lihui/bust:", len(bust))
for p, b_ in bust[:20]:
    print("   ", p, "->", b_)