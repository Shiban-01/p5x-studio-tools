"""Para bundles tl candidatos: lista TODOS los clips/actores y cuenta animators.

Asi se ve si la escena tiene varios personajes y que hace Kotone en ella.
"""
import pathlib
import re
import sys

import UnityPy

UnityPy.config.FALLBACK_UNITY_VERSION = "2022.3.49f1"


def hc(s):
    n = 0
    for c in s:
        n = (n * 131 + ord(c)) & 0xFFFFFFFF
    return n & 0x7FFFFFFF


B = pathlib.Path("C:/Users/Lukas/Downloads/P5X/Client/OuterPackage/Bundles/Windows")
tmp = pathlib.Path("_dl/_probe4.bundle")

CAND = sys.argv[1:] or ["tl_ue_00_042902e514.bundle", "tl_ue_04_04298c1b80.bundle",
                        "tl_e_02_1_27b96221.bundle", "tl_ue_05_0429ae691b.bundle"]

for nombre in CAND:
    hits = list(B.rglob(nombre))
    if not hits:
        print(f"{nombre}: NO ENCONTRADO")
        continue
    p = hits[0]
    d = p.read_bytes()
    j = d.find(b"UnityFS", max(0, hc(p.name) % 32 + 8 - 4), hc(p.name) % 32 + 16)
    if j > 0:
        d = d[j:]
    tmp.write_bytes(d)
    env = UnityPy.load(str(tmp))
    animators = 0
    playables = set()
    gos = set()
    for o in env.objects:
        t = o.type.name
        if t == "Animator":
            animators += 1
        elif t == "MonoBehaviour":
            try:
                nm = str(o.read().m_Name)
            except Exception:
                continue
            m = re.match(r"AnimationPlayableAsset of (.+)", nm)
            if m:
                playables.add(m.group(1))
        elif t == "GameObject":
            try:
                gos.add(str(o.read().m_Name))
            except Exception:
                pass
    clips = sorted(playables)
    rigs = sorted({c.split("@")[0] for c in clips if "@" in c})
    print(f"\n=== {p.name} ({p.stat().st_size // 1024} KB) animators={animators} clips={len(clips)} ===")
    print("  rigs/actores:", rigs)
    print("  clips:", clips[:24])
    otros = [g for g in sorted(gos) if g and not g.startswith(("Animation", "Activation", "Track", "Group"))]
    print("  gameobjects:", otros[:18])