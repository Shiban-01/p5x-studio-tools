"""1) Posiciones de walksurface/terrain en la escena iwai (para anclar a los actores).
2) Que bundle contiene el actor `frost_normal` y sus partes.
"""
import pathlib
import re

import UnityPy

UnityPy.config.FALLBACK_UNITY_VERSION = "2022.3.49f1"


def hc(s):
    n = 0
    for c in s:
        n = (n * 131 + ord(c)) & 0xFFFFFFFF
    return n & 0x7FFFFFFF


# ---------- 1) escena ----------
p = pathlib.Path("unity_projects/kotone/ExportedProject/Assets/GeneratedRes/Scene/PC/"
                 "ysc_tianshouge_shiwai_wyc/ysc_tianshouge_shiwai_wyc.unity")
t = p.read_text(encoding="latin1", errors="replace")

# id de GameObject -> nombre
go = {}
for m in re.finditer(r"^--- !u!1 &(\d+)\n(GameObject:.*?)(?=^--- |\Z)", t, re.S | re.M):
    nm = re.search(r"m_Name: (.*)", m.group(2))
    if nm:
        go[m.group(1)] = nm.group(1).strip()

obj = {}
for m in re.finditer(r"^--- !u!4 &(\d+)\n(Transform:.*?)(?=^--- |\Z)", t, re.S | re.M):
    g = re.search(r"m_GameObject: \{fileID: (\d+)\}", m.group(2))
    pos = re.search(r"m_LocalPosition: \{x: ([\d.eE+-]+), y: ([\d.eE+-]+), z: ([\d.eE+-]+)\}", m.group(2))
    if g and pos and g.group(1) in go:
        obj[go[g.group(1)]] = tuple(round(float(v), 2) for v in pos.groups())

print("=== objetos con nombre de suelo/superficie/terreno ===")
for k, v in obj.items():
    if re.search(r"walk|terrain|floor|ground|jz", k, re.I):
        print(f"  {k}: {v}")
print(f"\n(total transform de GameObjects: {len(obj)})")
print("=== muestra de otros objetos y su posicion ===")
for k, v in list(obj.items())[:14]:
    print(f"  {k}: {v}")

# ---------- 2) frost ----------
B = pathlib.Path("C:/Users/Lukas/Downloads/P5X/Client/OuterPackage/Bundles/Windows")
tmp = pathlib.Path("_dl/_frost.bundle")
for n in ["role_ackfrost4b192298", "role_ingfrost74f3ed18", "roletiny_aishuang748b12ea",
          "anim_ingfrost74f3ed18"]:
    hits = list(B.rglob(n + ".bundle"))
    if not hits:
        print(f"\n{n}: NO ENCONTRADO")
        continue
    pp = hits[0]
    d = pp.read_bytes()
    off = hc(pp.name) % 32 + 8
    j = d.find(b"UnityFS", max(0, off - 4), off + 8)
    if j > 0:
        d = d[j:]
    tmp.write_bytes(d)
    env = UnityPy.load(str(tmp))
    nombres = []
    for o in env.objects:
        if o.type.name in ("GameObject", "AnimationClip", "MonoBehaviour"):
            try:
                nm = str(o.read().m_Name)
                if nm and "frost" in nm.lower():
                    nombres.append(nm)
            except Exception:
                pass
    print(f"\n=== {pp.name} ({pp.stat().st_size // 1024 // 1024} MB) ===")
    print(f"  refs 'frost': {sorted(set(nombres))[:15]}")