import sys
from collections import Counter
import UnityPy

RUTA = sys.argv[1]
env = UnityPy.load(RUTA)
objs = list(env.objects)
print("bundle:", RUTA)
print("objetos:", len(objs), "| tipos:", Counter(o.type.name for o in objs).most_common())
print("container:", len(getattr(env, "container", {}) or {}))
try:
    print("externals:")
    for a in env.assets:
        for e in (getattr(a, "externals", None) or []):
            print("   ", e.path, "|", e.type, "|", e.guid)
except Exception as e:
    print("externals err", e)

nombres = []
for o in objs:
    try:
        d = o.read_typetree()
        nm = d.get("m_Name") or d.get("name") or "?"
        nombres.append((o.type.name, nm))
    except Exception as e:
        nombres.append((o.type.name, "<error %s>" % type(e).__name__))
print("--- nombres ---")
for t, n in nombres:
    print("   %-14s %s" % (t, n))