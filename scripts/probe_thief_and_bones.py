"""1) Que rigs trae part_63_thief  2) Que huesos tiene realmente el actor de wonder."""
import pathlib
import re

import UnityPy

UnityPy.config.FALLBACK_UNITY_VERSION = "2022.3.49f1"


def hc(s):
    n = 0
    for c in s:
        n = (n * 131 + ord(c)) & 0xFFFFFFFF
    return n & 0x7FFFFFFF


B = pathlib.Path("C:/Users/Lukas/Downloads/P5X/Client/OuterPackage/Bundles/Windows")

# 1) part_63_thief
p = next(B.rglob("part_63_thief61cd8233.bundle"))
d = p.read_bytes()
off = hc(p.name) % 32 + 8
i = d.find(b"UnityFS", max(0, off - 4), off + 8)
if i > 0:
    d = d[i:]
tmp = pathlib.Path("_dl/part63thief.bundle")
tmp.write_bytes(d)
env = UnityPy.load(str(tmp))
print("=== part_63_thief: GameObjects ===")
for o in env.objects:
    if o.type.name == "GameObject":
        print("  ", o.read().m_Name)

# 2) actor de wonder: buscar nombres Bip01 / Bone227
actor = pathlib.Path("unity_projects/scene_full/ExportedProject/Assets/wonder_uniform.prefab")
t = actor.read_text(encoding="latin1", errors="ignore")
names = re.findall(r"m_Name: (.+)", t)
names = [n.strip() for n in names]
print(f"\n=== actor wonder_uniform: {len(names)} nombres en el YAML ===")
for pat in ["Bip01", "Bone227", "BN_", "exDummy", "Jnt"]:
    hits = [n for n in names if pat in n]
    print(f"  contiene '{pat}': {len(hits)}  ej: {hits[:3]}")
print("  muestra de nombres:", names[:12])