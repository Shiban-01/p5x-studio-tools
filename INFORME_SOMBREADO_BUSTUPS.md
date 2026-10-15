# Bust-up shading in P5X: the exact recipe

Everything below comes from the game's own files, not from guessing:

- **The parameters per bust-up** live in `140/ui_lihui_shader.bundle`, as **216 MonoBehaviours**
  named `UI-DialogShader-<outfit>-<character>` (`changfu01-aqi`, `richang01-zhimingyoumei`,
  `guaidao01-...`, 216 in total). Dump them all with:

  ```
  AssetStudioModCLI.exe "…/140/ui_lihui_shader.bundle" -t monoBehaviour -o out -g none --unity-version 2022.3.49f1
  ```

  Each comes out as a JSON with the full parameter set (see below).

- **The maths** is the shader `UI/UIMultipleGradient` (the component behind it is
  `UI_Extend/UIMuitipleGradientParam` in `pwrd.muengine`). The GLES translation of that shader was
  read line by line to write this document.

- A working implementation of all of it is next to this file: `_dl/sombreado_lihui.py`
  (`python sombreado_lihui.py <json> <png> <out_dir>`); it writes the original, a gradient-only
  version and the exact version side by side.

## What the JSON holds

```
EffectFactor, Brightness, Saturation, Contrast,          # whole-image tone
GradientAlphaTop, GradientAlphaBottom,                  # the two ends of the gradient's own alpha ramp
GraBrightness, GraSaturation, GraContrast,              # tone applied to the gradient colour only
EnableFastBlur, BlurStrength,
gradientMode,                                           # 0 = linear, 1 = radial
Angle, Center{x,y}, Ratio{x,y},
gradient: { key0..key7 {r,g,b,a}, ctime0..7, atime0..7, m_NumColorKeys, m_NumAlphaKeys, ... }
```

`gradient` is Unity's serialised `Gradient`: colours/channels in `keyN`, positions in `ctimeN`
(16-bit, so divide by 65535), alpha positions in `atimeN`, and `m_NumColorKeys` / `m_NumAlphaKeys`
say how many keys are actually used (2 to 7 in this data).

## The exact order of operations

```hlsl
// 1) texture * vertex colour  (the Image tint; white here)
half4 col = tex2D(_MainTex, uv) * i.color;

// 2) optional 3x3 blur, fixed kernel, step in texels (the "x2" is in the shader)
if (_EnableBlur == 1.0) { /* weights (0.4566, 1.0, 0.4566) separable, normalised */ }

// 3) clip(col.a - 0.001)

// 4) base tone
half lum  = dot(col.rgb, half3(0.2125, 0.7154, 0.0721));
half3 base = col.rgb * _Brightness - lum;
base = _Saturation * base + lum;
base = (base - 0.5) * _Contrast + 0.5;

// 5) gradient coordinate, in the sprite's own UV space (0..1)
half a   = radians(_Angle);
half lin = dot(uv - 0.5, half2(sin(-a), cos(a))) + 0.5;
half rad = length((uv - _Center) * _Ratio) * 2.0;
half coord = lerp(lin, rad, _ModeSwitch_Linear_Radial);

// 6) 8-stop lookup out of the gradient (piecewise lerp, flat outside the ends)
half3 g = Gradient8(coord);

// 7) the gradient's own tone
half3 gt = _GraSaturation * (g * _GraBrightness - dot(g, LUM)) + dot(g, LUM);
gt = (gt - 0.5) * _GraContrast + 0.5;

// 8) MULTIPLIED with the base colour - not laid over the top
half3 gra = gt * base;

// 9) alpha ramp between the two ends
half ga = saturate((coord - _GradientAlphaBottomPosition) /
                   max(_GradientAlphaTopPosition - _GradientAlphaBottomPosition, 0.001))
          * (_GradientAlphaTop - _GradientAlphaBottom) + _GradientAlphaBottom;

// 10) mix, then the overall strength back onto the untouched colour
half3 mixed = lerp(base, gra, ga);
half3 finalRgb = lerp(col.rgb, mixed, _EffectFactor);
```

The base tone (step 4) and the gradient tone (step 7) both use the same luminance weights,
**(0.2125, 0.7154, 0.0721)**, and both do contrast around **0.5**.

## Why a gradient-only overlay is not exact

Reading the compiled shader, a script that reads the JSON and draws the gradient over the sprite is
missing all of this:

1. **The gradient is multiplied with the colour, not composited over it.** Any "normal" or "soft
   light" overlay diverges as soon as the texture is not white.
2. **`EffectFactor`** scales the whole effect and is often not 1 (0.959 for `changfu01-aqi`, and it
   ranges 0–1 with 15 distinct values in the set). Ignoring it over-applies the shading.
3. **The base tone pass** (`Brightness` 0.25–3.8, `Saturation` 0.3–1.83, `Contrast` 0.75–1.3). The
   gradient is multiplied by *that*, so ignoring it changes the result everywhere.
4. **The gradient's own tone pass** (`GraBrightness` 0.34–2.89, `GraSaturation` 0.25–2.91,
   `GraContrast` 0–3.31) — strong, and easy to miss.
5. **The alpha ramp** (`GradientAlphaTop/Bottom` plus the ramp span taken from the gradient's alpha
   key times). It decides *how much* gradient appears, which is what makes the shading look
   "sometimes right, sometimes off": the same colours with the wrong ramp show the gradient where
   the game shows none, and vice versa.
6. **Linear vs radial** (`gradientMode`) with `Angle`, `Center` and `Ratio`. A vertical overlay only
   matches `gradientMode = 0` with `Angle` near 0 or 180; in this data the angle ranges −16° to 78.4°
   and both modes are used.
7. **The key positions** are not 0..1 evenly spaced: they come from `ctimeN` (e.g. 0, 0.2824, 1.0).
   Stretching the colours across 0..1 moves every transition.

## Checked against the game

Pair used: `UI-DialogShader-changfu01-xiachuanling` (JSON) with the `xiachuanling-changfu-*` sprites
(`076/uitex_changfu512a3bdb.bundle`), compared against an in-game screenshot of the same bust-up.

Layers of a bust-up, bottom to top, as extracted (each one is a **full-canvas** texture, 572×732,
so they just stack):

```
benti (body)  →  benti-zhi  →  benti-yifu (clothes)  →  benti-toufa (hair)
              →  <expression>-yan1 (eyes)  →  <expression>-zui1 (mouth)
              (benti-lunkuo = outline, drawn underneath)
```

Skin tone of the brightest pixels, screenshot vs the four reconstructions:

| version | skin | hue | sat | distance to the screenshot |
|---|---|---|---|---|
| in-game screenshot | `#E7D4BC` | 32° | 0.19 | — |
| raw sprite, no shading | `#EEDFD1` | 30° | 0.13 | 13.5/255 |
| **this recipe** | **`#EBD4B4`** | **36°** | **0.23** | **4.2/255** |
| same, gradient axis flipped | `#F3DEB9` | 40° | 0.24 | 8.4/255 |
| `yinying01` instead of `changfu01` | `#E9CC90` | 40° | 0.38 | 18.2/255 |

So the recipe above is the one that lands on the game's colours, and the gradient axis goes **up**
(the ramp's "top" is the top of the sprite), i.e. plain Unity UVs.

**A character can have more than one JSON.** `xiachuanling` has `changfu01` and `yinying01`
("yinying" = shadow, with its own sprite set in a different bundle and a much warmer/olive
gradient). Picking the wrong variant is worth 18/255 — more than every other mistake combined.
Whoever wires this up should key on both the outfit and the variant.

## Batch: all 216 at once

```
_dl/emparejar_jsons.py    pairs every JSON with its sprite set (and prints the comparison)
_dl/lote_bustups.py       renders each pair (resumable: it skips what is already done)
_dl/hoja_bustups.py       builds a contact sheet of everything rendered
_dl/revisar_lote.py       flags empty / near-black renders
```

Result: **216 JSON → 120 paired and rendered**, 96 left over. Of the 120: 103 clean, 14 legitimately
dark (the `yinying` shadow variants and black-haired characters), 3 empty (`aochuncun`, its "body"
layer is not usable on its own). 10 renders are missing the eyes/mouth: those layers are cropped
textures positioned by the prefab, so they are skipped rather than dropped in the wrong place.

`_dl/comparacion_216_jsons.csv` (one row per JSON) and `.md` (summary) are there for the parameter
comparison. What the set looks like:

| | min | max | mean | distinct values |
|---|---|---|---|---|
| EffectFactor | 0.000 | 1.000 | 0.943 | 15 |
| Brightness | 0.250 | 3.800 | 1.070 | 79 |
| Saturation | 0.300 | 1.830 | 0.968 | 68 |
| Contrast | 0.750 | 1.300 | 1.054 | 41 |
| GradientAlphaBottom | 0.000 | 1.000 | 0.743 | 45 |
| GradientAlphaTop | 0.000 | 1.000 | 0.849 | 37 |
| GraBrightness | 0.340 | 2.890 | 1.254 | 88 |
| GraSaturation | 0.250 | 2.910 | 1.079 | 94 |
| GraContrast | 0.000 | 3.310 | 1.077 | 85 |
| Angle | −16.0 | 78.4 | 1.960 | 24 |

`gradientMode`: 215 linear, 1 radial. `EnableFastBlur`: 215 off, 1 on. Colour keys per gradient:
2→46, 3→59, 4→64, 5→32, 6→14, 7→1.

So blur and radial mode are **not** the usual suspects — one bust-up each. The things that actually
vary per character, and therefore the things a reconstruction must read: the two tone passes, the
alpha ramp, `EffectFactor`, and the key positions.

### Traps worth writing down

- **The `_#NN` suffix does not mean Sprite vs Texture2D** — it depends on export order. Pick by
  **size**: the Texture2D is the full canvas, the Sprite is cropped.
- **Bundles are per layer, not per character.** The body lives in `063/uitex_s_changfu…` while the
  eyes live in `119/uitex_changfu…`. One bundle per character+outfit means the last layer seen
  overwrites the others and the wrong bundle gets extracted.
- **The canvas is defined by the body layer**, not by the biggest layer. Otherwise, when the body is
  a cropped texture, you stack the outline alone and get a black silhouette (happened to 5 of them).
- Layer names have no single convention: `<char>-<outfit>-<layer>` and `<char>-<outfit>-<layer>-<expression>`
  (`lufeier-changfu-benti-tongchang` is the body). Find the part token, do not rely on position.
- The JSON uses the **short** character name, the sprites the **full** one (`lizi`→`duomicunlizi`,
  `suyu`→`xinjingsuyu`, `shuangye`→`zuocangshuangye`). Substring matching only when anchored: `aqi`
  sits inside `maqimu`, and pairing those two is a silent wrong answer.
- An outfit only counts if it has a **body layer**; otherwise it is another outfit's eyes/mouth.
- `_dl/alias_bustups.json` forces character+outfit for one JSON without touching code — that is the
  hook for the 96 that do not pair (58 are characters whose bust-up is not under that name).

## Assembling a bust-up: where the coordinates come from

`_dl/montar_bustup.py <json name | character/outfit>` stacks the layers and prints, per layer, the
texture size, the offset, and whether that offset was **read** or **deduced**. `--json` also writes a
`<name>.json` with the full part list — that is the data a bust-up viewer needs.

The coordinates come from the motor's `-m dump` mode, which dumps every asset as text:

| source | what it gives |
|---|---|
| Sprite | `m_Rect` (the sprite's rect inside its texture), `m_Pivot`, `m_PixelsToUnits`, `m_RD.texture` (which texture it points at) |
| Texture2D | `m_Width` / `m_Height` |

Placement rules, and how honest each one is:

| case | offset | exact? |
|---|---|---|
| the layer's texture **is** the canvas (same size) | (0,0) | yes, read |
| the sprite points at the **same texture** as the body | `m_Rect.x/y` | yes, read |
| the layer has its **own smaller texture** (eyes, mouth) | aligned to the **top** | deduced |

Why deduced: the canvas offset of a layer with its own texture lives in the **prefab**, and the
prefab is not readable — installed bundles are encrypted (`BundleFile is encrypted, but no key was
provided`), the motor's `-t` list has no GameObjects/RectTransforms, the vfile bundles are fonts and
atlases only, and the dumped Lua is compiled bytecode. Top alignment is verified instead: in
`jianajun` (body 984x988, eyes and mouth in their own 984x788 texture) the features land on the face
and the bust-up comes out complete; in `xiachuanling` (everything on the 572x732 canvas) all seven
offsets are read as (0,0) and the assembly matches the in-game capture.

**Glob trap** (it cost two false diagnoses): `name*.png` also matches `name-lunkuo.png` — the
outline, which is exactly the same size as the body — so it gets picked as the body and you get a
black silhouette. Match exact names (`<name>.png` and `<name>_#NN.png`).

**Trimming — Aaron called it.** AssetStudio/AssetRipper export a sprite trimmed to its tight mesh, so
the PNG is smaller than the texture. But the export is not simply "broken": the Texture2D is usually
a **sheet** holding several layers, and each sprite's position inside that sheet is in the dump as a
`(x, y, width, height)` rect in texture pixels — found by matching the size of the exported PNG. The
parser reads it and places the trimmed sprite there, **flipping Y** (Unity measures Y from the
bottom: `y_top = texture_height - y_bottom - sprite_height`).

Validated: assembling from the trimmed sprites at their mesh rects gives the **same** result as
assembling from the full sheets — **0.26% of pixels differ** (edges only, from rounding). Without the
Y flip the difference was **72%**. `montar_bustup.py --recortados` uses this path.

Which name carries the trimmed export and which the full sheet is **not predictable**: the `_#NN`
suffix sits on either one. For `xiachuanling`'s body the plain name is the full 572x732 and `_#77` is
the trimmed 548x720, while for its outline it is the other way round — plain is the trimmed 550x721
and `_#53` is the full 572x732. So the parser picks by **declared texture size** (`m_Width`/`m_Height`
from the dump).

**Layer order and sheet bleed (both fixed, reported by the user).** Two separate faults produced the
same artifact — skin pixels showing on top of the black hair:

1. **Order.** The hair must be the **topmost** layer (the bangs cover the edge of the eyes and the
   skin). It was below the eyes/mouth. Order now: outline → body → arms → clothes → eyes → mouth →
   **hair**.
2. **Sheet bleed.** A sheet can hold more than one layer: `xiachuanling`'s mouth sprite is 60x36 but
   its sheet has content across 108x88 (there are more mouths in that sheet), so pasting the whole
   sheet pushed extra content over the hair. The default is now to paste the **trimmed sprite at its
   mesh rect**; pasting whole sheets stays available behind `--hojas`.

Verified on the face crop: the dirty bangs edges and the light pixels over the hair are gone in the
new version.

**Coordinates by pixels — `_dl/montar_por_pixeles.py`.** Instead of dumping every bundle to read the
mesh rect (~40 s per bundle), it finds each loose sprite inside its sheet **by comparing pixels**, so
it needs nothing but the bulk textures folder.

- Optimization: correlate the alpha masks with an **FFT** (numpy) instead of sliding a window over
  every position; try the top 10 correlation peaks and validate each against the real pixels (many
  expressions share the same silhouette). Report the **fraction** of differing pixels, not the
  maximum — the maximum is 255 from a single edge pixel and tells you nothing. Cost: **0.60 s per
  bust-up**.
- Over the 120: **120 assembled, 0 failures**, 556 layers placed, **37 layers (6.6%)** packed in their
  own sheet (those cannot be placed without the prefab and are flagged). Total time **72 s**.
- Cross-check: for `xiachuanling` the 7 offsets found by pixels are exactly the ones from the dump,
  and the resulting montage differs in **0 pixels** from the dump-based one.
- `--listar` prints what goes with what: `xiachuanling-changfu` has 21 eye variants and 21 mouth
  variants across 7 expressions (tongchang, xiao, fennu, beiai, jingya, shengqi, huangzhang) plus a
  `haixiuxiao-saihong` blush layer.

**The viewer inside P5X Studio Tools.** The same assembly is shipped in the app as a new **Bust-ups**
tab:

- `p5x_studio/p5x_studio/bustups.py` — name splitting, the pixel search (÷16 → ÷4 → ÷1 pyramid with
  PIL; **no numpy**, which the .spec excludes on purpose so the binary stays small), a cached index of
  the textures folder, and `montar()`. One bust-up takes ~0.6 s once the index exists.
- `p5x_studio/p5x_studio/datos/bustups.json` — the pairing trimmed to what the viewer needs. It
  travels **inside the .exe** (added to `datas` in the spec), so the viewer needs nothing but the
  textures folder.
- The tab lists the 120 bust-ups, renders the portrait, offers an **expression selector** (21 eye and
  21 mouth variants across 7 expressions, plus the blush layer), lists every layer with the deviation
  it was measured with, and exports the PNG. Layers packed in their own sheet are flagged.
- Verified by piloting the **published .exe** over CDP: tab present, 120 rows, portrait assembled,
  expression change re-renders a different image, export writes the PNG, and the other tabs still
  work.

**The bulk dump does not need rewriting.** Measured over the 118,230 PNGs: 88,583 distinct names,
23,038 with two or more exports, 17,408 with differing sizes — and in a 300-pair sample, **zero** were
"the small one is the big one cropped": the small ones are the legitimate per-layer sprites (their own
mesh region). Rewriting them as full sheets would throw away exactly the per-part sprites a viewer
wants. The fix belongs in the parser (read the mesh rect), not in the textures.

**Sizing.** Aaron's note that every layer is set to the base layer's size matches what the dumps show
for layers whose texture *is* the canvas (all their rects are the canvas). For a layer packed in its
own smaller sheet (`jianajun`: body 984x988, eyes and mouth in a 984x788 sheet) stretching it to the
canvas pushes the features ~100 px down, off the face — so the parser places it unstretched at the
top and flags it as deduced. That single case still needs the prefab.

## Not yet verified (say it out loud rather than hide it)

- **Filling the 8 shader slots.** The component holds a Unity `Gradient` and the shader takes 8
  colours + 8 positions. The implementation evaluates the gradient at 8 evenly spaced points, which
  is exact for 2-key gradients and within ~0.003 for 3–7 keys. The precise fill happens in C#
  (`UIMuitipleGradientParam`) and is not visible in the GLSL.
- **The ramp span.** The alpha positions are taken from the gradient's alpha keys; the ramp *values*
  from `GradientAlphaTop/Bottom`. That matches every sample checked, but the C# assignment is the
  authority.
- **Colour space.** This is the mobile (GLES3) translation. On PC with a linear colour space the
  sample and the blend happen in different numbers; if a reconstruction matches the mid-tones but
  not the extremes (or the other way round), that is the thing to check. Measured both ways against
  the screenshot: doing the maths in **gamma space lands at 4.2/255**, in linear space at 6.7/255 —
  so the numbers in this document are the ones to use.
- **The JSON ↔ sprite pairing** is not in the data: the JSON is named by outfit+character
  (`richang01-zhimingyoumei`) while the sprites are named `<character>-<outfit>-<part>`
  (`zhuimingyoumei-changfu-shenti.png`), and a bust-up is several sprites (body, hair, eyes/mouth
  per expression, blush, outline). Whoever already has that mapping should keep it.