"""Parser manual del FlatBuffer zeusBundleManifest.txt (ZeusBundleManifestFB).

Esquema IL2CPP:
  ZeusBundleManifestFB: Infos: [ZeusAssetBundle]
  ZeusAssetBundle: Name:string, Hash:string, Dependencies:[int] (indices a Infos), Crc:uint32
"""
import json
import struct
from pathlib import Path

P = Path(r"C:\Users\Lukas\Downloads\P5X\Client\OuterPackage\Bundles\Windows\104\zeusBundleManifest.txt")
b = P.read_bytes()
print("bytes:", len(b))

def u32(p): return struct.unpack_from("<I", b, p)[0]
def i32(p): return struct.unpack_from("<i", b, p)[0]
def i16(p): return struct.unpack_from("<h", b, p)[0]

def table_field(tab, field):
    vt = tab - i32(tab)
    vtsz = i16(vt)
    if 4 + 2 * field >= vtsz:
        return 0
    off = i16(vt + 4 + 2 * field)
    return tab + off if off else 0

def read_string(voff):
    p = voff + u32(voff)
    n = u32(p)
    return b[p + 4:p + 4 + n].decode("utf-8", "replace")

root = u32(0)
print("root table @", root)
infos_f = table_field(root, 0)
vec = infos_f + u32(infos_f)
n = u32(vec)
print("Infos:", n)

bundles = []
for i in range(n):
    ep = vec + 4 + 4 * i
    tab = ep + u32(ep)
    name_f = table_field(tab, 0)
    hash_f = table_field(tab, 1)
    dep_f = table_field(tab, 2)
    crc_f = table_field(tab, 3)
    name = read_string(name_f) if name_f else None
    h = read_string(hash_f) if hash_f else None
    deps = []
    if dep_f:
        dvp = dep_f + u32(dep_f)
        m = u32(dvp)
        deps = [i32(dvp + 4 + 4 * k) for k in range(m)]
    crc = u32(crc_f) if crc_f else 0
    bundles.append({"index": i, "name": name, "hash": h, "deps": deps, "crc": crc})

print("primeros 5:")
for e in bundles[:5]:
    print("   ", e["index"], e["name"], "deps:", e["deps"][:6], "hash:", (e["hash"] or "")[:8], "crc:", e["crc"])

con_deps = [e for e in bundles if e["deps"]]
print("bundles con dependencias:", len(con_deps))
tot = sum(len(e["deps"]) for e in bundles)
print("aristas de dependencia totales:", tot)
for e in con_deps[:8]:
    nombres = [bundles[d]["name"] if 0 <= d < len(bundles) else "??%d" % d for d in e["deps"]]
    print("   %-46s -> %s" % (e["name"], ", ".join(nombres[:5])))

# comprobar rango de indices
fuera = [(e["name"], d) for e in bundles for d in e["deps"] if not (0 <= d < n)]
print("dependencias fuera de rango:", len(fuera), fuera[:5])

out = Path(r"C:\Users\Lukas\p5x-datamining\_dl\zeus_manifest.json")
out.write_text(json.dumps({"count": n, "bundles": bundles}, ensure_ascii=False, indent=0), encoding="utf-8")
print("guardado:", out, out.stat().st_size, "bytes")