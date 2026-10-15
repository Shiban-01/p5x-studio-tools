"""F1.4 — Migra los materiales exportados al shader toon propio.

Los 84 .mat apuntan al GUID placeholder de AssetRipper porque el shader original no se
exporta. Aqui se reescribe el YAML para apuntar a P5XToon.shader: como los nombres de las
propiedades coinciden EXACTAMENTE con los del material original, Unity conserva todos los
valores guardados (texturas, floats y colores) al reimportar.

Los originales se copian a _dl/backups/mat_originales/ antes de tocar nada.
"""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "unity_projects/kotone/ExportedProject/Assets"
BACKUP = ROOT / "_dl/backups/mat_originales"

SHADER_GUID = "7a1b2c3d4e5f60718293a4b5c6d7e8f9"
PLACEHOLDER = "0000000deadbeef15deadf00d0000000"
# Float propio para controlar el grosor del contorno en pixeles.
EXTRA_FLOAT = ("_OutlinePixel", "1.6")


def patch_mat(path: Path) -> str:
    txt = path.read_text(encoding="utf-8", errors="replace")
    if PLACEHOLDER not in txt:
        return "sin-placeholder"
    if "m_Shader:" not in txt:
        return "sin-shader"

    nuevo = txt.replace(PLACEHOLDER, SHADER_GUID)

    # Anadir el float propio dentro de m_Floats (misma indentacion que el resto).
    if f"{EXTRA_FLOAT[0]}:" not in nuevo and "    m_Floats:" in nuevo:
        nuevo = nuevo.replace("    m_Floats:\n",
                              f"    m_Floats:\n      {EXTRA_FLOAT[0]}: {EXTRA_FLOAT[1]}\n", 1)

    if nuevo == txt:
        return "sin-cambios"

    BACKUP.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, BACKUP / path.name)
    path.write_text(nuevo, encoding="utf-8")
    return "migrado"


def main():
    if not ASSETS.is_dir():
        sys.exit(f"no existe {ASSETS}")
    res = {}
    for mat in sorted(ASSETS.rglob("*.mat")):
        r = patch_mat(mat)
        res[r] = res.get(r, 0) + 1
    print("materiales:", res)
    print("backup en:", BACKUP)
    # Comprobacion
    quedan = sum(1 for m in ASSETS.rglob("*.mat")
                 if PLACEHOLDER in m.read_text(encoding="utf-8", errors="replace"))
    print(f"materiales que AUN apuntan al placeholder: {quedan}")
    muestra = sorted(ASSETS.rglob("*.mat"))[:1]
    for m in muestra:
        print(f"--- muestra {m.name} ---")
        for ln in m.read_text(encoding="utf-8", errors="replace").splitlines():
            if "m_Shader" in ln or "_OutlinePixel" in ln or "_ToonCutLocation" in ln:
                print("   ", ln.strip())


if __name__ == "__main__":
    main()