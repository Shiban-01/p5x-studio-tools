"""Inspecciona los MonoBehaviour de part_63_thief: raiz + primeros huesos de cada rig."""
import pathlib
import re

import UnityPy

UnityPy.config.FALLBACK_UNITY_VERSION = "2022.3.49f1"


def hc(s):
    n = 0
    for c in s:
        n = (n * 131 + ord(c)) & 0xFFFFFFFF
    return n & 0x7FFFFFFF


p = pathlib.Path("_dl/part63thief.bundle")
env = UnityPy.load(str(p))
print(f"objetos: {len(env.objects)}")
for o in env.objects:
    if o.type.name != "MonoBehaviour":
        continue
    d = o.read()
    if not hasattr(d, "m_Script"):
        continue
    raw = d.m_Script.read() if hasattr(d.m_Script, "read") else None
    name = getattr(d, "m_Name", "")
    try:
        tree = d.read_typetree()
    except Exception as e:
        print("  (no typetree)", name, str(e)[:40])
        continue
    if not any("Bone" in str(k) for k in tree.keys()):
        continue
    root = tree.get("mHighRootBoneName", tree.get("mRootBoneName", "?"))
    bones = tree.get("mHighMeshBoneNames") or tree.get("mMeshBoneNames") or []
    mats = tree.get("mHighMeshMaterials") or []
    print(f"\n{name}: raiz={root!r} huesos={len(bones)} materiales={len(mats)}")
    print("  primeros:", bones[:4])