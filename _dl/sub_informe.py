"""Genera las entregas finales: resultado_bustups_indice.json y informe_bustups_indice.md."""
import json
from collections import defaultdict
from pathlib import Path

DL = Path(r"C:\Users\Lukas\p5x-datamining\_dl")
REPO = Path(r"C:\Users\Lukas\p5x-datamining")

man = json.loads((DL / "zeus_manifest.json").read_text(encoding="utf-8"))
info = json.loads((DL / "bustups_indice_informe.json").read_text(encoding="utf-8"))
cara_fuera = json.loads((DL / "cara_fuera_del_visor.json").read_text(encoding="utf-8"))
retratos = json.loads((REPO / "p5x_studio/p5x_studio/datos/retratos.json")
                      .read_text(encoding="utf-8"))["bundles"]

bustups = info["bustups"]
# bundles con deps declaradas entre los que usa cada bust-up
deps_de_usados = {}
for d in bustups.values():
    for b, ds in d["deps_manifiesto"].items():
        deps_de_usados.setdefault(b, ds)

fuera_por_clave = {r["clave"]: r for r in cara_fuera}
bustups_out = {}
for clave, d in bustups.items():
    corto = clave.replace("UI-DialogShader-", "")
    r = fuera_por_clave.get(corto)
    bustups_out[clave] = {
        "personaje": d["personaje"], "personaje_alias": d["personaje_alias"], "ropa": d["ropa"],
        "assets": d["pasos_presentes"],           # {paso: [nombres de sprite]}
        "bundles_necesarios": d["bundles_necesarios"],
        "tiene_ojos": d["tiene_ojos"], "tiene_boca": d["tiene_boca"], "tiene_cara": d["tiene_cara"],
        "tiene_mask": d["tiene_mask"],
        "bundles_cara": r["bundles_cara"] if r else [],
        "bundles_cara_fuera_del_visor": r["bundles_cara_fuera_de_visor"] if r else [],
        "deps_manifiesto": d["deps_manifiesto"],
    }

resultado = {
    "manifiesto": {
        "fichero": "104/zeusBundleManifest.txt",
        "ruta": str(Path(r"C:/Users/Lukas/Downloads/P5X/Client/OuterPackage/Bundles/Windows/104/zeusBundleManifest.txt")),
        "que_es": "FlatBuffer ZeusBundleManifestFB (no es un .bundle); lo lee Zeus.Framework.Asset.ZeusAssetBundleManifest",
        "tamano_bytes": 1655028,
        "esquema": {"ZeusBundleManifestFB": ["Infos: [ZeusAssetBundle]"],
                    "ZeusAssetBundle": ["Name:string", "Hash:string", "Dependencies:[int] (indices a Infos)", "Crc:uint32"]},
        "total_bundles": man["count"],
        "bundles_con_dependencias": sum(1 for b in man["bundles"] if b["deps"]),
        "aristas_dependencia": sum(len(b["deps"]) for b in man["bundles"]),
        "constante_il2cpp": "AssetBundleUtils.ZeusBundleManifestFb = \"zeusBundleManifest.txt\"",
        "notas": [
            "Los nombres de bundle del manifiesto son el nombre de fichero (.bundle); la carpeta numerica es una dispersion (SCATTER_MODULUS=200) que no forma parte del nombre.",
            "Hay 16.845 bundles en el manifiesto y 16.535 en disco: 310 declarados pero no descargados (todos de familias atlas_/ui_font_/shared_/spinte, MENOS los de bust-up).",
            "Las Dependencies son indices enteros a la propia tabla Infos; se resuelven a nombres con zeus_manifest.json.",
            "El campo Hash sale vacio en todos y el Crc a 0 en los bundles de texturas de UI.",
            "No existe un objeto Unity 'AssetBundleManifest' en los bundles empaquetados: el juego usa este FlatBuffer mas 'assetMapName.txt' (AssetMapBundleFB). i18n_manifest y tlm_manifest son TextAssets sin relacion.",
        ],
    },
    "visor": {
        "carpeta_texturas": "C:/Users/Lukas/Desktop/P5X Studio Tools/extracted/textures (118.230 PNG)",
        "bundles_que_extrae": len(retratos),
        "fichero_lista": "p5x_studio/p5x_studio/datos/retratos.json",
        "logica_capas": "p5x_studio/p5x_studio/bustups.py (ORDEN de apilado, partir_nombre, paso_de, ALIAS_PERSONAJE)",
    },
    "resumen": {
        "bustups": info["resumen"]["total"],
        "con_cara": info["resumen"]["con_cara"],
        "sin_cara_en_el_emparejado": info["resumen"]["sin_cara"],
        "bundles_necesarios_union": info["resumen"]["bundles_necesarios_union"],
        "bundles_con_toda_la_cara_dentro_del_visor": len(cara_fuera) and
            sum(1 for r in cara_fuera if not r["bundles_cara_fuera_de_visor"]) + (
                info["resumen"]["total"] - len(cara_fuera)),
        "bustups_con_parte_de_la_cara_fuera_del_visor": sum(
            1 for r in cara_fuera if r["bundles_cara_fuera_de_visor"]),
        "bundles_con_cara_fuera_del_visor": sorted(
            {b for r in cara_fuera for b in r["bundles_cara_fuera_de_visor"]}),
        "bundles_de_bustup_con_dependencias_en_el_manifiesto": sum(
            1 for b, ds in deps_de_usados.items() if ds),
    },
    "dependencias_declaradas_por_los_bundles_de_bustup": deps_de_usados,
    "bustups": bustups_out,
    "comprobado_con_el_motor": [
        "026/uitex_uaidaofu552d57a7.bundle (duomicunlizi/guaidaofu): 10 assets, SOLO Sprite+Texture2D de cuerpo; sin yan/zui.",
        "129/uitex_aoningzi4dbe708f.bundle (gaoqiaoningzi/changfu): 68 assets; cuerpo 'gaoqiaoningzi-changfu-benti*' y cara 'gaoqiaoningzi-<expr>-yanN' SIN token de ropa.",
        "072/uitex_uaidaofu4734d5b1.bundle (aocunchun/aochuncun): 80 assets, caras bajo el nombre MAL ESCRITO 'aocunchun-guaidaofu-*' (el resto del juego usa 'aochuncun').",
        "114/uitex_uaidaofu7b37e8a5.bundle (yemaopengzi/guaidao): 10 assets, cuerpo + 'benti-mask', sin yan/zui.",
        "104/uitex_s_uaidaofu4734d5b1.bundle (aochuncun): 4 assets, solo 'benti-mask'/'benti-Rmask01'.",
        "Scan de los 16.535 bundles (censo_texturas.json) y del manifiesto (parser propio FlatBuffer).",
    ],
    "dudas": [
        "No he podido abrir NINGUN bundle con UnityPy directamente: estan cifrados (Unity 2022 ArchiveStorage) y la clave del cliente no se pudo derivar (brute_force_key sobre global-metadata.dat devolvio None con las firmas conocidas). Todo se ha hecho con el motor AssetStudioModCLI del proyecto (que ya sabe descifrar) y con los datos ya medidos (censo_texturas.json).",
        "Las firmas KEY_SIG/DATA_SIG de p5x_studio/p5x_studio/clave.py no dieron clave sobre el global-metadata.dat presente; puede que el cliente se haya actualizado o que la metadata no sea la correcta. NO he modificado la app.",
        "El emparejado JSON<->bust-up de emparejado_bustups.json es heuristica por nombre; 'tiene_cara' depende de esa heuristica. Los recuentos de bundles son exactos respecto al censo, pero la atribucion de una cara a un bust-up concreto con chorro de nombres irregulares es interpretable.",
        "No he encontrado prefabs de bust-up (los bundles de textura solo llevan Sprite+Texture2D). El prefab que coloca las capas no se ha localizado; la app lo suple buscando el sprite por pixeles.",
        "No he renderizado ni medido los 120 PNG del visor: el analisis es de inventario de assets y del indice, no de pixeles.",
    ],
}
(DL / "resultado_bustups_indice.json").write_text(
    json.dumps(resultado, ensure_ascii=False, indent=1), encoding="utf-8")

# ------------------------------- markdown -------------------------------
man_s = resultado["manifiesto"]
res = resultado["resumen"]


def tabla_cara():
    filas = [r for r in cara_fuera if r["bundles_cara_fuera_de_visor"]]
    out = ["| bust-up | personaje/ropa | bundles de cara que el visor NO extrae |", "|---|---|---|"]
    for r in sorted(filas, key=lambda x: x["clave"]):
        bs = ", ".join(b.split("/")[-1] for b in r["bundles_cara_fuera_de_visor"])
        out.append("| %s | %s/%s | %s |" % (r["clave"], r["personaje"], r["ropa"], bs))
    return "\n".join(out)


md = f"""# Bust-ups: indice de bundles, dependencias y causa de las capas que faltan

## 1. El indice que relaciona bundles: `zeusBundleManifest.txt`

- **Fichero**: `Client/OuterPackage/Bundles/Windows/104/zeusBundleManifest.txt` (1.655.028 bytes).
- **NO es un `.bundle`**: es un **FlatBuffer** (`ZeusBundleManifestFB`), el formato propio del motor
  `Zeus.Framework.Asset`. Se lee con `ZeusAssetBundleManifest` / `AssetBundleUtils`
  (`AssetBundleUtils.ZeusBundleManifestFb = "zeusBundleManifest.txt"`, `dump.cs`).
- **Esquema** (de `dump.cs`, TypeDefIndex 17023/17024):
  - `ZeusBundleManifestFB`: `Infos: [ZeusAssetBundle]`
  - `ZeusAssetBundle`: `Name:string`, `Hash:string`, `Dependencies:[int]`, `Crc:uint32`
  - `Dependencies` son **indices enteros** a la propia tabla `Infos`.
- **Medido** (parser propio, sin libreria flatbuffers): **{man_s['total_bundles']} bundles**,
  **{man_s['bundles_con_dependencias']} declaran dependencias**, **{man_s['aristas_dependencia']} aristas**.
- Otros ficheros que NO son el indice: `105/assetMapName.txt` (FlatBuffer `AssetMapBundleFB`: mapa
  hash/prefijo de asset -> bundle; 139.759 entradas H2b, solo 12 paths legibles), `070/i18n_manifest…`
  y `159/tlm_manifest…` (ambos TextAssets sin relacion), y no hay objeto Unity `AssetBundleManifest`
  dentro de los bundles.
- El nombre de un bundle en el manifiesto es el **nombre de fichero** (`anim_battle…bundle`); la
  carpeta numerica (`000/`, `104/`…, `SCATTER_MODULUS=200`) es una dispersion y no forma parte del nombre.

### Dependencias de los bundles de los bust-ups

Comprobado: **ningun bundle de textura de bust-up declara dependencias**
({res['bundles_de_bustup_con_dependencias_en_el_manifiesto']} con deps de {len(deps_de_usados)}).
Ej.: `uitex_changfu*, uitex_s_changfu*, uitex_uaidaofu*,
uitex_aoningzi*` -> `deps = []`. Es decir: **seguir el grafo de dependencias no aporta ninguna capa**;
un cargador que solo tire de las dependencias del bundle del cuerpo no recupera nada.

## 2. Composicion de cada bust-up (sprites) y su bundle

Detalle completo en `resultado_bustups_indice.json` (campo `bustups`). Cada bust-up es uno de los 120
JSON `UI-DialogShader-<ropa>-<personaje>`; sus capas son **Sprites** (cada uno con su `Texture2D`) con
nombres `<personaje>-<ropa>-<capa>[-<expresion>]`. **No hay prefabs** en estos bundles: solo
`Sprite` + `Texture2D` (verificado con el motor). Los pasos que reconoce el visor
(`p5x_studio/p5x_studio/bustups.py`) son: outline, body, arms, clothes, blush, face, eyes, mouth,
marks, mask, hair, glasses, hat.

- Bundles distintos que aportan capas a los 120 (union): **{res['bundles_necesarios_union']}**.
- El visor extrae solo **{resultado['visor']['bundles_que_extrae']}** bundles (`datos/retratos.json`).
- Bust-ups con parte de la CARA en bundles que **no** estan en `retratos.json`:
  **{res['bustups_con_parte_de_la_cara_fuera_del_visor']} de 120** (afectan a
  **{len(res['bundles_con_cara_fuera_del_visor'])}** bundles distintos).

## 3. Por que faltan capas (sobre todo la cara)

La causa **no** es el indice de dependencias: esos bundles no declaran ninguna. Las capas que faltan se
explican por como el visor decide **que bundles extraer**:

1. **La cara vive en un bundle distinto del cuerpo, y ese bundle no esta en la lista del visor.**
   El visor extrae un conjunto fijo de 80 bundles (`retratos.json`), calculado desde el emparejado
   JSON<->bust-up. Para **{res['bustups_con_parte_de_la_cara_fuera_del_visor']} de 120** bust-ups,
   los sprites de ojos/boca (o la cara base) estan en uno de estos **{len(res['bundles_con_cara_fuera_del_visor'])}**
   bundles que **no** se extraen, asi que el visor nunca tiene esos PNG -> la cara no se puede montar.
   El cuerpo si esta en un bundle extraido, por eso el retrato sale sin cara.
2. **El indice de dependencias no lo puede arreglar**: esos bundles tienen `deps=[]`, asi que la
   dependencia cuerpo->cara no esta declarada en ningun sitio; no se puede "tirar del hilo".
3. **Nombres irregulares** que ademas rompen cualquier emparejado por nombre:
   - erratas del propio juego: `aochuncun` vs `aocunchun` (el cuerpo/ojos van con `aocunchun`, las
     mascaras con `aochuncun`; la app ya tiene `ALIAS_PERSONAJE = {{"aochuncun": "aocunchun"}}`);
   - caras **sin token de ropa**: `gaoqiaoningzi-tongchang-yan1` junto a `gaoqiaoningzi-changfu-benti`;
   - doble guion: `yemaopengzi-changfu--haixiu-yan1`;
   - la ropa del JSON (`changfu01`) no siempre es la del sprite (`changfu`), o el bust-up se empareja a
     una ropa (`guaidaofu`) cuyas caras estan bajo OTRA ropa (`changfu`, `yundongfu`) -> se extrae el
     bundle equivocado.

### Bundles con la cara que el visor no extrae

{tabla_cara()}

## 4. Comprobado con datos reales

{chr(10).join('- ' + c for c in resultado['comprobado_con_el_motor'])}

## 5. Dudas / lo que NO he podido confirmar

{chr(10).join('- ' + c for c in resultado['dudas'])}

## 6. Ficheros generados (todo bajo `_dl/`, nada tocado fuera)

- `zeus_manifest.json` – manifiesto FlatBuffer parseado (bundle -> deps).
- `bustups_indice_informe.json` – analisis por bust-up.
- `resultado_bustups_indice.json` – entrega consolidada (manifiesto + bust-ups + resumen).
- `cara_fuera_del_visor.json` – casos de cara fuera del visor.
- `informe_bustups_indice.md` – este informe.
- `sub_parse_manifest.py`, `sub_analizar_bustups.py`, `sub_resumen_cara.py`, `sub_dump_bundle.py`,
  `sub_sacar_clave.py`, `sub_parse_assetmap.py` – scripts.
- `_assetlists/` – listas de assets (XML) de 6 bundles sacadas con el motor.
"""
(DL / "informe_bustups_indice.md").write_text(md, encoding="utf-8")
print("escrito resultado_bustups_indice.json y informe_bustups_indice.md")
print("tamano json:", (DL / "resultado_bustups_indice.json").stat().st_size)
print("tamano md:", (DL / "informe_bustups_indice.md").stat().st_size)