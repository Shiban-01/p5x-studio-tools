"""Inspecciona las capas extraidas del bust-up de xiachuanling y los parametros de su JSON."""
import json
from pathlib import Path

from PIL import Image

O = Path(r"C:\Users\Lukas\AppData\Local\hermes\cache\scratch\xiachuanling")
capas = ["benti", "benti-yifu", "benti-toufa", "benti-lunkuo", "benti-zhi",
         "tongchang-yan1", "tongchang-zui1", "haixiuxiao-saihong"]
print("=== tamanos de las capas (Sprite y Texture2D) ===")
for c in capas:
    for f in sorted(O.glob("xiachuanling-changfu-%s*.png" % c)):
        im = Image.open(f)
        print("   %-52s %s %s" % (f.name, im.size, im.mode))

print()
print("=== parametros del JSON de xiachuanling ===")
j = Path(r"C:\Users\Lukas\p5x-datamining\_dl\lihui_shader_json"
         r"\UI-DialogShader-changfu01-xiachuanling.json")
d = json.loads(j.read_text(encoding="utf-8"))
for k, v in d.items():
    if k != "gradient":
        print("   %-20s %s" % (k, v))
g = d["gradient"]
print("   gradient: NumColorKeys=%s NumAlphaKeys=%s Mode=%s ColorSpace=%s"
      % (g["m_NumColorKeys"], g["m_NumAlphaKeys"], g["m_Mode"], g["m_ColorSpace"]))
for i in range(int(g["m_NumColorKeys"])):
    k = g["key%d" % i]
    print("      color%d  pos %.4f  rgb (%.3f, %.3f, %.3f)  a %.3f"
          % (i, g["ctime%d" % i] / 65535, k["r"], k["g"], k["b"], k["a"]))
for i in range(int(g["m_NumAlphaKeys"])):
    k = g["key%d" % i]
    print("      alfa%d   pos %.4f  a %.3f" % (i, g["atime%d" % i] / 65535, k["a"]))