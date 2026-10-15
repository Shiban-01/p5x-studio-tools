# P5X UI shaders: what the game actually has

Extracted from the shipped build (Unity **2022.3.49f1**). The shader *names* and their
**exact property lists** come out of the game's own shader assets, so they are not guessed:
every name below is a `Shader` asset inside `106/shaders.bundle` (431 shaders + 14 compute
shaders in that bundle alone).

## The gacha card shader (character illustration + weapon)

`UI/chouka` ("chouka" = the gacha card) is the one wired to the `lihui` artwork
(lihui = the character illustration). It also carries the weapon illustration slots
(`_wuqi*`, wuqi = weapon), so this single shader shades both layers of a card:

    _Color, _ColorMask, _ISPurple, _ISShipei, _MainTex, _Softlihui, _Stencil, _StencilComp, _StencilOp, _StencilReadMask, _StencilWriteMask, _Time, _UseUIAlphaClip, _ZWriteMode, _lihui, _lihuiScale, _lihuiShiPei, _lihuiSoft, _lihuiSoft_ST, _lihui_ST, _wuqiLihuiBlack, _wuqiVFX, _wuqiVFXSp, _wuqiVFXTint, _wuqilihui, _wuqilihui_ST

Other UI shaders that shade artwork:

### UI/BlurBackground

    _BlurSize, _Color, _ColorAdd, _ColorMask, _DownSampledColorTexture, _MainTex, _MainTex_ST, _ProjectionParams, _Stencil, _StencilComp, _StencilOp, _StencilReadMask, _StencilWriteMask, _TextureSampleAdd, _UseUIAlphaClip, _dynamicResScaleRecord

### UI/DebugDefault

    _BakeLightCount, _BaseColor, _BaseMap, _BaseMap_ST, _BumpScale, _CascadeShadowSplitSphereRadii, _CascadeShadowSplitSpheres0, _CascadeShadowSplitSpheres1, _CascadeShadowSplitSpheres2, _CascadeShadowSplitSpheres3, _Color, _ColorMask, _Cull, _DebugSaturationValue, _DiffuseNLFix, _DirectSpecEnd, _HLODMAPON, _HighlightIntensity, _LightmapST, _MAIN_LIGHT_SHADOWS, _METALLICSPECGLOSSMAP, _MainLightShadowParams, _MainLightShadowmapSize, _MainLightWorldToShadow, _MainTex, _NormalScale, _OcclusionStrength, _SPECULAR_SETUP, _Smoothness, _StaticPointBakeSize, _StaticPointPosOffset, _Stencil, _StencilComp, _StencilOp, _StencilReadMask, _StencilWriteMask, _TEXTURE_COMBINE, _UseUIAlphaClip, _WorldSpaceCameraPos, _ZWrite

### UI/P3RFinalAttack

    _BaseTint, _Center, _ColorModeEnable, _Debug, _InitColor, _MainTex, _Offset1, _Offset2, _OverlayColor, _Radius, _SaturateLevel, _ScaledScreenParams, _ShadowColor, _SkinLerp

### UI/UIMaskColorTint

    _AlphaClip, _BlackPartColor, _BlendUI, _ClipRect, _ColorMask, _Cutoff, _DstBlendUI, _MainTex, _MainTex_ST, _SrcBlendUI, _Stencil, _StencilComp, _StencilOp, _StencilReadMask, _StencilWriteMask, _WhitePartColor

### UI/UIMultipleGradient

    _AlphaClip, _AlphaControl, _Angle, _BlurStrength, _Brightness, _Center, _ClipRect, _ColorMask, _Contrast, _EffectFactor, _EnableBlur, _GraBrightness, _GraContrast, _GraSaturation, _GradientAlphaBottom, _GradientAlphaBottomPosition, _GradientAlphaTop, _GradientAlphaTopPosition, _GradientColors, _GradientPositions, _LR0_Angle1, _Linear0_Radial1, _MainTex, _MainTex_TexelSize, _ModeSwitch_LR_Angle, _ModeSwitch_Linear_Radial, _Ratio, _Saturation, _ScreenParams, _ShadowAlpha, _ShadowOffset, _Stencil, _StencilComp, _StencilOp, _StencilReadMask, _StencilWriteMask, _UIMaskSoftnessX, _UIMaskSoftnessY, _UseUIAlphaClip

### UI/UIUnmask

    _BlurStrength, _EnableBlur, _MainTex, _MainTex_TexelSize

### UI/WaveScreenShot

    _ApRimColor, _ApRimColorRange, _ApRimSharpness, _ApRimThickness, _ColorDown, _ColorMask, _ColorMid, _ColorTop, _DisRimCustom, _EnableDarkRim, _LumAdd, _LumMax, _LumMin, _MainLightColor, _MainLightPosition, _MainTex, _ProjectionParams, _RimColor, _RimIntensity, _RimSharpness, _RimThickness1, _RoleDistanceRimMask1, _RoleDistanceRimWidth, _RoleNearWidth1, _ScreenParams, _Sequence1Alpha, _Sequence1Num, _Sequence1X, _Sequence1Y, _Sequence2Alpha, _Sequence2Num, _Sequence2X, _Sequence2Y, _SequenceTex1, _SequenceTex1_ST, _SequenceTex2, _SequenceTex2_ST, _Speed1, _Speed2, _Stencil, _StencilComp, _StencilOp, _StencilReadMask, _StencilWriteMask, _Time, _UseUIAlphaClip, _Use_LastSceneTex, _WaveIntensity, _WaveSpeedX, _WaveSpeedY, _WaveTiling, _WorldSpaceCameraPos

## Every UI / UIEffect shader in the build

| shader | properties |
|---|---|
| `Athena/UI/UiStarSingle` | _BandBlackPercent, _BandSpeed, _BandWidth, _BaseColor, _Color, _ColorMask, _MainTex, _Rotation, _Screen_Spaced, _Smoothness, _Stencil, _StencilComp, _StencilOp, _StencilReadMask, _StencilWriteMask, _Time, _UseUIAlphaClip |
| `UI/Additive` | _Color, _ColorMask, _MainTex, _MainTex_ST, _Stencil, _StencilComp, _StencilOp, _StencilReadMask, _StencilWriteMask, _TextureSampleAdd, _UseUIAlphaClip |
| `UI/Additive_ColorChangeOverTime` | _ClipRect, _Color, _ColorMask, _CycleLength, _MainTex, _MainTex_ST, _NoiseTex, _NoiseTex_ST, _PannerSpeed, _PannerTime, _ScaledScreenParams, _Stencil, _StencilComp, _StencilOp, _StencilReadMask, _StencilWriteMask, _Time |
| `UI/BlurBackground` | _BlurSize, _Color, _ColorAdd, _ColorMask, _DownSampledColorTexture, _MainTex, _MainTex_ST, _ProjectionParams, _Stencil, _StencilComp, _StencilOp, _StencilReadMask, _StencilWriteMask, _TextureSampleAdd, _UseUIAlphaClip, _dynamicResScaleRecord |
| `UI/CoopText` | _ColorIntensity, _ColorMask, _FadeSpeed, _GhostAlpha, _GhostRange, _GhostSpeed, _MainTex, _RandomSeed, _Stencil, _StencilComp, _StencilOp, _StencilReadMask, _StencilWriteMask, _Time |
| `UI/DebugDefault` | _BakeLightCount, _BaseColor, _BaseMap, _BaseMap_ST, _BumpScale, _CascadeShadowSplitSphereRadii, _CascadeShadowSplitSpheres0, _CascadeShadowSplitSpheres1, _CascadeShadowSplitSpheres2, _CascadeShadowSplitSpheres3, _Color, _ColorMask, _Cull, _DebugSaturationValue, _DiffuseNLFix, _DirectSpecEnd, _HLODMAPON, _HighlightIntensity, _LightmapST, _MAIN_LIGHT_SHADOWS, _METALLICSPECGLOSSMAP, _MainLightShadowParams, _MainLightShadowmapSize, _MainLightWorldToShadow, _MainTex, _NormalScale, _OcclusionStrength, _SPECULAR_SETUP, _Smoothness, _StaticPointBakeSize, _StaticPointPosOffset, _Stencil, _StencilComp, _StencilOp, _StencilReadMask, _StencilWriteMask, _TEXTURE_COMBINE, _UseUIAlphaClip, _WorldSpaceCameraPos, _ZWrite |
| `UI/Default Grey` | _Color, _MainTex |
| `UI/Default ZWrite` | _ClipRect, _Color, _ColorMask, _MainTex, _MainTex_ST, _ScreenParams, _Stencil, _StencilComp, _StencilOp, _StencilReadMask, _StencilWriteMask, _TextureSampleAdd, _UIMaskSoftnessX, _UIMaskSoftnessY, _UseUIAlphaClip |
| `UI/Default_VFX` | _BlendMode, _COLOR_SPLIT, _ClipRect, _Color, _ColorMask, _ColorSplitIntensity, _DistortionIntensity, _DistortionSpeedX, _DistortionSpeedY, _DistortionTex, _DistortionTex_ST, _DstBlend, _EnableColorSplit, _EnableOverlay, _EnableScreenSpaceUV, _EnableUIJitter, _Frequency, _JitterAdd, _JitterIntensity, _JitterSpeed, _MainTex, _MainTex_ST, _OverlayBlendMode, _OverlayColor, _OverlaySpeedX, _OverlaySpeedY, _OverlayTex, _OverlayTex_ST, _OverlayTex_STJ, _ScreenParamsL, _SrcBlend, _Stencil, _StencilComp, _StencilOp, _StencilReadMask, _StencilWriteMask, _TextureSampleAdd, _Threshold, _Time, _UI_JITTER, _UseUIAlphaClip |
| `UI/Default_ZTestOff` | _ClipRect, _Color, _ColorMask, _MainTex, _MainTex_ST, _ScreenParams, _Stencil, _StencilComp, _StencilOp, _StencilReadMask, _StencilWriteMask, _TextureSampleAdd, _UIMaskSoftnessX, _UIMaskSoftnessY, _UseUIAlphaClip |
| `UI/DissolvedUI` | _ClipRect, _Color, _ColorMask, _MainTex, _MainTex_ST, _ScreenParams, _Stencil, _StencilComp, _StencilOp, _StencilReadMask, _StencilWriteMask, _TextureSampleAdd, _UIMaskSoftnessX, _UIMaskSoftnessY, _UIVertexColorAlwaysGammaSpace, _UseUIAlphaClip |
| `UI/ItemSixPointStar` | _AreaX, _AreaY, _AriseSpeed, _Blades, _ClipRect, _ColorMask, _CutOff, _Iridescence, _MainTex, _Param, _Pow, _RotateSpeed, _ScreenParams, _Size, _Stencil, _StencilComp, _StencilOp, _StencilReadMask, _StencilWriteMask, _Threshold, _Time, _Tint, _UIMaskSoftnessX, _UIMaskSoftnessY, _UseUIAlphaClip |
| `UI/LoopCircle` | _CircleColor1, _CircleColor2, _CircleSpeed, _CircleWidth, _Color, _ColorMask, _MainTex, _MainTex_ST, _Stencil, _StencilComp, _StencilOp, _StencilReadMask, _StencilWriteMask, _Time, _UseUIAlphaClip |
| `UI/Multiple` | _ClipRect, _Color, _ColorMask, _MainTex, _MainTex_ST, _Stencil, _StencilComp, _StencilOp, _StencilReadMask, _StencilWriteMask |
| `UI/P3RFinalAttack` | _BaseTint, _Center, _ColorModeEnable, _Debug, _InitColor, _MainTex, _Offset1, _Offset2, _OverlayColor, _Radius, _SaturateLevel, _ScaledScreenParams, _ShadowColor, _SkinLerp |
| `UI/Transfer_RoundType` | _Angle, _Blend, _ColorMask, _Height, _MainTexA, _MainTexB, _Scaler, _Stencil, _StencilComp, _StencilOp, _StencilReadMask, _StencilWriteMask, _Width |
| `UI/UIBlackFog` | _ClipRect, _FogColor, _FogColorMask, _FogIntensity, _FogSpeed, _FogSpeedSinIntensity, _FogTex, _FogTex_ST, _MainTex, _MainTexAlphaIntensity, _MainTexSpeed, _MainTex_ST, _Max, _NoisePow, _ScreenParams, _Stencil, _StencilComp, _StencilOp, _StencilReadMask, _StencilWriteMask, _TextureSampleAdd, _Time, _TimeAlpha, _UIMaskSoftnessX, _UIMaskSoftnessY, _UseUIAlphaClip, _useMainTexTimeAlpha, _useSin |
| `UI/UIBlendColor` | _Blend, _Color, _ColorMask, _MainTex, _MainTex_ST, _Pow, _Saturation, _Stencil, _StencilComp, _StencilOp, _StencilReadMask, _StencilWriteMask, _TextureSampleAdd, _UseUIAlphaClip |
| `UI/UIDepthClip` | _Color, _ColorMask, _MainTex, _MainTex_ST, _Stencil, _StencilComp, _StencilOp, _StencilReadMask, _StencilWriteMask, _ZWrite, _ZWriteOp |
| `UI/UIDepthOnly` | _Color, _ColorMask, _MainTex, _MainTex_ST, _Stencil, _StencilComp, _StencilOp, _StencilReadMask, _StencilWriteMask, _ZWrite, _ZWriteOp |
| `UI/UIMaskColorTint` | _AlphaClip, _BlackPartColor, _BlendUI, _ClipRect, _ColorMask, _Cutoff, _DstBlendUI, _MainTex, _MainTex_ST, _SrcBlendUI, _Stencil, _StencilComp, _StencilOp, _StencilReadMask, _StencilWriteMask, _WhitePartColor |
| `UI/UIMultipleGradient` | _AlphaClip, _AlphaControl, _Angle, _BlurStrength, _Brightness, _Center, _ClipRect, _ColorMask, _Contrast, _EffectFactor, _EnableBlur, _GraBrightness, _GraContrast, _GraSaturation, _GradientAlphaBottom, _GradientAlphaBottomPosition, _GradientAlphaTop, _GradientAlphaTopPosition, _GradientColors, _GradientPositions, _LR0_Angle1, _Linear0_Radial1, _MainTex, _MainTex_TexelSize, _ModeSwitch_LR_Angle, _ModeSwitch_Linear_Radial, _Ratio, _Saturation, _ScreenParams, _ShadowAlpha, _ShadowOffset, _Stencil, _StencilComp, _StencilOp, _StencilReadMask, _StencilWriteMask, _UIMaskSoftnessX, _UIMaskSoftnessY, _UseUIAlphaClip |
| `UI/UIScene` | _CharacterFocusIntensity, _Color, _ColorMask, _HitFactor, _MainTex, _MainTex_ST, _NoFocusIntensity, _SceneFocusIntensity, _SceneOrCharacter, _Stencil, _StencilComp, _StencilOp, _StencilReadMask, _StencilWriteMask, _TextureSampleAdd, _UseUIAlphaClip |
| `UI/UIUnmask` | _BlurStrength, _EnableBlur, _MainTex, _MainTex_TexelSize |
| `UI/UIVertexJitter` | _CutOff, _MainTex, _Time, _XOffsetFrequency, _XOffsetStrength, _YOffsetFrequency, _YOffsetStrength |
| `UI/Wave` | _Color, _ColorMask, _MainTex, _MainTex_ST, _Stencil, _StencilComp, _StencilOp, _StencilReadMask, _StencilWriteMask, _TextureSampleAdd, _Time, _UseUIAlphaClip, _WaveIntensity, _WaveSpeedX, _WaveSpeedY, _WaveTiling |
| `UI/WaveScreenShot` | _ApRimColor, _ApRimColorRange, _ApRimSharpness, _ApRimThickness, _ColorDown, _ColorMask, _ColorMid, _ColorTop, _DisRimCustom, _EnableDarkRim, _LumAdd, _LumMax, _LumMin, _MainLightColor, _MainLightPosition, _MainTex, _ProjectionParams, _RimColor, _RimIntensity, _RimSharpness, _RimThickness1, _RoleDistanceRimMask1, _RoleDistanceRimWidth, _RoleNearWidth1, _ScreenParams, _Sequence1Alpha, _Sequence1Num, _Sequence1X, _Sequence1Y, _Sequence2Alpha, _Sequence2Num, _Sequence2X, _Sequence2Y, _SequenceTex1, _SequenceTex1_ST, _SequenceTex2, _SequenceTex2_ST, _Speed1, _Speed2, _Stencil, _StencilComp, _StencilOp, _StencilReadMask, _StencilWriteMask, _Time, _UseUIAlphaClip, _Use_LastSceneTex, _WaveIntensity, _WaveSpeedX, _WaveSpeedY, _WaveTiling, _WorldSpaceCameraPos |
| `UI/chouka` | _Color, _ColorMask, _ISPurple, _ISShipei, _MainTex, _Softlihui, _Stencil, _StencilComp, _StencilOp, _StencilReadMask, _StencilWriteMask, _Time, _UseUIAlphaClip, _ZWriteMode, _lihui, _lihuiScale, _lihuiShiPei, _lihuiSoft, _lihuiSoft_ST, _lihui_ST, _wuqiLihuiBlack, _wuqiVFX, _wuqiVFXSp, _wuqiVFXTint, _wuqilihui, _wuqilihui_ST |
| `UIEffect/Effect2` | _ALPHAPREMULTIPLY_ON, _ALPHATEST_ON, _AlphaClip, _BaseColor, _BaseMap, _BaseMap_ST, _Blend, _Classify, _Color, _Cull, _Cutoff, _DstBlend, _EFFECT, _FAKEHIGHLIGHT, _MRTEnable, _MainTex, _QueueOffset, _ROLE, _SampleGI, _SceneOrCharacter, _SrcBlend, _Surface, _UnlitIntensity, _ZWrite |
| `UIEffect/Effect4` | _Color1, _Color2, _ComparisonOperation, _DeltaT, _Distort, _DistortIntensity, _Distort_ST, _DstBlend, _MainTex, _Mask, _Mask_ST, _PassOperation, _Period, _SrcBlend, _Stencil, _StencilReadMask, _Tex1, _Tex1Speed, _Tex1_ST, _Tex2, _Tex2Speed, _Tex2_ST, _Time |
| `UIEffect/Effect_O` | _ALPHAPREMULTIPLY_ON, _ALPHATEST_ON, _AlphaClip, _BaseColor, _BaseMap, _BaseMap_ST, _Blend, _Classify, _Color, _Cull, _Cutoff, _DstBlend, _EFFECT, _FAKEHIGHLIGHT, _MRTEnable, _MainTex, _QueueOffset, _ROLE, _SampleGI, _SceneOrCharacter, _SrcBlend, _Surface, _UnlitIntensity, _ZWrite |
| `UIEffect/Effect_StarBeats` | _Alpha, _BaseMap, _ColorMask, _HueShiftSpeed, _MainTex, _Saturation, _SparkColor, _SparkSpeed, _Stencil, _StencilComp, _StencilOp, _StencilReadMask, _StencilWriteMask, _Time, _Value |
| `UIEffect/FanShoujiPing` | _BaseColor, _BlockLayer1_U, _BlockLayer1_V, _BlockLayer2_U, _BlockLayer2_V, _BlockPow, _GTex, _MainTex, _Time |
| `UIEffect/HuaPing` | _BlockIntensity, _BlockPow, _BlockSize, _MainTex, _Time |
| `UIEffect/UIPolygonFlow` | _Brightness, _Color, _ColorMask, _DstBlend, _MainTex, _Mask, _Mask_ST, _NoiseTex, _NoiseTex_ST, _PatternTex, _PatternTex_ST, _Speed, _SrcBlend, _Stencil, _StencilComp, _StencilOp, _StencilReadMask, _StencilWriteMask, _Time |
| `UIEffect/UIWordArt_TianERong` | _Alpha, _BackColor, _ChangeBar, _ColorMask, _Direc, _DstBlend, _FlowSpeed, _InnerHighColor, _InnerMidSmokeIntensity, _InnerMiddleColor, _MainTex, _MaskTex, _NoiseTex, _OuterMaskAdd, _OuterSmokeIntensity, _SmokeColor, _SrcBlend, _Stencil, _StencilComp, _StencilOp, _StencilReadMask, _StencilWriteMask, _Time, _UseUIAlphaClip |
| `UIEffect/textfield` | _BackAlpha, _BackColor, _ChangeBar, _ColorAdd, _ColorDiv, _ColorMask, _ColorPow, _ColorSub, _IsLineToOut, _IsMaskAffect, _LineMask, _LineNumFactor, _LinePow, _LineWidth, _MainTex, _Mask0Tex, _Mask1Tex, _Mask2Tex, _Stencil, _StencilComp, _StencilOp, _StencilReadMask, _StencilWriteMask, _TexProblem, _Time, _TimeScale, _UseUIAlphaClip |

## Findings that usually explain an 'off sometimes' recreation

1. **Blend state is per material, not fixed.** These properties show up all over the UI
   shaders: `_SrcBlend`, `_DstBlend`, `_Blend`, `_ALPHAPREMULTIPLY_ON`, `_ZWriteMode`,
   `_DstBlendUI`/`_SrcBlendUI`. If your reconstruction hardcodes straight alpha
   (`SrcAlpha, OneMinusSrcAlpha`) you match the game only where alpha is 0 or 1, and you
   drift everywhere else - exactly an intermittent mismatch.
2. **Three- and multi-stop gradients are the shading.** `UI/WaveScreenShot` uses
   `_ColorTop` / `_ColorMid` / `_ColorDown`; `UI/UIMultipleGradient` uses
   `_GradientColors` + `_GradientPositions` with `_GradientAlphaTop/Bottom` and
   `_AlphaControl`. Reproducing the ramp without the same colour stops and the same
   alpha control gives a near miss.
3. **Tinting by tone band.** `UI/UIMaskColorTint` has `_BlackPartColor` / `_WhitePartColor`
   with `_AlphaClip` + `_Cutoff`: a two-band tint driven by a mask, not a multiply.
4. **UI vertex colour space.** `UI/DissolvedUI` carries `_UIVertexColorAlwaysGammaSpace`.
   Gamma vs linear handling of vertex colour is a classic source of differences that only
   show up on some colours.
5. **Saturation / luminance controls are explicit.** `UI/UIBlendColor` (`_Blend`,
   `_Pow`, `_Saturation`), `UI/P3RFinalAttack` (`_SaturateLevel`, `_SkinLerp`,
   `_BaseTint`, `_ShadowColor`).

## The compiled bytecode (and where it stops)

- The build ships the compiled programs: **360 DXBC blobs** in
  `106/shaders.bundle`, extracted to `_dl/shaders_out/`.
- The standard disassembler (`d3dcompiler_47.dll`, `D3DDisassemble`) **refuses all of
  them** (`E_FAIL`), including after repairing the container header. Sanity check: the same
  call compiles and disassembles a test shader fine, and the game's payload is structured
  data (entropy 4.8 bits/byte), not encrypted noise.
- Conclusion: the programs are stored in a form the runtime repairs/expects, so **readable
  shader assembly is not available from the files alone**. The property lists above are.

## What would unblock a line-by-line comparison

The name of the shader/material being recreated (`UI/chouka`? something else?), and a
picture of a case where the reconstruction looks wrong next to the game. With the material
in hand we can read which textures and colours it feeds in, which is usually enough to find
the missing term.
