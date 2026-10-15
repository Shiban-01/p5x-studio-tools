# PLAN DE ATAQUE — P5X: cinemáticas → Unity → MP4
Estado de partida: **pre-alpha funcional** (2026-09-25). Assets extraídos, skinning resuelto,
escenario inyectado, MP4 saliendo. Falta el *render* del juego y la *puesta en escena* real.

## ESTADO DE EJECUCIÓN
- **F0 HECHO** (2026-09-25): `scripts/inventory_state.py` → `_dl/state.json`; ~5 GB liberados
  (107 GB libres); backups de ProjectSettings/Packages/capturadores en `_dl/backups/` +
  manifiestos de stages (`stage_*.txt`) para poder reconstruirlos. Decisión: **Built-in RP**
  (el proyecto no trae proyecto URP: `m_CustomRenderPipeline: {fileID: 0}`).
- **F1 HECHO** (2026-09-25): `Assets/Shaders/P5XToon.shader` + `scripts/patch_materials_toon.py`
  (84/84 materiales migrados por edición de YAML, valores conservados). Contorno en espacio de
  pantalla, corte toon con `_ToonCutLocation`/`_ToonCutSharpness`, rim por `_RimThickness1`.
  Gate de 12 frames OK y **render completo de 180 frames** con MP4:
  `media/p5x_kotone_toon.mp4`. Verificado con visión: contorno negro, colores planos, dos tonos,
  sin magenta.
- **HALLAZGO GRANDE (F1.5)**: los shaders SÍ se pueden recuperar parcialmente. `shaders.bundle`
  (84 MB, hash-ofuscado) trae 431 Shader → AssetRipper exporta **424 `.shader`**, pero con el
  cuerpo en stub (`//DummyShaderTextExporter`): lo auténtico es el **bloque `Properties` con
  defaults y enums**. El shader de personaje es `role.shader` ("Universal Render Pipeline/Role");
  el juego es **URP**. Copia de referencia en `_dl/backups/shaders_reales/` (6 shaders clave +
  lista de los 424). El HLSL original va compilado en el build ⇒ irrecuperable.
- Deuda asumida: los 63 renderers del **escenario** siguen cayendo al shader de respaldo
  (sus materiales no resuelven) → darles shader propio es tarea de F2/F1-bis.
- **CORRECCIÓN IMPORTANTE (F1-bis)**: la migración por edición de YAML + `.meta` escrito a mano
  **NUNCA funcionó**. Unity no puede parsear un `.meta` escrito a mano
  (`Unable to parse file …P5XToon.shader.meta: [Parser Failure at line 11]`) ⇒ el shader no se
  importaba y los materiales quedaban con el **shader de ERROR (magenta 255,0,255)**. El "toon"
  que se dio por bueno en F1 era en realidad el shader `Standard` de respaldo (la verificación
  por visión fue un falso positivo; se detectó midiendo el color exacto de los píxeles).
  **Arreglo**: `Assets/Editor/P5XApplyToon.cs` asigna el shader por API desde Unity (que genera
  su propio `.meta`). Verificado: `isSupported=True`, 84/84 materiales migrados, 0 con shader de
  error, valores conservados (`_ToonCutLocation` 0,55 `_EnableOutline` 1). **Regla nueva: nunca
  escribir `.meta` a mano; dejar que Unity lo genere.**
- **F2 HECHO** (2026-09-25): el shader toon se aplica **solo a personajes**
  (`_SceneOrCharacter` ≥ 0,5 o nombre `PC0*`/`wonder*`), y el **escenario vuelve a `Standard`**
  (25 materiales) porque el toon ignora las **71 luces puntuales/área** del nivel y lo dejaba a
  oscuras (brillo medio 40 → 90). Atmósfera real del bundle aplicada en el capturador:
  **Trilight, ambiente azul nocturno (0,089 0,223 0,356)**, sin niebla. Lightmaps: **no hay**
  (todos los renderers en `65535` ⇒ iluminación en tiempo real, no horneada). Los personajes
  reciben esa misma luz de escena por **`ShadeSH9`** (esféricos armónicos), no solo su
  `_AmbientColor` propio.

## Definición de hecho (objetivo final)
Un MP4 por cinemática, con: personajes con **shader toon propio + contorno**, escenario real
del juego, **iluminación horneada**, **cámara real del timeline**, animación facial, y
subtítulos del texto de historia. Todo reproducible offline, retomable y documentado.

## Reglas de trabajo (no negociables)
- **$0**: todo el trabajo pesado es local (Unity + ffmpeg + Python). Coste de tokens ≈ 0;
  solo consume mi orquestación. Nada depende de proveedores para esto.
- **Verificar con `vision_analyze`**, nunca fiarse del exit code.
- **Scripts retomables** (saltar lo ya hecho).
- **No redistribuir assets**; uso research/fan-content.
- **Backup del capturador fuera de `Assets/`** (`_dl/editor_good/`): AssetRipper borra
  `Assets/Editor/` en cada export.
- **Disco**: ~102 GB libres → no acumular stages; borrar intermedios al cerrar una fase.
- **Gate visual por fase**: render de 10–20 frames (no 180) para validar antes de gastar
  5 min por render completo.

## Hallazgo que reordena las prioridades
Los materiales exportados conservan **la interfaz completa del shader original** (nombres de
propiedades, keywords y valores afinados), aunque el código del shader no se exportó
(los 84 `.mat` apuntan al GUID placeholder `0000000deadbeef15deadf00d0000000`):

- Toon: `_ToonCutLocation` 0.55, `_ToonCutSharpness` 12, `_ToonCutLocationBackLight`,
  `_ToonCutLocationFaceLight`, `_ToonDarkColorTint`, `_ToonShadowColorTint`.
- Contorno: `_EnableOutline` 1, `_OutlineWidth1/3/5/6`, `_OutlineColor`,
  `_OutlineSkinColor`, `_OutlineTex` ✓, keyword `_ENABLE_OUTLINE_TEXTURE`.
- Sombra: `_ToonDarkMap` ✓, `_ShadePosition` ✓, `_EnableFaceShadow`, `_FaceShadowTex`,
  `_StkDarkColor` / `_StkDarkRange` / `_StkDarkSharpness` (controles estilo Persona).
- Otros: `_Rim*`, `_MatcapMap`/`_MatcapMask`, `_MetallicGlossMap` ✓, `_BumpMap` ✓,
  `_AmbientColor`, `_LightColor`, `_Polarization*`, `_AlphaClip`/`_Cutoff`.

⇒ **El shader se puede reimplementar fielmente**, no a ciegas. Solo faltan 2 texturas
compartidas: `_DiffuseRampTexture` y `_MatcapMap` (ambas placeholder ⇒ buscar en otros bundles).

---

# FASES

## F0 — Saneamiento y línea base (barato, 0 riesgo)
| # | Tarea | Criterio de aceptación |
|---|---|---|
| F0.1 | `scripts/inventory_state.py` → `_dl/state.json` (bundles, stages, proyectos, entregables, MP4s) | Un comando responde "¿qué tengo ya?" |
| F0.2 | Liberar disco: borrar `unity_projects/_scene_iwai`, stages crudos ya inyectados | ≥120 GB libres |
| F0.3 | Backup de `ProjectSettings/` + `Packages/` + capturadores de cada proyecto | Re-exportar no pierde nada |
| F0.4 | Decidir pipeline: **Built-in RP** (lo que el proyecto usa hoy, `m_CustomRenderPipeline: 0`) vs instalar URP (más fiel al original) | Decisión escrita en RETOMAR.md |

## F1 — SHADER TOON PROPIO  ← *la palanca grande*  ✅ HECHO (con corrección F1-bis)
**Por qué primero:** multiplica el valor de cada render futuro. Hoy todo sale con `Standard` plano.
**Corrección F1-bis:** la migración inicial por YAML `.meta` a mano no funcionó (Unity no parsea
ese `.meta`); se rehízo con `P5XApplyToon.cs` por API. Ver "ESTADO DE EJECUCIÓN".
| # | Tarea | Criterio de aceptación |
|---|---|---|
| F1.1 ✅ | `Assets/Shaders/P5XToon.shader` con las propiedades EXACTAS del material original | Sin errores de compilación; mismas props visibles |
| F1.2 ✅ | Shading toon: `_BaseMap` × cut(`_ToonCutLocation`, `_ToonCutSharpness`) con `_ToonDarkMap` y `_ToonDarkColorTint` | Sombra dura en 2 tonos, no degradado |
| F1.3 ✅ | Pase de contorno (inverted hull) con `_OutlineColor`/`_OutlineSkinColor` | Contorno negro limpio, grosor estable en píxeles |
| F1.4 ✅ | `Assets/Editor/P5XApplyToon.cs`: asigna el shader conservando texturas y valores | `isSupported=True`, 84/84 migrados, 0 con shader de error |
| F1.5 ⏳ | Recuperar `_DiffuseRampTexture` y `_MatcapMap` en bundles locales (ramps: 256×16) | Pendiente: no son críticos (el toon ya corta por `_ToonCutLocation`) |
| F1.6 ✅ | **GATE**: 12 frames de Kotone+wonder; verificación por medida de píxeles | A/B: negros 0,6%→10,3% en la silueta = contorno real; 0% magenta |

## F2 — Iluminación y atmósfera  ✅ HECHO
| # | Tarea | Criterio de aceptación |
|---|---|---|
| F2.1 ✅ | Lightmaps: **verificado que NO existen** (todos los renderers en `m_LightmapIndex 65535`) ⇒ la escena del juego es de **luz en tiempo real** | Sin lightmaps que bindear (no era una pérdida) |
| F2.2 ✅ | Atmósfera real del bundle en el capturador: `RenderSettings.ambientMode = Trilight`, azul nocturno (0,089 0,223 0,356), sin niebla; personajes con `ShadeSH9` | Personajes integrados en la noche azul |
| F2.3 ✅ | Escenario devuelto a `Standard` (25 materiales) porque el toon ignora las 71 luces del nivel | Brillo medio 40 → 90; entorno visible |
| F2.4 ✅ | **GATE**: 12 frames vs. render anterior | 0% magenta, contornos presentes, entorno azul nocturno |

## F3 — Cámara real del timeline  ← *la otra palanca grande*  ✅ HECHO
**Por qué importa:** deja de ser "dos modelos filmados a mano" y pasa a ser *la* cinemática.
| # | Tarea | Criterio de aceptación |
|---|---|---|
| F3.1 ✅ | `scripts/map_camera_tracks.py` (estructura del `.playable`: grupos, tracks, clips) + `probe_timeline_camera.py` / `extract_timeline_camera.py` / `extract_vcam_params.py` / `extract_camera_curves.py` sobre el bundle del timeline | JSON con tracks, tomas, VCam y curvas |
| F3.2 ✅ | Tomas reales en `P5XKotoneCapture.cs`: `TOMAS[]` con pos/rot/FOV/ventanas de tiempo, `EvalToma()` con mezcla smoothstep, temblor Perlin, placas de fundido, tiempo = segundo del timeline (`tInicio`) | Cámara con el encuadre del juego |
| F3.3 ✅ | **GATE**: 12 frames justo en el corte CM001→CM002 | 0% magenta, tomas usadas CM001..CM002, encuadre coherente |

**Lo que se recuperó (datos auténticos del bundle `tl_ue_04_04298c1b80`):**
- Grupo **`摄像组`** = `CinemachineTrack` `主摄像机` + `CameraShakeTrack` `持续震动`.
- **5 tomas**: `CM001 Black Board` (0–0,667 s, fundido negro), `CM001` (0,667–26,667),
  `CM002` (26,667–41,833), `CM003` (41,833–49,667), `CM003 White Board` (49,667–52, fundido
  blanco). Mezclas: 1,333 s en los cortes, 1,5 s en las placas.
- Las tomas son **`CinemachineVirtualCamera` estáticas** (`m_Follow`/`m_LookAt` vacíos: los asigna
  el juego en runtime) ⇒ no hay *follow* que reproducir, el encuadre es el transform de cada VCam.
- Lente **FOV 30**, near 0,3 (antes usaba 68 a mano → encuadre totalmente distinto).
- `CinemachineTransposer` offset (0,0,−10) y `CinemachineComposer` centrado (soft zone 0,8).
- Temblor: `CinemachineBasicMultiChannelPerlin` amplitud **0,4**, frecuencia **0,35**.
- Los clips `Recorded*` (tracks en modo *infinite clip*) traen las curvas de posición/euler: son
  casi constantes (el yaw salta justo en los cortes), o sea **el movimiento lo da el corte entre
  VCam, no una interpolación continua**.
- **HALLAZGO**: el evento original NO ocurre en la zona del escenario que teníamos. Las cámaras
  viven en x≈279,7 z≈284,3 y el bundle referencia `FX_Tartaros_FLD_ForbiddenDoor` y
  `BGM_P3R_TheVoiceSomeoneCalls_StoryBGM` ⇒ **Tartarus, junto a la Puerta Prohibida**. Se
  comprobó que no hay ni un renderer a <25 u de ese punto en `scn_iwai_wyc`. **Solución**: se
  recoloca el rig completo al escenario inyectado **conservando el encuadre** (distancias y
  ángulos idénticos); las alturas van referidas al suelo (cámaras a 1,55–1,84 m).
- **Siguiente paso natural (F3-bis)**: localizar el chunk de escena de Tartarus (raíz del chunk
  cerca de x≈279, z≈284) y usarlo como fondo real en vez de Iwatodai.

## F3.5 — El guion del timeline (LA palanca grande)  ← *nuevo, medido el 2026-09-25*
**Hallazgo:** el timeline no trae solo la cámara. `_dl/scene_script.json` (generado con
`Assets/MonoBehaviour/*.asset`) muestra **24 tracks con sus clips, tiempos y assets resueltos**,
y **todos los assets existen ya en el proyecto** (0 "FALTA"). O sea: la coreografía real de los
52 s es reproducible sin extraer nada nuevo.
| # | Tarea | Criterio de aceptación |
|---|---|---|
| F3.5.1 | Reescribir el capturador como **evaluador de timeline**: por actor, en el instante t, elegir el clip activo (ventana `m_Start..m_Start+m_Duration`), muestrear en `m_ClipIn + (t − m_Start)` y respetar `m_BlendInDuration`/`m_BlendOutDuration` con sus curvas | Cada actor hace lo que el guion dice, no un bucle elegido a mano |
| F3.5.2 | **Audio real** con ffmpeg: BGM `BGM_P3R_TheVoiceSomeoneCalls` (0–51,7 s) + SFX (pasos de botas t=39,8; pasos de suela t=26,1/39,5/42,6; `SFX_FlashWhite_Short_01` t=48,0) | MP4 con la música y los efectos en su segundo exacto |
| F3.5.3 | **Barras de cine** del track `UI` (`剧情上下黑边（窄）`, 52 s) | Aspecto de cinemática |
| F3.5.4 | Props: `Tartaros_FLD_ForbiddenDoor` (52,8 s) + 4 tracks `Activation` (t≈9,2 y 47,6) + `虚拟挂载` (atado a `h_M_HR1`) | Puerta y props presentes y activados cuando toca |
| F3.5.5 | Render completo 0–52 s (1.566 frames) → 1 MP4 | La escena entera, no un tramo |

**El guion, tal cual (extracto de 24 tracks):**
- **wonder_uniform**: `stand_01` (0–40) · `walk` (39,3–45,8) · `stand_01` (45–52).
- **PC079_01 (Kotone)**, 14 clips: `stand_story` (0–8,4) · `stand_holdsth_start_story` (8,1) ·
  `stand_holdsth_story` (10,3) · `stand_holdsth_start_story` (10,7) · `stand_story`
  (**11,3–24,5, con clipIn 12,13**) · `zuozhuanxiang135_story` (25,3: **gira 135°**) ·
  `stand_story` (27–39,6) · `walk_loop_story` (39,1 y 41,2: **anda**) · `walk_end_story` (45) ·
  `stand_chupeng_start/loop/end_story` (45,7–51,2) · `stand_story` (50,8).
- **Diálogo** (`对话`): texto chino directo en el asset — t=12,33 `{PLAYER_NAME}认识的成年人还挺多的嘛。` (12,7 s) y t=27,33 `好了，振作起来，去找剩下的碎片吧！ 等4句` (11,7 s). **F5 deja de ser un misterio**: el texto está aquí, no hace falta resolver el `SN`.
- `自动跳播轨道` en t=41,33 (`►►|`) = marcador de salto; sub-playable de 5,58 s con
  `PC063_thief@stand_story` / `宙斯看向` pertenece a **otro** director anidado.

**Coste real medido:** 180 frames tardaron 4 min 13 s (≈1,4 s/frame) ⇒ 52 s ≈ **37 min**. Un solo
pase nocturno.

## F4 — Cara, detalle y piezas que faltan
| # | Tarea | Criterio de aceptación |
|---|---|---|
| F4.1 | Blendshapes/morph de los clips `_bs` (los rigs ya se cargan, las curvas no se aplican) | Cara se anima (boca/parpadeo) |
| F4.2 | Texturas pendientes: `PC079_01_eyelid`, `_bc` normal de wonder | 0 partes sin textura en el log |
| F4.3 | Bindear armas (`PC079_01_qiang`, `naginata`) al hueso correcto | Arma en la mano, no flotando |
| F4.4 | Localizar `frost_normal` (3er actor del apretón) | Actor presente o descartado con motivo |

## F5 — Texto y subtítulos
| # | Tarea | Criterio de aceptación |
|---|---|---|
| F5.1 | Resolver `SN: P3RE0121` → tablas de historia (`page.py` / tablas UTF) | Texto plano por SN |
| F5.2 | Generar `.srt` por escena (o subtítulos quemados) | Vídeo entendible sin saber chino |

## F6 — Cobertura: escalar a todas las cinemáticas
| # | Tarea | Criterio de aceptación |
|---|---|---|
| F6.1 | `scripts/build_scene.py <tl>`: stage → export → captura → MP4 → ficha, leyendo los ActionGroups (`map_p3p_scene.py`) para actores/clips/duración | 1 comando = 1 MP4 |
| F6.2 | Catálogo Kotone: 12 caps del prólogo (`tl_ue_00`…`tl_ue_05`) + epílogo (`tl_e_02_1`) | 13 MP4 con nombre y ficha |
| F6.3 | Extender a otros personajes/eventos (Aegis/wonder ya está; PC063, etc.) | Pipeline acepta cualquier `tl_*` |
| F6.4 | Ficha por vídeo: actores, clips, duración, fuentes, limitaciones conocidas | Documento por escena |

## F7 — Infraestructura y cierre
| # | Tarea | Criterio de aceptación |
|---|---|---|
| F7.1 | Actualizar `RETOMAR.md` en cada hito | Retomada en <5 min |
| F7.2 | Publicar hitos en subforo `restauracion-en-unity` (`_post_unity_update.py`) | Post verificado por read-back |
| F7.3 | Decidir el cron `p5x-tool-updates` (¿avisar a #general o silenciar?) | Decisión aplicada |
| F7.4 | Skill `p5x-unity-toon-capture` con el pipeline completo | Reusable sin re-descubrir |
| F7.5 | Entregables finales en `media/` con nombres legibles | 1 MP4 por cinemática, sin duplicados |

---

## Orden y por qué
```
F0 → F1 → F2 → F3 → F4/F5 → F6 → F7
```
- **F1 antes que todo**: cada render futuro se beneficia; hacer F6 antes sería automatizar una
  base que va a cambiar.
- **F2 y F3** son las que más "parecido" añaden después del shader.
- **F6 al final**: la automatización se construye sobre un pipeline ya estable.

## Riesgos y mitigación
| Riesgo | Mitigación |
|---|---|
| El shader del juego no clonable al 100% | Parámetros y valores YA conocidos ⇒ iterar a ojo contra el CG; aceptar ~90% |
| Binding de lightmap perdido en el export | Asignación manual por índice; si fallan los UV2, iluminación propia equivalente |
| CameraTracks no resolubles | Fallback: cámara scripteada (lo que ya funciona) |
| Espacio en disco | 1 proyecto Unity por escena, borrar stages al terminar |
| AssetRipper borra `Assets/Editor/` | Backup en `_dl/editor_good/` (ya en marcha) |
| Coste por iteración (~5 min/render) | Gates de 10–20 frames antes de renders completos |
| AssetRipper se cae solo | Relanzar `tools/AssetRipper13/... --headless --port 57973` |

## Coste estimado
Todo local (Unity/ffmpeg/Python): **0 tokens** salvo mi orquestación. Cada fase cierra con un
gate visual = ~1 render corto. F1 es la fase más iterativa (shader a ojo): esperar 5–10 ciclos
de ajuste antes del gate final.