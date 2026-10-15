# QUÉ PUEDE CARGAR UNITY HOY — y qué necesita trabajo

Referencia rápida para trabajar **a mano** en la PC. Estado verificado el 2026-09-27.
Todo lo de abajo está medido sobre el proyecto real, no son estimaciones.

## 1. Los proyectos que hay

| Carpeta | Tamaño | Para qué sirve |
|---|---|---|
| `unity_projects/kotone/ExportedProject` | **3,3 GB de Assets** | **El proyecto bueno.** Kotone (PC079) + wonder + escenario + timeline |
| `unity_projects/scene_full` | 3,1 GB | Export grande del escenario |
| `unity_projects/scene_tl005` | 545 MB | Prueba de otro timeline |
| `unity_projects/PC063_full` | 146 MB | Prueba del arreglo de rig (tiene su propio `P5XFixRig.cs`) |
| `unity_projects/_shaders` | 4,9 MB | Los **425 shaders** del juego desofuscados (referencia) |

Versión: **Unity 2022.3.49f1** — la misma con la que exporta AssetRipper. No cambiar.

## 2. Qué carga Unity ahora mismo (recuentos reales)

| Categoría | Cuánto | ¿Se ve / funciona? |
|---|---|---|
| Animaciones `.anim` | **724** (+9 en `AnimationClip/`) | ✅ se muestrean; `PC079_01@*`, `wonder_uniform@*`, `PC063_thief@*` |
| Mallas | 36 | ✅ cargan con huesos y pesos |
| Materiales | 84 | ✅ migrados al toon propio (`P5XToon`) |
| Texturas | 167 | ✅ vinculadas por nombre (arreglo estricto, idempotente) |
| Avatares / AnimatorController | 3 / 3 | ✅ humanoides, funcionan |
| Prefabs | 36 | ⚠️ **solo huesos** — ver 3.1 |
| MonoBehaviours (timeline, diálogos) | 169 | 📖 se leen como datos: guion, cámara, audio |
| Escenas `.unity` | 1 | ⚠️ el escenario inyectado, **sin personajes dentro** — ver 3.2 |
| Menús propios en `P5X/` | 6 | ✅ ver sección 4 |

## 3. Lo que NO carga tal cual (y por qué)

**3.1 Un personaje visible — el prefab es solo el esqueleto.**
`PC079_01.prefab`, `wonder_uniform.prefab`, `PC063_02.prefab` tienen **0 `SkinnedMeshRenderer`**.
AssetRipper los tira porque los scripts de `MUActor` quedan como stubs (sin campos serializados).
Si arrastras un personaje a la escena ves **huesos y nada más**.
→ *Resuelto*: la malla se reconstruye leyendo el manifiesto del rig (`*_wholeexport_rig.prefab`:
`mHighRootBoneName` + `mHighMeshBoneNames` + `mHighMeshMaterials`). Lo hace el capturador y el
**menú de modo manual** (sección 4).

**3.2 El escenario sale en magenta al abrirlo a mano.** ✅ **Arreglado y medido.**
El bundle del escenario no exporta los materiales reales (GUID placeholder → `InternalErrorShader`):
**34 de las 63 referencias de material** están rotas. El capturador lo arreglaba *en memoria* antes de
renderizar (por eso los MP4 salían limpios), pero al abrir la escena en el Editor nunca se aplicaba.
El menú de modo manual ahora lo arregla **en la propia escena** antes de guardarla (sustituye por
`Standard` y rescata textura por material o por nombre de objeto/malla).
Medido sobre el mismo encuadre: **magenta puro 1,612 % → 0,000 %**.

**3.8 El escenario trae su propia `Main Camera`.** ⚠️ Trampa real, ya resuelta.
La escena exportada del juego incluye una cámara llamada `Main Camera` con la etiqueta `MainCamera`.
Con dos cámaras etiquetadas, `Camera.main` (y la **Game view** al darle a Play) elegía la del
escenario, así que se veía la arquitectura y **los personajes quedaban fuera de cuadro** — parecía
que la escena estaba mal montada cuando en realidad estaba perfecta (24 `SkinnedMeshRenderer` con
malla, 67 huesos, materiales y actores activos, verificado en el YAML).
→ *Resuelto*: el menú de modo manual **desactiva** la cámara del escenario al montar (queda
`m_Enabled: 0` en el fichero, reversible) y el menú de captura busca `cam_manual` **por nombre**, no
por etiqueta.

**3.3 El shader original del juego no se puede usar.** Del `shaders.bundle` solo se recuperó el
bloque `Properties` (119 propiedades); el HLSL va compilado en el binario. Se usa el toon propio
`P5XToon.shader` (contorno, corte toon, SDF de cara) — que es lo que se ve en los MP4.

**3.4 La escena real del evento (Tartarus) no está en el cliente instalado.** El escenario
inyectado es Iwatodai (`ysc_tianshouge_shiwai_wyc`). El barrido por posición (x≈279 / z≈284) quedó
en 610/1598 con 39 candidatos.

**3.5 La cara no se anima desde los clips.** De **724 `.anim`, 0 tienen curvas de blendshape**: la
animación facial va por un sistema de runtime que no tenemos. La palanca real es el material
(SDF `_FaceShadowTex`), y ya está aplicada.

**3.6 Faltan 7 texturas de personaje** (no existen en los bundles que tenemos):
`PC079_01_eyelid` + `wonder_uniform_{eye,eyelid,cheekred,hair,bottom,shoes}`. Son detalles finos
(esclerótica, mejillas): el render funciona sin ellas.

**3.7 El timeline no es un TimelineAsset de Unity.** `TL_P3P_Event_side_prologue_04_04.playable` es
un MonoBehaviour con los datos; no se puede abrir en la ventana Timeline. El guion se evalúa por
código (`P5XTimelineData.cs` + el evaluador del capturador).

## 4. Modo manual — menús disponibles en la barra `P5X/`

### Lanzador: `unity.bat` (en `C:\Users\Lukas\p5x-datamining\`)
Doble clic = menú. O por línea de comandos:

| Comando | Qué hace |
|---|---|
| `unity.bat abrir` | Abre el proyecto en el Editor (GUI) — **es lo que quieres para trabajar a mano** |
| `unity.bat escena` | Monta la escena manual en lote y luego abre el Editor |
| `unity.bat captura` | PNG de la vista de `cam_manual` |
| `unity.bat gate` | Gate rápido: 24 frames barriendo los 52 s (~1 min) |
| `unity.bat render` | Render completo del timeline, 1584 frames (~37 min) |

### Menús de Unity (barra `P5X/`)

Con el proyecto abierto, arriba:

| Menú | Qué hace |
|---|---|
| `P5X/modo manual: montar actores en la escena abierta` | Suelta **Kotone y wonder con malla** en la escena (**11 y 13 partes** skinneadas; medido: Kotone 1,08×1,68×1,01 m, wonder 1,05×1,82×0,99 m), les pone un **AnimatorController con su clip** (para darle a Play), añade **cámara con el encuadre real del timeline** y luz con el ambiente del juego, arregla los materiales del escenario, **desactiva la cámara del escenario** y **guarda la escena** en `Assets/Scenes/Manual_Kotone_Wonder.unity` |
| `P5X/modo manual: abrir la escena manual` | Abre esa escena guardada |
| `P5X/modo manual: capturar la vista de la camara a PNG` | Un fotograma desde `cam_manual` → `media/cinematics_capture/manual/` (registra en el log qué cámaras hay y cuál usa) |
| `P5X/asignar shader toon a los materiales` | Idempotente. Se ejecuta tras re-exportar |
| `P5X/arreglar texturas (estricto)` | Idempotente. Vincula las texturas por nombre |
| `P5X/capture escena kotone-wonder` | El render por lotes del timeline (52 s) |

### Flujo recomendado en la PC
1. **Doble clic en `C:\Users\Lukas\p5x-datamining\unity.bat`** → opción [1] (abrir). Equivale a
   `unity.bat abrir`. La primera vez tarda unos minutos (importa 3,8 GB y compila shaders); las
   siguientes abre en segundos porque la caché (`Library/`, 439 MB) ya está hecha.
   *Alternativa por Unity Hub*: Add → Add project from disk → `unity_projects\kotone\ExportedProject`
   (versión 2022.3.49f1).
2. Abre en el Project la escena del escenario:
   `Assets/GeneratedRes/Scene/PC/ysc_tianshouge_shiwai_wyc/ysc_tianshouge_shiwai_wyc.unity`
3. Barra **P5X** → `modo manual: montar actores en la escena abierta`.
   Aparecen `MAN_PC079_01`, `MAN_wonder_uniform`, `cam_manual` y `luz_manual`.
4. **Play** para ver la animación (cada actor lleva su clip). Para cambiar de clip: selecciona el
   actor y usa la ventana **Animation**, o pon un clip de `Assets/` en el AnimatorController.
5. Mueve `cam_manual` a tu gusto, o selecciona un objeto y usa **Ctrl+Shift+F** para encuadrar.
   El encuadre por defecto es el del timeline en t=25,5 s (wonder de espaldas en primer plano,
   Kotone al fondo): es el real de la cinemática. Para cambiarlo, edita la constante `T_MANUAL`
   al principio del bloque "MODO MANUAL" en `P5XKotoneCapture.cs`.
6. `P5X/modo manual: capturar la vista...` para un PNG suelto. Para vídeo: graba la ventana Game
   (OBS) o usa el pipeline por lotes.

### Verificación de que esto funciona (hecho, no supuesto)
Render de la escena manual guardada, sin pasar por el pipeline:
`media/cinematics_capture/manual/vista_20260927_044534.png` → **los dos personajes con textura**
(wonder de espaldas con chaqueta mostaza, capucha crema, vaqueros oscuros y zapatillas rojas;
Kotone de frente con pelo castaño y uniforme negro con detalles rojos), el escenario visible y
**magenta puro 0,000 %**. Medición objetiva de píxeles mostaza: 0,072 % en el render del pipeline
→ **0,448 %** en el manual (wonder está más cerca), lo que confirma que la malla y las texturas
están de verdad, no solo "en el log".

### Reglas de convivencia con el proyecto
- **Nunca edites un `.meta` a mano**: rompe el parser YAML de Unity (`Parser Failure at line 11`).
  Los shaders se asignan por API, nunca escribiendo el `.meta`.
- Si vuelves a exportar con AssetRipper, **borra `Assets/Editor/` en cada export**: los scripts
  están respaldados en `_dl/editor_good/` (verificados por hash) — cópialos de vuelta.
- El proyecto es **Built-in RP** (venía de URP y se portó). No metas paquetes de URP.
- Los detalles sin textura salen **magenta** (`255,0,255`): es la señal de "falta material", no un
  fallo del render.

## 5. Qué merece trabajo, por orden de lo que se nota

1. **Escena manual con el escenario + actores** — ✅ hecho (este documento).
2. **Tartarus (fase E)**: el fondo real del evento. Barrido por posición: 610/1598, 39 candidatos
   en `_dl/tartarus_scan.json`.
3. **Texturas de cara que faltan** (7) y afinar el SDF. Impacto fino.
4. **F6 cobertura**: los 13 capítulos — el pipeline ya funciona; es encadenar escenas.
5. **F5 texto/subtítulos**: los SN de las líneas ya están localizados (`P3R021229`…`P3R021237`).

## 6. Comandos útiles desde consola (batch)

```bash
# el render completo del timeline (52 s, ~37 min) + audio
cd /c/Users/Lukas/p5x-datamining/unity_projects/kotone/ExportedProject
"/c/Users/Lukas/Unity/2022.3.49f1/Editor/Unity.exe" -batchmode -quit \
  -projectPath "C:/Users/Lukas/p5x-datamining/unity_projects/kotone/ExportedProject" \
  -executeMethod P5XKotoneCapture.Run -logFile "C:/Users/Lukas/p5x-datamining/_dl/a_full.log"

# el gate de 24 frames (barrido rápido de 52 s, para validar antes de gastar el render)
#   -> -executeMethod P5XKotoneCapture.RunGate

# montar la escena manual sin abrir la GUI
#   -> -executeMethod P5XKotoneCapture.MontarManual
```
Los mismos métodos están en los menús, así que en la GUI es un clic.
