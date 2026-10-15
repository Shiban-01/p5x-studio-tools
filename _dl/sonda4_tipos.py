import collections
import glob
import os
import xml.etree.ElementTree as ET

p = glob.glob(r"C:\Users\Lukas\AppData\Local\hermes\cache\scratch\sonda2\salida\**\*.xml", recursive=True)[0]
r = ET.parse(p).getroot()
por_src = collections.defaultdict(collections.Counter)
for a in r.findall("Asset"):
    src = os.path.basename((a.findtext("Source") or "").strip())
    por_src[src][a.findtext("Type")] += 1

print("%-42s %-7s %-6s %s" % ("bundle", "assets", "texturas", "tipos dentro"))
for src in sorted(por_src):
    c = por_src[src]
    tex = c.get("Texture2D", 0) + c.get("Sprite", 0)
    tipos = ", ".join("%s=%d" % (k, v) for k, v in c.most_common(4))
    print("%-42s %-7d %-6d %s" % (src[:42], sum(c.values()), tex, tipos[:60]))