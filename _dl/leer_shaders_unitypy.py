
import sys
from collections import Counter
import UnityPy

B = r"C:\Users\Lukas\p5x-datamining\game_dump\fileContentOut\Bundles\Windows\106\shaders.bundle"
env = UnityPy.load(B)
print("objetos:", len(env.objects))
print("tipos:", Counter(o.type.name for o in env.objects).most_common())
sh = [o for o in env.objects if o.type.name == "Shader"]
print("\nSHADERS:", len(sh))
for o in sh[:12]:
    try:
        d = o.read_typetree()
        print("   -", d.get("m_Name"), "| subprogramas:", len(d.get("m_SubShaders") or []))
    except Exception as e:
        print("   - (error al leer:", type(e).__name__, str(e)[:60], ")")
