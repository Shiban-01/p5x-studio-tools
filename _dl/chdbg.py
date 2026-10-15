import re, sys
from pathlib import Path
sys.argv = ["x", "unity_projects/scene_tl005/ExportedProject/Assets", "TL_P3re_PC063_00"]
src = open("scripts/choreography.py", encoding="utf-8").read().split("def walk")[0]
exec(src)

f = Path("unity_projects/scene_tl005/ExportedProject/Assets/MonoBehaviour/Playable动画.asset")
print("doc key:", (str(f), "11400000") in DOCS)
print("path str repr:", repr(str(f)))
keys = [k for k in DOCS if "Playable" in k[0]]
print("claves Playable:", keys[:3])
