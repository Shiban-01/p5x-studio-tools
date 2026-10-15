# Cómo se aplica `UI/UIMultipleGradient` a los bust-ups de diálogo (P5X)

Fuentes: `il2cpp/dumped/dump.cs`, `unity_projects/_shaders/ExportedProject/Assets/uimultiplegradient.shader`,
`_dl/desensamblado_gradiente.txt` (desensamblado de GameAssembly.dll), bundle `118/scn_ss_storyfdcf4db.bundle`
(prefabs de diálogo, dump con AssetStudioModCLI), Lua `OuterPackage/Lua/Windows/E1FB7EBC7F8D631.bytes`,
param assets `140/ui_lihui_shader.bundle`.

## 1) ¿Imagen compuesta o por capas? — POR CAPAS

El componente `MUEngine.UI.UIMultipleGradient` (dump.cs:382354) lleva una **lista de entradas**
`List<UIMultipleGradient.UIMultipleMaterial> materials` (dump.cs:382358). Cada entrada es UNA capa:

- `description` (描述) / `tableKey` (表格字段) — nombre de la capa y clave de tabla
- `Material material` — material propio (shader `UI/UIMultipleGradient`) por capa
- `UIMuitipleGradientParam param` — ScriptableObject con los valores por capa
- `mask / maskable / showMaskGraphic / MaskDepthLayer` (0–7) — stencil entre capas
- `Image image` — la Image de UI a la que se aplica

Los prefabs reales (`UIMultipleGradient_#4040.json` etc. de `scn_ss_storyfdcf4db.bundle`) serializan
**11–12 entradas** con tableKeys fijos: `mask, head, eye, mouth, shadow, expression, peishi1..peishi6`.
Es decir: NO hay un filtro global sobre la imagen compuesta; cada capa visible recibe su propia
instancia de material con sus propios parámetros. La imagen compuesta es el apilado de Images
(mismo lienzo 572×732) cada una con su material.

## 2) Parámetros del shader → capas

Mismo **set** de uniformes en todas las capas (valores distintos por capa vía `UIMuitipleGradientParam`):

| Campo del ScriptableObject | Uniforme (SetParamDefault 0x23C3630 / Update 0x23C3DA0) |
|---|---|
| EffectFactor | `_EffectFactor` |
| Brightness / Saturation / Contrast | `_Brightness` `_Saturation` `_Contrast` |
| GradientAlphaTop / GradientAlphaBottom | `_GradientAlphaTop` `_GradientAlphaBottom` |
| GraBrightness / GraSaturation / GraContrast | `_GraBrightness` `_GraSaturation` `_GraContrast` |
| EnableFastBlur / BlurStrength | `_EnableBlur` / `_BlurStrength` |
| gradient (keys/tiempos) | `_GradientColors`, `_GradientPositions`, `_GradientAlphaTopPosition`, `_GradientAlphaBottomPosition` |
| gradientMode (Linear/Radial/Angle) | `_ModeSwitch_Linear_Radial`, `_ModeSwitch_LR_Angle` |
| Angle / Center / Ratio | coords del gradiente |
| — (stencil por entrada) | `_Stencil` `_StencilComp` `_StencilOp` `_StencilReadMask` `_StencilWriteMask` `_ColorMask` |

Mapeo de capas (tableKey → Image en Lua → sprite del bust-up):

| tableKey | descripción | Image (Lua) | capa de arte | parámetros por defecto (prefab 12 entradas) |
|---|---|---|---|---|
| `head` | 头像材质效果 | mImgHead (headImage) | `benti` (piel/cuerpo) | `UI-DialogShader-changfu01-jianajun` |
| `eye` | 眼部材质效果 | mImgEye (frames de expresión) | `yan*` (ojos) | `UI-DialogShader-changfu01-suyu` |
| `mouth` | 嘴部材质效果 | mImgMouth | `zui*` (boca) | `UI-DialogShader-changfu01-jianajun` |
| `shadow` | 阴影材质效果 | mImgShadow | `yinying` (sombra) | `UI-DialogShader-changfu01-jianajun` |
| `expression` | 表情 | mImgExpression | capas de expresión | `UI-DialogShader-changfu01-jianajun` |
| `peishi1..peishi6` | 配饰1..6 | mImageAdornment1..6 | pelo `toufa`, ropa `yifu`, máscara `mianju`, gafas `mojing`, etc. (hasta 6 adornos) | peishi1-4,6 → `changfu01-suyu`; peishi5 → `common-none` |
| `mask` | (stencil) | mImgHeadMask (nodo `benti-heimiaobian` = contorno negro/lunkuo) | `lunkuo` / contorno | `UI-DialogShader-common-none` (EffectFactor=0 → **sin tinte**); mask=1, showMaskGraphic=1, MaskDepthLayer=0 |

Los adornos (pelo/ropa/máscara/gafas) van a `peishi1..peishi6` — las texturas del bust-up
(`benti-toufa`, `benti-yifu`, `benti-mianju`, `benti-mojing`) se cargan como Images de adorno
(campos `adornment1..6` de `ConfDialogHead2D` ↔ `mImageAdornment1..6`). Esto explica que el uniforme
(p. ej. `yifu`) y la piel (`benti`) no se tiñan igual: son materiales y `UIMuitipleGradientParam`
distintos, con gradientes propios (p. ej. assets `UI-DialogShader-<traje>-<personaje>-toufa`).

## 3) La clase que controla el shader

`UIMultipleGradient.UIMultipleMaterial` (dump.cs:382280, TypeDefIndex 5493):
`SetParamDefault()` RVA 0x23C3630, `Update()` RVA 0x23C3DA0 (escribe los uniformes), `get/set_Param`.
`UIMultipleGradient` (dump.cs:382354): `Start`, `UpdateMaterials`, `Update`, `OnDestroy`,
`SetMaterialParam(string tableKey, string paramAssetName)` (dump.cs:382369) — busca la entrada cuyo
`tableKey` coincide (lambda `b__0`, dump.cs:382346) y carga asíncronamente el
`UIMuitipleGradientParam` por nombre (callback `b__1`, dump.cs:382349). Expuesto a Lua por
`MUEngine_UI_UIMultipleGradientWrap.SetMaterialParam` (dump.cs:41703).

En Lua (dialog view, `E1FB7EBC7F8D631.bytes`): `self.mHeadMat:SetMaterialParam(...)` iterando las
claves `head, eye, mouth, shadow, expression, peishi1..peishi6` (constantes del bytecode) contra la
config `ConfDialogMatParam` (11 campos String con esos mismos nombres); `ConfDialogHead2D.materialParamSn`
elige la fila. También `DICommonConfig._filterMatParamShaderName` (dump.cs:349254) filtra materiales
por nombre de shader.

## 4) `_LayerMask` / `_ApplyToLayers` / `_TargetLayer` — NO EXISTEN

El Properties del shader (uimultiplegradient.shader) está completo: `_MainTex`, `_EffectFactor`,
`_Brightness`, `_Saturation`, `_Contrast`, `_GradientAlphaTop/Bottom`, `_GraBrightness/_GraSaturation/_GraContrast`,
`_BlurStrength`, `_ShadowOffset`, `_ShadowAlpha`, `_EnableBlur`, bloque stencil
(`_StencilComp/_Stencil/_StencilOp/_StencilWriteMask/_StencilReadMask/_ColorMask`),
`_UseUIAlphaClip/_AlphaClip`, `_ModeSwitch_Linear_Radial/_ModeSwitch_LR_Angle`, `_AlphaControl`.
No hay ninguna propiedad de selección de capas: la selección es **externa** (material propio por Image,
elegido por `tableKey`) y de **stencil** (`MaskDepthLayer` 0–7 ↔ `_Stencil*`).

## Conclusión para el remapeo de tinte

Para reproducir el tinte del juego hay que aplicar el shader **por capa**, con el
`UIMuitipleGradientParam` correcto por slot (`head` para piel, `peishiN` para pelo/ropa/máscara,
`eye`/`mouth` para ojos/boca, `mask` = contorno sin tinte con EffectFactor=0), usando los assets
`UI-DialogShader-<traje>-<personaje>[-toufa|-mianju|-face|-eye]` (216 en `140/ui_lihui_shader.bundle`).
Aplicar UN juego de parámetros sobre la imagen compuesta es lo que produce el desajuste uniforme vs piel.
