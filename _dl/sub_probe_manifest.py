import sys
from collections import Counter
import UnityPy

P = r"C:\Users\Lukas\Downloads\P5X\Client\OuterPackage\Bundles\Windows\104\zeusBundleManifest.txt"
env = UnityPy.load(P)
print("assets:", len(env.assets))
for a in env.assets:
    print("  asset:", getattr(a, "name", None), "| objects:", len(a.objects),
          "| unity:", getattr(a, "unity_version", None),
          "| big:", getattr(a, "big_id_enabled", None))
objs = list(env.objects)
print("objetos totales:", len(objs))
print("tipos:", Counter(o.type.name for o in objs).most_common(30))

for o in objs[:5]:
    try:
        d = o.read_typetree()
        print("---", o.type.name, "claves:", list(d.keys())[:30])
    except Exception as e:
        print("--- error", o.type.name, type(e).__name__, str(e)[:100])

# container
try:
    c = env.container
    print("container entradas:", len(c))
    for k in list(c)[:10]:
        print("   ", k)
except Exception as e:
    print("container error:", type(e).__name__, str(e)[:120])