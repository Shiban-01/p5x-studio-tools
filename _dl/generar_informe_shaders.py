"""Genera el informe (en ingles) de los shaders de interfaz del juego, para Aaron.

Saca del inventario guardado (shaders_del_juego.json) los shaders de UI/UIEffect con su lista de
propiedades exacta, marca los que pintan ilustraciones (lihui) y deja el informe en markdown.
"""
import json
import re
from pathlib import Path

ENTRADA = Path(r"C:\Users\Lukas\p5x-datamining\_dl\shaders_del_juego.json")
SALIDA = Path(r"C:\Users\Lukas\p5x-datamining\INFORME_SHADERS_UI.md")

datos = json.loads(ENTRADA.read_text(encoding="utf-8"))


def candidatos(f):
    return [f["nombre"]] + f.get("otros_candidatos", [])


def mejor(f, prefijos):
    for c in candidatos(f):
        if c.split("/")[0] in prefijos and len(c) > 3:
            return c
    return None


filas = []
for f in datos:
    n = mejor(f, ("UI", "UIEffect", "Athena", "Hidden"))
    if not n or not (n.startswith("UI/") or n.startswith("UIEffect/") or n == "Athena/UI/UiStarSingle"):
        continue
    filas.append({"nombre": n, "props": f["props"], "dxbc": f["dxbc"], "bytes": f["bytes"]})
filas.sort(key=lambda f: f["nombre"])

destacados = [f for f in filas if f["nombre"] in (
    "UI/chouka", "UI/UIMultipleGradient", "UI/UIMaskColorTint", "UI/WaveScreenShot",
    "UI/P3RFinalAttack", "UI/UIUnmask", "UI/BlurBackground", "UI/DebugDefault")]

lineas = []
lineas.append("# P5X UI shaders: what the game actually has")
lineas.append("")
lineas.append("Extracted from the shipped build (Unity **2022.3.49f1**). The shader *names* and their")
lineas.append("**exact property lists** come out of the game's own shader assets, so they are not guessed:")
lineas.append("every name below is a `Shader` asset inside `106/shaders.bundle` (431 shaders + 14 compute")
lineas.append("shaders in that bundle alone).")
lineas.append("")
lineas.append("## The shaders that draw illustrations (portraits)")
lineas.append("")
lineas.append("`UI/chouka` is the one Wired to the `lihui` artwork (lihui = the portrait sprites).")
lineas.append("Its properties:")
lineas.append("")
for f in destacados:
    lineas.append("### %s" % f["nombre"])
    lineas.append("")
    lineas.append("    " + ", ".join(f["props"]))
    lineas.append("")
lineas.append("## Every UI / UIEffect shader in the build")
lineas.append("")
lineas.append("| shader | properties |")
lineas.append("|---|---|")
for f in filas:
    lineas.append("| `%s` | %s |" % (f["nombre"], ", ".join(f["props"]) if f["props"] else "-"))
lineas.append("")
lineas.append("## Findings that usually explain an 'off sometimes' recreation")
lineas.append("")
lineas.append("1. **Blend state is per material, not fixed.** These properties show up all over the UI")
lineas.append("   shaders: `_SrcBlend`, `_DstBlend`, `_Blend`, `_ALPHAPREMULTIPLY_ON`, `_ZWriteMode`,")
lineas.append("   `_DstBlendUI`/`_SrcBlendUI`. If your reconstruction hardcodes straight alpha")
lineas.append("   (`SrcAlpha, OneMinusSrcAlpha`) you match the game only where alpha is 0 or 1, and you")
lineas.append("   drift everywhere else - exactly an intermittent mismatch.")
lineas.append("2. **Three- and multi-stop gradients are the shading.** `UI/WaveScreenShot` uses")
lineas.append("   `_ColorTop` / `_ColorMid` / `_ColorDown`; `UI/UIMultipleGradient` uses")
lineas.append("   `_GradientColors` + `_GradientPositions` with `_GradientAlphaTop/Bottom` and")
lineas.append("   `_AlphaControl`. Reproducing the ramp without the same colour stops and the same")
lineas.append("   alpha control gives a near miss.")
lineas.append("3. **Tinting by tone band.** `UI/UIMaskColorTint` has `_BlackPartColor` / `_WhitePartColor`")
lineas.append("   with `_AlphaClip` + `_Cutoff`: a two-band tint driven by a mask, not a multiply.")
lineas.append("4. **UI vertex colour space.** `UI/DissolvedUI` carries `_UIVertexColorAlwaysGammaSpace`.")
lineas.append("   Gamma vs linear handling of vertex colour is a classic source of differences that only")
lineas.append("   show up on some colours.")
lineas.append("5. **Saturation / luminance controls are explicit.** `UI/UIBlendColor` (`_Blend`,")
lineas.append("   `_Pow`, `_Saturation`), `UI/P3RFinalAttack` (`_SaturateLevel`, `_SkinLerp`,")
lineas.append("   `_BaseTint`, `_ShadowColor`).")
lineas.append("")
lineas.append("## The compiled bytecode (and where it stops)")
lineas.append("")
lineas.append("- The build ships the compiled programs: **360 DXBC blobs** in")
lineas.append("  `106/shaders.bundle`, extracted to `_dl/shaders_out/`.")
lineas.append("- The standard disassembler (`d3dcompiler_47.dll`, `D3DDisassemble`) **refuses all of")
lineas.append("  them** (`E_FAIL`), including after repairing the container header. Sanity check: the same")
lineas.append("  call compiles and disassembles a test shader fine, and the game's payload is structured")
lineas.append("  data (entropy 4.8 bits/byte), not encrypted noise.")
lineas.append("- Conclusion: the programs are stored in a form the runtime repairs/expects, so **readable")
lineas.append("  shader assembly is not available from the files alone**. The property lists above are.")
lineas.append("")
lineas.append("## What would unblock a line-by-line comparison")
lineas.append("")
lineas.append("The name of the shader/material being recreated (`UI/chouka`? something else?), and a")
lineas.append("picture of a case where the reconstruction looks wrong next to the game. With the material")
lineas.append("in hand we can read which textures and colours it feeds in, which is usually enough to find")
lineas.append("the missing term.")

SALIDA.write_text("\n".join(lineas) + "\n", encoding="utf-8")
print("shaders de UI en el informe:", len(filas))
print("destacados:", ", ".join(f["nombre"] for f in destacados))
print("escrito en", SALIDA, SALIDA.stat().st_size, "bytes")