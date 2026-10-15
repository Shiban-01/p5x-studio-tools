"""Lista todos los JSON de sombreado de un personaje y el color de su degradado.

Si la captura del juego no cuadra con el JSON que use, puede ser que el mismo personaje tenga varios
(de una escena de dialogo 'richang', de traje 'changfu', de ladron 'guaidao'...) con degradados de
tono distinto.
"""
import json
import sys
from pathlib import Path

D = Path(r"C:\Users\Lukas\p5x-datamining\_dl\lihui_shader_json")
nombre = sys.argv[1] if len(sys.argv) > 1 else "xiachuanling"

for f in sorted(D.glob("*%s*.json" % nombre)):
    d = json.loads(f.read_text(encoding="utf-8"))
    g = d["gradient"]
    n = int(g["m_NumColorKeys"])
    colores = []
    for i in range(n):
        k = g["key%d" % i]
        colores.append("%.3f,%.3f,%.3f @%.2f" % (k["r"], k["g"], k["b"], g["ctime%d" % i] / 65535))
    print("%s" % d["m_Name"])
    print("    Effect %.2f | base %.2f/%.2f/%.2f | gra %.2f/%.2f/%.2f | alfa %.2f..%.2f | modo %s | angulo %.2f"
          % (d["EffectFactor"], d["Brightness"], d["Saturation"], d["Contrast"],
             d["GraBrightness"], d["GraSaturation"], d["GraContrast"],
             d["GradientAlphaBottom"], d["GradientAlphaTop"],
             "radial" if d["gradientMode"] else "lineal", d["Angle"]))
    print("    colores: %s" % " | ".join(colores))
    print("    claves de alfa: %s" % " ".join("%.3f" % (g["atime%d" % i] / 65535)
                                              for i in range(int(g["m_NumAlphaKeys"]))))
    print()