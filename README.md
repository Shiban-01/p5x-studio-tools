# P5X Datamining — entorno listo

> **ESTADO 2026-09-24: objetivo vídeos+audio COMPLETADO.**
> `media\videos_mp4\` → **346 MP4 (3.5 GB)** de los 347 .usm (1 es stub vacío en el juego).
> `media\soundtrack_wav\` → **504 WAV (20 GB)** música/SFX de los 401 .awb.
> Los scripts `extract_all_usm.py` / `extract_all_audio.py` son retomables: relánzalos tras un update del juego y solo procesan lo nuevo.
>
> **Reutilización fácil: `p5x.bat`** (raíz de esta carpeta). Doble clic = menú; o
> `p5x.bat video | audio | todo | step1`.

Pipeline completo para extraer assets de *Persona 5: The Phantom X* (PC, versión gratis).

```
game_dump\fileContentOut\          salida del paso 1 = punto de partida de todo lo demás
```

## Estructura

| Carpeta | Contenido |
|---|---|
| `tools\P5X_vFileContentExtract\` | Paso 1. Extrae del contenedor del juego (v1.0.1) |
| `tools\AssetStudioGUI\` | Paso 3. AssetStudioMod v0.19.0 — mirar/exportar assets (texturas, FBX, audio, MonoBehaviour→JSON) |
| `tools\AssetStudioCLI\` | Lo mismo, sin interfaz, para exportar en lote |
| `tools\Il2CppDumper\` | Paso 3b. Genera los dummy DLL que AssetStudio necesita para leer MonoBehaviour en juegos il2cpp |
| `tools\usmbreak\` | Paso 4. Descifra vídeos CRIWARE `.usm` |
| `scripts\` | One-click por paso (ver abajo) |
| `game_dump\` | **← aquí copias los archivos del juego** |
| `output\` | exportaciones de AssetStudio |
| `il2cpp\in\` | aquí copias `GameAssembly.dll` + `global-metadata.dat` (solo para paso 3b) |

## Qué copiar del juego

Instalación PC de P5X (épico/Steam no — el launcher propio). En `P5X\client\bin\`:

- `_vfileIndexV2.fb` → `game_dump\`
- **todos** los `_vfileContent*` → `game_dump\` (mismos nombres, misma carpeta)

## Orden de uso

1. **`scripts\step1_extract_vfilecontent.bat`** — doble clic. Vuelca todo a `game_dump\fileContentOut\` (bundles ya desofuscados + BMS descifrados + tablas/lua).
2. `step2_deobfuscate_bundles.bat <carpeta>` — *opcional*, solo para bundles sacados por otra vía (CDN "OuterPackage").
3. **`scripts\step3a_open_assetstudio.bat`** — File → Load folder → `game_dump\fileContentOut`. Con 16 GB de RAM: carga carpetas de bundles **por partes**, no el dump completo.
   - 3b: si quieres leer MonoBehaviour con nombres de campos: copia los 2 dll/dat a `il2cpp\in\` y corre `scripts\step3b_il2cppdumper.sh` (bash de git). El `dump.cs` resultante es un mapa de todas las clases del juego. En AssetStudio apunta el AssemblyPath a `il2cpp\dumped\dummy`.
4. **Vídeos** → `scripts\extract_all_usm.py` (RESUELTO 2026-09): la llave de la guía **SÍ es válida** (`1729401234202`), el problema era la HERRAMIENTA: usmbreak/MueruTools implementan el cifrado viejo (Sofdec), pero P5X usa **Sofdec Prime 2 (VP9 cifrado)** → se desencripta con **WannaCRI** (`pip install wannacri`; ya instalado en `tools\env\`). Los clips del build CN a veces necesitan `-e gbk` (el script ya reintenta solo). Salida: VP9 → `.mp4` con ffmpeg.

## Audio (banda sonora) — RESUELTO 2026-09

- Los vídeos .usm casi NO llevan audio (1 de 347). La música está en `*.awb` (401 bancos, 1.1 GB).
- OJO: los `.acb` están cifrados (tabla `@UTF`, `ciph` activo) y ni vgmstream ni VGAudio los abren. PERO los **`.awb` contienen las voces HCA concatenadas SIN tabla, y el audio HCA está SIN CIFRAR** — vgmstream lo decodifica directo.
- Pipeline verificado: separar voces buscando magic `HCA\0` → `vgmstream-cli -o out.wav voz.hca` → WAV 48 kHz estéreo reales (música confirmada por análisis espectral).
- Script: `scripts\extract_all_audio.py` → 504 WAV en `media\soundtrack_wav\<banco>\` (música del modo rítmico en `MusicGame\`, BGM de historia en `BGM_*`, `FilmBGM` = 2 pistas cinemáticas).
- Los nombres de cue→banco están en `Client\bin\Media\Windows\CueInfoMap.txt` (6399 entradas) para identificar qué es cada cosa.

## Dónde están los vídeos .usm (verificado en la instalación real)

NO están en `_vfileContent` (el paso 1 no los toca):
- `Client\OuterPackage\Media\Windows\` — **347 vídeos, ~13 GB**: CG de historia (`CG_P5X_OP.usm`, `CG_zx_Event_*`), habilidades (`Skill_*`), actividades, vinilos. EL CONTENIDO REAL.
- `Client\bin\Media\Windows\` — solo 5 (`REMAIN-CG1*.usm`, intros) + audio real en `.acb/.awb` CRIWARE (se extraen con criconv/vgmtoolbox, no usmbreak).
- `Client\OuterPackage\Bundles\Windows\` — ~16 533 bundles de contenido descargable, **sin ofuscar** (verificado: todos empiezan con `UnityFS`). "OuterPackage" = el paquete de contenido bajado por el launcher, no bundles cifrados. El paso 2 sigue sin necesitar jamas.

## Trucos de la comunidad (ResHax, jul 2025)

- El juego es **Unity 2022.3.49f1, il2cpp + casi toda la lógica en Lua** — configs y texto suelen estar en `.lua`/tablas que el paso 1 entrega planos, sin tocar AssetStudio.
- Prefijos internos: `role_*` = armaduras de personajes, `p_*` = personas, `sd_*` = sombras, `n_*` = NPCs; sufijos `_normal`/`_uniform` = mundo real, `_thief` = metaverso.
- Modelos con rig completo: se exportan vía el **Animator** (no la malla suelta); las mallas viven en bundles separados (una por body/face/hair). AssetRipper es alternativa si quieres reensamblar en Unity.
- La herramienta del paso 1 se rompió una vez tras un update chino (header cambió) → fix 1.0.1. Si un build nuevo falla, sospecha de eso antes que de tu uso.

*Todo GPL/MIT, descargado hoy de los releases oficiales. Uso personal/estudio: recuerda que redistribuir assets del juego infringe su ToS.*
