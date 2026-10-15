"""F2.0 — Diagnostica por que los renderers del escenario no usan los materiales propios.

Lee la .unity exportada, saca las referencias a materiales de los renderers, resuelve los GUID
contra los .meta del proyecto y dice: cuantas resuelven, cuales faltan y que shader acaban usando.
"""
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROJ = ROOT / "unity_projects/kotone/ExportedProject"
ASSETS = PROJ / "Assets"
ESCENA = ASSETS / "GeneratedRes/Scene/PC/ysc_tianshouge_shiwai_wyc/ysc_tianshouge_shiwai_wyc.unity"

NUESTRO_SHADER = "7a1b2c3d4e5f60718293a4b5c6d7e8f9"
PLACEHOLDER = "0000000deadbeef15deadf00d0000000"


def mapa_guids() -> dict:
    m = {}
    for meta in ASSETS.rglob("*.meta"):
        try:
            txt = meta.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        g = re.search(r"^guid:\s*([0-9a-f]{32})", txt, re.M)
        if g:
            m.setdefault(g.group(1), meta.with_suffix(""))
    return m


def shader_de(mat: Path) -> str:
    try:
        txt = mat.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return "?"
    g = re.search(r"m_Shader:\s*\{fileID:\s*\d+,\s*guid:\s*([0-9a-f]{32})", txt)
    if not g:
        return "sin m_Shader"
    gh = g.group(1)
    if gh == NUESTRO_SHADER:
        return "P5X/Toon (nuestro)"
    if gh == PLACEHOLDER:
        return "PLACEHOLDER (roto)"
    return f"otro guid {gh[:8]}"


def main():
    print(f"escena: {ESCENA.exists()}  {ESCENA.stat().st_size / 1000:.0f} KB")
    txt = ESCENA.read_text(encoding="utf-8", errors="replace")
    guids = mapa_guids()
    print(f"guids indexados desde .meta: {len(guids)}")

    refs = re.findall(r"m_Materials:\s*\n((?:\s*-\s*\{fileID:\s*2100000,\s*guid:\s*([0-9a-f]{32})[^}]*\}\s*\n?)+)", txt)
    todos = re.findall(r"-\s*\{fileID:\s*2100000,\s*guid:\s*([0-9a-f]{32})", txt)
    print(f"referencias a material (fileID 2100000) en la escena: {len(todos)}  ({len(refs)} bloques)")

    cnt = Counter()
    faltan = Counter()
    for g in todos:
        p = guids.get(g)
        if p is None or not p.exists():
            cnt["MATERIAL NO EXPORTADO (null -> fallback)"] += 1
            faltan[g] += 1
        else:
            cnt[shader_de(p)] += 1
    for k, v in cnt.most_common():
        print(f"  {v:5}  {k}")
    if faltan:
        print("guids de material que faltan en el proyecto:")
        for g, v in faltan.most_common(10):
            print(f"   {g}  x{v}")

    # Materiales existentes: cuantos son nuestros
    mats = list(ASSETS.rglob("*.mat"))
    sh = Counter(shader_de(m) for m in mats)
    print(f"materiales en el proyecto: {len(mats)}")
    for k, v in sh.most_common():
        print(f"  {v:5}  {k}")

    # UV2 / lightmap en las mallas
    meshes = list((ASSETS / "Mesh").glob("*.asset")) if (ASSETS / "Mesh").is_dir() else []
    print(f"mallas exportadas: {len(meshes)}")


if __name__ == "__main__":
    main()