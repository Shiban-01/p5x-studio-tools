"""Compara los 216 JSON de sombreado y lo deja en CSV + resumen, para revisarlo y para la futura
funcion de P5X Studio.

Salidas:
  _dl/comparacion_216_jsons.csv    una fila por JSON con todos sus parametros
  _dl/comparacion_216_jsons.md     resumen (rangos, reparto por ropa, claves, avisos)
"""
import csv
import json
from collections import Counter
from pathlib import Path

DL = Path(r"C:\Users\Lukas\p5x-datamining\_dl")
D_JSON = DL / "lihui_shader_json"
CSV = DL / "comparacion_216_jsons.csv"
MD = DL / "comparacion_216_jsons.md"

filas = []
for f in sorted(D_JSON.glob("*.json")):
    d = json.loads(f.read_text(encoding="utf-8"))
    g = d["gradient"]
    resto = d["m_Name"].replace("UI-DialogShader-", "", 1)
    ropa, _, personaje = resto.partition("-")
    n_color = int(g["m_NumColorKeys"])
    n_alfa = int(g["m_NumAlphaKeys"])
    claves = []
    for i in range(n_color):
        k = g["key%d" % i]
        claves.append("%.3f,%.3f,%.3f@%.3f" % (k["r"], k["g"], k["b"], g["ctime%d" % i] / 65535))
    filas.append({
        "nombre": d["m_Name"], "ropa": ropa, "personaje": personaje,
        "EffectFactor": d["EffectFactor"], "Brightness": d["Brightness"],
        "Saturation": d["Saturation"], "Contrast": d["Contrast"],
        "GradientAlphaBottom": d["GradientAlphaBottom"], "GradientAlphaTop": d["GradientAlphaTop"],
        "GraBrightness": d["GraBrightness"], "GraSaturation": d["GraSaturation"],
        "GraContrast": d["GraContrast"], "EnableFastBlur": d["EnableFastBlur"],
        "BlurStrength": d["BlurStrength"], "gradientMode": d["gradientMode"],
        "Angle": d["Angle"], "Center": "%.2f,%.2f" % (d["Center"]["x"], d["Center"]["y"]),
        "Ratio": "%.2f,%.2f" % (d["Ratio"]["x"], d["Ratio"]["y"]),
        "claves_color": n_color, "claves_alfa": n_alfa,
        "alfa_desde": g["atime0"] / 65535, "alfa_hasta": g["atime%d" % (n_alfa - 1)] / 65535,
        "color_keys": " | ".join(claves),
    })

with CSV.open("w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(filas[0].keys()))
    w.writeheader()
    w.writerows(filas)
print("csv:", CSV, "(%d filas)" % len(filas))

# ---- resumen ----
lineas = ["# Los 216 JSON de sombreado de bust-up: comparacion", ""]
lineas.append("%d JSON en total." % len(filas))
lineas.append("")
lineas.append("## Rangos de parametros")
lineas.append("")
lineas.append("| campo | min | max | media | valores distintos |")
lineas.append("|---|---|---|---|---|")
for campo in ["EffectFactor", "Brightness", "Saturation", "Contrast", "GradientAlphaBottom",
              "GradientAlphaTop", "GraBrightness", "GraSaturation", "GraContrast",
              "BlurStrength", "Angle"]:
    vals = [f[campo] for f in filas]
    lineas.append("| %s | %.3f | %.3f | %.3f | %d |"
                  % (campo, min(vals), max(vals), sum(vals) / len(vals), len(set(vals))))

lineas += ["", "## Reparto", ""]
def reparto(titulo, contador):
    lineas.append("**%s:** %s" % (titulo, ", ".join("%s=%d" % (k, v) for k, v in sorted(contador.items()))))
    lineas.append("")

reparto("Ropa (etiqueta del JSON)", Counter(f["ropa"] for f in filas))
reparto("gradientMode (0 lineal, 1 radial)", Counter(f["gradientMode"] for f in filas))
reparto("EnableFastBlur", Counter(f["EnableFastBlur"] for f in filas))
reparto("Claves de color", Counter(f["claves_color"] for f in filas))
reparto("Claves de alfa", Counter(f["claves_alfa"] for f in filas))
reparto("EffectFactor", Counter(f["EffectFactor"] for f in filas))

lineas += ["## Los que se salen de lo comun", ""]
lineas.append("Son los que mas facilmente delatan una recreacion que no los tenga en cuenta:")
lineas.append("")
for titulo, clave, cond in [
    ("EffectFactor bajo (el efecto casi no se ve)", "EffectFactor", lambda v: v < 0.5),
    ("Brightness fuera de 1 (tono base fuerte)", "Brightness", lambda v: abs(v - 1) > 0.25),
    ("GraContrast alto (degradado muy contrastado)", "GraContrast", lambda v: v > 2),
    ("GraSaturation alta", "GraSaturation", lambda v: v > 2),
    ("Rampa de alfa corta (menos de la mitad de la imagen)", "alfa_hasta",
     lambda v: v < 0.5),
]:
    sel = [f for f in filas if cond(f[clave])]
    lineas.append("**%s: %d**" % (titulo, len(sel)))
    lineas.append("")
    for f in sel[:12]:
        lineas.append("- `%s` — %s=%.3f" % (f["nombre"], clave, f[clave]))
    if len(sel) > 12:
        lineas.append("- …y %d mas (ver el CSV)" % (len(sel) - 12))
    lineas.append("")

MD.write_text("\n".join(lineas), encoding="utf-8")
print("resumen:", MD)
print()
print("\n".join(lineas[:26]))