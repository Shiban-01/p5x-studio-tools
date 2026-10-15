# Retomar aquí — P5X: animaciones → Unity → MP4 (estado al 2026-09-25 22:15)

## FALLO 7: las COPIAS del motor (`_2`) pintaban otro busto como cara — 2026-10-05

**Lo que reportó el usuario** (captura de `changweiaige`): "las texturas que comparten rostro, ésta
claramente debiese ocupar el rostro de otro personaje, y esto es una variante".

**Causa, medida:** el motor vuelve a exportar el mismo asset con sufijo de copia (`lunkuo_2`,
`toufa_2`, `mianju_2`, `benti_2`, `yan2_2`). `paso_de()` sólo limpiaba los dígitos finales, así que
`lunkuo_2` quedaba como `lunkuo_` → **sin paso**. Y ahí entraba la regla de la cara de
`partir_nombre()` (`benti-<algo>` sin parte conocida = CARA de esa expresión): `benti-lunkuo_2` se
clasificaba como **cara** y el visor pintaba encima el **dibujo completo de la variante** (un contorno
de lienzo entero, 580×648, ~60 % opaco) creyendo que era el rostro. De paso, `lunkuo_2` salía en el
selector de expresiones.

**Alcance:** **14 de los 120** retratos estaban así, `changfu01-xiachuanling` y `zhifu01-aocunchun`
entre ellos. Unos mostraban el contorno de la variante y otros el pelo (`-toufa_2`).

**Arreglo:** `_sin_copia()` limpia el sufijo `_N` antes de clasificar (en `paso_de` y en el test de
`PARTES_BASE`). `paso_de("lunkuo_2")` → `outline`, `("toufa_2")` → `hair`, `("mianju_2")` → `mask`,
`("benti_2")` → `body`, `("yan2_2")` → `eyes`. La copia queda como candidata de su paso y pierde
frente a la original por `_variante()` (0 < 2), que es lo que el mapa del emparejado dice que usa el
juego.

**Verificado:** 14 → **0 de 120**; `changweiaige` 6→**5** capas (outline, body, clothes, mask, hair,
sin cara falsa), `xiachuanling` 8→**7**; render revisado a ojo: una sola figura coherente y la máscara
sobre la cara. Regresión en `tests/test_bustups.py` (sección 7).

**Lección para la próxima:** al clasificar nombres de assets, normalizar **todos** los sufijos
conocidos del motor (`_#NN` del recorte, `_N` de la copia) antes de decidir; si no, el que no se limpia
cae en la primera regla que lo acepte, y esa regla es la de la cara.


## VISOR DE BUST-UPS AUTOSUFICIENTE — 2026-10-04 (extracto de retratos, sin el bulk)

**La pega que puso el usuario:** el visor leía las texturas del **bulk** (`extracted/textures`,
**63 GB**), así que para ver retratos había que pasar antes por el bulk entero: eso le quitaba la
autosuficiencia a la herramienta. Pidió o bien un extracto propio, o bien un aviso del espacio.

**Lo que hacía falta de verdad (medido, no supuesto):** los 120 bust-ups emparejados sólo usan
**2.683 nombres de asset = 5.360 PNG = 167 MB**, y **todo** sale de bundles `uitex_*`. El mapa de
bust-ups (`_dl/emparejado_bustups.json`) ya apuntaba el bundle de cada capa ⇒ el extracto va a tiro
hecho: **80 bundles**, no las 1.506 familias de texturas de interfaz.

**Cómo queda:**

| | Bulk entero | Extracto de retratos |
|---|---|---|
| PNG | 118.230 | **5.360** |
| Peso | 63 GB | **175 MB** |
| Tiempo | 1 h 38 min | **2,1 min** |
| Bundles leídos | 118.425 | **80** |

- Botón **Extract portraits** en la pestaña Bust-ups (`#retr-sacar`), con barra de progreso, cancelar
  y abrir carpeta. Va a `extracted/portraits/` y **viaja con el `.exe`** (los bundles medidos van en
  `p5x_studio/datos/retratos.json`, 3 KB, aparte del mapa porque éste se recorta para el ejecutable).
- `bustups.carpeta_texturas()` prefiere el extracto **sólo si está completo** (marca `_listo.json`):
  con media extracción hecha, el bulk entero da mejores retratos que una carpeta a medias.
- El mismo motor del bulk (reanudar, cancelar, progreso), pero en lotes de 40 y **tirando los PNG que
  no son de ningún retrato ANTES de ordenarlos** (`lote.es_de_retrato`, que ignora el sufijo `_#NN`
  del recorte): si no, el disco tendría que aguantar los 10 GB de la familia `uitex` entera.
- Textos ES/EN del visor actualizados: el aviso de "sin texturas" ya manda al botón nuevo.

**Verificado de punta a punta:**
- Prueba con 2 bundles (220 PNG / 7,7 MB en 12 s): **5 bust-ups montan sólo con el extracto**, y sus
  capas son **idénticas** a las del bulk (5/5, incluido `yongzhuang-suyu` con 7 capas).
- Extracción completa real a `Desktop\P5X Studio Tools\extracted\portraits`: **80/80 bundles,
  5.360 PNG, 175,1 MB, 2,1 min, 0 fallos**, marca de completo escrita.
- Suite `tests/test_bustups.py` ampliada con el extracto (qué se guarda, de dónde se lee).

**Pendiente de decisión del usuario:** si el extracto completo sustituye al bulk, el bulk (63 GB) ya
no hace falta para el visor y se puede borrar (no se ha tocado).


## ENTREGA: modelo de Kotone Shiomi + borrado de progresos — 2026-09-27 06:30

**Entregable: `C:\Users\Lukas\p5x-datamining\kotone_shiomi\`** (146 MB, 123 ficheros) — el modelo de
Kotone Shiomi (PC079_01) con **piel de 124 huesos**, **24 expresiones faciales** y **51 texturas
originales**, en carpetas separadas para uso externo:

| Carpeta | Contenido |
|---|---|
| `01_modelo/glb/` | `Kotone_Shiomi_completo.glb` (el personaje entero) + 9 piezas sueltas |
| `01_modelo/obj/<cat>/` | OBJ + MTL (los MTL ya apuntan a `02_texturas/`) |
| `02_texturas/` | 51 PNG agrupados: cuerpo, cara, ojos, pelo, armas, otros |
| `03_esqueleto/` | `huesos.json` (124 huesos con padre y TRS local), `esqueleto_arbol.txt`, `bindposes.bin`, FBX |
| `04_expresiones/` | `expresiones.json` + 24 OBJ (uno por expresión, malla ya deformada) |
| `05_materiales/` | `materiales.json` + `tabla_texturas.md` (qué es cada ranura del shader P5X/Toon) |
| `06_origen/` | `procedencia.json` (bundle de origen + sha256) |
| `preview/` | renders de referencia (frente, 3/4, lado, espalda, cara, hoja de contacto) |
| `LEEME.md` / `README.md` | documentación en español e inglés |

**Verificación hecha (no solo "parece bien"):**
- Validación estructural del GLB parseándolo desde cero: accesores, índices en rango, morph
  targets del mismo tamaño que la malla, `inverseBindMatrices` = nº de huesos, imágenes PNG válidas
  → **los 10 GLB, OK**.
- **Rasterizado propio** del GLB completo: alto 1,68 m, Y-arriba, silueta con cabeza arriba,
  **3 tramos en el 25-40% = brazos extendidos + torso** (T-pose), **2 tramos simétricos de piernas**
  → figura humanoide completa y derecha.
- Render con textura: **3.965 colores distintos** (frente al render plano: 10) y la cara con ojos en
  sus cuencas, boca centrada y pelo en la cabeza ⇒ **UVs correctas**.
- Las 24 expresiones mueven vértices de verdad (parpadeo 1.842 vértices / 24,9 mm; la neutra
  `*_tongchang` 0,12 mm, como debe ser).

### CORRECCIÓN (2026-09-27, tras aviso del usuario): la V de las UV estaba sin invertir

El usuario avisó de "fallas en el texturizado" y pasó el sprite del juego (`PC079_01_01_09_01`)
como referencia. Comparando **mediciones** (no la vista: la visión volvió a inventarse colores):

| Zona | Mi primera exportación | Con la V invertida (correcto) | Sprite |
|---|---|---|---|
| espinilla | (28,28,28) negro | **(205,199,191) claro** | media BLANCA |
| tobillo | (59,57,54) oscuro | (176,168,159) claro | media blanca |
| cara | 87% de texels = piel lisa (sin rasgos) | rasgos: cejas, iris, pestañas | cara con rasgos |

**Causa:** Unity guarda la V de las UV de abajo arriba (origen abajo); el PNG del bundle y la
convención de glTF/OBJ van de arriba abajo. Sin `v → 1 − v`, la textura cae espejada en vertical:
los calcetines blancos salen negros y la cara sale como una máscara lisa. **Arreglado** en
`build_kotone_package.py` (helper `uv_gltf`), y afecta a GLB y OBJ por igual.

Otros dos defectos hallados en la misma revisión y corregidos:
- El **párpado** usaba el material de relleno `Standard` (AssetRipper no supo resolverlo): ahora
  lleva el material de la cara, que es el suyo (sus UV caen sobre la piel del atlas de la cara).
- El `_BumpMap` del cuerpo apuntaba a la normal del **LOD** (`body_lodlow_nm`); ahora usa
  `PC079_01_body_nm`.
- La **pistola** sigue sin textura: ese material no se pudo recuperar (queda documentado).

**Lección para la skill (no editable desde aquí):** al volcar datos de Unity para uso externo,
comprobar SIEMPRE la orientación de la V de las UV contra una referencia conocida. Y verificar
contra arte oficial con medidas por zona, no con la vista.

### Guía que pasó el usuario (método de la comunidad, para la próxima vez)

`P5X Character Importer` (con los scripts de `github.com/aaronlink127/P5X_Research` sustituyendo
`Scripts/PWRD.MUEngine` + `p5xfashion.cs`): monta el modelo en Unity (rig + body + head), se
**compila el reproductor con LZ4** (`data.unity3d`) y ese fichero se abre en **AssetStudioMod**,
que sí exporta un **FBX ya riggeado** con los clips de animación. Es la vía "oficial" de la
comunidad y evita escribir el GLB a mano; el paquete de aquí se hizo por la vía artesanal porque
el proyecto de Unity ya no existía cuando llegó la guía.

**Aviso de visión:** el modelo de visión **alucinó** dos veces (describió texturas y colores en un
render que era de colores planos por pieza). La lección ya conocida: **medir píxeles** (colores
distintos, fracción de magenta, perfil de filas) y no fiarse de la descripción.

**Borrado (el usuario lo pidió explícitamente): 19 GB liberados** (132 → 153 GB libres)
- `unity_projects/{kotone,scene_full,scene_tl005,PC063_full}` → 7,6 GB (la restauración en Unity).
- `_dl/{scn_stage,tex_stage,tex_stage2,shaders_stage,scene_wyc_stage,bundles_kotone,stage,cam_stage,
  probe2,tex_ui_pc079,test_anim,kotone,test_bundle,proj_test,ast_part,ar.zip,ar13.zip}` → 12,5 GB.
- **Salvado antes de borrar:** `unity_respaldo/` (1,5 MB) = los 10 scripts de `Assets/Editor/`
  (`P5XKotoneCapture.cs`, `P5XExportKotone.cs`, `P5XFixTextures.cs`, `P5XApplyToon.cs`,
  `P5XTimelineData.cs`, …), `Scenes/Manual_Kotone_Wonder.unity` y `Shaders/P5XToon.shader`.
- **NO se tocó `media/`** (24 GB: 351 MP4, 506 WAV, capturas): son entregables, no progreso.
- Se conservan: `_dl/kotone_dump/` (3,8 MB: el volcado crudo, permite **rehacer el paquete sin
  Unity** con `scripts/build_kotone_package.py`), `_dl/ast_role/`+`ast_anim/` (config y esqueleto),
  `unity_projects/_shaders/` (425 shaders del juego) y los logs.
- Queda un directorio vacío **bloqueado** (`unity_projects/kotone/ExportedProject/Assets/Editor`,
  0 bytes): lo retiene la terminal de Hermes que tuvo el cwd dentro; se puede borrar al reiniciar.

**Consecuencia:** `MANUAL.md`, `unity.bat` y `p5x.bat` describen proyectos que ya no existen →
**histórico**. Para volver a abrir Unity habría que re-exportar con AssetRipper13 desde los bundles
del cliente (intactos en `C:\Users\Lukas\Downloads\P5X`).

**Receta que SÍ funciona para sacar un modelo con piel y expresiones de estos bundles** (lección
para la skill `p5x-datamining`, que es del usuario y no se puede editar desde aquí):
1. **AssetStudioModCLI** → texturas PNG y mallas OBJ del bundle de partes
   (`part_pc079_01…bundle`; el de rol solo trae config y los Animators).
2. **Unity** sobre el proyecto reconstruido → volcar vértices, huesos, pesos, bind poses,
   **blendshapes** y materiales a binario+JSON (`P5XExportKotone.cs`). Los `mesh.vertices` **sí** se
   leen aunque el YAML diga `m_IsReadable: 0`.
   - `Buffer.BlockCopy` NO acepta arrays de `Vector3`/`Vector2` (solo primitivos): convertir a
     `float[]` antes.
3. **Escribir el GLB a mano en Python** (`build_kotone_package.py`): es la única vía, porque ningún
   exportador saca un FBX ya *riggeado* (los `SkinnedMeshRenderer` se montan en runtime).
   - El modelo viene **Z-arriba y mirando a −Y** → nodo raíz del GLB con **−90° sobre X** (deja
     Y-arriba y mirando a +Z, la convención glTF). En los OBJ se hornea.
   - Las matrices de bind van **fila-mayor** en Unity → trasponer a columna-mayor para glTF, y
     conjugar con el espejo (`M' = B·M·B`, `B = diag(−1,1,1,1)`).
   - Las armas se enganchan **por código** a la mano (el dato no está en los bundles): van sueltas.
4. **Verificar sin depender de la visión**: parsear el GLB desde cero + rasterizarlo
   (`verificar_glb_kotone.py`, `preview_kotone.py`).

---

> **PLAN DE ATAQUE completo: `PLAN.md`** (8 fases F0–F7, criterios de aceptación y riesgos).
> Orden: F0 ✅ → **F1 shader toon** ✅ → **F2 luz** ✅ → **F3 cámara real** ✅ → F4/F5 cara+texto
> → F6 cobertura → F7 cierre.
>
> **Entregable actual: `media/p5x_kotone_timeline_52s.mp4`** — **la cinemática completa de 52,77 s**
> (1584 frames, 1280×720, h264 + AAC), con el **guion real del timeline**, la **cámara real** de las
> 5 tomas y el **audio real** (BGM `BGM_P3R_TheVoiceSomeoneCalls` + 5 SFX en su segundo exacto).
>
> ### F3.5 — el guion del timeline (A, hecho)
> `scripts/build_timeline_script.py` lee los tracks `角色动画`/`角色动画_0` del PlayableDirector y
> genera `Assets/Editor/P5XTimelineData.cs` (17 clips, 2 actores: **PC079_01** 14 clips y
> **wonder_uniform** 3) + `_dl/audio_events.json` + `_dl/guion.txt`. El capturador lo evalúa por
> frame con la **extrapolación de Timeline** (los clips tienen huecos: `stand_story` acaba en
> 24,53 y el giro empieza en 25,27 → se mantiene la pose). Los clips de caminar conservan su
> desplazamiento (delta desde el punto de entrada) en vez de ir fijos.
> **Gate nuevo: 24 frames que BARREN los 52 s** (valida todo el timeline en ~1 min).
> Medición final: 1584 frames, 0,000% magenta, negro al inicio y **blanco en f_1560** (t=52).
>
> ### Tiempos reales del juego (medido, no supuesto)
> El timeline **se pausa** en los diálogos (`WaitForDialogEnd: 1` en los clips de `对话`) y cada
> nodo trae su espera: `MinStayTime` (p. ej. 1,67 s), `DelayShowTime`, `DelayTimespan`.
> **Suman 21,72 s de lectura real dentro de 30,84 s de ventana** ⇒ **las ventanas del timeline ya
> contemplan el auto-texto y el render lineal es el modelo correcto**; no hay que inventar esperas.
> Solo `AdvancedDialogClip_2` (t=12,333) se pasa +1,37 s (nodo con `MinStayTime: 5,0`).
> Hay un `BranchDialogNode` (`SN: P3R021233`): ahí es donde el juego pide input.
> Detalle en `_dl/dialogos_timing.json`. Los `SN` de las líneas: P3R021229…P3R021237.
>
> ### B — audio real (hecho)
> `scripts/extract_sfx.py` extrae los cues desde los `.acb` (CRI ACB multi-stream, vía vgmstream
> `-m/-s`): 13 WAV en `media/sfx_wav/`. `scripts/mux_audio.py` monta el MP4 con BGM recortada a
> 52,77 s + `afade` de salida y los SFX con `adelay` en su segundo exacto.
> Niveles verificados: picos en t=26 (-20,8 dB), t=40 (-18,7), t=48 (-18,6).
>
> ### D — cara: lo que falta de verdad (medido)
> **Ninguno de los 724 `.anim` del proyecto tiene curvas de blendshape** ⇒ la cara NO se anima
> desde los clips de historia; el facial va por otro sistema en runtime. Lo que sí falta son
> **texturas**: el log del capturador dice "sin textura" para `PC079_01_eyelid`,
> `wonder_uniform_eye/eyelid/cheekred/hair/bottom/shoes`. Ahí está el margen real de D.
>
> ### E — Tartarus: pendiente
> El chunk de escena del evento (raíz del chunk cerca de x≈279, z≈284) sigue sin localizar.
>
> ### F3: la cámara ya es la del juego
> Datos extraídos del bundle del propio timeline (`tl_ue_04_04298c1b80`), no inventados:
> grupo `摄像组` → `CinemachineTrack` `主摄像机` + `CameraShakeTrack` `持续震动`; **5 tomas**
> (`CM001 Black Board` 0–0,667 · `CM001` 0,667–26,667 · `CM002` 26,667–41,833 · `CM003`
> 41,833–49,667 · `CM003 White Board` 49,667–52 con fundido blanco), mezclas de 1,333 s,
> **FOV 30** (antes 68 a mano), near 0,3, transposer offset (0,0,−10), temblor Perlin amplitud
> 0,4 / frecuencia 0,35. Scripts: `scripts/map_camera_tracks.py`,
> `probe_timeline_camera.py`, `extract_timeline_camera.py`, `extract_vcam_params.py`,
> `extract_camera_curves.py`, `dump_timeline_hierarchy.py`.
>
> ⚠️ **El evento original NO está en Iwatodai**: las VCam viven en x≈279,7 z≈284,3 y el bundle
> referencia `FX_Tartaros_FLD_ForbiddenDoor` + `BGM_P3R_TheVoiceSomeoneCalls_StoryBGM` ⇒
> **Tartarus, junto a la Puerta Prohibida**. En `scn_iwai_wyc` no hay ni un renderer a <25 u de
> ese punto. Por eso el rig se **recoloca entero al escenario inyectado conservando el encuadre**
> (mismas distancias y ángulos; alturas referidas al suelo). **F3-bis pendiente**: encontrar el
> chunk de escena de Tartarus (el chunk cuya raíz caiga en x≈279, z≈284) y usarlo de fondo real.
>
> ⚠️ **F1 (leer antes de tocar el shader):** la migración por YAML con `.meta` escrito a mano
> **nunca funcionó** (Unity no lo parsea) ⇒ el shader no se importaba y todo salía con el shader
> de error (magenta). Se arregló asignándolo **por API** con `Assets/Editor/P5XApplyToon.cs`.
> **Regla: nunca escribir `.meta` a mano.** Verificar siempre midiendo el color de los píxeles
> (la visión dio un falso positivo).
>
> 📋 **Inventario de cámaras (volcado en `_dl/cam_clips.txt`, 111 bundles / 688 clips):** la
> familia `anim_camera*` es **de combate** (`*_thief@attack/critical/oneMore/skill_*_camera`).
> **No existe** ningún clip de cámara para nuestro evento: solo hay genéricos
> (`camera@TL_zx_Event_06_29_04`, `camera@gongdiandaota_story`) ⇒ se confirma que para
> `TL_P3P_Event_side_prologue_04_04` **la única vía es Cinemachine** (lo que hace F3).
> Para F6 (cobertura) sí son oro: **`PC079_01@` tiene 5 cámaras de combate**
> (`critical_camera`, `general_attack02_camera`, `oneMore_Camera`, `skill03_camera`,
> `SpecialEffect_camera`).

## Lo que funciona hoy
- Escena `TL_P3re_PC063_00` renderizada completa en Unity 2022.3.49f1:
  Aegis (atuendo de ladrón fantasma) + wonder (uniforme), 168 frames @30fps = 5,6 s.
- Salida: `media/cinematics_capture/scene_aegis_wonder/f_*.png` + `scene_v7.mp4`
  (copia: `media/p5x_animacion_aegis_wonder.mp4`).
- Log del render: `media/cinematics_capture/scene_aegis_wonder/log.txt`
  (dice, por cada malla, qué textura se vinculó o por qué no).

## Script de captura (IMPORTANTE)
`unity_projects/scene_full/ExportedProject/Assets/Editor/P5XSceneCapture.cs`
**Copia buena en `_dl/editor_good/`** — restaurarla si se re-exporta:
AssetRipper **borra `Assets/Editor/`** en cada export y el respaldo viejo
(`_dl/editor_backup/`) es la versión SIN parches. Copiar SIEMPRE desde `_dl/editor_good/`.

## Bugs resueltos (no volver a tropezar)
1. El bundle de partes correcto depende del **clip**, no del personaje:
   clip `PC063_thief@stand_story` ⇒ partes en `part_63_thief` (cabeza/pelo/cara ahí).
2. Las mallas se resuelven por **`mHighMeshName`** (el `mMesh` viene `{fileID: 0}`).
3. La lista de huesos del manifiesto viene **indentada** ⇒ regex `^\s*-\s*(.+?)\s*$`.
4. Materiales: shader y texturas apuntan a GUID placeholder `0000000deadbeef…`.
   Las texturas reales sí están en `Assets/Texture2D` ⇒ re-vincular por nombre
   (`PickTexture`: palabras del token, prefiere `_bc`, ignora `LOD1`).
5. Cámara: los actores miran a **+z** ⇒ cámara en +z; y la luz debe ir **alineada
   con la cámara** o salen siluetas negras.
6. AssetRipper puede ignorar `CreateSubfolder=false` y exportar **anidado**
   (`ExportedProject/ExportedProject/…`) ⇒ mover a la raíz con `cp -r …/Assets/. Assets/`.

## Pendiente para mañana
- Texturas de **wonder**: solo se vinculó la cara (`wonder_uniform_face_scar01_bc`).
  El cuerpo de wonder solo existe como variante `scar01` (bundle
  `role_other_orm_maya15356304.bundle`); su `_bc` "normal" no está en el escenario.
  Buscar el bundle que lo tenga y añadirlo a `_dl/scene_full` + re-export.
- Aegis quedó **completa** (cuerpo, cara, pelo, adorno) con las texturas UI de
  `role_other_thief_ui36c2b5cd.bundle`.
- Verificar el MP4 final con visión (¿colores reales, cara visible, sin deformaciones?).
- Publicar el cierre en el subforo `restauracion-en-unity` de Discord
  (`discord/_post_unity_update.py` sirve de plantilla).

## Comando de render (repetible)
```
"/c/Users/Lukas/Unity/2022.3.49f1/Editor/Unity.exe" -batchmode -quit \
  -projectPath "C:/Users/Lukas/p5x-datamining/unity_projects/scene_full/ExportedProject" \
  -executeMethod P5XSceneCapture.Run \
  -logFile "C:/Users/Lukas/p5x-datamining/_dl/scene_run.log"
```
Tarda ~4-5 min (o ~10 si Unity tiene que reimportar assets nuevos).

## Discord (ya montado y verificado)
- Servidor `1382155606932328582`, categoría P5X DATAMINING + 7 canales + 7 subforos.
- Vigilante `discord/check_updates.py --quiet` + cron `p5x-tool-updates` (10am, deliver a #general).
- Subforo `restauracion-en-unity` = `1552916824352628736`.

---

# KOTONE SHIOMI (PC079) — hallazgos 2026-09-25 (tarde)

## Dónde aparece
**1. Cinemáticas pre-renderizadas (evento P3P), ya extraídas:**
- `media/videos_mp4/CG_P3P_Event_Main_05_3_movie.mp4` (48,5 s, 2400x1080) — Kotone confirmada
  a resolución completa (t=21 s: primer plano de su cara, lazo rojo, brazalete S.E.E.S.).
- `media/videos_mp4/CG_P3P_Event_Main_01_3_movie.mp4` (17,5 s) — aparece de espaldas.
- Pistas de audio que confirman su presencia en el evento:
  `ch_CLB_Event_P3P_PC079.acb`, `..._PC079_2.acb`, `..._PC079_epilogue.acb`.
- Ojo: Kotone lleva **lazo** rojo (Makoto lleva corbata) y su arma es **qiang/lanza**
  (el part bundle trae `PC079_01_qiang`, `qiangtao`, `gun_02`, `weapon_02..05`).

**2. Escenas 3D in-game (timelines) — índices generados:**
- `_dl/pc079_timelines.json` — **58 timelines** referencian PC079 (41 de historia).
- `_dl/pc079_clips.json` — **8 packs** con clips suyos; TODOS sus clips de historia están
  en `anim_story3e4b7414.bundle` (80 clips: walk/sit/yawn/talk/jiayou/zheyan/think/roubing_eat…).
- Campaña del evento P3P: `tl_ue_00_01` … `tl_ue_05_04` (prólogo lateral, 12 escenas) +
  `tl_e_02_1` (epílogo). Los GameObject delatan el nombre real:
  p.ej. `TL_P3P_Event_side_prologue_04_04`, `TL_P3P_Event_epilogue_02_1_2`.

## Escena renderizada (v1)
`TL_P3P_Event_side_prologue_04_04` — **Actor 0 = Kotone (PC079_01) + wonder_uniform**.
(El timeline también usa PC063_thief y wonder_thief: Actor 1 y Actor 3.)
- Proyecto Unity: `unity_projects/kotone/ExportedProject` (export de `_dl/kotone_stage`, 3,3 GB).
- Capturador: `Assets/Editor/P5XKotoneCapture.cs` (`P5XKotoneCapture.Run`).
- Clips: Kotone `PC079_01@walk_loop_story` + wonder `wonder_uniform@walk`, 8 s @30fps.
- Salida: `media/cinematics_capture/scene_p3p_kotone/` + `media/p5x_escena_kotone_p3p.mp4`.
- Resultado: **Kotone 11 partes / wonder 13, 0 omitidas**; texturas de ojos, cara y armas OK.

## Trampas nuevas
- **AssetRipper se cae solo** (el server deja de responder, curl → `000`). Relanzar con:
  `tools/AssetRipper13/AssetRipper.GUI.Free.exe --headless --port 57973`
  (AssetRipper **13** es el que exporta bien; el de `tools/AssetRipper/` no).
- El export a veces crea **carpeta anidada** `…/ExportedProject/ExportedProject/Assets`:
  entonces `cp -r ExportedProject/Assets/. Assets/` y se borra la anidada.
- `scripts/choreography.py` devuelve `[]` en estas escenas: los tracks quedan como assets
  sueltos. Usar `scripts/map_p3p_scene.py` (ActionGroup → PlayAnimationAction → clip) y
  `m_FixedDuration` del `.playable` para la duración real (aquí 51,67 s).

## Pendientes de Kotone
- Escenas más expresivas por renderizar: `tl_ue_00_04` (jiayou/zheyan: anima y guiña el ojo
  mientras wonder pelea), `tl_n_01_3` (chayao, manos en la cadera + walk),
  `tl_e_02_1` (sentada + bostezo).
- Texturas de cuerpo de wonder siguen en `scar01` (falta el `_bc` normal), y a Kotone le
  falta `PC079_01_eyelid` (solo eso).
- Honrar los tiempos reales del timeline requeriría resolver los `m_Tracks` (fileID sin guid).

---

# FASE 12 — Escenario de fondo en la escena de Kotone (2026-09-25 tarde-noche)

## Hecho
Escena `TL_P3P_Event_side_prologue_04_04` renderizada **con el escenario real de Iwatodai detrás**:
Kotone (`PC079_01@woshou_frost_story`) + wonder (`wonder_uniform@stand_01`), 180 frames @30fps = 6 s.
- Salida: `media/cinematics_capture/scene_p3p_kotone_bg/` + **`media/p5x_kotone_con_escenario.mp4`**.
- Fondo visible: pasarela elevada con barandillas, vigas y soportes triangulares blancos, muros azules.
- Capturador actualizado: `Assets/Editor/P5XKotoneCapture.cs` (copia en `_dl/editor_good/`).

## Cómo se resolvió (4 trampas, todas nuevas)
1. **`scn_1_p3p_*` no sirven**: son mallas de colisión (0 MB). El escenario visual es
   `scn_iwai_wyc718eb6dc.bundle` (42 MB) → AssetRipper lo exporta como **escena Unity**
   `ysc_tianshouge_shiwai_wyc.unity` (no como prefab). Se inyecta copiando
   `unity_projects/_scene_iwai/ExportedProject/Assets/.` → `unity_projects/kotone/ExportedProject/Assets/`.
2. **El `walksurface` es un marcador de zona, no el suelo**: su Y (97,4) está ~4 m por debajo
   de la calle y los actores quedaban flotando. El nivel de calle se deduce de la **mediana de
   las bases de los muros** (`bounds.min.y` de renderers con alto > 4 m) = **101,69**.
   Con el *mínimo* sale mal: la base de la torre baja a 78.
3. **La escena exportada pierde el shader de TODOS sus materiales** (GUID placeholder →
   magenta). Se recorre `FindObjectsOfType<Renderer>` y se sustituye el material por Standard
   conservando `mainTexture`: **63 de 63 renderers** estaban rotos.
4. **`SampleAnimation` anima también la RAÍZ del actor**: si el clip trae curvas de raíz, el
   personaje se va lejísimos (wonder acabó a **228 unidades** de la cámara y parecía no existir:
   13/13 renderers "visibles" pero fuera de encuadre). Se vuelve a fijar `position`/`rotation`
   del actor **en cada frame** tras samplear.
- El suelo del nivel **no viaja en este bundle** (las superficies caminables no traen malla
  visible) → se añade una plataforma propia a la altura de la calle. Con eso no flotan.

## Pendientes de esta fase
- Localizar el suelo/calle real del nivel (buscar otro bundle `scn_*` con la malla del suelo).
- Tercer actor del apretón: `frost_normal` (clip `frost_normal@woshou_pc079_*`). En los bundles
  `frost` solo hay actores pequeños tipo Jack Frost (`role_ackfrost`, `role_ingfrost`, huesos
  `b frostNN`) — el `frost_normal` sigue sin localizar.
- El `Player.log` avisa de "Main Camera" de la escena a **y=117** (vista de editor, inservible).

# D — CARA Y DETALLE (2026-09-25, 22:00)

## Hallazgo que reencuadra la fase
De los **724 `.anim` del proyecto, NINGUNO tiene curvas de blendshape**. La cara NO se anima
desde los clips de historia (`stand_story`, etc. solo mueven huesos): la animación facial va por
otro sistema en runtime que no tenemos. Conclusión: D no se ataca por animación facial.

## La palanca real: los materiales
AssetRipper deja muchos slots de textura apuntando a un guid que **no es una textura** (el del
propio shader o el placeholder `0000000deadbeef…`). Efecto: material plano, sin contorno propio,
sin sombra, sin darkcolor y — en la cara — **sin `_FaceShadowTex`**, que es el mapa SDF con el
que el shader hace el sombreado cel del rostro.

Script: `Assets/Editor/P5XFixTextures.cs` (`P5XFixTextures.Run`), rellena por API.

## TRAMPA GRANDE: el emparejamiento laxo empeora el render
Una primera versión emparejaba por "familia + marca de la propiedad" y asignó **437 texturas**,
muchas absurdas a ojo (el color base como *normal map*, el SDF facial como *metallic*, un `_e` de
arma como emisión del cuerpo). Eso **empeora** el render: no es "rellenar huecos".
Reglas que sí funcionan (versión estricta, idempotente):
1. El sufijo de la propiedad tiene que ser el **último token** del nombre (`_bc`, `_nm`, `_stroke`,
   `_shadow`, `_darkcolor`, `_pk`, `_mask01`, `_s`, `_e`), o el penúltimo si lleva `_0`.
2. La parte del material (face/hair/body/eye/eyelid/…) se busca por **subcadena**, no por token
   exacto: los materiales llevan variantes (`PC079_01_body01`, `PC079_01_body_lodlow`) que el
   token exacto no captura, y sin eso colaban texturas de OTRAS partes.
3. `_FaceShadowTex` solo en materiales de cara, y aceptando el nombre real del SDF
   (`wonder_unifom_face_f02_maya` — sí, con la errata "unifom" — lleva `face` y `f0`).
4. Si no hay coincidencia estricta: **null**. Mejor vacío que una textura falsa.
Resultado de la pasada estricta: **105 puestas / 201 quitadas** en 84 materiales.

## Estado verificado de los dos actores (leyendo los `.mat` en disco)
- **Kotone (PC079) completa**: face (bc/shadow/darkcolor + `_FaceShadowTex=PC079_01_face_f`),
  body01 (bc/lodlow_nm/stroke/shadow/darkcolor/pk/mask01), hair (bc/stroke/shadow/s), eye
  (bc + `_EyeDiffuseTex`). Solo falta su textura de **eyelid** (no está en el proyecto).
- **wonder**: recuperado el **SDF facial** (`_FaceShadowTex` apuntaba al shader; ahora
  `wonder_unifom_face_f02_maya`) y su material de **piel, que no tenía textura base**. Nuevo
  `_BumpMap` de cuerpo.

## Gate (24 frames que barren los 52 s) — OK
`GATE_D2_EXIT 0`: 0,000 % magenta en los 24; curva de brillo intacta (0 → 94 → 108 → 113 → 161 →
255). `vision_analyze`: la cara de Kotone en CM003 tiene rasgos definidos (ojos tras las gafas,
cejas, boca), pelo y uniforme con textura; wonder con ropa sombreada. Nada roto.

## Texturas que siguen faltando (con la prueba de que no están)
`PC079_01_eyelid` · `wonder_uniform_{eye,eyelid,cheekred,hair,bottom,shoes}`.
- `grep -a` sobre los 16.535 bundles del cliente: "PC079_01_eyelid" **no aparece en ninguno**.
- `part_s_port_rig*` (34 bundles, 136 MB) contiene **solo mallas**: p. ej. el bundle
  `037/part_s_port_rig6f15ec8c.bundle` tiene 10 objetos y son `Mesh`/`GameObject` de
  `wonder_uniform_shoes` — ninguna textura. (Ojo: un `grep` por "wonder_uniform_shoes" da
  falso positivo porque casa con el nombre de la MALLA.)
- Aviso metodológico: el `grep` sobre bundles comprimidos (LZ4/LZMA) **no ve** las cadenas, así
  que "no aparece" solo es concluyente para los que están sin comprimir.

## Pendiente de D
- `P5XFixTextures` corre a mano; conviene encadenarlo antes del render (ya está en el flujo).
- Si algún día aparece un bundle con las texturas de `wonder_uniform_*`, soltarlas en
  `Assets/Texture2D/` y re-ejecutar `P5XFixTextures.Run` (es idempotente).

# ESTADO AL CIERRE DEL DÍA — 2026-09-25 22:15 (seguimos mañana)

## Entregable final del día
`media/p5x_kotone_timeline_52s_v2.mp4` — **los 52,77 s completos, con los materiales arreglados**.
- h264 **1280×720**, **1583 frames**, 52,77 s, **AAC** (BGM `BGM_P3R_TheVoiceSomeoneCalls` +
  5 SFX: pasos de suela t=26,13 / 39,50 / 42,57, botas t=39,80, `SFX_FlashWhite_Short_01` t=48,00).
- Medición del render: **0,000 % magenta**, brillo 0→94 (CM001) →108 (CM002) →113 (CM003) →
  255 (fundido blanco); frame más brillante `f_1560` = t=52,00 ✓.
- Se conserva la versión anterior (materiales sin arreglar) como `media/p5x_kotone_timeline_52s.mp4`
  para comparar.
- Verificado además con `vision_analyze` en CM003: rostro con ojos/cejas/boca, uniforme y pelo con
  textura, nada roto. Lo único plano que queda es el **suelo** (el nivel real no viaja en el bundle).

## Renders y scripts de hoy
| Qué | Dónde |
|---|---|
| Render final (1584 PNG) | `media/cinematics_capture/scene_p3p_kotone_bg/` |
| Log del render | `_dl/d_full.log` |
| MP4 con audio | `media/p5x_kotone_timeline_52s_v2.mp4` |
| Reparador de materiales (Editor) | `Assets/Editor/P5XFixTextures.cs` → `P5XFixTextures.Run` |
| Rescate de texturas (cliente→proyecto) | `scripts/rescue_textures.py`, `scripts/extract_parts.py` |
| Escáner de escenas por posición | `scripts/scan_tartarus.py` |

## E — en curso, RESUMIBLE (aquí se retoma mañana)
`python scripts/scan_tartarus.py` (añadir `--resumen` para ver el estado sin escanear nada).
**Barrido 610 de 1598 `scn_*`, 39 candidatos.** El estado vive en `_dl/tartarus_scan.json` y el
script salta lo ya escaneado, así que basta con relanzarlo tal cual.

Criterio (F3-bis): buscar por **posición**, no por nombre — "Tartaros" sale como nombre de FX en
media base y engaña. El evento vive en x≈279,7 / z≈284,3 y la cámara a **y≈101,7**.

Candidatos a mirar mañana primero (por cercanía y por altura de suelo):
- `scn_oulang1l203bd491` → x=241,4 **y=102,3** z=284,2 · 1 transform (`Area Light`, `RP_11`, `Spot Light`)
- `scn__juexing24a0923` → x=281,2 y=110,5 z=285,1 · **503 transforms** (el más poblado cerca del punto)
- `scn_2_dating2bd999a7` → x=278,5 y=99,1 z=268,9 · 33
- `scn_ng_youce3e39b24c` → x=263,2 y=106,2 z=280,0 · 3
- `scn_01_10_01bdeff44` → x=293,3 y=100,2 z=297,8 · 17
- `scn__01_a_01b1370ce` → x=281,7 y=113,7 z=282,4 · **4, con `walksurface` y `terrain`** (el suelo del nivel, que es justo lo que falta)
Ninguno lleva "Tartaros" en el nombre → hay que decidir por geometría/altura, no por nombre.

## D — cerrado (con una limitación conocida)
Ver la sección "D — CARA Y DETALLE" de arriba. Resumen: la cara **no** se anima desde los clips
(0 de 724 `.anim` con blendshapes), la mejora real vino de los **materiales** (SDF facial de wonder
recuperado, piel de wonder sin textura base, Kotone completa) y quedan 7 texturas que **no están**
en los bundles que tenemos (`PC079_01_eyelid` + `wonder_uniform_{eye,eyelid,cheekred,hair,bottom,shoes}`).

## Cómo se retoma (comandos exactos)
```bash
# 1) seguir el barrido de escenas (resumible, ~90 min para las 1598)
cd /c/Users/Lukas/p5x-datamining && tools/env/Scripts/python.exe scripts/scan_tartarus.py

# 2) ver el estado del barrido sin escanear
tools/env/Scripts/python.exe scripts/scan_tartarus.py --resumen

# 3) re-render completo del timeline (si se tocan materiales/escena)
cd unity_projects/kotone/ExportedProject
"/c/Users/Lukas/Unity/2022.3.49f1/Editor/Unity.exe" -batchmode -quit -projectPath \
  "C:/Users/Lukas/p5x-datamining/unity_projects/kotone/ExportedProject" \
  -executeMethod P5XKotoneCapture.Run -logFile "C:/Users/Lukas/p5x-datamining/_dl/d_full.log"

# 4) montar el MP4 con audio
cd /c/Users/Lukas/p5x-datamining
tools/env/Scripts/python.exe scripts/mux_audio.py \
  media/cinematics_capture/scene_p3p_kotone_bg media/p5x_kotone_timeline_52s_v2.mp4
```

## Notas de entorno
- Antes de renderizar, y si se tocan materiales: `P5XFixTextures.Run` (es idempotente).
- **Ningún proceso quedó en vuelo** al cerrar (Unity, escáner y mux terminados o parados a mano).
- Disco C: **98 GB libres**. El stage del escáner (`_dl/scn_stage/`) se limpia solo en cada vuelta.
- `skill_manage` sigue rechazando `p5x-datamining` (es del usuario) → las lecciones van aquí.

# MODO MANUAL EN UNITY (2026-09-27) — qué carga hoy y qué no

Documento aparte: **`MANUAL.md`** (inventario completo + flujo de trabajo a mano). Resumen de lo
hecho y de lo aprendido, que es lo que no conviene volver a descubrir:

- **Menús nuevos en `P5X/`** (en `P5XKotoneCapture.cs`): `modo manual: montar actores en la escena
  abierta`, `modo manual: abrir la escena manual`, `modo manual: capturar la vista de la camara a
  PNG`. Salida: `Assets/Scenes/Manual_Kotone_Wonder.unity` + `MAN_<actor>.controller` por actor.
- Los **prefabs de personaje son solo esqueleto** (0 `SkinnedMeshRenderer`; AssetRipper tira los
  renderers porque los scripts de MUActor quedan stubs). La malla se construye leyendo el manifiesto
  `*_wholeexport_rig.prefab`. Verificado: Kotone **11 partes**, wonder **13**.
- **El escenario trae su propia `Main Camera` (etiqueta MainCamera).** Con dos etiquetadas,
  `Camera.main` y la Game view eligen la del escenario ⇒ se ve la arquitectura y **los personajes
  quedan fuera de cuadro**, aunque la escena esté perfecta. El menú de montaje **desactiva la cámara
  del escenario** y el de captura busca `cam_manual` **por nombre**. No fiarse de `Camera.main`.
- **El arreglo de materiales del escenario (34 de 63 refs rotas → magenta) solo vivía en memoria
  dentro del capturador**: al abrir la escena a mano salía magenta (medido 1,612 %). Extraído a
  `ArreglaMaterialesEscena(Action<string> L)`, que ahora usan el capturador y el modo manual.
  Medición tras el arreglo: **0,000 %**.
- La cámara por defecto de la escena manual usa `T_MANUAL = 25,5f` + `EvalToma` (encuadre real del
  timeline, `anclaSuelo = ANCLA_MANUAL`).
- **Lección de método (otra vez): la visión sola no basta.** La visión dijo "no hay personajes" dos
  veces cuando el problema real era (a) materiales magenta y (b) la cámara equivocada; y describió a
  wonder como "estructura arquitectónica". Lo que resolvió el caso fue **medir píxeles** (magenta,
  mostaza) y **proyectar la posición del actor a píxeles** para saber dónde mirar.

# ANÁLISIS DE COMPLETITUD DE VÍDEOS — 2026-09-26 08:50 (¿tenemos TODOS los USM?)

Pregunta del usuario: comprobar si hay más USM dentro de los ficheros y si los tenemos todos.

## Inventario (medido)
- **352 `.usm` en todo el cliente**: 347 en `OuterPackage/Media/Windows` + **5 en `bin/Media/Windows`**.
  3,85 GB en total · mediana 6,8 MB · mínimo 3 KB · máximo 99,9 MB (VP9 / Sofdec Prime).
- La carpeta `bin/Media/Windows` **no la miraba el pipeline** (`extract_all_usm.py` por defecto solo
  recorre `OuterPackage/Media/Windows`) ⇒ ahí estaban 5 vídeos nunca extraídos.
- **Extraídos ahora: 351 MP4** (antes 346). Los 5 recuperados son `REMAIN-CG1`, `REMAIN-cg1_1..4`
  (VP9 **2340×1080**, 2–8,5 s). `REMAIN-CG1` es nada menos que la **pantalla del logo de SEGA**
  (verificado con `vision_analyze` sobre un fotograma).

## El único USM sin MP4 es un marcador, no un vídeo
`CG_yugao_2_1.usm` = **3072 bytes**. Cabecera válida (`CRID` + bloque `@UTF`) pero **sin carga de
vídeo**: wannacri produce un `.ivf` de **0 bytes** y devuelve `ERROR: Please run probe`.
Para comparar: el resto de la familia son `CG_yugao_1_2/1_3/1_4` de **5–16 MB**. Es un hueco de
catálogo, no un fallo de extracción. (Total: 352 ficheros, 351 vídeos reales, 1 marcador.)

## No hay vídeos escondidos en los contenedores
1. **Contenido empaquetado**: el índice `bin/_vfileIndexV2.fb` (que describe `_vfileContent0`,
   838 MB) lista **312 `.bundle`, 100 `.bytes` de Lua, 5 `.txt`, 1 `.json` — CERO `.usm`**.
2. **Bundles y `.acb`**: un `grep -a "CRID"` marca ~25 ficheros, pero **son falsos positivos**: la
   firma de un USM real es `CRID` seguido de `@UTF` en los 64 bytes siguientes (en los USM del juego
   `@UTF` está en el offset 0x20). Comprobado uno a uno: detrás hay bytes aleatorios ⇒ **0 vídeos
   embebidos**. Script: `scripts/scan_embedded_usm.py` — recorrido COMPLETO de los 85 GB del
   cliente: **20.311 ficheros, 212 s, 0 coincidencias con firma real**; solo 27 ficheros con un
   "CRID" suelto (todos falsos positivos). Informe en `_dl/embedded_usm.json`.

## Auditoría de integridad de los MP4 (`scripts/audit_videos.py`)
351 auditados con `ffprobe`: **todos abren, tienen pista de vídeo y duración > 0**. Cinco salían
marcados solo por *tamaño* bajo respecto al USM (`ui_tuitu01_1_back_001`, `ui_tuitu01_3_back_001`,
`ui_tuitu01_3_back_revert_001`, `wonder_jump_3`, …). Verificado que **no es corrupción**:
- `ui_tuitu01_*` tienen imagen real (desviación 64–79, ~3.000 colores).
- `wonder_jump_1/2/3` son **un elemento pequeño sobre fondo negro** (brillo ~0,5 · desviación ~10) —
  las tres por igual, incluidas las dos que la auditoría NO marcó ⇒ es un efecto con canal alfa que
  el MP4 no conserva, no un fichero roto.

## Lo que el juego espera vs lo que hay
De la config y el Lua volcados (`ConfDataDefault.bytes`, `ConfDataText.bytes` + 9 Lua) salen **20
nombres de `.usm` citados**; 18 están en disco. Los 2 que no:
- **`cg_01_dilao_juexingdonghua.usm`** (la cinemática de despertar) — **no existe en el cliente**.
  Es la única referencia real a un vídeo ausente. Candidato a descarga bajo demanda.
- `t_.usm` — parece una plantilla de formato, no un fichero.

## Lectura de conjunto
Tenemos **todo lo que el cliente instalado trae** (352/352 ficheros; 351 vídeos reales) y **nada
queda escondido** en el contenido empaquetado ni en los bundles. Pero la carpeta `Media` local
**no es el catálogo completo de producción**: hay huecos de numeración (`CG_yugao` tiene 1_2…1_4
pero no 1_1; `2_1` es un marcador; las familias `CG_zx_Event_0x` tienen índices salteados) y una
cinemática citada por el propio Lua sin fichero. **Aviso**: el análisis de huecos agrupa por los
últimos dígitos del nombre y colapsa los que tienen 3 componentes numéricos ⇒ es un **indicio**,
no una prueba. Para el set completo habría que ir al manifiesto del CDN/hotfix, que no está en disco.

## Scripts nuevos de este análisis
- `scripts/audit_videos.py` — cruza USM↔MP4 y valida cada MP4 con ffprobe (abre, duración, pista de
  vídeo, ratio de tamaño). Informe en `_dl/audit_videos.json`.
- `scripts/scan_embedded_usm.py` — busca USM embebidos por firma real (`CRID`+`@UTF`), no por
  subcadena. Informe en `_dl/embedded_usm.json`.

## Arreglado en la fuente (`scripts/extract_all_usm.py`)
- El defecto ahora cubre **las dos** carpetas de Media (antes solo `OuterPackage`), y acepta varias
  separadas por `;`. Verificado: con cero argumentos informa `347 + 5 = 352`.
- Guarda nueva: un USM de menos de **8 KB** se reporta como `STUB-sin-video` sin llamar a WannaCRI
  (es un marcador de catálogo, no un fallo) — antes generaba un `.ivf` de 0 bytes.
- El `.ivf` de respaldo solo se copia a la salida si pesa > 1 KB (antes dejaba ficheros vacíos).
- Prueba real tras el arreglo: `351 skip + 1 STUB CG_yugao_2_1 (3072 bytes)`, **0 restos** en
  `media/videos_mp4/` y **351 MP4**.

## Exportar el modelo a glTF y verlo en Blender: trampas que costaron tiempo (28-sep)

- **Los morph targets de un glTF tienen que declarar sus accesores como `VEC3`.** Si se declaran
  `SCALAR`, Blender aborta la importación entera (`all the input array dimensions except for the
  concatenation axis must match exactly ... index 0 has size 3 and the array at index 1 has size 1`)
  y **cualquier medición posterior se hace sobre una escena a medias**, así que se sacan conclusiones
  falsas (aquí: "la piel está rota, se desvía 1,4 m"). Señal de alarma clara: dos ejecuciones dan
  resultados **idénticos hasta el decimal** — imposible si el fichero de verdad ha cambiado.
- **Los nodos de malla con piel tienen que colgar del nodo raíz del esqueleto.** Si quedan como
  raíces sueltas de la escena, Blender los mete en la colección `Orphan Nodes`, que **no está en la
  escena**, y el modelo no se renderiza (sale el fondo vacío). `visible_get()` en modo background
  devuelve `False` para todo, así que no vale como aviso: hay que medir los píxeles del render.
- **Con una restricción `TRACK_TO` en la cámara hay que mover TAMBIÉN el objeto blanco.**
  `rotation_euler` se ignora y la cámara se queda mirando al origen, con lo que la figura sale
  desplazada ~0,8 m (justo el centro del modelo) y cortada por arriba. Lo robusto es **cámara
  ortográfica** (`ortho_scale` = alto a cubrir): el encuadre no depende del sensor ni del FOV.
- **Al medir un render, hay que enmascarar la figura.** Contar "piel" u "oscuro" sobre la imagen
  entera mezcla el fondo: un fondo oscuro se cuenta como pelo y los porcentajes no significan nada.
- **`vision_analyze` se equivocó 3 veces seguidas en esta tarea** (dijo "cara blanca y sin textura"
  cuando la medición daba **7.069 colores distintos** frente a 1.654 del render anterior, y "máscara
  negra en la nariz" cuando el negro era el **1,5 %** de los píxeles). Sirve para orientarse, nunca
  como juez: confirmar con conteo de píxeles o con el dato estructural (materiales e imágenes del GLB).
- Los **GLB por pieza** se rehacen con `build_kotone_glb.py <clave>` (claves: `cuerpo`, `cara`,
  `ojo`, `parpado`, `pelo`): conserva el esqueleto completo (329 huesos) y solo cambia qué mallas se
  escriben. La herencia de material del párpado va **por nombre de material**, no por nombre de pieza
  (`mats_por_nombre` está indexado por nombre de material y ahí estuvo el cruce que la rompía).
- Los **renders** de comprobación: `scripts/blender_render_modelo.py <glb> <carpeta> [oscuro]`
  (fondo oscuro = mismo aspecto que los renders antiguos del paquete, para poder compararlos).
- **Bobinado de triángulos (lo que se vio "con las texturas por dentro"):** si las caras están al
  revés de las normales, en la vista **Sólido** de Blender no se aprecia nada raro (no descarta caras
  traseras) pero en **Material Preview** el modelo se ve del revés y la cara parece un hueco negro.
  Medirlo así, sin depender de la vista:
  `dot(cross(v1-v0, v2-v0), media de las normales de los 3 vértices) > 0` debe cumplirse en ~100% de
  las caras (antes: **0%**, después: **100%**). Ojo: la conversión de ejes de este proyecto tiene
  determinante **+1**, así que **no hay que invertir el bobinado**; solo una conversión espejo
  (determinante −1) lo exige. Al invertirlo "por si acaso" el modelo entero sale del revés.
- **Orientación del frente:** el modelo del juego viene mirando a **−Z** (comprobado: la malla de la
  cara y la de los ojos están en −Z, el pelo en +Z). El estándar glTF espera el frente en **+Z**, así
  que sin tocarlo el personaje se ve **de espaldas en la vista frontal de Blender** (mira a +Y). Se
  corrige con un giro de 180° sobre Y en el nodo raíz `PC079_01_raiz` (así lo lleva el paquete). La
  forma rápida de comprobarlo: tras importar, medir el centro de la malla de la cara (debe estar en
  −Y) o mirar el modelo desde la vista frontal.
- Las **normales del OBJ** iban con otro mapeo que las posiciones (signo Z cambiado), así que no había
  forma de que el bobinado cuadrara: se regeneraron los 10 OBJ desde `_dl/kotone_dump/` con las mismas
  transformaciones ya verificadas del GLB (`scripts` de esta sesión, T = (x,y,z)→(−x, z, y), V del UV
  volteada, sin invertir caras). Ahora los OBJ se generan **desde el propio GLB** con
  `scripts/exportar_obj_desde_glb.py`, para que no se puedan desincronizar.

### Lecciones de la sesión del brazalete (28-sep, tarde)

- **Un giro de 180° sobre la vertical NO cambia de qué brazo es una pieza: solo cambia hacia dónde
  mira el personaje.** Girar el modelo entero nunca arregla "el brazalete está en el brazo que no
  es". Para mover una pieza de un brazo al otro hay que girar **la pieza** 180° sobre la vertical.
  Es un giro (determinante +1): el emblema sigue legible y el bobinado no cambia; un espejo sí
  obligaría a voltear caras.
- **La vertical del dato de este juego es Z, no Y.** El espacio del volcado es Z-arriba (cabeza en
  z 1,424, pelvis en 0,941). Un giro de 180° sobre Y "para girar sobre la vertical" deja la pieza
  **bajo el suelo** (se midió z = −1,255 con la piel ya aplicada) y cambia frente por espalda. La
  lección operativa: **comprobar la altura (z) después de cualquier giro**; en un render frontal la
  figura sigue pareciendo bien aunque la pieza esté en el suelo.
- **Antes de girar nada, medir si el modelo está espejado, con datos.** Dos comprobaciones que zanjan
  la duda: (a) posición media de los **vértices que gobierna un hueso concreto**, en el GLB y en el
  volcado del juego — si coinciden (aquí `Bip01 L Hand` → x = +0,520 en ambos), la malla y el skin
  son fieles; (b) en Blender, hueso contra vértices con peso > 0,4 — tienen que caer del mismo lado.
  **ERROR DE CONCLUSION QUE HUBO QUE CORREGIR (importante):** de ahí NO se sigue que el modelo no
  esté espejado. Lo que decide no es el determinante en abstracto, sino si la conversión **espeja o
  no**, y eso depende de la mano del espacio de ORIGEN. El del juego es **zurdo**; glTF/Blender es
  **diestro**; al leer un espacio zurdo y escribirlo en uno diestro, T = (x,y,z)→(−x, z, y) (det +1,
  un giro) produce el **espejo** del modelo. La conversión correcta es **(x,y,z)→(x, z, y)** (det −1,
  espejo) y, como un espejo sí invierte la orientación de las caras, el **bobinado hay que voltearlo**
  (`[:, [0,2,1]]`). Síntoma que lo delata sin discusión: **texto espejado en el modelo** (las letras
  S.E.E.S. de la banda se leían al revés) y accesorios en la extremidad contraria. Medir con
  `scripts/quiralidad.py` (signo de `det([izquierda, arriba, delante])`): giros lo conservan, espejos
  lo invierten.
- **Las piezas con rig propio no comparten huesos con el cuerpo** (el brazalete usa
  `xiuzhang_Bone002..005`, y ninguno de ellos aparece en la lista del cuerpo), así que su colocación
  es reconstruida, no leída. Se verifica comparando sus huesos con los del cuerpo **en el espacio del
  juego** (aquí: malla del brazalete en x −0,181, z 1,255; `UpperArm_L_02` en −0,198, 1,247).
- **Pendiente en las armas:** el material `PC079_01_qiang` (lanza) coge la textura del `qiangtao` por
  coincidencia de prefijo de nombre, y la pistola usa el material de relleno `Standard` sin textura.
  Hay que identificar cuál de los juegos `weapon_02..05` corresponde a cada arma. Ojo: la comparación
  con el sprite oficial mostró la **pistolera en la cadera contraria** a la del arte, así que cuando
  se arreglen las texturas hay que revisar también de qué lado van las armas (son piezas con rig
  propio, colocación reconstruida, igual que el brazalete).
- Antes de dar por bueno un lado/guión de una pieza: **comparar con el arte oficial, pero del
  personaje correcto**. En `_dl/sprite_completo.png` está el protagonista **masculino**, que no sirve
  para juzgar el uniforme de Kotone (el solapamiento del blazer es al revés entre uno y otro).
- **Shader toon en Blender: funciona** (ver `kotone_shiomi/LEEME.md` §12). `scripts/blender_toon.py`
  replica el cálculo del shader con nodos (corte duro en ColorRamp CONSTANTE sobre el N·L ya envuelto,
  tinte de sombra por material, rim con smoothstep a mano, contorno por Freestyle) y lee los valores
  afinados de cada `.mat` — el tercer argumento es la carpeta de materiales. Saca `media/toon_blender/`
  con 4 vistas + `kotone_toon.blend`, que lleva el grupo `P5X_Toon` para usarlo a mano. Ojo con tres
  cosas: el umbral va en la escala envuelta (0.55, no 0.10); hay que usar los tintes reales de cada
  material (el de por defecto deja todo plano); y el rim con rampa ancha difumina el corte.
- **Shader toon en Unity: funciona** (LEEME §11). Proyecto `unity_com/RipperProj/
  ExportedProject`, shader en `Assets/Shaders/P5XToon.shader`, y `P5XToonRender.BatchRender` saca 4
  vistas a `media/toon/`. Al migrar materiales hay que recorrer **todos** los renderers (no solo los
  `SkinnedMeshRenderer`) y contar píxeles **magenta** en el render: un renderer sin material sale
  magenta puro y se cuela sin que se note en el log. Pendiente ahí: la pistola lleva un material
  **provisional** (no hay textura `gun_02` en el proyecto) y la lanza usa la del `qiangtao`.


## 2026-09-29 — Exportacion a MMD (PMX) TERMINADA

`kotone_mmd/` tiene el paquete: `Kotone_Shiomi.pmx` (1,9 MB), `tex/` (9 texturas), 2 previews y
`LEEME-MMD.md`. Verificado reimportando con el propio `mmd_tools`: 334 huesos, nombres estandar MMD
(`センター`, `上半身`, `上半身2`, `首`, `頭`, `腕.L/R`, `ひじ.L/R`, `足.L/R`, `ひざ.L/R`, `足首.L/R`),
4 cadenas IK (`足ＩＫ.L/R` -> `ひざ` cadena 2; `つま先ＩＫ.L/R` -> `足首` cadena 1), 25 morphs con
nombres japoneses, 8 de 9 materiales con su textura, altura 20,00 unidades (el Miku oficial: 20,12),
y mover `足ＩＫ.L` desplaza la malla 1,25 unidades.

Tres trampas resueltas (documentadas en el skill `unity-game-datamining`,
`references/mmd-pmx-export.md`): el lado de los huesos MMD va **delante** (`左腕`, no `腕.左`);
las imagenes empaquetadas hay que **escribirlas a disco** o el PMX sale sin texturas; y el nodo de
textura debe llamarse **`mmd_base_tex`** o el exportador no lo ve.

Segunda trampa de medicion anotada: con una restriccion IK el resultado no esta en `rotation_euler`
(queda en 0) sino en la matriz visual — y no hay que medir "la primera malla de >1000 vertices"
(puede ser el pelo: da 0,000 y parece que el IK esta roto).

Pendientes de siempre: pistola sin textura de color, lanza con textura de vaina, sin fisicas
(pelo/falda/ropa rigidos), cara sin mapa SDF, y las zonas `REPINTAR_piel` para repintar a mano.


## 2026-09-29 — MMD crasheaba al cargar: causa encontrada y corregida

El PMX exportado hacia que MikuMikuDance se cayera (violacion de acceso 0xC0000005 en el desplazamiento
0xB03A7, dos intentos, siempre el mismo). Evidencia y causa:

1. Registro de eventos de Windows: fallo a 0xB03A7 en MikuMikuDance.exe x64 v9.32.
2. Desensamblado de la instruccion del fallo: `cmp dword ptr [rsi+0x10], 0` con `rsi` cargado desde la
   pila -> MMD desreferencia un puntero invalido al construir estructuras internas.
3. La funcion que contiene ese punto referencia las cadenas `表示･IK･外親`, `Disp/IK/OP` y `Facial`:
   es el codigo con el que MMD arma los **frames de pantalla**.

El PMX tenia **CERO frames de pantalla**: yo creaba el objeto raiz a mano, y el exportador escribe los
frames tal como esten en el objeto raiz. Se corrige creando la raiz con `Model.create` del propio
complemento (que llama a `initialDisplayFrames`) y rellenando Root (7 huesos), 表情 (24 morphs) e IK
(4 huesos). `validar_pmx.py` ahora lo comprueba y falla si no hay frames.

NO se pudo reproducir el cargado en MMD de forma automatica: MMD no lee la linea de comandos (ni
GetCommandLine ni argv, verificado con la ventana), no tiene opcion de "cargar modelo" en los menus
(el menu file solo tiene new/open/save/pose/motion/WAV), y el soltado entre procesos esta bloqueado
(PostMessage/SendMessage con WM_DROPFILES devuelven error 6 porque el sistema valida el handle del
soltado en el proceso que lo envia). La prueba tiene que hacerla el usuario.


## 2026-09-29 — "esas piernas no se ven naturales": causa medida y arreglada

Diagnostico (todo medido con la malla evaluada, no a ojo):

- El esqueleto del juego trae los `Bip01` como huesos gruesos de control, con las articulaciones mal
  puestas y las colas arbitrarias (0 de 109 huesos con la cola en la cabeza del hijo). Muslo 0,118 m,
  pantorrilla 0,510 m. La "rodilla" (`Bip01 L Calf`) estaba a z=0,911 = altura de cadera.
- Las articulaciones reales las marcan los auxiliares: `Thigh_L_01` (cadera, z=0,941), `Bone_xi_L`
  (rodilla, z=0,504), `Bone_zhou_L` (codo), `UpperArm_L_01` (hombro). La piel la llevan ellos.
- Alcance del IK viejo: 0,63 m para una pierna de 1,20 m => al mover el pie, la pierna se doblaba por
  la cadera y la malla se estiraba como una cinta (verificado en render).
- Aparte: el `.blend` de artistas estaba **roto desde antes**. `Bip01 Pelvis` tiene
  `COPY_LOCATION -> CTRL_Raiz` en modo absoluto y espacio mundo, y el control esta en el origen: al
  evaluar, la pelvis se iba al suelo y arrastraba el cuerpo **1,38 m**. Los pies y las manos tenian
  `COPY_ROTATION` tambien absolutas en mundo (0,26 m).

Arreglo: `scripts/arreglar_piernas.py` (nuevo, 250 lineas)
1. cabezas de las cadenas estandar -> articulaciones de los auxiliares (cadera, rodilla, hombro, codo)
2. colas encadenadas (cada cola en la cabeza del hijo), brazos incluidos
3. piernas colgando de `Bip01 Pelvis` en vez de la columna
4. roll alineado para flexionar sobre el X local
5. limite de IK en rodillas con el signo MEDIDO (girar +20 grados y ver si el tobillo va atras)
6. controles de IK reubicados en la punta de su cadena
7. copias de posicion/rotacion pasadas a relativas y a espacio LOCAL

Resultados verificados:
- desvio de la malla en reposo: 1,38 m -> **0,000025 m** (blend de artistas) y 0,000001 m (fuente PMX)
- controles reales: rodilla z=0,50-0,62 en todas las posturas, muneca sube 0,45 m, piel rota 0,4%
- PMX reimportado: `ひざ` a z=6,10 de 20 unidades (30% = rodilla; antes 18,2 = cadera), `足` a 11,40
  (57% = cadera), y moviendo `足ＩＫ.R` el doblez mide **68,5 grados** por la rodilla
- validador estricto del PMX: SIN FALLOS (3 frames, 334 huesos, 4 IK, 24 morphs, todos los bytes)
- GLB comprobado: 1,652 m de alto, 1,20 de ancho -> sano, no se horneo deformado

Archivos actualizados: `kotone_artista/Kotone_Shiomi.blend` (reemplazado; respaldo del roto en
`_dl/Kotone_Shiomi_ROTO_respaldo.blend`), `kotone_mmd/` (PMX + tex + 3 previews + LEEME-MMD.md reescrito),
`kotone_mmd_sin_ik/`, `LEEME-artistas.md` (seccion nueva).

Scripts nuevos: `arreglar_piernas.py`, `probar_controles.py`, `probar_piernas_ik.py`,
`medir_pmx_rodilla.py`, `preview_rodilla_pmx.py`. `arreglar_esqueleto.py` quedo obsoleto (regla de
"hijo mas lejano" equivocada: elegia `Thigh_L_02` y daba muslos de 0,60 m); usar `arreglar_piernas.py`.

Pendiente: que el usuario pruebe el **PMX nuevo en MMD** (el crash anterior fue por los 0 frames de
pantalla; ahora lleva 3 y pasa el validador, pero MMD no se puede automatizar en esta maquina).

## 2026-09-29 — Tutorial de extraccion publicado en Discord

Canal nuevo **`#tutorial-extraccion-3d`** (id `1554607979989434443`, categoria P5X DATAMINING):
19 mensajes + 5 imagenes + el `.md` adjunto (verificado leyendo el canal de vuelta).
Documento fuente: `tutorial_extraccion_3d/TUTORIAL.md` (33.861 chars). Imagenes generadas con
`scripts/generar_imagenes_tutorial.py` (PIL; diagramas medidos, no ilustraciones inventadas).
Republicar/actualizar: `discord/post_tutorial.py` (borra lo suyo y reescribe) o
`discord/republish.py tutorial-extraccion-3d`.

Cubre el recorrido juego -> contenedor -> bundles -> AssetStudio -> Unity -> FBX/Blender, con las
dos vias (comunidad y artesanal) y las 10 trampas. **NO incluye MMD ni Source** (a peticion del
usuario: son pasos irrelevantes para ese tutorial).

Paquete portable de herramientas en `tutorial_extraccion_3d/herramientas/`: `propias/` (scripts
portados, sin rutas absolutas), `unity/` (los `.cs` de Editor + el shader toon), `terceros/`
(enlaces con version + descargador automatico), `referencia/` (el escritor de GLB completo).

### Herramientas del tutorial: portabilidad hecha y verificada (2026-09-29)

`tutorial_extraccion_3d/herramientas/` (27 ficheros, 481 KB): `propias/` (11 scripts, `--help` OK en
los 11, sin rutas absolutas), `unity/` (5 `.cs` + shader), `terceros/` (URLs con version + descargador
automatico), `referencia/` (el escritor de GLB completo).

- Los tres `.cs` que llevaban rutas fijas (`P5XExportKotone`, `P5XFixRig`, `P5XApplyToon`) ahora deducen
  el proyecto de `Application.dataPath`, con variables `P5X_PROJ/P5X_DUMP/P5X_OUT/P5X_LOG` para
  forzarlas. Verificado que el delta de llaves vs los originales es exactamente el de la funcion
  auxiliar (+1/+1) y que no queda ninguna ruta `C:/Users/...`. **Compilar en Unity NO probado.**
- `09_render_blender.py`: probado de verdad con Blender 5.2.2 (aqui SI esta instalado, el subagente no
  lo vio): 5 PNG correctos, figura = 16,6 % de pixeles, 27.267 colores. Blender se cae AL CERRAR
  (EXCEPTION_ACCESS_VIOLATION en python313.dll, pila WM_exit). Acotado: script vacio, import del glTF,
  render de un cubo y bpy_extras+9 renders salen limpios => defecto de apagado de Blender con esa
  escena, no del script. El aviso va impreso por el propio script.
- El `.zip` publicado en Discord se verifico bajandolo otra vez: **bytes identicos** (sha256) y zip integro.


---

## 29-09-2026 (tarde) — CAUSA DEL CRASH ENCONTRADA: el esqueleto iba girado

El `console.log` del usuario (crash con el plan B) no traía ningún error de modelo: se cortaba en
seco en la carga del mapa. Eso descarta un rechazo con mensaje y apunta a datos mal formados que el
motor lee sin validar. Persiguiendo eso aparecieron **cinco fallos, cuatro míos**:

1. **★ Formato del esqueleto del SMD.** El bloque `skeleton` quiere
   `<índice> <px> <py> <pz> <rx> <ry> <rz>` (ángulos de Euler). Yo escribía **13 números**
   (posición + matriz 3×3). studiomdl leía la **primera fila de la matriz como si fueran ángulos** y
   compilaba sin una queja: el modelo salía con **todos los huesos girados** (medido: el quaternion
   compilado era `cos θ, sin θ` de lo que yo creía haber escrito). Se ve en las posiciones locales:
   el juego tiene `Spine1` en `(3.5, 0, 0)` (el hueso apunta a su hijo en +X) y el mío salía en
   `(-0.3, 0, -3.2)`.
   Conversión correcta: la de `mathlib.AngleQuaternion` (orden ZYX), **verificada contra los 82
   huesos del modelo del juego** (ida y vuelta, coincidencia 1.000000).
2. **★ Orden del producto de rotaciones.** `rot_global()` acumulaba `R(hijo) · R(raíz)` en vez de
   `R(raíz) · R(hijo)`, así que las posiciones locales quedaban expresadas en un sistema girado: la
   columna se iba hacia −Z. Arreglado en `construir_source.py`.
3. **★ Las cajas de impacto.** El conjunto se llamaba `default` y tenía 19 cajas con **centro y
   tamaño** donde el formato pide **mínimo y máximo** en el **espacio local** del hueso: salían todas
   invertidas (`min z 59.3 > max z 11.5`), y con grupos 8–13 que no existen. **Todos los humanoides
   de L4D2 llevan un conjunto llamado `L4D` con 17 cajas y los grupos estándar** (1 cabeza, 2 pecho,
   3 estómago, 4/5 brazos, 6/7 piernas); L4D2 lo busca **por nombre**. Ahora: `L4D`, 17 cajas en los
   17 huesos del juego, grupos 1–7, cero invertidas, X de 0 a la longitud del hueso.
4. **★ `empaquetar_source.py` no copiaba las fuentes.** studiomdl compila desde `gamedir/modelsrc`:
   el SMD se quedó congelado en la versión de las 18:14 y **todos los arreglos del esqueleto se
   perdían en silencio** (el compilador imprimía `Completed` y el `.mdl` salía igual). Ahora el paso
   `=== 0)` copia SMD, idle y los dos `.qc` en cada compilación.
5. **★ Mi lector del VPK** tenía el árbol bien pero mal los desplazamientos de extracción; y el
   lector del `.vtx` trataba como absolutos unos offsets que son **relativos al bloque padre**, y el
   `flags` de la tira como 2 bytes cuando es **1**.

**Verificado en el paquete A instalado** (40.060 bytes, versión 49): 82 huesos con quaternion
**idéntico al del juego** (82 de 82, peor 1.000000), 0 padres distintos, conjunto `L4D` con 17 cajas y
grupos 1–7, 0 invertidas, `.phy` de 17 cajas con **checksum que coincide con el `.mdl`**
(0x72220B37), animaciones incluidas, 32 attachments, 16.277 vértices. El `.mdl` de dentro del VPK es
**byte a byte el compilado** (CRC 1A981E80).

**Herramienta nueva**: `scripts/auditar_malla.py` recorre `.vvd` + `.dx90.vtx` y comprueba que ningún
índice de hueso o de peso se sale de rango, que los conteos cuadran y que los `boneID` de las tiras
apuntan a huesos que existen. El modelo del juego sale limpio como referencia.

**Pendiente**: probar el paquete A en el juego (ahora instalado). Si volviera a caer, el lanzador
`PROBAR-PAQUETE.bat` alterna B (sin animaciones), C (sin animaciones ni física) y D (control: el
modelo original del juego), y conviene arrancar con `-insecure -console -condebug` para que quede el
`console.log`.


## 30-09-2026 (tarde) — Paquete kotone_shiomi pasado a ingles

La carpeta `kotone_shiomi/` entera esta en ingles: carpetas (`01_model`, `02_textures`, `03_skeleton`,
`04_expressions`, `05_materials`, `06_origin`), ficheros (`bones.json`, `skeleton_tree.txt`,
`body.obj`, `weapon_spear.glb`), claves y valores de los JSON (`modelo`->`model`, `huesos`->`bones`),
y los comentarios de los MTL. El documento largo (403 lineas) esta traducido en `README.md`; el
original en castellano queda como `README.es.md`. Registro reversible en
`06_origin/migration_es_to_en.txt`.

Lecciones de esta migracion, para la proxima:

- **Al renombrar un paquete hay que reescribir las referencias internas.** Los OBJ llevan
  `mtllib <fichero>.mtl` y los MTL `map_Kd`/`map_Bump` con rutas relativas. Si solo se renombran los
  ficheros, las rutas quedan muertas. Lo mejor: buscar la textura por su nombre base en el inventario
  real y recalcular la ruta relativa, en vez de sustituir cadenas a mano.
- **Renombrar carpetas cuando el destino ya existe falla con WinError 5** (acceso denegado), no lo
  sobrescribe. Si al mover ficheros ya se crearon las carpetas nuevas, el renombrado de carpeta hay
  que hacerlo **fusionando** (mover lo que quede dentro y borrar la vieja si queda vacia).
- **Un script de migracion idempotente se puede relanzar sin miedo**: si se aplica a medias y se
  vuelve a lanzar, los nombres ya traducidos se traducen a si mismos y se saltan.
- **Los OBJ de expresiones (`04_expressions/obj/`) apuntaban a un `.mtl` que nunca existio.** Ya
  venia roto de antes. Ahora apuntan al material de la cara, que es el que les toca.
- **Los OBJ que exporta AssetStudio vienen Z-arriba**: al importarlos en Blender hay que pasar
  `forward_axis="Y", up_axis="Z"` o salen tumbados (y con `NEGATIVE_Y` en el frente, girados 180
  grados, mirando a la nuca).
- **Verificar un documento no es buscar cadenas**: hay que comprobar que las rutas que cita existan
  de verdad. Ojo con los nombres sueltos (que se resuelven en su carpeta, no en la raiz) y con los
  que el propio documento dice que faltan.

Previews: las 6 de referencia (cuatro vistas, primer plano de cara y hoja de contacto) rehechas desde
el GLB actual con `scripts/preview_kotone.py`. Las 7 comparativas del 28-sep solo se renombraron,
porque comparan contra renders antiguos.


## 30-09-2026 (tarde, 2) — Preview: NO hay lanza, son dos pistolas

Al rehacer las previews de "Kotone completo y sus armas" salio un error de fondo, ya corregido.

**Lo que hay de verdad** (medido sobre los GLB, y confirmado a ojo):

| malla del juego | que es | mide | donde esta |
|---|---|---|---|
| `PC079_01_qiang` | pistola | 10 x 9 x 8 cm | en la cadera, dentro de la funda |
| `PC079_01_qiangtao` | funda | 26 x 16 x 20 cm | cadera |
| `wq_makpon_gun_02` | segunda pistola | 13 x 16 x 2 cm | guardada en el **origen** (el juego la coloca al usarla) |

`qiang` (枪) es **pistola**, no lanza; `qiangtao` (枪套) es **funda**, y el nombre del propio juego lo
confirma. Lo que en el paquete se llamaba `weapon_spear` era la pistola de la cadera. Renombrados a
`weapon_gun_01`, `weapon_gun_holster` y `weapon_gun_02` (GLB, OBJ, MTL, huesos y SUMMARY), y el
README corregido.

**Ademas**: el README afirmaba que sobre su cabeza se veia una naginata a la espalda, y que por eso
el encuadre medía 2,00 m. Es falso: la vista frontal no tiene nada sobre la cabeza y el modelo mide
**1,68 m**. Se reescribio ese parrafo.

**Leccion (render)**: dibujar los vertices crudos sin aplicar la piel da el modelo **girado 180
grados en Y** respecto a lo que muestra Blender (comprobado: aplicar `mundo(hueso) * IBM` cambia el
signo de X y Z, no el tamano). Las vistas siguen siendo validas porque estan etiquetadas por lo que
se ve (frontal = su cara), pero conviene saberlo: un visor 3D la ensena mirando al otro lado.
Ademas, las armas guardadas en el origen (como `gun_02`) aparecen a ras de suelo, que es donde el
artista las dejo.

**Preview final**: `00`..`11` rehechas desde los GLB actuales (vistas, cara, las tres armas, la hoja
de armas, Kotone con la pistola enfundada y detalle de la cadera); `12`..`18` son los registros de
antes/despues, devueltos y renumerados para no chocar; y `blender/`, `blender_dark/`, `head/`,
`head_parts/` (23 renders de estilo toon) siguen valiendo, porque el modelo no cambio.

Scripts: `scripts/preview_modelos.py` (sustituye a `preview_kotone.py`, jubilado en
`_dl/scripts_obsoletos/`), `scripts/medir_armas.py`, `scripts/probar_piel.py`,
`scripts/renombrar_armas.py`, `scripts/revisar_paquete.py`.


## 30-09-2026 (tarde, 3) — FBX del modelo y las CUATRO ARMAS LARGAS

**FBX.** `kotone_shiomi/Kotone_Shiomi_full.fbx` (25,8 MB), exportado del GLB completo con las
texturas incrustadas. Verificado reimportandolo con `blender_verificar_fbx.py`: 1 armadura
`PC079_01_raiz` con **329 huesos**, 10 mallas (todas con UV y modificador de armadura), **24 shape
keys** (las expresiones: 20 cara + 3 ojo + 1 parpado), 0 acciones. Los huesos sin pesos son los
ayudantes conocidos (`t_*`, `Magica Cloth`, `h_*`, `qunzi_*`), los mismos que se podaron en la
version optimizada. Ojo: el FBX llevaba tambien un `Icosphere` de 42 vertices sin material ni pesos. **Quitado.**
No venia del modelo: el GLB tiene 9 mallas y ninguna esfera (comprobado leyendo su indice), pero el
**importador de glTF de Blender** crea una al leer el GLB, y como el FBX se exportaba despues, se la
llevaba dentro. Ahora `exportar_fbx.py` la borra antes de exportar y `blender_verificar_fbx.py`
arranca desde una escena de fabrica vacia, para que la escena de inicio del usuario no se cuele en
el informe y parezca un fallo del fichero. Verificado de nuevo: 329 huesos, 9 mallas, 29.846
vertices, 0 acciones, ninguna esfera.

**Las armas largas.** El usuario tenia razon: hay armas de verdad, y son **cuatro astas de ~2 m**,
en el mismo bundle del cuerpo (`part_pc079_011ef29087.bundle`, carpeta 145). Extraidas con
`AssetStudioModCLI -m export -t Mesh --filter-by-name weapon`:

| malla | vertices | tri | tamano | texturas |
|---|---|---|---|---|
| `weapon_02` | 1344 | 1377 | 0,18 x 1,96 x 0,18 m | `PC079_01_weapon_02_*` |
| `weapon_03` | 1894 | 2211 | 0,15 x 1,95 x 0,16 m | `PC079_01_weapon_03_*` |
| `weapon_04` | 2330 | 3058 | 0,18 x 1,95 x 0,17 m | `PC079_01_weapon_04_*` |
| `weapon_04_01` | 280 | 234 | 0,07 x 0,04 x 1,44 m | idem |
| `weapon_04_02` | 94 | 152 | 0,04 x 0,04 x 0,04 m | idem |
| `weapon_05` | 2680 | 4356 | 0,23 x 2,00 x 0,20 m | `PC079_01_weapon_05_*` |

**No hay `weapon_01`** en el bundle (ni su textura): los juegos van de 02 a 05. Son un guandao, una
naginata, otra guandao y un ji con cuchillas laterales (mirado, no supuesto).

Instaladas en `01_model/obj/weapons/` con su MTL. **AssetStudio no escribe material** cuando se le
pide solo `-t Mesh`, asi que cada MTL se reconstruyo desde los `.mat` del juego leyendo los GUID:
ranura a ranura (`_BaseMap`/`_MainTex`, `_BumpMap`, `_MetallicGlossMap`, `_OutlineTex`,
`_ShadePosition`, `_ToonDarkMap`, `_EmissionMap`). El nombre de la textura sale del `.meta` de cada
`Texture2D`, no de adivinar. Preview de cada una: `preview/19..22_weapon_0N.png` y la hoja
`23_long_weapons_contact_sheet.png`.

**Leccion (rutas relativas en los MTL).** Desde `01_model/obj/weapons/` hasta la raiz del paquete
hay **tres** niveles, no dos: las texturas se referencian con `../../../02_textures/...`. Se colo un
`../../` en las armas nuevas y en `gun_02.mtl`; corregido. Comprobarlo con un bucle que abra cada
`map_*` y mire si el fichero existe: es la unica forma de verlo.

**Leccion (OBJ de AssetStudio).** Vienen **Z-arriba** y sin material. Al rasterizarlos hay que
convertir `(x, y, z) -> (x, z, -y)` y voltear la V de las UV (convencion de Unity).

**Aviso.** Entre medias desaparecieron de `preview/` las comparativas `12..18` y las carpetas
`blender_dark/`, `head/`, `head_parts/` sin que ningun script mio las tocara; se devolvieron desde
`_dl/preview_historico_28sep/`. Si eso fue a proposito, hay que decirlo para no reponerlas.

Scripts: `exportar_fbx.py`, `preview_armas.py`, `medir_armas_nuevas.py`, `texturas_armas.py`,
`actualizar_summary.py`.

## 30-09-2026 (tarde, 4) - README limpio + zip del paquete

- `kotone_shiomi/README.md` reescrito: **213 lineas / 10.436 bytes** (antes 485 / 27.966). Fuera
  las nueve secciones de la extraccion (como se hizo, la reconstruccion del GLB, el brazalete, el
  espejo/quiralidad, el shader en Unity, las trampas y los errores). Solo queda lo que necesita
  quien va a usar el modelo. Verificado: las 31 rutas que cita existen, 0 referencias a los
  ficheros que el usuario borro (comparativas 12-18 y las subcarpetas salvo `blender/`).
- Corregido un dato falso que llevaba el README desde el principio: decia **124 huesos**; son
  **329** (medido: 329 joints en el GLB y 329 huesos al reimportar el FBX).
- El README viejo se guarda en `_dl/README_anterior_con_notas.md` (fuera del paquete).
- **`kotone_shiomi.zip`** rehecho: 222,6 MB, 163 ficheros, integridad OK, y el README de dentro
  coincide byte a byte con el nuevo (sha256 igual).
- Arreglado antes en la sesion: los 6 OBJ de armas largas no llevaban `mtllib`/`usemtl` (AssetStudio
  no los escribe) y entraban en Blender sin textura; el FBX llevaba un `Icosphere` de 42 vertices
  que **crea el importador de glTF de Blender**, no el fichero (FBX reexportado limpio, 10 objetos).
  Las lecciones estan en el skill `unity-game-datamining`, `references/importar-en-blender.md`.


## 02-10-2026 — PENDIENTE PARA MAÑANA: interfaz nueva (WebView2) con caida a la clasica

**Decision del usuario:** modernizar la interfaz de P5X Studio. Hoy es funcional pero anticuada y todo
va metido con calzador en la ventana. Referencia estetica: `cobalt.tools` — minimalista, mucho aire,
un solo color de acento, nada de adornos. **No** copiarla tal cual.

**Herramienta elegida: pywebview**, que usa **WebView2** (el motor web que Windows 11 ya trae). El
usuario lo aprobo explicitamente por eso: **no abre navegador** ni obliga a instalar Chrome, y no hay
Chromium que empaquetar (el exe no engorda como con Electron).

**★ Requisito del usuario: fallback.** Si WebView2 no esta disponible, la app debe **arrancar con la
interfaz clasica (tkinter)** en vez de fallar. Deteccion con **las dos vias**, porque cada una falla
distinto: (a) mirar si el motor esta registrado en Windows (clave del cliente de EdgeUpdate para el
WebView2 Evergreen Runtime) y (b) **intentar** abrir la ventana nueva y capturar el fallo. Ademas,
poder **forzar la clasica** con variable de entorno / parametro (para probar y para quien la prefiera).

**★ El trabajo de verdad es la separacion, no el fallback.** Hoy en `herramientas.py` la logica y los
widgets estan entremezclados (la funcion que busca el audio sabe de colores de fila), asi que no hay
forma de que dos interfaces distintas la usen. Hay que **sacar el motor del panel** y dejar que la
interfaz solo le pida cosas. Premios de ese trabajo, los tres a la vez:
1. el fallback a la interfaz clasica;
2. **las dos interfaces en paralelo** mientras la nueva madura (elegir cual empaquetar en cada version);
3. migrar a Qt (PySide6) mucho mas barato si algun dia se quiere, o reutilizar el motor desde otra UI.

**Prototipo hecho y aprobado:** `prototipo_ui/explorador.html` — pantalla del explorador de bundles
con la estetica buscada (riel lateral, buscador grande, filtros por tipo con sus recuentos, lista y
panel de detalle). Es una maqueta autonoma: HTML + CSS + JS sin dependencias, con **selector ES/EN**
funcionando y una muestra de nombres de bundle reales. El usuario dijo que le gusta mucho el diseño.
**El diseño no se pierde elijas lo que elijas**: es una paleta, un espaciado y cuatro componentes;
pasarlo a QSS (Qt) es traducirlo, no rehacerlo.

**Antes de empezar mañana, contexto del dia:**
- La version **publica con solo la pestana de Herramientas** (bundles, recursos, texturas, video/audio)
  se encargo en paralelo; su requisito clave es que funcione **sin los indices empaquetados**, solo
  con la carpeta del juego. Comprobar si termino y **reconstruir el exe** (Windows no deja sobrescribir
  un ejecutable en marcha: cerrarlo antes con `Stop-Process`).
- Al extraer video ahora se conservan **todas** las pistas de audio (efectos + cada doblaje), con su
  idioma y su nombre en el flujo (`jpn`/`chi`/`und`). Ojo: ffmpeg **tira** `title=` salvo con
  `+use_metadata_tags`, y lo que el reproductor muestra de verdad es `handler_name`.
- Coste honesto de pywebview: el proyecto pasa a tener dos lenguajes (Python el motor, HTML/CSS/JS la
  cara). Si algun dia se prefiere un solo lenguaje: PySide6+QSS (nativo, binario grande) o Flet
  (Python puro, trae su propio motor).

### ★ PASO FINAL OBLIGATORIO (peticion del usuario): probar la autosuficiencia DESDE EL ESCRITORIO

Cuando la interfaz nueva este terminada y el `.exe` reconstruido, **el ultimo paso no es dar el visto
bueno desde la carpeta de trabajo**: hay que **mover `P5X Studio Tools.exe` junto con sus dependencias
a `C:/Users/Lukas/Desktop/` y ejecutarlo desde ahi**.

Por que importa: desde dentro de `p5x_studio/` todo puede parecer autonomo y en realidad estar
resolviendo rutas **relativas al directorio de trabajo**. Desde el escritorio eso se cae. Es la unica
prueba que zanja de verdad el requisito "funciona en un equipo ajeno".

Comprobar desde el escritorio:
1. **Arranca** (y con que interfaz: la nueva con WebView2; y forzando `P5X_STUDIO_UI=clasica`, la de tkinter).
2. **Lista los 16535 bundles del disco** (no de un indice empaquetado).
3. **Extrae algo real**: un video con **todas** sus pistas de audio etiquetadas (jpn/chi/und).
4. **Donde escribe** las extracciones y si toca el proyecto (no deberia).
5. **Que necesito de verdad** al moverlo: si el `.exe` es de fichero unico no deberia necesitar nada.
   Si necesita algun fichero o runtime, **eso es un hallazgo** y hay que anotarlo.
6. Y al terminar, **dejarlo de nuevo en `p5x_studio/`** (o decir donde quedo), sin duplicados sueltos.

Con eso hecho y verificado, la version Tools se puede **marcar como Public-Beta**.

## 03-10-2026 (tarde) — Interfaz nueva de P5X Studio Tools: FASE 1 VERIFICADA por el padre

El subagente de esta fase **murio por corte del proveedor** (Nous Portal, 3 intentos, 227 llamadas,
2h34m) con el codigo ya escrito pero **sin una sola verificacion ejecutada**. Lo ha cerrado el padre.

### Lo que estaba roto y se arreglo
- **`arranque_tools.py` llamaba a `gui_tools.arrancar` directamente**, asi que la interfaz nueva
  **nunca se alcanzaba**: `ui.py` (el selector) quedaba muerto. Corregido a `from p5x_studio.ui import arrancar`.
- `pywebview` **no estaba instalado** (el subagente creyo instalarlo). Instalado en el .venv: 6.2.1,
  con `pythonnet` 3.2.0 y el backend winforms importando.
- El arnes `_dl/ui_fase/leer_dom.py` tenia un `NameError` (la variable `res` vivia dentro de la
  funcion de `webview.start`): `RES` a nivel de modulo. Y `probar_pantallas.py` tenia una sonda que
  pywebview no podia invocar (funcion con argumento -> None): pasada a IIFE.

### Verificacion real (medida, no impresion)
| Que | Resultado |
|---|---|
| Fachada `motor.py` sin interfaz | 16.535 bundles de disco en **1.492 ms**; 25 tipos; suma de filtros por tipo = 16.535 (cuadra) |
| Inspector por la fachada | `115/shared_3e45cab0.bundle` (372,77 MB) -> **148 recursos en 0,6 s** |
| Video/audio | 347 `.usm` / 401 `.awb`; distintivo honesto `sin_dato` (no inventa) |
| Paridad ES/EN | 93 claves `web_` en cada idioma, **0 huerfanas** |
| Ventana NUEVA | abre y pinta: **visible a los 451 ms**, cierre total 7,1 s, captura 249 KB |
| Riel lateral + 5 pantallas | Bundles / Inspector / Recursos / Texturas / Video y audio, **0 errores de JS** |
| Explorador por el DOM real | 701 filas pintadas; chip `part` -> **"700 de 906 mostrados"**; panel de detalle abre con nombre, ruta, tamano y tipo |
| **E2E por el puente web** | `gacha_fourth_thief_last_04_new.usm` -> MP4 6,48 MB con **4 flujos: video + jpn "japones" + chi "chino" + und "efectos (SFX)"** |
| Caida a la CLASICA (`P5X_STUDIO_UI=clasica`) | abre y pinta (tkinter, pestanas arriba, tabla, registro "Actividad") |
| Modo AUTO (dos vias) | registro WebView2 = 154.0.4258.53 + prueba real de ventana = ok -> **elige web** |

Evidencia en `_dl/ui_fase/`: `01_explorador_nuevo.png`, `02_clasica.png`, `pantallas.json`,
`e2e_puente2.txt`, `medir_fachada.py`, `leer_dom.py`, `probar_pantallas.py`, `capturar_clasica.py`.
Decision registrada en `p5x_studio/cache/ui_decision.txt`.

### Pendiente de la fase 1 (lo que NO se ha hecho)
- **El `.exe` NO se ha reconstruido**: `P5X Studio Tools.exe` (18 MB, del 02-10) sigue siendo el de
  la interfaz clasica. Al reconstruir hay que **empaquetar pywebview**, que es el punto delicado:
  necesita `clr`/`pythonnet` y los DLL de WebView2 (`webview/lib/*.dll`, `runtimes/win-*/native/WebView2Loader.dll`).
  Mirar `_pyinstaller_hooks_contrib/stdhooks/hook-webview.py` (ya presente en el entorno) o usar
  `--collect-all webview`.
- **El Explorer de bundles es la unica pantalla probada a fondo**; las otras cuatro existen con su
  marcado, botones y avisos, y no dan error, pero **no se ha ejercitado su flujo completo** desde la web
  (exportar texturas, construir indice, exportar recursos desde el inspector).
- Falta el **paso final del escritorio** (mover el .exe a `C:/Users/Lukas/Desktop/` y probarlo ahi).

## 03-10-2026 (noche) — FASES 2, 3 y 4 CERRADAS: empaquetado con WebView2 y prueba en el escritorio

### Fase 2 — los flujos de las cuatro pantallas restantes (por el puente real de la web)
| Pantalla | Resultado |
|---|---|
| Inspector | bundle abierto -> 15 recursos -> **15 ficheros escritos** |
| Texturas | exportadas y listadas 15 imagenes; abierta con Pillow 512x512 RGBA |
| Buscador | indice limitado -> 3.730 recursos, 120 avisos de progreso; busqueda y cancelacion OK |
| Video/audio | `.awb` -> 4 WAV (`BGM_BlankCue_04.hca` -> 3,9 MB) |
Cero fallos. Ejercitado con `_dl/ui_fase/fase2_flujos.py` (informe en `fase2_flujos.txt`).

### Dos defectos REALES que salieron al probar (ya corregidos)
1. **Un indice a medias se presentaba como completo.** `construir_indice_recursos(limite=...)` (que
   es solo para pruebas) escribia en el indice DE VERDAD, y `indice_recursos_estado()` lo daba por
   bueno. Ahora: con `limite` se escribe en `cache/herramientas/indice_prueba.json`, y el indice
   guarda `bundles_cubiertos`/`bundles_totales`. Si cubre menos bundles de los que hay, el estado
   sale `parcial=True` y **la pantalla lo avisa en ambar** ("Indice PARCIAL: cubre 40 de 16.535...").
   Lo mismo en la interfaz clasica (`her_sync_parcial`). Claves nuevas en ES y EN: paridad 595/595.
2. **El autotest se moria** en el paso de video si faltaba `wannacri` (excepcion sin capturar en un
   .exe de ventana = proceso colgado sin informe). Ahora cada paso va en su try, apunta el motivo y
   sigue; y el informe lleva una linea nueva con las herramientas externas: `wannacri=si/no`,
   `vgmstream=`, `ffmpeg=`, `motor=`.

### Fase 3 — el .exe con la interfaz nueva dentro
- `P5X Studio Tools.spec`: se añade la PAGINA (`p5x_studio/ui_web/`) en `datas` y se recolectan
  `webview`, `pythonnet` y `clr_loader` con `collect_all` (hacen falta sus DLL: WebView2Loader.dll,
  Microsoft.Web.WebView2.Core.dll). Es lo que hace que la ventana nueva funcione CONGELADA.
- **Fallo corregido antes de empaquetar:** la sonda de WebView2 devuelve False cuando el binario
  esta congelado (no puede lanzar un subproceso), asi que el modo AUTO **habria caido SIEMPRE a la
  clasica** aunque WebView2 funcione. Ahora, congelado, la segunda via es el intento real de ventana.
- Tamano: **22.195.477 B (22,2 MB)**, frente a 18,0 MB de la version clasica (+4,2 MB por pywebview,
  pythonnet y sus DLL). Respaldo del .exe anterior en `P5X Studio Tools.exe.bak_20261003_antes_ui_web`.
- Verificado congelado en su carpeta: diagnostico OK, autotest OK (16535 de disco, 148 recursos,
  12 texturas, video omitido), modulos de MODELOS ausentes.

### Fase 4 — movido AL ESCRITORIO con sus dependencias
Carpeta: `C:\Users\Lukas\Desktop\P5X Studio Tools\` (**304 MB**):
- `P5X Studio Tools.exe` (22,2 MB)
- `motor/` (16 MB) -> el motor AssetStudioModCLI, sin el no se abren bundles
- `tools/env` (97 MB) -> `wannacri.exe` (extractor de .usm)
- `tools/vgmstream` (13 MB) -> `vgmstream-cli.exe` (audio de los .acb)
- `tools/ffmpeg/bin/ffmpeg.exe` (**163 MB**) -> montaje del MP4

Autotest DESDE EL ESCRITORIO (todo verde): `wannacri=si vgmstream=si ffmpeg=si motor=si`,
16535 bundles de disco, inspector 148 recursos, texturas 12 imagenes (Pillow 512x512 RGBA),
`appicon_2.usm -> appicon_2.mp4 (0,1 MB)` avisando "sin sonido emparejado (video mudo)".
Ventana: `modo_pedido=auto webview2_registrado=154.0.4258.53 -> interfaz=web (auto, dos vias ok)`,
titulo `P5X Studio · Tools`, explorador pintando 16.535 con chips por tipo y "700 de 16.535 mostrados".
Escribe TODO dentro de su propia carpeta (`cache/`, `herramientas_extraidas/`); **no toca el proyecto**.
Captura: `_dl/ui_fase/04_escritorio_ventana.png`.

### HALLAZGOS que necesitan decision (NO resueltos)
1. **Las herramientas externas no se pueden obtener desde la interfaz.** El panel de dependencias
   ensena `wannacri`, `vgmstream`, `ffmpeg` y `motor` con su estado, pero **solo el motor tiene boton
   de descarga**. En un equipo ajeno sin `tools/` el explorador, el buscador y las texturas
   funcionarian igual, pero **el video/audio no** (lo dice con claridad: "No encuentro wannacri
   (el extractor de .usm)"). Opciones: (a) botones de descarga como el del motor; (b) empaquetarlas
   dentro (engordaria el .exe ~270 MB mas); (c) dejarlo documentado en el README.
2. **`ffmpeg` en este equipo sale del PATH de Hermes**
   (`C:\Users\Lukas\AppData\Local\hermes\tools\ffmpeg-...`), no del proyecto: es un espejismo de
   autosuficiencia. Los 163 MB que ocupa son el mayor lastre de la distribucion.
3. **`tools/env` son 97 MB** para usar solo `wannacri`: un entorno minimo (uv venv + wannacri)
   ocuparia mucho menos. Merece la pena mirarlo antes de publicar.
4. Falta rehacer el **README en ingles** explicando la carpeta `tools/` y que NO se redistribuyen
   assets. Y decidir si ya se marca como **Public-Beta** (el usuario dijo que con esto hecho, si).

## 03-10-2026 (noche) — las 9 tareas de la lista: HECHAS y verificadas

Plan guardado en `.hermes/plans/2026-10-03_173703-p5x-tools-deps-console-folders.md`. Sin repositorio
git en el proyecto, asi que el respaldo de cada paso esta en `p5x_studio/_bk_tools_pre_deps/`.

**Todo lo que sigue es de la version Tools.** El extractor de modelos queda fuera por decision del
usuario; comparte `herramientas.py`/`idiomas.py`/`dependencias.py`, asi que heredara los nombres
nuevos de carpeta cuando se reconstruya su `.exe`.

### 1. Boton de dependencias con consola de solo lectura
- `dependencias.asegurar_todas()` baja motor + wannacri + vgmstream + ffmpeg, **sin pararse si una
  falla** (devuelve `ok` y `fallos`).
- `TAMANOS_MB` = 16 + 5 + 11 + 105 = **137 MB** (medidos, no estimados); `peso_aproximado_mb()`.
- Ventana nueva (WebView2): boton en el riel → modal con peso, lista de las cuatro, boton de
  descarga y **consola `<pre>`**: no hay dentro ningun campo editable (una prueba lo cuenta: 0).
- Ventana clasica (`VentanaDependencias`, tkinter): consola `tk.Text` con `state=disabled`; el
  usuario ve el progreso y no puede escribir. Hace falta porque sin WebView2 no se abre la nueva.
- El registro va linea a linea y esta **acotado a 400 lineas** en Python y 800 en la ventana: el
  sondeo manda la lista entera cada 700 ms y una descarga de 115 MB imprime cientos de lineas.

### 2. Peso: 289 MB → 131 MB de dependencias
| | antes | ahora | como |
|---|---|---|---|
| wannacri | 97 MB | **3 MB** | entorno minimo con `uv`, no el de 97 MB |
| ffmpeg | 163 MB | **101 MB** | gyan.dev `essentials` (105 MB en un fichero) en vez del `gpl` estatico (497 MB en disco) + poda de `ffplay`/`ffprobe`/`doc`/`lib`/`include` |
| vgmstream | 13 MB | 11 MB | sin cambios |

Descartado a proposito: BtbN `lgpl-shared` descarga menos (80 MB) pero deja **154 MB** en disco.
Lo que el usuario acaba copiando es la carpeta, no lo que tardo en bajar una vez.

### 3. Carpetas en ingles (coherentes con los ficheros del juego)
`motor/`→`engine/`, `herramientas_extraidas/`→`extracted/` (`textures/`), `tools/env/`→`tools/wannacri/`,
`cache/herramientas/`→`cache/work/`, `indice_recursos.json`→`resource_index.json`, y las subcarpetas
del panel (`explorador`→`explorer`, `recursos`→`resources`).

`ajustes.migrar_nombres()` corre al arrancar y renombra lo viejo **solo si el nombre nuevo no
existe**: una instalacion con datos no pierde nada. En el proyecto y en el escritorio ya esta hecho.
`tools/env` se sigue mirando ademas de `wannacri` porque el tutorial de Kotone y los apuntes viejos
lo citan.

### 4. El motor ya no depende de la copia del Escritorio
`ruta_assetstudio()` miraba tambien `~/Desktop` y `~/Downloads` y **se daba por contento**. Ahora
`asegurar_assetstudio` comprueba primero SU carpeta y, si solo hay una copia de fuera, se baja la
suya igual (lo dice en el registro). Sin esto la carpeta dejaria de valer tal cual en otro equipo.

### 5. Indice incremental
`construir_indice_recursos` guarda la huella (fecha + tamano) de cada bundle y la proxima vez
**solo abre los que cambiaron**; los demas se reutilizan del indice anterior y los que desaparecen
salen del indice. Prueba: 3 bundles → visita 3; 2a vuelta → visita 0; toco uno → visita 1; borro uno
→ sus recursos se van.

### 6. Simular que no hay WebView2
`P5X_STUDIO_WEBVIEW2_OFF=1` → `webview2_registrado()` devuelve None → interfaz clasica. Comprobado en
el codigo y en el `.exe` congelado (`cache/ui_decision.txt` lo deja escrito).

### 7. README y Public-Beta
`README_TOOLS.md` reescrito en ingles: boton de dependencias con la tabla de pesos, la carpeta
`tools/`, la estructura de carpetas, las tres pistas de audio y "no se redistribuyen assets".
`VERSION = "1.0.0-beta"` (sale en el titulo de la ventana). **El README ya viaja con la carpeta del
escritorio** (antes no habia ninguno).

### 8. Pruebas: `p5x_studio/tests/` (sin pytest, por el presupuesto $0)
7 scripts con ciclo rojo→verde, todos verdes: `test_carpetas`, `test_dependencias`, `test_api_tareas`,
`test_pantalla_deps` (DOM real, 1180x700), `test_ventana_clasica` (tkinter real),
`test_e2e_video` (por la ventana: clic en la fila → extraer → ffprobe), `test_indice_incremental`.
Paridad ES/EN 619/619, 0 huerfanas.

### 9. Escritorio
`C:\Users\Lukas\Desktop\P5X Studio Tools\` = **190 MB** (ver §10; en la fase anterior eran 154 y
antes 303): `.exe` 22 MB + `engine/` 16 + `tools/` 153 (uv 39 + wannacri 3,7 + vgmstream 11 +
ffmpeg 101) + README. Autotest congelado verde (`wannacri=si vgmstream=si ffmpeg=si motor=si`) y
extrae video de verdad (`appicon_2.usm → appicon_2.mp4`). Sin rutas del equipo dentro del binario.

### 10. Prueba de fuego (carpeta vacia) — 3 oct
Informe completo en `p5x_studio/INFORME_PRUEBA_DE_FUEGO.md`. Resumen: carpeta borrada y recreada
solo con `.exe` + README (22 MB), y **todo lo demas lo bajo la propia app**. 34/34 comprobaciones
sobre el `.exe` congelado, + 6/6 en un ensayo de equipo ajeno, + 7/7 la suite.

- **Como se comprobo el `.exe` congelado (tecnica nueva, reutilizable):** se anadio
  `P5X_STUDIO_UI_CDP=<puerto>` a `ui_web.arrancar()` (apagado por defecto) que pone
  `webview.settings["REMOTE_DEBUGGING_PORT"]`; con eso se pilota la ventana por CDP. Piloto en
  `_dl/pilotar_exe.py` (necesita `websocket-client` en el venv, solo para pruebas). Tres trampas:
  (1) `websocket.create_connection(..., suppress_origin=True)` o Chromium contesta 403; (2) hay que
  esperar a `document.readyState==='complete'` o se pregunta a `about:blank`; (3) para saber si algo
  se ve, `getBoundingClientRect()`, no `offsetParent` (null en elementos `position:fixed`).
- **Fallo real gordo:** wannacri necesita `uv` y la app solo lo buscaba en el equipo (PATH,
  `~/.local/bin`, `~/.cargo/bin`). En un equipo sin `uv`, la extraccion de video se caia (el plan B
  `python -m venv` no puede funcionar dentro de un `.exe`). Ahora la app se baja **su propio uv** a
  `tools/uv/` (39 MB) como una pieza mas: `asegurar_uv()`, primero en `ORDEN`. Ensayo que lo prueba:
  `_dl/probar_uv_sin_equipo.py` (correr con `PATH`/`USERPROFILE` capados).
- **Fallo real menor:** la lista decia "instalado" a herramientas que estaban FUERA de la carpeta
  (motor del escritorio, ffmpeg del PATH). Ahora son tres estados: *instalado* / *fuera de la
  carpeta* (con ruta en el tooltip) / *falta*.
- **Peso:** dependencias 177 MB anunciadas / **190 MB la carpeta** (antes 154: +39 del uv propio).
  El peso mostrado y las filas suman, porque `uv` es una fila mas de la lista.
- **Lo que no se puede comprobar aqui:** SmartScreen en un equipo ajeno, WebView2 ausente de verdad
  (se simula), el indice completo (29 min; se probo arrancar-progreso-cancelar), y el traslado real
  de la carpeta a otro equipo.

### 11. La Tools pasa a ingles (solo lo visible) — 3 oct
Peticion del usuario: "elimina cualquier rastro del español de la herramienta". Alcance acordado en el
claro: **solo lo visible** (interfaz, consola de descarga, errores); comentarios, docstrings y nombres
de ficheros/funciones/variables se quedan como estan (son ~11.400 lineas y no los ve nadie).

- **La ventana nueva no recibe español**: `motor.textos()` sirve **solo** el diccionario `en` (111
  claves `web_`), asi que la pagina no tiene de donde sacar una frase en español. Fuera el boton `ES`
  del riel, `lang="es"`→`lang="en"`, borrados el conmutador y su evento en `app.js`, y `num()` fijo a
  `en-US` (los miles salen `16,535`, no `16.535`).
- **Fuera el selector** tambien en la ventana clasica (`gui_tools.py`) y `motor.activar_idioma()` /
  `idiomas_disponibles()` borrados: ya no hay forma de pedir otro idioma. `ui.py` fija
  `idiomas._ACTIVO["v"] = "en"` al arrancar en vez de leer el ajuste guardado.
- **Frases sueltas traducidas**: las 26 de `dependencias.py` (consola de descarga y errores), las del
  registro `cache/ui_decision.txt` (`ui=web` / `ui=classic`), los textos de reserva del HTML (los que
  se ven antes de que cargue el JS), los dos que armaban `"5 de 5"` y `REQUISITOS`.
- `README_TOOLS.md` (§Language) decia "Spanish / English, switchable from the rail": ahora dice que
  va **solo en ingles** y por que (el juego lista sus ficheros en ingles).
- **NO se toco el diccionario `ES` de `idiomas.py`** (623 claves) a proposito: lo usa el **extractor
  de modelos**, que si es bilingue. Borrarlo lo rompe. Tampoco los comentarios.
- **Comprobado**: barrido con `ast` de todas las cadenas literales de los modulos de la Tools → 0
  español pintado (los restos que salen son claves internas tipo `est["fuera"]`); paridad ES/EN
  623/623 intacta; suite 7/7; **prueba de fuego 36/36** con dos comprobaciones nuevas: "la ventana no
  tiene ni una palabra en español" y "la consola de descarga tambien va en ingles".

### 12. Pestana "Bulk textures": TODAS las texturas, ordenadas por categoria — 4 oct

**Que hace.** La pestana nueva (la ultima del riel) saca las texturas de todos los bundles de las
categorias marcadas y las deja en `extracted/textures/<Categoria>/<conjunto>/<textura>.png`.

**Los numeros que la sostienen (medidos, no estimados a ojo).**
- 16.535 bundles; **118.425 texturas** = 77.864 `Texture2D` + 40.561 `Sprite` (censo con el motor en
  modo info: `_dl/censo_texturas.py`). 8.573 bundles no tienen ninguna.
- **~35 GB** de PNG y **~2-3 h** (factor 0,27x sobre lo que declara el motor; 0,69 s por bundle;
  `_dl/sonda3_peso.py` y `_dl/sonda7_calibra.py`). La carpeta de bundles pesa 72 GB.
- El motor acepta la carpeta entera como entrada y `-t tex2d`, y `-g fileName` deja
  `bundle/CAB/textura.png` (probado en `_dl/sonda5_layout.py`; `containerFull` es inservible: hace
  una carpeta por textura).

**Las categorias salen de la FAMILIA del bundle, no del nombre de la textura.** La idea de partida
era clasificar por el nombre ("escenarios / personajes / npc / sprites"); al cruzarla con los datos
(`_dl/sonda6_cruce.py`) se cayo: **"NPC" no existe** como categoria en el juego y `PC0xx` esta
repartido por familias enteras (uitex 3.409, part 841, atlas 414, shared 138... y solo 43 en
`role_`). Los nombres de textura son abreviaturas en pinyin (`yjs_jz_912_nmas`, `sb_niudan`,
`wonder_normal_13_bc`): sacar "personaje/escenario" de ahi seria adivinar. La familia es fiable. Para
"todo lo de un personaje" esta el **filtro por texto** (p. ej. `PC079`).

**Categorias finales** (`lote.CATEGORIAS`): UI 2.215 · Scenery 1.598 · Characters 1.330 ·
Character icons 1.809 · Particles 906 · Effects 439 · Shared 6.134 · Other 2.104 (esta ultima va
desmarcada: son familias sin texturas).

**Mecanica.** Los bundles se juntan con **enlaces duros** (ni se copian los 72 GB ni se toca la
carpeta del juego; si el sistema no deja enlazar, copia). Se manda el lote al motor, se recogen los
PNG y se colocan por categoria y conjunto, donde "conjunto" es el bundle sin el hash. Se comprueba
el **espacio libre** antes de arrancar. Es **reanudable**: lo hecho queda apuntado por carpeta
destino en `cache/work/bulk_texturas.json`, y una nueva corrida sigue por donde iba (hay una casilla
para mirarlo todo otra vez). Cancelable en cualquier momento; corre en un hilo, asi que la app sigue
usable. El reparto por **tipo de mapa** (`Color`/`Normal`/`Emission`/`Lightmap`/`Shadow`/`Mask`/
`Packed`/`Stroke`/`Data`, deducido del sufijo del nombre) es opcional y va apagado.

**Los fallos que destapo la prueba del modulo** (de la herramienta, no de la prueba):
- `organizar()` se llevaba tambien los PNG de bundles de OTRA categoria (inofensivo en el flujo
  real, porque cada lote lleva solo los suyos, pero fragil): ahora comprueba que el bundle sea de la
  categoria antes de moverlo.
- **`_apuntar()` no guardaba el manifiesto**: reanudar no habria servido de nada. Detectado porque la
  prueba comprobaba que la segunda corrida terminase mucho mas rapido que la primera.
- Y un tercero de nombres: a la carpeta `<bundle>.bundle_export` se le anadia otro `.bundle`, asi que
  salian conjuntos tipo `role__weiyang40b9bdc8.bundle.bundle`.

**Pruebas.** `tests/test_lote.py` (nuevo, 8a prueba de la suite: categorias, nombres de conjunto,
tipos de mapa, inventario, enlaces duros + respaldo por copia, organizacion con colisiones, manifiesto
y **una corrida real** de 2 bundles con `limite=2`). Suite **8/8**. Prueba de punta a punta por la
ventana (`_dl/prueba_bulk_ui.py`): 20/20, incluida una extraccion real que deja los PNG en
`Effects\efx_bugs\`. A la prueba de fuego se le anadio el paso `3b) TEXTURAS EN BLOQUE` con
`P5X_STUDIO_BULK_LIMITE=2` (gancho de prueba: corta el lote a N bundles por categoria).

**Lo que queda abierto.** El bulk vive solo en la interfaz nueva: en la **clasica (sin WebView2)** no
esta (la app funciona igual, solo no tiene esa pestana).

**CORRIDA COMPLETA (4 oct, 09:28:27 → 11:06:53 = 1 h 38 min).** Verificada contra el censo
(`_dl/verificacion_final_bulk.py`): **118.420 de 118.425 texturas = 99,996 %** (118.404 exactas por
nombre + 16 con nombre decorado por el motor: `.tga.png`, `.png_#1288`, `_001`). Los **3.979
conjuntos** que pide el censo existen los 3.979, **0 vacios**; **0 PNG de 0 bytes**; **0 ficheros
sueltos** en la raiz; 30 PNG al azar abiertos con PIL, 0 ilegibles; **118.230 PNG / 67,65 GB** en
1 h 38 min (el peso real casi dobla la estimacion de 36 GB — la estimacion se quedo corta, el disco
no). Los 14.431 bundles quedaron apuntados en el manifiesto.

Los **5 que faltan** (0,004 %) son atlas de fuentes de Unity con nombre generico (`Font Texture`,
`LiberationSans SDF Atlas`) cuyo contenedor es el propio `.ttf`/`.otf`: el motor no los exporta como
textura. Se cubririan con una pasada aparte (`-t all`) sobre esos 5 bundles `ui_font`/`ui_ythmgame` si
alguna vez hacen falta para reconstruir la interfaz.

Nota: 25.419 ficheros llevan sufijo de desempate (`_#`, `_2`) — es el motor resolviendo nombres
repetidos dentro de un mismo conjunto (normal en los atlas de sprites: UI 22.505, Scenery 2.391). No
se pierde nada: son ficheros distintos con el mismo nombre de origen.

### Lo que queda abierto
- El **extractor de modelos** (`P5X Studio.exe`): reconstruirlo para que herede los nombres nuevos
  de carpeta. Sigue fuera de esta tanda, como pidio el usuario.
- Kotone Shiomi (PC079): el CRASH en L4D2 sigue sin diagnosticar.
- Publicar: decidir donde (Discord/Workshop) y si el `.exe` pasa SmartScreen en un equipo ajeno
  (aqui no se puede probar).

# SOMBREADO DE BUST-UP (shader UI/UIMultipleGradient) — 4 oct (peticion de la comunidad)

**De donde sale el dato.** El sombreado de cada bust-up esta en
`Client/OuterPackage/Bundles/Windows/140/ui_lihui_shader.bundle`: **216 MonoBehaviours**
`UI-DialogShader-<ropa>-<personaje>`. Volcado completo (ya hecho, en `_dl/lihui_shader_json/`):

```
AssetStudioModCLI.exe ".../140/ui_lihui_shader.bundle" -t monoBehaviour -o _dl/lihui_shader_json -g none --unity-version 2022.3.49f1
```

**La cuenta, en orden** (sacada del GLSL movil que paso la comunidad, implementada en
`_dl/sombreado_lihui.py`):

1. `color = textura * color de vertice` (el tinte del Image; blanco si no hay).
2. desenfoque 3x3 opcional, nucleo fijo (0.4566, 1, 0.4566), paso = texel * `BlurStrength` * 2.
3. descarte si alfa < 0.001.
4. tono base: `base = sat*((col*brillo) - lum) + lum`, luego `(base-0.5)*contraste+0.5`,
   con `lum = dot(col, (0.2125, 0.7154, 0.0721))`.
5. coordenada: lineal = `dot(uv-0.5, (sin(-ang), cos(ang))) + 0.5`; radial = `length((uv-centro)*ratio)*2`;
   se mezclan por `gradientMode`.
6. degradado de 8 paradas (el componente guarda un `Gradient` de Unity; se evalua en 8 puntos).
7. tono del degradado: igual que 4 pero con `Gra*` y **sobre el color del degradado**.
8. **el degradado se MULTIPLICA por el color base** (`gra = gTono * base`) — no se superpone.
9. rampa de alfa entre `GradientAlphaBottom/Top` (posiciones tomadas de las claves de alfa).
10. mezcla por esa rampa y despues `EffectFactor` sobre el color original.

**Validado contra el juego.** Par real `UI-DialogShader-changfu01-xiachuanling` + sprites
`xiachuanling-changfu-*` (`076/uitex_changfu512a3bdb.bundle`), contra una captura del juego: piel
`#EBD4B4` contra `#E7D4BC` del juego = **4,2/255** de desvio (el sprite crudo esta a 13,5; con la
rampa invertida 8,4; con el otro JSON del mismo personaje 18,2). En **espacio gamma** gana a lineal
(4,2 contra 6,7). Captura de control en `_dl/prueba_xiachuanling/captura_vs_sombreado.png`.

**Modo lote** (lo que luego va a P5X Studio):
`_dl/emparejar_jsons.py` (empareja JSON <-> sprites y compara los 216) → `_dl/lote_bustups.py`
(renderiza, reanudable) → `_dl/hoja_bustups.py` (hoja de contacto) → `_dl/revisar_lote.py`
(descarta vacios/negros). Salida en `_dl/bustups_sombreados/` (**120 PNG**), hoja en
`_dl/hoja_bustups.png`, comparacion de parametros en `_dl/comparacion_216_jsons.csv`/`.md`.

**Estado del lote:** 216 JSON → **120 emparejados y renderizados** (36 de confianza alta, 83 media,
1 baja), 96 sin emparejar. De los 120: 103 claramente bien, 14 oscuros legitimos (variantes
`yinying` = sombra y personajes de pelo negro), 3 vacios (`aochuncun`, su "cuerpo" no sirve).
10 renders se quedan sin ojos/boca (esas capas van recortadas y las coloca el prefab).

**Trampas nuevas (no volver a tropezar):**
- El sufijo `_#NN` del motor **no** distingue Sprite de Texture2D: depende del orden de exportacion.
  Se elige **por tamano** (el Texture2D es el lienzo completo, el Sprite va recortado).
- **El bundle va por capa**: las capas de un mismo bust-up viven en bundles distintos
  (`063/uitex_s_changfu…` cuerpo, `119/uitex_changfu…` ojos). Guardar un bundle por personaje+ropa
  hace que la ultima capa pisie a las demas y se extraiga el bundle equivocado.
- **El lienzo lo marca el cuerpo**, no la capa mas grande: si no, cuando el cuerpo va recortado se
  apila solo el contorno y salen siluetas negras (paso con 5).
- Los nombres de capa no siguen una convencion: `<p>-<ropa>-<capa>` y `<p>-<ropa>-<capa>-<expresion>`
  (`lufeier-changfu-benti-tongchang` = el cuerpo). Hay que buscar el token de parte, no la posicion.
- El JSON usa el **nombre corto** del personaje y los sprites el **completo** (`lizi`→`duomicunlizi`,
  `suyu`→`xinjingsuyu`, `shuangye`→`zuocangshuangye`). Subcadena solo si esta **anclada**: `aqi` esta
  dentro de `maqimu` y emparejarlos es un error silencioso.
- Una ropa solo vale si tiene **capa de cuerpo**; si no, son ojos/boca de otra ropa.
- Cada personaje puede tener **varios JSON** (`changfu01`, `yinying01`): elegir mal cuesta 18/255,
  mas que cualquier otro fallo.
- `alias_bustups.json` permite forzar personaje+ropa para un JSON concreto sin tocar codigo.

**Montaje por capas leyendo COORDENADAS — `_dl/montar_bustup.py`** (lo que pide el visor de
Bust-ups de P5X Studio: ver Original / Version con Shader y extraer montados como PNG).

```
montar_bustup.py UI-DialogShader-changfu01-xiachuanling --json
montar_bustup.py xiachuanling/changfu          # tambien acepta personaje/ropa
```

De donde salen las coordenadas (esto SI se lee; el motor tiene modo `-m dump`, que vuelca cada asset
a texto):

- del **Sprite**: `m_Rect` (el rect del sprite dentro de su textura), `m_Pivot`, `m_PixelsToUnits` y
  a que textura apunta (`m_RD.texture` PathID);
- del **Texture2D**: `m_Width`/`m_Height`.

Reglas de colocacion (y su honestidad):

| caso | offset | exacto? |
|---|---|---|
| la capa tiene **rect de malla** en el dump (lo normal) | `malla.x`, `alto - malla.y - malla.alto` | **si**, leido |
| la textura de la capa ES el lienzo (mismo tamano) | (0,0) | **si**, leido |
| el sprite apunta a la MISMA textura que el cuerpo | `m_Rect.x/y` | **si**, leido |
| la capa tiene textura propia mas pequena (ojos/boca) | alineada **arriba** | **deducido** |

**El rect de la malla es la clave** (aviso de Aaron). El sprite exportado va recortado a su malla
ajustada — la boca de `xiachuanling` sale 60x36 en vez del lienzo 572x732 — y la textura es una
**hoja** que contiene varias capas. La posicion de ese recorte dentro de la hoja esta en el dump del
Sprite, en un rect `(x, y, width, height)` en pixeles de la textura; se localiza buscando el que mide
lo mismo que el PNG exportado. **OJO: en Unity la Y se mide desde ABAJO**, asi que hay que darle la
vuelta (`y_arriba = alto_textura - y_abajo - alto_sprite`).

**Orden de apilado (corregido por el usuario).** El **pelo va ARRIBA de todo**: el flequillo tapa el
borde de los ojos y de la piel. Si va debajo de los ojos/boca se ven pixeles de piel sobre el negro
del pelo. Orden: contorno → cuerpo → brazos → ropa → ojos → boca → **pelo**.

**No pegar la hoja entera.** Una hoja puede llevar MAS de una capa dentro: la boca de `xiachuanling`
mide 60x36 pero el contenido de su hoja ocupa 108x88 (hay mas bocas en la hoja), asi que pegando la
hoja se cuela contenido de mas encima del pelo. Por eso ahora lo normal es pegar el **sprite
recortado en su rect de malla**; la via de la hoja entera queda detras de `--hojas`. Comprobado a
ojo: los artefactos (piel sobre el pelo, flequillo sucio) desaparecen.

Comprobado: montar con los sprites recortados colocados por su rect de malla da el MISMO resultado
que montar con las hojas enteras — **0,26 % de pixeles distintos** (solo bordes, por redondeo);
sin voltear la Y la diferencia era del **72 %**. Es decir: las coordenadas estan bien y ademas
sirven para montar con los recortes (mucho menos peso). Flag del script: `--recortados`.

**Coordenadas por PIXELES (idea del usuario) — `_dl/montar_por_pixeles.py`.** En vez de volcar cada
bundle para leer el rect de la malla (lento: ~40 s por bundle), se busca el sprite suelto dentro de su
hoja **comparando pixeles**, asi que basta con la carpeta del bulk, que es lo que ya esta repartido.

- Optimizacion: correlacion de las mascaras de alfa por **FFT** (numpy) en vez de probar ventanas una a
  una; se prueban los 10 picos mas altos y se valida comparando los pixeles (muchas expresiones
  comparten silueta). Se mide la **fraccion** de pixeles distintos, no el maximo (el maximo da 255 por
  un solo borde y no dice nada). Coste: **0,60 s por bust-up**.
- Resultado en los 120: **120 montados, 0 fallos**, 556 capas colocadas, **37 capas (6,6 %)** con hoja
  propia (esas no se pueden colocar sin el prefab y se marcan). Tiempo total **72 s**.
- Validacion cruzada: en `xiachuanling`, los 7 offsets que saca por pixeles son EXACTAMENTE los del
  dump, y el montaje resultante difiere en **0 pixeles** del montado por dump.
- `--listar` dice que va con que: en `xiachuanling-changfu` hay 21 variantes de ojos y 21 de boca
  repartidas en 7 expresiones (tongchang, xiao, fennu, beiai, jingya, shengqi, huangzhang) mas una capa
  `haixiuxiao-saihong` (rubor).

**Visor de Bust-ups en la app (pestana "Bust-ups").** La misma cuenta, metida en P5X Studio Tools:

- `p5x_studio/p5x_studio/bustups.py` — el motor: troceado de nombres (`partir_nombre`, `paso_de`),
  busqueda por pixeles (`localizar`, piramide ÷16 -> ÷4 -> ÷1 con PIL, **sin numpy**: esta en los
  EXCLUIDOS del .spec para que el binario no engorde), indice de la carpeta de texturas cacheado en
  `cache/indice_texturas.json` (con version, para no reutilizar un indice viejo) y `montar()`.
- `p5x_studio/p5x_studio/datos/bustups.json` (194 KB) — el mapa del emparejado recortado a lo que el
  visor necesita (personaje, ropa y nombres de capa). **Viaja dentro del .exe** (anadido a `datas` en
  el .spec): el visor no depende de tener `_dl` al lado.
- `motor.py` — `bustups_lista`, `bustups_ver`, `bustups_exportar`, `bustups_texturas`.
- `ui_web.py` — los metodos del puente. El PNG viaja como **data URL**: la pagina no puede leer del
  disco y asi al cambiar de expresion no se pelea con la cache del navegador.
- `ui_web/{index.html,app.js,estilo.css}` — pestana nueva: lista de bust-ups, visor, selector de
  expresion, capas con su desvio y boton de exportar. Los textos van en `idiomas.py` (`web_bust_*`,
  en los DOS diccionarios: la paridad es/en se comprueba).
- `tests/test_bustups.py` — troceado, orden de apilado, mapa y montaje real (si hay texturas; la
  carpeta se puede dar con `P5X_STUDIO_TEXTURAS`).

Trampas que costo encontrar (todas cazadas por las pruebas o por el piloto):

- `carpeta_extraidas()` devuelve **texto**, no `Path`: hay que envolverlo.
- El emparejado solo lista **ojos y boca**; el cuerpo, el pelo, la ropa y el contorno se sacan de los
  nombres que haya en la carpeta de texturas (prefijo `<personaje>-<ropa>-`, con la ropa **sin** su
  variante numerica: el JSON dice `changfu01` y los sprites `changfu`).
- El indice tiene que agrupar `<nombre>.png` y `<nombre>_#NN.png` bajo la **misma** clave (el sufijo
  no dice cual es el lienzo y cual el recorte): si no, `localizar` compara una imagen consigo misma y
  devuelve (0,0) en todas las capas.
- El `difiere` se mide **solo sobre los pixeles visibles** y en L sobre RGB: convirtiendo el RGBA a L
  se mezcla el alfa y salen porcentajes de mas del 100 %.

**Tres fallos mas, vistos por el usuario en capturas (arreglados).**

1. **Se mezclaba el retrato con una silueta de CUERPO ENTERO.** Hay bust-ups (jianajun, jianajun2,
   fushanjiadai01/02, y 27 en total con mas de un lienzo) que traen, en las mismas texturas, el
   retrato del dialogo Y una silueta de cuerpo completo (1076x2020). El lienzo se cogia de la capa de
   cuerpo, que era la del cuerpo entero -> el retrato salia en un lienzo gigante con la cabeza en
   negro y las capas sueltas. Ahora el lienzo se **vota entre todas las capas** (`_lienzo_dominante`):
   gana el grupo de tamanos que comparten mas capas (el retrato) y, dentro del grupo, se usa el
   tamano mayor para que ninguna capa se salga. Tolerancia de 4 px por el pixel de extrude de Unity.
   Las capas que no caen en ese lienzo se **dejan fuera** (antes se pegaban arriba, que era peor).
2. **Faltaba la cara.** `jianajun-changfu-benti-tongchang` no es una parte: es la CARA de ese gesto
   (y la del gesto por defecto se llama `tongchang`). Sin clasificarla, la cabeza salia vacia. Ahora
   `benti-<expresion>` -> (expresion, `cara`) y hay paso `face` (bajo los ojos).
3. **Faltaban las gafas y demas adornos.** Censo de las partes sin clasificar en los 120: `yanjing`
   (gafas, 8), `mojing` (gafas de sol, 3), `mask`/`Rmask01`/`mask02`/`Lmask01`/`mianju` (mascaras),
   `maozi` (sombrero), `han`/`lei` (sudor y lagrimas), `hongyun`/`haixiu`/`saihonghunluan` (variantes
   de rubor) y `lian` (cara). Todas tienen ya su paso. Orden final: contorno, cuerpo, brazos, ropa,
   rubor, **cara**, ojos, boca, gotas, mascara, pelo, **gafas**, sombrero (las gafas por encima de
   todo, como pidio el usuario).

Ademas: los adornos (rubor, gotas, mascara, gafas, sombrero) y los ojos/boca/cara son **por
expresion**; si el gesto elegido no los trae, no se cogen de otro (colar el sudor de `juewang` en un
retrato `beiai` daba un 48 % de desvio y se veia). La estructura (contorno, cuerpo, brazos, ropa,
cara, pelo) cae a la capa base o a `tongchang` cuando la expresion no la trae aparte.

Efecto secundario a confirmar: el rubor de `xiachuanling` venia de `haixiuxiao-saihong` (otra
expresion), asi que con `tongchang` ya no se pinta. Si en el juego el rubor va siempre, hay que
decidir si los adornos se filtran o no.

Cuarto fallo, encontrado al medir el lote: la expresion **`0`**. Los sprites del cuerpo por defecto
se llaman `<personaje>-<ropa>-0-benti` / `-0-toufa`, y `0` sale como una expresion mas en la lista.
Al elegirla, los ojos y la boca no caian a `tongchang` y el retrato salia sin cara. `0` y `tongchang`
son ahora respaldos de la cadena de eleccion, y `0` ya no aparece en el selector (es el cuerpo, no un
gesto). En la interfaz el selector lleva una primera opcion **Default** = gesto neutro del juego.

Estado del lote con los arreglos: **120/120 se montan**; 114 con 4 o mas capas y los 6 restantes son
casos legitimos (`lufeier` solo tiene cara, ojos y boca en las texturas; `jianajun`/`jianajun2`/`lizi`
tienen la cara como capa base y su silueta de cuerpo entero queda fuera a proposito).

El caso `aochuncun` de mas abajo no era un hueco de la extraccion: era una errata del nombre (ver
sexto fallo).

Sexto: **la errata del propio juego**. `aochuncun` (con h) es solo el nombre del shader y de tres
assets sueltos en `UI/uitex_s_uaidaofu` (siluetas y contornos de la cabeza); TODOS los sprites de su
retrato (cuerpo, pelo, ropa, contorno, ojos, boca y su propia mascara `benti-mianju`) se llaman
`aocunchun`, sin h, y viven en `UI/uitex_uaidaofu` (1.050 ficheros). El visor buscaba con la grafia
del shader, no encontraba nada y dejaba al personaje con una mascara suelta. Hay una tabla
`ALIAS_PERSONAJE` en `bustups.py` con esa equivalencia (documentada como errata del juego, no como
nuestro error). Con ella: `guaidao01-aochuncun` monta **7 capas** (contorno, cuerpo, ropa, ojos,
boca, mascara y pelo) y su selector ofrece 6 expresiones. Lo que NO se puede saber desde los ficheros
es a quien iban destinadas esas tres siluetas de `uitex_s_uaidaofu`: son del mismo diseno (mismo
sombrero, pluma y rizos), pero van en un juego aparte.

Ademas, el selector de expresiones ahora se calcula **sobre las texturas** y no solo sobre el mapa,
asi que ofrece todas las que existen de verdad (a `xiachuanling` le ha aparecido `haixiuxiao`), y su
primera opcion es el gesto neutro del juego, no `beiai` (que era lo que salia por defecto).

Quinto fallo, el mas gordo: **la ropa con numero**. Hay conjuntos cuyo numero forma parte del nombre
(`gaojuanxing-guaidao01-beiai-yan1`) y otros donde el sprite va sin el (`xiachuanling-changfu-benti`
para la ropa `changfu01`). Se recortaba el numero siempre, asi que en los primeros el prefijo no
casaba, se caia al prefijo `<personaje>-` y el trozo de la ropa se tomaba por la expresion: ojos,
boca y cara se perdian (quedaba solo el cuerpo). Ahora se prueban los dos prefijos, el exacto
primero, tanto al partir el nombre como al recorrer el indice. Medido: ojos 346 -> 386 y boca
350 -> 390 sobre 480 montajes; `gaojuanxing` paso de 1 capa a 4.

Estado del lote tras los cinco arreglos: **120/120 montan**; 97 con 4 o mas capas y 23 con 3, que
son legitimos (el sprite del cuerpo ya trae contorno, ropa, gorro o gafas horneados; `lufeier` solo
tiene cara, ojos y boca en las texturas). Los unicos flojos de verdad son los `aochuncun` (mascara
suelta, por el hueco de extraccion).

El desplazamiento dentro del lienzo de las capas con textura propia vive en el **prefab**, y no se
puede leer: los bundles instalados estan cifrados (`BundleFile is encrypted, but no key was
provided`; el `-t` del motor tampoco exporta GameObjects) y en el vfile no hay bundle de prefab (sus
312 son fuentes y atlas). Los Lua del dump son bytecode compilado, asi que tampoco estan ahi.

**La regla de arriba esta comprobada**: en `jianajun` (cuerpo 984x988, ojos y boca en textura propia
984x788) los rasgos caen en la cara y el bust-up sale completo; en `xiachuanling` (todo el lienzo
572x732) los siete offsets son (0,0) leidos y el montaje coincide con la captura del juego.

**Ojo con el glob de los PNG** (bug que costo dos diagnosticos falsos): `nombre*.png` tambien captura
`nombre-lunkuo.png` (el contorno, que mide lo mismo que el cuerpo) y se cuela como cuerpo → silueta
negra. Hay que buscar nombres EXACTOS (`<nombre>.png` y `<nombre>_#NN.png`).

**Recorte de sprites (aviso de Aaron, confirmado).** AssetStudio y AssetRipper exportan el sprite
recortado a su malla ajustada, asi que el PNG es mas pequeno que la textura y pegarlo en (0,0)
descuadra el montaje. Cada capa se exporta DOS veces (una recortada, una entera) y **no se sabe cual
es cual por el nombre**: el sufijo `_#NN` cae en cualquiera de las dos. En `xiachuanling`, el cuerpo
tiene el nombre limpio = entero 572x732 y `_#77` = recortado 548x720; el contorno al reves: nombre
limpio = recortado 550x721 y `_#53` = entero 572x732. Solucion: elegir por el tamano QUE DECLARA el
dump (`m_Width`/`m_Height`) y tirar el recortado. Comprobado en 4 bust-ups: 11 export enteros y 11
recortados, se eligio el entero en todos. Script de la comprobacion: `_dl/verificar_recorte.py`.

**Lo que falta para la funcion de P5X Studio:** (a) el visor en si (pestana o ventana: Original /
con Shader, y boton de exportar el montado); (b) el alias de los 96 sin emparejar (58 son personajes
cuyo bust-up no esta con ese nombre en los sprites); (c) el relleno de las 8 paradas lo hace el C# de
`UIMuitipleGradientParam`, no el GLSL (con 4,2/255 de desviacion se puede dar por bueno); (d) si se
quiere el offset EXACTO de ojos/boca de todos los personajes, hay que sacar la clave de los bundles
(UnityCN) para leer los prefab.

---

## RETOQUE DEL SHADER E INTERRUPTOR EN EL VISOR — 2026-10-05

El usuario vio la hoja de los 120 retratos sombreados y la encontro "amarilla y tostada, como el
primer intento". Comparando el sombreado **contra los JSON de cada personaje** salieron dos fallos
reales (los dos ya corregidos):

**Fallo 8: las paradas del degradado se reconstruian equiespaciadas.** `muestrear_8()` evaluaba el
Gradient de Unity en 8 puntos 0, 1/7 ... 1 y se los pasaba al shader como `_GradientColors` /
`_GradientPositions`. Eso solo coincide con degradados de **2 paradas**; el C# en realidad le pasa las
paradas del Gradient **tal cual** (sus propios tiempos de 16 bits) y rellena las ranuras de sobra
repitiendo la ultima. De los 120 retratos, **100 tienen 3 o mas paradas** (hasta 7), asi que estaban
desplazadas. Verificado: con las paradas reales, los colores `#FF5200` y `#FFEC93` que el shader ve
en `lizi` son los que declara su JSON.

**Fallo 9: la rampa de alfa se leia de las claves de COLOR.** El GLSL saca `_GradientAlphaBottom/Top
Position` de las claves **de alfa** (`atime`). En `xiachuanling` las de color estan en 0,30 / 0,45 /
1,00 y las de alfa en 0,006 / 1,00: la rampa era otra. Se ve en la comparacion contra la referencia:
1,37/255 de desviacion media antes, 0,00/255 despues.

**Y el tope (el retoque propiamente dicho).** Los personajes con `GraSaturation` / `GraContrast` altos
(hasta 2,91 y 3,31) disparan el tono del degradado fuera de rango: en `lizi` el azul llega a **-0,02**
y `gra` a 2,8 sobre 1. El retrato acababa aclarado a amarillo (los blancos a `#FEF3A8`). Se recorta el
tono del degradado a [0,1] (constante `TOPE` en `p5x_studio/sombreado.py`): los personajes cuyos
parametros ya estaban en rango **no cambian** y los otros dejan de tostarse. El tono base se deja tal
cual (el GLSL no lo recorta) y el resultado final se acota al guardar, como el framebuffer del juego.

Medido sobre los 12 primeros: la calidez (R-B) que suma el shader pasa de **+0,146 a +0,098** de media,
con el caso del que hay captura del juego (`changfu01-xiachuanling`) intacto: **4,2/255** de la piel de
la captura. Sin las tres cosas se quedaba en 29/255.

**El interruptor en la herramienta.** Modulo nuevo `p5x_studio/sombreado.py` (el mismo shader, **sin
numpy**: el tono base es `A*color + D*luminancia + E` y sale exacto en el bucle, el degradado va por
tabla de 1024 niveles). Los 120 juegos de parametros viajan en `p5x_studio/datos/shaders.json`
(65,5 KB), que entra en el `.exe` por el `datas` del `.spec` sin tocar nada. `montar(..., shader=True)`
guarda el PNG aparte (`<clave>_<expresion>_shader.png`) para poder alternar; `bustups_ver` /
`bustups_exportar` del motor y de `ui_web` llevan el flag, y el visor tiene la casilla **Shader** al
lado del selector de expresion. Coste: **+0,35 s** por retrato (montar 0,4-0,9 s, con shader 0,75-1,22 s).

**Verificacion.** El port de la app contra la implementacion de referencia (numpy): **0,00/255** de
desviacion media en 4 retratos (1/255 como maximo, por redondeo). Suite de bust-ups en verde con 9
comprobaciones nuevas del shader. La hoja rehecha esta en
`_dl/prueba_sombreado/hoja_shader_retocada.png`, y las tiras sin/con shader en las mismas carpeta
(`arreglo_shader_*.png`).

**Pendiente de decision del usuario:** los retratos con degradado muy caliente en su propio JSON
(`changfu01-lizi`, `changfu-xindaozhen`, `changfu01-jintianheyan`) siguen llevando un tinte ambar
fuerte aunque ya no se aclaren a amarillo. Su JSON lo dice asi (`#FF5200` en el degradado, `GraS 2,21`),
y no hay captura del juego de esos personajes para comprobarlo: hay que mirarlos en el juego con la
casilla puesta y sin ella.

### CORRECCION: la rampa de alfa (el amarillo que ve el usuario)

La comparacion del usuario, medida: piel del juego `#E9D3B7` (calidez +49,3) contra la nuestra
`#E8D0B1` (+55,1) — rojo casi igual, **azul 6,4 abajo** (7,8 en las sombras). Es el "ligeramente mas
amarillo".

Causa: la rampa de alfa del degradado. El GLSL la saca de `_GradientAlphaBottomPosition` y
`_GradientAlphaTopPosition`, dos **posiciones que el JSON no trae** (las calcula el C#). Mi
"correccion" de la tanda anterior las tomaba de las paradas de la curva de alfa. Medidas las dos
opciones contra la captura del juego:

| posiciones de la rampa | piel | distancia | azul |
|---|---|---|---|
| claves de ALFA (lo que habia) | `#EBD4B4` | 4,1/255 | -7,7 |
| claves de COLOR (correcto) | `#ECD7BC` | **2,8/255** | **+-0,0** |

Con las de color el azul cae exactamente en el de la captura. O sea: aquel cambio fue una regresion
y es la causa del amarillo. Lo que si era correcto de aquella tanda son los **valores** de la rampa
(`GradientAlphaBottom`/`Top`: 0,274 y 1,0 en xiachuanling), no sus posiciones.

Comprobado de paso, por si acaso: el espacio de color. Gamma (lo que hay) 0,0/255 contra la
referencia; lineal a medias 7,7/255 y lineal completo 7,0/255. **Se queda gamma**, y el tope del
degradado no toca a este personaje (0,1/255).

Anotado para no repetirlo: el JSON no tiene `GradientAlphaBottomPosition`/`TopPosition`, asi que esto
es **medido contra la captura**, no deducido de los ficheros. No volver a cambiarlo a las claves de
alfa.

---

## INGENIERIA INVERSA DEL SHADER: LOS VALORES ESTAN EN EL CODIGO (2026-10-05)

El usuario tenia razon: llevaba tandas deduciendo `_GradientAlphaBottomPosition` /
`_GradientAlphaTopPosition` de los JSON y de medidas contra capturas, y las dos veces me equivoque.
Estos no son datos del fichero: los escribe el C# en cada frame. Se leen del binario.

### Metodo (sirve para cualquier propiedad del shader)

1. `Il2CppDumper.exe Client/pc/GameAssembly.dll Client/pc/P5X_Data/il2cpp_data/Metadata/global-metadata.dat _dl/il2cpp_out`
   -> `dump.cs` (34,5 MB), `script.json` (nombres -> RVA), `stringliteral.json` (literales -> RVA).
2. En `dump.cs`, buscar la clase que consume el ScriptableObject: `MUEngine.UI.UIMultipleGradient`
   y su `UIMultipleMaterial`. Cada metodo trae su `RVA` (direccion virtual = 0x180000000 + RVA).
3. Desensamblar con **capstone** (no hizo falta Ghidra ni Unity): `_dl/desensamblar_gradiente.py`
   anota los `lea` RIP-relativos con el literal de `stringliteral.json`. Ojo: `stringliteral.json`
   trae **RVA**, no VA, y hay que usar la **longitud real** de la instruccion al calcular el destino
   (`movss xmm7,[rip+d]` mide 8, no 7: con 7 se lee un float desalineado y sale basura).
4. Buscar quien referencia cada literal: `_dl/buscar_usuarios_propiedades.py` barre los `48 8d ??`
   del .text. Cada propiedad del shader aparece dos veces: una en `SetParamDefault` (valores por
   defecto) y otra en `UIMultipleMaterial.Update` (valores de verdad).
5. Para cada `SetFloat`, mirar de donde sale el valor: `_dl/de_donde_sale_cada_valor.py`.

### Lo que dice el codigo

`UIMultipleMaterial.Update` (RVA 0x23C3DA0) reparte:

| propiedad | de donde sale |
|---|---|
| `_EffectFactor` `_Brightness` `_Saturation` `_Contrast` | `param` + 0x18, 0x1C, 0x20, 0x24 |
| `_GradientAlphaTop` `_GradientAlphaBottom` | `param` + 0x28, 0x2C |
| `_GraBrightness` `_GraSaturation` `_GraContrast` | `param` + 0x30, 0x34, 0x38 |
| `_GradientColors` | `this.gradientColors` (+0x50) |
| `_GradientPositions` | `this.gradientPositions` (+0x58) |
| **`_GradientAlphaBottomPosition`** | **0.0 constante** (`xorps xmm2, xmm2`) |
| **`_GradientAlphaTopPosition`** | **1.0 constante** (constante del .rdata en 0x1834523BC) |

Los arrays `gradientColors`/`gradientPositions`/`gradientAlpha`/`gradientAlphaPositions` los cuece el
C# desde el `Gradient` del ScriptableObject: son las claves **ordenadas por tiempo**, con las ranuras
de sobra repitiendo la ultima. `_ColorCount` y `_AlphaCount` se asignan pero **el GLSL no los usa**
(no aparecen en el shader), asi que la evaluacion es sobre las 8 ranuras.

### Consecuencias

* La rampa de alfa va de 0 a 1 con los valores `GradientAlphaBottom` / `GradientAlphaTop` del JSON.
  Antes la ponia entre las paradas de las claves de color (un ajuste contra la captura del juego que
  cuadraba por casualidad) y antes aun entre las de alfa. Las dos estaban mal.
* El "tope" (recortar el tono del degradado a [0,1]) **no existe en el juego**: lo meti para tapar
  el tono tostado, que venia del error de la rampa. Fuera (`TOPE = False`).
* La captura del juego no sirve como referencia fina: es una pantalla compuesta, con el post-proceso
  del juego encima. El montaje propio es el sprite crudo. Diferencias de 3-4/255 entre ambos son
  esperables y **no** son motivo para cambiar el modelo.

---

## EL INDICE DE BUNDLES Y LOS BUST-UPS SIN CARA (2026-10-05)

### El indice que une los bundles

Esta en el propio juego: **`104/zeusBundleManifest.txt`**, el `AssetBundleManifest` de Unity.

    16.845 bundles, 10.520 con dependencias, **136.793 aristas**

Analizado a `_dl/zeus_manifest.json` (2,7 MB) con `_dl/sub_parse_manifest.py`. Los pares
asset -> bundle quedaron en `_dl/assetmap_pairs.json`, y el analisis de los bust-ups en
`_dl/bustups_indice_informe.json` y `_dl/cara_fuera_del_visor.json`.

### Por que faltaban capas

* El extracto de retratos del visor miraba **80 bundles**; los bust-ups necesitan texturas de **118**.
  Faltaban 39, casi todos `uitex_*` de ropa y de personaje (undongfu, zhuang02, chushifu, idaofu02...).
* `p5x_studio/p5x_studio/datos/retratos.json` pasa de 80 a **119 bundles**, y el extracto se ha
  rehecho: 5.402 PNG, 0 fallos. Con eso entran las texturas de cara de 11 de los 15 bust-ups que
  salian a cara descubierta.

### Los 15 que siguen saliendo sin rostro, y por que

Son `guaidao01-bainiao`, `guaidao01-longchuanxueshi`, `guaidao01-qinyinmianju`, `guaidao01-qinyinsp`,
`guaidao01-qinyintoufa`, `guaidao01-tengchuanxueshi`, `guaidao01-xisenyangcai-face`,
`guaidao01-yemaopengzi01/02`, `guaidaofu-chibo`, `guaidaofu01-qinyin`, `guaidaofu02-chibo`,
`sifu01-lizi`, `yongzhuang-lizi`, `yongzhuang-yemaopengzi`.

Montados y mirados uno a uno: montan (contorno, cuerpo, ropa, mascara, pelo, sombrero) pero **la cara
sale blanca y sin rasgos**. Los ficheros que hay en el extracto para `bainiao` son
`bainiaochengsi-guaidaofu-benti{,-mianju,-toufa,-yifu,-lunkuo}.png`: el `benti` de estos personajes es
el cuerpo **con la cara ya en blanco**, y el rostro es una textura **compartida** que no sale de su
propio nombre (es el mismo caso que el usuario ya describio: "las texturas que comparten rostro").

Averiguado de paso, y probado: el mapa usa el nombre **corto** (`bainiao`) y los assets el **completo**
(`bainiaochengsi`), y ademas con otra ropa (`guaidao01` vs `guaidaofu`). Se probo a que `_prefijos()`
admitiera el nombre pelado (sin ropa) para alcanzar `bainiaochengsi-...`, pero **se revirtio**: la prueba
de la suite exige que los prefijos cierren con guion (es lo que corta el nombre del sprite), y ademas no
arreglaba nada, porque lo que falta no es el nombre del cuerpo sino de donde sale el rostro compartido.

### Lo que queda para el usuario

1. Decidir como se resuelve el rostro compartido de esos 15 (mirarlo a mano en el juego, o sacarlo por
   dependencias del manifiesto). Es lo unico que falta para que no quede ningun busto sin cara.
2. Re-extraer retratos en la herramienta al recibir el .exe nuevo: `datos/retratos.json` viaja dentro y
   ahora pide 119 bundles, pero la carpeta del usuario sigue con lo viejo hasta que lo pulse.

---

## RESPALDO DE CARA POR FAMILIA DE ROPA (2026-10-05, tras el analisis del manifiesto)

### Que decia el analisis del subagente, y que era cierto

El informe `_dl/informe_bustups_indice.md` corrige mi primera lectura: **seguir el grafo de dependencias
no arregla nada**, porque los bundles de textura de los bust-ups declaran `deps=[]`. Las dos causas
reales eran la lista corta de bundles (ya ampliada a 119) y los **nombres irregulares**.

### La causa que quedaba, ya resuelta en codigo

Los trajes de ladron fantasma llevan la **cara en OTRA ropa del mismo personaje**:

    mapa:  guaidao01-bainiao -> personaje=bainiaochengsi, ropa=guaidaofu
    assets: bainiaochengsi-guaidaofu-benti{,-lunkuo,-mianju,-toufa,-yifu}   (sin ojos ni boca)
            bainiaochengsi-changfu-beiai-yan1 / -zui1                      (los ojos y la boca, en changfu)

El mapa esta BIEN (nombre completo incluido); lo que falla es que la cara no esta en esa ropa.

Implementado en `bustups.py`:

* `PASOS_PRESTABLES` = estructura + ojos y boca. Los adornos (sombrero, mascara, rubor) NO se prestan:
  son de cada traje y prestarlos queda peor que dejarlos fuera.
* En `capas_de`, si los prefijos exactos dejan pasos vacios, se busca en el **mismo personaje con
  cualquier ropa** y esas capas entran como `base` (su expresion no es la del bust-up y el selector no
  acepta gestos que no tocan). Solo se rellenan pasos vacios, asi que nada que ya funcionaba cambia.
* En `prefijos_retratos`, se guarda el personaje entero **solo cuando su ropa no trae cara**; hacerlo
  siempre multiplica el extracto (de 5.400 a 130.000 ficheros en el conteo del propio extracto).

Verificado montando los 15 y mirandolos: **los ocho que se pudieron comparar pasan de
`outline,body,clothes,mask,hair` a incluir `eyes`, `mouth` y la cara, bien alineada** (revision visual
sin rasgos desplazados). Suite `OK` y los 120 siguen montando `120/120`, 0 fallos.

### Lo que falta, y es de inventario, no de codigo

El respaldo funciona **contra el volcado completo** (`extracted/textures`), pero no contra el extracto
de retratos: para `bainiaochengsi-changfu-beiai-yan1` y sus equivalentes, **el asset no esta en ninguno
de los 119 bundles** de `datos/retratos.json`. Comprobado: los prefijos son correctos (141, con
`bainiaochengsi-` y `qinyin-` incluidos) y el nombre pasa el filtro, pero el fichero no se escribe.

Siguiente paso: sacar del indice del volcado (`_dl/indice_bulk.json`, nombre de asset -> rutas con la
carpeta del bundle) que bundle guarda la cara de cada uno de esos personajes y sumarlos a la lista.

### El ultimo paso, con el punto exacto donde se corta

El extractor filtra con `organizar(salida, destino, "ui", solo=prefijos)` sobre los 119 bundles, y los
prefijos son correctos (141, con `bainiaochengsi-` y `qinyin-` dentro): el nombre
`bainiaochengsi-changfu-beiai-yan1` pasa el filtro.

Lo que no cuadra es la **agrupacion del volcado**: la ruta del asset es
`extracted/textures/UI/uitex_bainiao/bainiaochengsi-changfu-beiai-yan1.png`, pero en el juego
**solo existe un** bundle con ese nombre (`158/uitex_-bainiao32bec548.bundle`, que ya esta en la lista)
y no produce ese fichero. O sea: la carpeta `UI/uitex_bainiao/` del volcado NO se corresponde con el
bundle `uitex_-bainiao...`, sino con otro criterio de agrupacion.

Siguiente paso, concreto: averiguar la regla con la que el volcado nombra sus carpetas de UI (mirar
`organizar` en `lote.py`) y, con ella, que bundle guarda la cara de cada uno de esos personajes; o
barrer los nombres de asset de los 16.535 bundles buscando `<personaje>-<otra ropa>-yan1`. Con esos
bundles en `datos/retratos.json`, el respaldo de cara ya implementado los montara sin tocar mas codigo
(probado contra el volcado completo: los ocho comparables salen con ojos, boca y cara bien encajada).

Nota: `extraer_retratos` informa `ficheros` contando TODO el arbol de `extracted/` (`rglob` sobre
destino), no solo `portraits`: de ahi los 130-135 mil de los ultimos informes. La carpeta `portraits`
sigue en 6.762 PNG / 226 MB.

---

## LA VERSION GLOBAL (STEAM) DEL JUEGO (2026-10-05)

El usuario desinstalo la version china y tiene la **global (Steam)**. La carpeta china que usaba el
proyecto (`C:/Users/Lukas/Downloads/P5X`) ya no existe.

### Donde esta y como es

```
C:\Program Files (x86)\Steam\steamapps\common\P5X\
    P5X.exe, P5XLaunch/
    client/                     <- en minuscula (la china era `Client`)
        OuterPackage/
            Bundles/Windows/<num>/*.bundle      15.469 bundles (la china tenia 16.535)
            Config/Windows, Lua/Windows, Media/, ZeusSetting/
        pc/GameAssembly.dll, P5X_Data/il2cpp_data/Metadata/global-metadata.dat
```

Lo importante: **nombres y numeracion de bundle identicos** a la china
(`158/uitex_-bainiao32bec548.bundle`, `105/assetMapName.txt`, `083/Windows` con el manifiesto, las
200 carpetas numeradas). O sea: la lista de 119 bundles de `datos/retratos.json` sigue valiendo tal
cual en la global. Lo unico que fallaba era **encontrar** la carpeta (esta dentro de Steam) y que la
comparacion de rutas de Python distingue mayusculas (`Client` != `client`).

### Lo que se toco (`p5x_studio/ajustes.py`)

  - `SUBRUTAS_BUNDLES`: se prueban, en orden, `Client/OuterPackage/Bundles/Windows`,
    `client/...`, `OuterPackage/Bundles/Windows` y `Bundles/Windows`. `SUBRUTA_BUNDLES` se mantiene
    como la primera, por compatibilidad. Nuevo `subruta_bundles(juego)` y `detectar_juego()`,
    `carpeta_bundles()` y `resolver_carpeta_juego()` pasan por el.
  - `_bibliotecas_steam()`: lee `libraryfolders.vdf` (varias bibliotecas, otro disco) y devuelve las
    carpetas `steamapps/common`, sin repetir. `NOMBRES_JUEGO` prueba `P5X`,
    `Persona5ThePhantomX`, `Persona 5 The Phantom X`, `Persona5X`, `PhantomX`.
  - `resolver_carpeta_juego()` compara sin distinguir mayusculas: si el usuario senala la propia
    carpeta de bundles de la global, antes se rechazaba.
  - Pruebas nuevas: `tests/test_version_global.py` (14 comprobaciones, con carpetas de mentira).

### Lo verificado contra el juego real

  - `detectar_juego()` encuentra sola `C:\Program Files (x86)\Steam\steamapps\common\P5X` (sin
    configuracion previa). Dentro del .exe publicado, `estado()` devuelve esa misma carpeta y
    `carpeta_bundles` con los 15.469 bundles.
  - El motor lee los bundles de la global: extraccion de los 119 bundles -> 7.012 PNG, **0 fallos**,
    137 s, y deja la marca de extracto COMPLETO.
  - **La global ARREGLA los bustos sin cara.** Su `uitex_bainiao` trae 76 texturas `bainiaochengsi-*`
    (incluidas `bainiaochengsi-changfu-beiai-yan1/2/3` y `-zui1/2/3`); la china no tenia ninguna. Los
    15 personajes que salian sin rostro ahora montan 7-8 capas con `eyes`, `mouth` y `face`:
    **0 de 15 sin cara**, y comprobado a ojo en la hoja (8 de 8 con cara completa, 0 en blanco).

### Lo que queda abierto

  - **Tres bust-ups incompletos en la global**, porque su bundle NO esta en la lista de 119 (que se
    hizo con la china): `changfu01-xiaochurihe` (su `benti` no viene, solo los ojos/boca de otra
    ropa), `sifu01-zhenhexinlv` y `sifu02-zhenhexinlv` (personaje `zhenhe`: 0 texturas en el
    extracto; "no layer could be read" en el visor). No es un fallo de codigo: es que la global es
    mas pequena (15.469 bundles frente a 16.535) y faltan bundles. Con ellos anadidos a
    `datos/retratos.json`, el codigo ya los montara.
  - **[PERDIDA, error mio]** Al probar la extraccion pase `destino = extracted` en vez de
    `extracted/portraits`; `extraer_retratos` limpia su destino, asi que se borro **`extracted/textures`
    (el bulk entero, 63 GB, 118.230 PNG, 1 h 38 min de trabajo)** y el extracto chino de retratos.
    No afecta al visor (lee `portraits`, que se rehizo desde la global, y esta mejor que antes porque
    trae las caras), pero el bulk hay que rehacerlo desde la pestana *Bulk textures* si se quiere
    (63 GB, ~1 h 40 min). Anotado aqui para no repetirlo: **nunca pasar `extracted` como destino de
    `extraer_retratos`; el destino es `extracted/portraits`.**

---

## EMPAQUETADO 0.0.2 BETA (2026-10-05)

  - `ajustes.py`: `VERSION = "0.0.2-beta"` (era `1.0.0-beta`; el usuario pidio el numero 0.0.2).
    La version se ve en el **titulo de la ventana** (`ui_web.arrancar`, `P5X Studio · Tools <version>`)
    y viaja en `motor.estado()["version"]`. Comprobado arrancando el .exe: `version = 0.0.2-beta`.
  - `README_TOOLS.md`: cabecera 0.0.2 y seccion "New in 0.0.2"; **las dos versiones del juego**
    (china y global/Steam) y que la global se detecta sola leyendo `libraryfolders.vdf`; **seccion
    nueva del visor de bust-ups** (120 retratos, capas, shader sacado del juego, Extraer retratos
    ~220 MB frente a los 63 GB del bulk); fila de `portraits/` en la tabla de carpetas; fila
    **Bust-ups** en la tabla de pestanas.
  - `.exe` reconstruido: **22.315.349 B** (5 oct 18:34), en el escritorio y dentro del zip.
  - Paquete: `C:\Users\Lukas\Desktop\P5X-Studio-Tools-0.0.2-beta-win64.zip`, **22,0 MB**, 2 entradas
    (`P5X Studio Tools/P5X Studio Tools.exe` + `P5X Studio Tools/README_TOOLS.md`), igual que el
    1.0.0 anterior. **NO lleva `extracted/`, `portraits/`, `cache/`, `engine/` ni `tools/`**: eso lo
    genera la app (es lo que la mantiene ligera). El usuario lo pregunto expresamente; comprobado
    antes de empaquetar (carpeta de preparacion limpia, `du` 22 MB).

### Limpieza hecha

  - Borrado (con su visto bueno) el `extracted/UI/` suelto que dejo la extraccion mal dirigida:
    4.710 PNG redundantes. `extracted/` queda con `_listo.json` y `portraits/` (7.012 PNG, marca
    `{"completo": true, "png": 7012}`). Queda un `_listo.json` **viejo en la raiz** de `extracted/`
    (de 06:36, dice 135.375): no lo lee nadie (el visor lee el de `portraits/`), se deja como esta.
