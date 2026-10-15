"""F1.5 — Busca las texturas compartidas que los materiales dejan como placeholder:
`_DiffuseRampTexture` (rampa de difusion del toon) y `_MatcapMap` (esfera matcap).

Explora: (a) las texturas ya exportadas en todos los proyectos Unity, por nombre y por
tamano (una ramp suele ser diminuta y alargada), (b) los nombres de bundle del cliente.
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROYECTOS = ROOT / "unity_projects"
BUNDLES = Path("C:/Users/Lukas/Downloads/P5X/Client/OuterPackage/Bundles/Windows")
CLAVES = ("ramp", "matcap", "clamp", "toon", "_ht", "gradient", "lut", "sphere")


def dimensiones(p: Path):
    """Lee ancho/alto del IHDR de un PNG sin dependencias."""
    try:
        with p.open("rb") as f:
            head = f.read(26)
        if head[:8] != b"\x89PNG\r\n\x1a\n":
            return None
        return int.from_bytes(head[16:20], "big"), int.from_bytes(head[20:24], "big")
    except OSError:
        return None


def main():
    print("=== (a) texturas por nombre en proyectos exportados ===")
    hits = []
    pequenas = []
    total = 0
    for proj in sorted(x for x in PROYECTOS.iterdir() if x.is_dir()) if PROYECTOS.is_dir() else []:
        tex = proj / "ExportedProject" / "Assets" / "Texture2D"
        if not tex.is_dir():
            continue
        pngs = sorted(tex.glob("*.png"))
        total += len(pngs)
        for p in pngs:
            n = p.name.lower()
            if any(k in n for k in CLAVES):
                hits.append((proj.name, p.name))
            d = dimensiones(p)
            if d and (d[0] <= 32 or d[1] <= 32):
                pequenas.append((proj.name, p.name, d))
    print(f"texturas revisadas: {total}")
    for proj, n in hits:
        print(f"  NOMBRE  {proj:12} {n}")
    if not hits:
        print("  (ninguna coincide por nombre)")
    print(f"=== (b) texturas diminutas (candidatas a ramp) : {len(pequenas)} ===")
    for proj, n, d in pequenas[:20]:
        print(f"  {proj:12} {n:44} {d[0]}x{d[1]}")

    print("=== (c) bundles del cliente con pinta de recurso compartido ===")
    if BUNDLES.is_dir():
        nombres = []
        for dirpath, _dirnames, filenames in os.walk(BUNDLES):
            for fn in filenames:
                low = fn.lower()
                if any(k in low for k in ("ramp", "matcap", "common", "toon", "shader", "effect", "effectparam")):
                    nombres.append(fn)
        for n in sorted(set(nombres))[:25]:
            print("  ", n)
        print(f"  total candidatos: {len(set(nombres))}")
    else:
        print("  (no se encontro el directorio de bundles)")


if __name__ == "__main__":
    main()