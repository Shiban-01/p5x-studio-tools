# N040 = Theo / Theodore (Persona 5: The Phantom X)

Buscado el 30-09-2026 en todo el cliente PC (`C:/Users/Lukas/Downloads/P5X/Client/OuterPackage`).

## Convencion de nombres del juego (aprendida aqui)

| prefijo | que es |
|---|---|
| `role_<codigo>` | el actor: prefab, animator y configuracion (no lleva geometria) |
| `part_<codigo>_NN` | el modelo del personaje (mallas + texturas). Kotone: `part_pc079_01`, 88 MB |
| `part_port_rig*` | retratos (busto): cara, ojos, parpados, pelo |
| `part_n_normal*` | cuerpos genericos de NPC (`..._body_wholeexport_rig_...`) |
| `shared_*` | trozos compartidos: texturas de cara/cuerpo y armas |
| `uitex_`, `atlas_`, `tl_`, `scn_`, `anim_`, `efx_` | interfaz, timelines, escenas, animaciones, efectos |

Los codigos: `pc0NN` = personaje jugable, `n0NN` = NPC con nombre, `n_<nombre>` = NPC generico,
`ng<algo>` = variante de generico.

## Todo lo que hay de N040

| bundle | carpeta | tamano | contenido |
|---|---|---|---|
| `role_n0403cff2cee.bundle` | 016 | ~30 KB | actor: `N040_triggermap` (mapa de disparadores de animacion, vacio), `MUActorEntityExportInfo`, `ZeusLookAt` y un Animator |
| `shared_2f727ec3.bundle` | 049 | 2,69 MB | `N040` (curvas de cara y parpadeo), texturas `N040_body_face_bc`, `_darkcolor`, `_f`, `_shadow`, `N040_body_eye_bc` |
| `part_port_rig4f85a00a.bundle` | 023 | 4,74 MB | mallas `N040_hair`, `N040_hair_shadow` + texturas `N040_body_hair_bc`, `_nm`, `_s`, `_stroke` |
| `part_port_rig59cdd175.bundle` | 130 | ~90 KB | mallas `N040_eye`, `N040_eyelid`, `N040_face`, `N040_face_shadow` |
| `part_t_rig_bs194115c7.bundle` | 088 | 0,49 MB | segundo rig de cara, este con malla LOD: `N040_face_lod`, `N040_face`, `N040_eye`, `N040_eyelid`, `N040_face_shadow` |
| `uitex_ang-n0405026582d.bundle` | 047 | 0,91 MB | textura de interfaz con `N040_04_tongchang_zui` (cara sacando la lengua) |

**No existe** ningun `part_n040` ni `part_n040_01`: el cuerpo entero no esta en el cliente con ese
nombre. Lo que hay es cabeza (cara, ojos, parpados, pelo) con sus sombras, y ademas **dos** juegos de
cara: el de retrato (`part_port_rig`, carpeta 130) y el de escena con LOD (`part_t_rig_bs`, carpeta
088). Es coherente con un NPC que aparece en el Velvet Room: busto y retrato.

Comprobado con dos barridos: cabeceras de los 16.535 bundles (256 KB de cada uno, 19 coincidencias) y
`grep` de los 72 GB completos (111 coincidencias). De esas 111, solo 2 tienen texto legible alrededor
de "N040" (`part_port_rig4f85a00a` y `part_t_rig_bs194115c7`); las otras 109 son bytes sueltos dentro
de bloques comprimidos, no rutas de assets.

## Datos concretos

- `N040.txt` (dentro de `shared_2f727ec3`) es la configuracion de expresiones: curva `fake_speak`
  (ritmo de habla falsa, 11 claves), `normal_blink` (14 claves) y emociones `face_tongchang` y
  `face_beiai`. Es el equivalente de lo que en Kotone quedo en `04_expresiones`.
- El actor trae 3 MonoBehaviour + 1 Animator y **ninguna malla**, igual que el de Kotone.
- Los bundles de Unity llevan el indice de rutas de sus assets **sin comprimir al principio**: leer
  los primeros 256 KB de cada uno basta para saber que personajes contiene. Con eso se barrio el
  cliente entero (16.535 bundles) sin extraer nada.

## Herramientas que quedan hechas

- `scripts/inspeccionar_bundle.py <bundle>` — que trae un bundle (tipos, nombres, tamanos).
- `scripts/buscar_en_bundles.py <carpeta> <termino...> [--bytes N]` — en que bundles aparece un
  termino, leyendo solo las cabeceras.
- Truco del dump: `AssetStudioModCLI.exe <bundle> -m dump -o <carpeta>` deja un `.txt` **por asset**
  con su nombre real; `ls` de esa carpeta es la lista de assets.

## Siguiente paso

Extraer con AssetStudioModCLI (mallas OBJ + texturas PNG) los dos `part_port_rig` y el
`shared_2f727ec3`, y montar el busto en Unity igual que se hizo con Kotone (mismo esqueleto de
piel/expresiones). Al ser una cabeza sin cuerpo, el pipeline de Source no aplica.


## Extraccion hecha (30-09-2026)

El busto esta extraido y montado en `n040_theo/`: `Theo_Busto.blend`, `Theo_Busto.glb`, renders en
`preview/`, mallas en `01_modelo/`, texturas en `02_texturas/` y la procedencia con sha256 en
`06_origen/procedencia.json`. Detalles y avisos en `n040_theo/LEEME-Theo.md`.
