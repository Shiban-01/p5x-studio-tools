"""Abre el Shader UI/UIMultipleGradient en los bundles del juego y saca su lista real de propiedades.

El dump.cs da los campos del C#, y el GLSL de AssetRipper da la cuenta, pero la lista de propiedades
con sus valores por defecto esta en el propio asset del Shader (`m_ParsedForm.m_PropInfo`). Eso es la
fuente original: con ella se sabe que propiedades existen de verdad y con que valor arrancan, que es
lo que faltaba para la rampa de alfa.
"""
import re
import sys
from collections import Counter
from pathlib import Path

import UnityPy

JUEGO = Path(r"C:/Users/Lukas/Downloads/P5X/Client/OuterPackage/Bundles/Windows")
CACHE = Path(r"C:/Users/Lukas/p5x-datamining/p5x_studio/cache/work/shaders")
SALIDA = Path(r"C:/Users/Lukas/p5x-datamining/_dl/shaders_originales")
SALIDA.mkdir(parents=True, exist_ok=True)


def bundles_candidatos():
    """Los bundles donde el censo anterior vio UIMultipleGradient."""
    vistos = []
    for xml in CACHE.glob("*/assets.xml"):
        try:
            if "UIMultipleGradient" in xml.read_text(encoding="utf-8", errors="replace"):
                vistos.append(xml.parent.name)
        except Exception:
            continue
    return vistos


def main():
    nombres = bundles_candidatos()
    print("bundles candidatos segun el censo: %d" % len(nombres))
    for n in nombres:
        print("   ", n)

    # el nombre del cache es <numero>_<resto>.bundle; se busca el fichero real en el juego
    encontrados = []
    for n in nombres:
        cand = list(JUEGO.rglob(n))
        if not cand:
            cand = list(JUEGO.rglob("*" + n.split("_", 1)[-1]))
        encontrados.extend(cand)
    print("ficheros reales localizados: %d" % len(encontrados))

    for f in encontrados:
        try:
            env = UnityPy.load(str(f))
        except Exception as e:
            print("  %s: no se pudo abrir (%s)" % (f.name, type(e).__name__))
            continue
        shaders = [o for o in env.objects if o.type.name == "Shader"]
        if not shaders:
            continue
        for o in shaders:
            try:
                d = o.read_typetree()
            except Exception as e:
                print("  %s: shader ilegible (%s)" % (f.name, type(e).__name__))
                continue
            nombre = d.get("m_Name") or ""
            parsed = d.get("m_ParsedForm") or {}
            props = parsed.get("m_PropInfo", {}).get("m_Props", []) or []
            textos = [p.get("m_Name") for p in props]
            if "UIMultipleGradient" not in nombre and not any(
                    t and ("GradientAlpha" in t or "GraBrightness" in t) for t in textos):
                continue
            print()
            print("=" * 90)
            print("%s   en %s/%s" % (nombre, f.parent.name, f.name))
            print("=" * 90)
            print("propiedades declaradas en el shader: %d" % len(textos))
            for p in props:
                n = p.get("m_Name")
                ptype = p.get("m_Type")
                vals = p.get("m_DefValue") or []
                desc = p.get("m_Description") or ""
                marca = "  <-- " if n and ("Gradient" in n or "Gra" in n) else ""
                print("   %-34s tipo %-3s def %-28s %s%s" % (n, ptype, vals[:4], desc[:40], marca))
            (SALIDA / (re.sub(r"[^A-Za-z0-9_.-]", "_", nombre or "shader") + ".json")).write_text(
                __import__("json").dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
            print("   (objeto completo guardado en shaders_originales/)")
    return 0


if __name__ == "__main__":
    sys.exit(main())