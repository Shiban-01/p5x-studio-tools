"""F0.1 — Inventario del estado del proyecto P5X.

Responde en un comando: que tengo ya extraido, exportado y renderizado.
Escribe _dl/state.json y resume por consola.
"""
import json
import os
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUNDLES = Path("C:/Users/Lukas/Downloads/P5X/Client/OuterPackage/Bundles/Windows")


def du(p: Path) -> int:
    """Tamano recursivo en bytes (os.scandir, no Path.rglob: 16k bundles)."""
    total = 0
    stack = [p]
    while stack:
        cur = stack.pop()
        try:
            with os.scandir(cur) as it:
                for e in it:
                    try:
                        if e.is_dir(follow_symlinks=False):
                            stack.append(Path(e.path))
                        else:
                            total += e.stat(follow_symlinks=False).st_size
                    except OSError:
                        pass
        except OSError:
            pass
    return total


def count(pat: str, base: Path = ROOT) -> int:
    return sum(1 for _ in base.glob(pat))


def main():
    state = {"fecha": time.strftime("%Y-%m-%d %H:%M:%S")}

    # Bundles originales del cliente
    if BUNDLES.is_dir():
        state["bundles_cliente"] = {
            "ruta": str(BUNDLES),
            "n": sum(1 for e in os.scandir(BUNDLES) if e.is_file()),
            "mb": round(du(BUNDLES) / 1e6, 1),
        }

    # Stages de trabajo
    stages = {}
    for sub in ("_dl", "unity_projects", "media"):
        d = ROOT / sub
        if d.is_dir():
            stages[sub] = {"mb": round(du(d) / 1e6, 1)}
            if sub == "unity_projects":
                proyectos = {}
                for p in sorted((x for x in os.scandir(d) if x.is_dir()), key=lambda e: e.name):
                    exp = Path(p.path) / "ExportedProject" / "Assets"
                    proyectos[p.name] = {
                        "mb": round(du(Path(p.path)) / 1e6, 1),
                        "assets_ok": exp.is_dir(),
                        "materiales": count("**/*.mat", exp) if exp.is_dir() else 0,
                        "clips": count("**/*.anim", exp) if exp.is_dir() else 0,
                        "texturas": count("**/*.png", exp) if exp.is_dir() else 0,
                    }
                stages["proyectos_unity"] = proyectos
        state["stages"] = stages

    # Entregables
    media = ROOT / "media"
    if media.is_dir():
        mp4 = sorted(media.glob("*.mp4"))
        state["entregables"] = [
            {"nombre": m.name, "mb": round(m.stat().st_size / 1e6, 2)} for m in mp4
        ]

    # Capturas frame a frame
    cap = media / "cinematics_capture"
    capturas = {}
    if cap.is_dir():
        for d in sorted((x for x in os.scandir(cap) if x.is_dir()), key=lambda e: e.name):
            pngs = list(Path(d.path).glob("f_*.png"))
            capturas[d.name] = {
                "frames": len(pngs),
                "mb": round(du(Path(d.path)) / 1e6, 1),
                "log": (Path(d.path) / "log.txt").is_file(),
            }
    state["capturas"] = capturas

    out = ROOT / "_dl" / "state.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")

    # Resumen
    print(f"=== INVENTARIO {state['fecha']} ===")
    if "bundles_cliente" in state:
        b = state["bundles_cliente"]
        print(f"bundles cliente : {b['n']} archivos, {b['mb'] / 1000:.1f} GB")
    if "stages" in state:
        for k, v in state["stages"].items():
            if k == "proyectos_unity":
                continue
            print(f"{k:16}: {v['mb'] / 1000:.2f} GB")
    for profe, v in state.get("stages", {}).get("proyectos_unity", {}).items():
        print(f"  proyecto {profe:14} {v['mb'] / 1000:.2f} GB  mat={v['materiales']:3} "
              f"clips={v['clips']:4} png={v['texturas']:3} assets={v['assets_ok']}")
    print(f"entregables MP4 : {len(state.get('entregables', []))}")
    for m in state.get("entregables", []):
        print(f"  {m['nombre']:46} {m['mb']:.2f} MB")
    print(f"capturas        : {len(state.get('capturas', {}))}")
    for k, v in state.get("capturas", {}).items():
        print(f"  {k:28} {v['frames']:4} frames  {v['mb']:.1f} MB")
    print(f"-> {out}")


if __name__ == "__main__":
    main()