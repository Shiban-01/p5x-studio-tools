"""Herramientas de clips P5X.
  names <bundle>            lista AnimationClips del bundle
  grep <patron> [subfilt]   bundles cuyo contenido crudo contiene el patron (rapido)
  clip <patron> [subfilt]   UnityPy: que AnimationClip CONCRETO lo contiene (lento, fino)
"""
import sys
from pathlib import Path

B = Path("C:/Users/Lukas/Downloads/P5X/Client/OuterPackage/Bundles/Windows")
if not hasattr(__import__("UnityPy").config, "FALLBACK_UNITY_VERSION"):
    pass
import UnityPy
UnityPy.config.FALLBACK_UNITY_VERSION = "2022.3.49f1"

mode = sys.argv[1]

def load(p):
    env = UnityPy.load(str(p))
    return env

if mode == "names":
    env = load(sys.argv[2])
    for o in env.objects:
        if o.type.name == "AnimationClip":
            d = o.read()
            print(" clip:", getattr(d, "m_Name", "?"), "| len:", getattr(d, "m_SampleRate", "?"))
elif mode == "grep":
    pat = sys.argv[2].encode()
    sub = sys.argv[3] if len(sys.argv) > 3 else "anim"
    n = 0
    for f in B.rglob("*.bundle"):
        if sub not in f.name: continue
        if pat in f.read_bytes():
            print("HIT:", f); n += 1
    print("hits:", n, file=sys.stderr)
elif mode == "clip":
    pat = sys.argv[2]
    sub = sys.argv[3] if len(sys.argv) > 3 else "anim"
    files = [f for f in B.rglob("*.bundle") if sub in f.name]
    for i, f in enumerate(files):
        if pat.encode() not in f.read_bytes():  # pre-filtro rapido
            continue
        try:
            env = load(f)
            for o in env.objects:
                if o.type.name != "AnimationClip": continue
                try: nm = o.read().m_Name
                except Exception: continue
                if nm and pat.lower() in str(nm).lower():
                    print("CLIP HIT:", f, "->", nm)
        except Exception as e:
            print("err", f, str(e)[:60], file=sys.stderr)
    print("done", file=sys.stderr)
