"""Extractor: de un personaje del indice a una carpeta ordenada igual que la de referencia.

El trabajo pesado lo hace AssetStudioModCLI, que es el unico que abre los bundles cifrados del
juego. Esta capa se encarga de lo demas: decidir que ficheros mirar, lanzar el motor, repartir lo
que devuelve en carpetas por parte, enlazar cada malla con sus texturas, dibujar las vistas previas
y escribir un README que se entienda sin saber nada de esto.

Estructura que produce:

    <salida>/<id>_<nombre>/
        <id>_<nombre>.glb        EL MODELO: malla, UVs, texturas incrustadas, esqueleto y pesos
        <id>_<nombre>_full.fbx   el mismo modelo en FBX (armadura + pesos de piel)
        01_model/obj/<parte>/    la geometria suelta en OBJ con su MTL al lado (sin huesos)
        02_textures/<parte>/     texturas en PNG (las mismas que van incrustadas en el GLB)
        03_skeleton/             detalle del esqueleto (esqueleto.json)
        04_expressions/          expresiones y morphs, si el juego los expone
        05_materials/            que textura corresponde a cada pieza
        preview/                 vistas previas en PNG
        06_modelo_base/          cara, ojos y pelo que se toman del modelo base de una skin
        README.md
        SUMMARY.json
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

from . import ajustes, bases, dependencias, glb_rig, preview, rig_unitypy, unity
from .idiomas import idioma_actual, t


def _ruta_recurso(nombre: str) -> Path:
    """Ruta de un fichero de datos del paquete, dentro o fuera del ejecutable congelado."""
    if getattr(sys, "frozen", False) and getattr(sys, "_MEIPASS", None):
        return Path(sys._MEIPASS) / "p5x_studio" / nombre
    return Path(__file__).resolve().parent / nombre

REGLAS_PARTE = [
    ("face", ("face", "kao")),
    ("hair", ("hair", "toufa", "kami")),
    ("eyes", ("eye", "yan", "eyelid")),
    ("weapons", ("weapon", "qiang", "wq_", "wp_", "sword", "blade", "gun")),
    ("body", ("body", "skin", "cloth", "uniform", "shenti", "xiuzhang")),
]
PARTES = ["body", "face", "hair", "eyes", "weapons", "other"]

def nombre_parte(parte: str) -> str:
    """Nombre legible de una parte en el idioma activo (`body` -> `Cuerpo y ropa`)."""
    return t("ex_parte_" + parte)

# sufijos que el motor anade a las copias de baja calidad o auxiliares
SUFIJOS_DESCARTABLES = ("_lod", "_lodlow", "_shadow", "_lodhigh")

# carpeta donde se dejan las piezas que se toman del modelo base de una skin
CARPETA_BASE = "06_modelo_base"

# Un escenario puede traer mas de mil mallas. Dibujar una vista previa por malla tarda minutos y la
# lamina sale ilegible (una columna de miles de pixeles), asi que se limita a las piezas mas grandes.
MAX_PREVIAS_ESCENA = 48


def _clasificar(nombre: str) -> str:
    n = (nombre or "").lower()
    for parte, pistas in REGLAS_PARTE:
        if any(p in n for p in pistas):
            return parte
    return "other"


def _limpiar(nombre: str) -> str:
    n = re.sub(r"[^A-Za-z0-9_.-]+", "_", nombre or "sin_nombre").strip("_")
    return n[:90] or "sin_nombre"


def _es_descartable(nombre: str) -> bool:
    n = nombre.lower()
    return any(n.endswith(s) or (s + ".") in n for s in SUFIJOS_DESCARTABLES)


def _ejecutar_motor(entradas: list[Path], salida: Path, modo: str, tipos: str, log) -> None:
    """Lanza el motor de extraccion sobre una lista de bundles."""
    exe = dependencias.ruta_assetstudio()
    if not exe:
        raise RuntimeError(t("ex_falta_motor"))
    orden = [str(exe)] + [str(e) for e in entradas] + [
        "-m", modo, "-t", tipos, "-o", str(salida), "--log-level", "Warning",
        "-r", "--unity-version", "2022.3.49f1"]
    r = subprocess.run(orden, capture_output=True, text=True, timeout=3600,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if r.returncode != 0:
        detalle = (r.stdout or "") + (r.stderr or "")
        raise RuntimeError(t("ex_motor_fallo", detalle[-800:]))
    if log:
        log(t("ex_motor_ficheros", len(entradas)))


def _ejecutar_motor_por_fichero(entradas: list[Path], salida: Path, modo: str, tipos: str,
                                log) -> None:
    """Lanza el motor una vez por bundle.

    Comprobado en este juego: si se le pasan varios bundles en la misma orden, no exporta nada y
    termina en decimas de segundo sin dar error. Uno a uno si funciona, y ademas aisla el fallo de
    un bundle concreto para que no arrastre a los demas.
    """
    salida.mkdir(parents=True, exist_ok=True)
    for i, entrada in enumerate(entradas, 1):
        if log:
            log(t("ex_progreso_fichero", i, len(entradas), entrada.name))
        try:
            _ejecutar_motor([entrada], salida / entrada.stem, modo, tipos, None)
        except Exception as e:
            if log:
                log(t("ex_no_procesar", str(e)[:200]))


def _escribir_mtl(ruta_mtl: Path, material: str, texturas: list[Path], raiz: Path | None = None) -> str:
    """MTL de UN solo material: color base y mapa de normales, apuntando a sus texturas.

    Antes se escribia un material por CADA textura de la pieza y luego se aplicaba el primero a
    todas las caras: una lanza acababa pintada con la textura de la pistola (el primer nombre por
    orden alfabetico). El formato OBJ solo entiende un `map_Kd` y un `map_Bump`, asi que aqui se
    elige el color base (`_bc`) y la normal (`_nm`) de ESTA malla, y los demas mapas del juego
    (sombra, contorno, matcap...) se dejan anotados como comentario para no perder la informacion.

    La ruta se escribe RELATIVA a la carpeta del MTL: los PNG viven en `02_textures/...` y el MTL en
    `01_model/obj/...`, asi que un nombre suelto no resuelve y el modelo se abre sin texturas.
    """
    bc = _elegir_mapa(texturas, MAPAS_COLOR)
    nm = _elegir_mapa(texturas, MAPAS_NORMAL)

    def destino(t: Path) -> str:
        if raiz is not None:
            try:
                return os.path.relpath(t, ruta_mtl.parent).replace("\\", "/")
            except ValueError:
                return t.name
        return t.name

    lineas = ["newmtl " + material, "Ka 0.2 0.2 0.2", "Kd 0.8 0.8 0.8",
              "Ks 0.0 0.0 0.0", "d 1.0", "illum 1"]
    if bc is not None:
        lineas.append("map_Kd " + destino(bc))
    if nm is not None:
        lineas.append("map_Bump " + destino(nm))
    for extra in texturas:
        if extra is bc or extra is nm:
            continue
        lineas.append(t("ex_mapa_extra", destino(extra)))
    lineas.append("")
    ruta_mtl.write_text("\n".join(lineas), encoding="utf-8")
    return material


def _colocar_malla(final: Path, origen: Path, texturas: list[Path], raiz: Path,
                   material: str) -> str:
    """Copia un OBJ a su sitio, le escribe su MTL (un material) y se lo enlaza dentro del fichero."""
    final.parent.mkdir(parents=True, exist_ok=True)
    if not final.exists():
        shutil.copy2(origen, final)
    ruta_mtl = final.with_suffix(".mtl")
    _escribir_mtl(ruta_mtl, material, texturas, raiz)
    texto = final.read_text(encoding="utf-8", errors="replace")
    if "mtllib" not in texto:
        texto = "mtllib %s\n" % ruta_mtl.name + texto
    if "usemtl" not in texto:
        texto = texto.replace("\nf ", "\nusemtl %s\nf " % material)
    final.write_text(texto, encoding="utf-8")
    return material


# sufijos con los que el juego nombra los distintos mapas de una MISMA pieza: PC079_01_body_bc,
# PC079_01_body_nm, PC079_01_body_pk... Quitandolos queda la "base" de la textura, que es lo que se
# compara con el nombre de la malla para enlazarlas. El orden importa: primero los sufijos largos.
SUFIJOS_MAPA = ("_darkcolor", "_lodlow", "_stroke", "_shadow", "_mask01", "_nmas", "_bcm",
                "_mask", "_basecolor", "_maintex", "_normal", "_bump", "_bc", "_nm", "_pk",
                "_e", "_f", "_s", "_op")

# que sufijo lleva el color base y cual la normal, para el MTL
MAPAS_COLOR = ("_bc", "_bcm", "_basecolor", "_maintex")
MAPAS_NORMAL = ("_nm", "_nmas", "_normal", "_bump")

# partes que van cada pieza en su propia subcarpeta (armas y props), para que no se mezclen sus
# texturas con las del cuerpo del personaje
PARTES_SUELTAS = ("weapons", "other")


def _base_textura(nombre: str) -> str:
    """`PC077_01_weapon_02_bc` -> `pc077_01_weapon_02` (la pieza a la que pertenece el mapa)."""
    n = (nombre or "").lower()
    for s in SUFIJOS_MAPA:
        if n.endswith(s):
            return n[:-len(s)]
    return n


def _emparejar(prefijo: str, bases: list[str]) -> str | None:
    """Base de textura que corresponde a una malla, comparando nombres.

    Se prueban tres cosas, de mas fiable a menos: coincidencia exacta; una base que sea el principio
    del nombre de la malla (una lanza `weapon_04_01` pertenece a `weapon_04`); y el nombre de la
    malla como principio de una base (el cuerpo `pc077_01_body` usa el atlas `pc077_01_body_lodlow`).
    En el ultimo caso se coge la base MAS CORTA, que es la variante principal y no la de sombra.
    """
    p = (prefijo or "").lower()
    if not p:
        return None
    if p in bases:
        return p
    candidatas = [b for b in bases if p.startswith(b)]
    if candidatas:
        return max(candidatas, key=len)
    candidatas = [b for b in bases if b.startswith(p)]
    if candidatas:
        return min(candidatas, key=len)
    return None


def _elegir_mapa(texturas: list[Path], sufijos: tuple) -> Path | None:
    """De una lista de texturas, la que termina en alguno de esos sufijos (bc, nm...)."""
    for s in sufijos:
        for t in texturas:
            if t.stem.lower().endswith(s):
                return t
    return None


def _nombre_material(malla: str) -> str:
    """Nombre de material UNICO por malla: evita que al unir todo en un FBX se mezclen texturas."""
    return "mat_" + _limpiar(malla)


def _nombre_pieza(malla: str, actor: str = "") -> str:
    """Nombre de carpeta de una pieza suelta: `PC077_01_weapon_02_wholeexport_rig_...` -> `weapon_02`."""
    p = _prefijo_rig(malla) or malla
    if actor:
        bajo = p.lower()
        for pre in (actor.lower() + "_", actor.lower()):
            if bajo.startswith(pre) and len(bajo) > len(pre):
                p = p[len(pre):]
                break
    return _limpiar(p)


def _prefijo_rig(nombre: str) -> str | None:
    """Prefijo de textura que pide una malla del base: `..._rig_chord_normal_face` -> `chord_normal_face`.

    Las mallas del juego se llaman `<actor>_<traje>_wholeexport_rig_<prefijo_textura>`. Ese ultimo
    trozo es justo el nombre con el que empiezan sus texturas (`chord_normal_face_bc`), asi que sirve
    para enlazar malla y textura sin depender del material del juego. Las versiones con morph llevan
    delante `bs_`, que se quita.
    """
    n = (nombre or "").lower()
    i = n.find("_rig_")
    if i < 0:
        return None
    toks = [t for t in n[i + 5:].split("_") if t]
    while toks and toks[0] in ("bs", "ps", "b"):
        toks = toks[1:]
    return "_".join(toks) if toks else None


def _prefijo_grupo(nombre: str) -> str | None:
    """Los dos primeros trozos del prefijo de rig: `chord_normal_face` -> `chord_normal_`."""
    p = _prefijo_rig(nombre)
    if not p:
        return None
    toks = p.split("_")
    return "_".join(toks[:2]) + "_" if len(toks) >= 2 else None


# piezas que NO son ropa: una cara, unos ojos o un pelo valen para cualquier traje del actor (el
# juego los guarda en el bundle del uniforme aunque se este extrayendo la ropa normal)
PIEZAS_COMUNES = ("face", "eyes", "hair")

# mallas que NO son del modelo: el juego mete en los bundles del rig (y en los `shared_merged`) las
# "mallas de hueso" (`b_l_hiza01`, `b r hiji02`): son ayudas del esqueleto, no geometria que se pinte.
# Si no se descartan, la extraccion se llena de rodillas y codos sueltos en `other/`.
PATRON_MALLA_HUESO = re.compile(r"^b[_ ][lr][_ ]", re.I)


def _es_malla_hueso(nombre: str) -> bool:
    """Si una malla es una ayuda de esqueleto (`b_l_hiza01`) y no una pieza del modelo."""
    return bool(PATRON_MALLA_HUESO.match((nombre or "").strip()))


def _traje_de_malla(malla: str, actor: str, claves: list) -> str | None:
    """A que traje del actor pertenece una malla, por el nombre: `<actor>_<traje>_<pieza>...`.

    Se quita el actor del principio y se busca la clave de traje MAS LARGA que encabeza el resto
    (para que `closer_uniform_swimsuit_body` sea del banador y no del uniforme).
    """
    n = (malla or "").lower()
    bajo = (actor or "").lower()
    resto = n
    if bajo and n.startswith(bajo):
        resto = n[len(bajo):].lstrip("_")
    cands = [c for c in claves if c and (resto == c or resto.startswith(c + "_"))]
    return max(cands, key=len) if cands else None


def _es_del_traje(malla: str, actor: str, clave: str, claves: list) -> bool:
    """Si una malla (o textura) entra en la extraccion del traje elegido.

    El juego mete en el MISMO bundle mallas de varios trajes del actor (`166/part__uniform` trae la
    ropa normal, la deportiva y el uniforme), asi que al pedir un traje salian todos mezclados. Se
    descartan las piezas que el nombre delata como de OTRO traje, salvo cara, ojos y pelo, que son
    del actor y no de la ropa. Un actor con un solo traje no pierde nada: casi ninguna malla declara
    traje y se queda.
    """
    t = _traje_de_malla(malla, actor, claves)
    if t is None or t == clave:
        return True
    return _clasificar(malla) in PIEZAS_COMUNES


def _extraer_modelo_base(raiz: Path, trabajo: Path, base_id: str, opciones: dict,
                         di, marca) -> dict | None:
    """Extrae del modelo base la cara, los ojos (con parpados) y el pelo, y deja alli sus texturas.

    Todo va a `06_modelo_base/`, separado de lo que trae la skin, y el resumen anota de que base
    viene, que piezas se tomaron y de que bundles. El cuerpo y las armas del base no se tocan: la
    skin ya trae los suyos.
    """
    info = bases.info_base(base_id)
    carpeta_bundles = ajustes.carpeta_bundles()
    if not carpeta_bundles:
        raise RuntimeError(t("ex_sin_bundles"))
    ficheros = [carpeta_bundles / f for f in info["bundles"]]
    ficheros = [f for f in ficheros if f.is_file()]
    if not ficheros:
        raise RuntimeError(t("ex_base_sin_ficheros", base_id))
    di(t("ex_base_tomadas", info["nombre"], len(ficheros), ", ".join(info["grupo"])))
    destino = raiz / CARPETA_BASE
    for sub in ("01_model/obj", "02_textures"):
        (destino / sub).mkdir(parents=True, exist_ok=True)

    tipos = []
    if opciones.get("mallas", True):
        tipos.append("mesh")
    if opciones.get("texturas", True):
        tipos.append("tex2d")
    if not tipos:
        return None
    _ejecutar_motor_por_fichero(ficheros, trabajo / "base_export", "export", ",".join(tipos), di)

    crudos_obj = sorted((trabajo / "base_export").rglob("*.obj"))
    crudos_png = sorted((trabajo / "base_export").rglob("*.png"))

    # solo se toman las piezas que a la skin le faltan: cara, ojos (incluye parpados) y pelo
    quiero = set(bases.PIEZAS_BASE)
    mallas = sorted(o for o in crudos_obj if _clasificar(o.stem) in quiero)
    if not mallas:
        raise RuntimeError(t("ex_base_sin_cara", base_id))

    # La misma cara vive en varios bundles del base (el modelo normal, el de ladron, el de la
    # guitarra...). Se queda una copia de cada pieza, prefiriendo la del modelo principal al traje
    # de ladron, para no llenar la carpeta de triplicados.
    def _es_traje(nombre: str) -> bool:
        return "thief" in nombre.lower()

    mallas.sort(key=lambda o: (_es_traje(o.stem), o.stem.lower()))
    vistas: dict[tuple, str] = {}
    unicas: list[Path] = []
    for o in mallas:
        k = (_prefijo_rig(o.stem) or o.stem.lower(),
             "lod" if _es_descartable(o.stem) else "",
             "bs" if "_bs_" in o.stem.lower() else "")
        if k in vistas:
            continue
        vistas[k] = o.stem
        unicas.append(o)
    mallas = sorted(unicas)
    prefijos = sorted({p for p in (_prefijo_rig(m.stem) for m in mallas) if p})
    grupos_prefijo = sorted({p for p in (_prefijo_grupo(m.stem) for m in mallas) if p})

    def vale_textura(png: Path) -> bool:
        if _clasificar(png.stem) in quiero:
            return True
        bajo = png.stem.lower()
        return any(bajo.startswith(p) for p in prefijos)

    texturas_finales: list[Path] = []
    por_parte: dict[str, list[Path]] = {k: [] for k in PARTES}
    for png in crudos_png:
        if not vale_textura(png):
            continue
        parte = _clasificar(png.stem)
        carpeta = destino / "02_textures" / parte
        carpeta.mkdir(parents=True, exist_ok=True)
        final = carpeta / png.name
        if not final.exists():
            shutil.copy2(png, final)
        texturas_finales.append(final)
        por_parte[parte].append(final)

    materiales = []
    mallas_por_parte: dict[str, list[str]] = {k: [] for k in PARTES}
    bases_textura = sorted({_base_textura(t.stem) for t in texturas_finales})
    for obj in mallas:
        parte = _clasificar(obj.stem)
        final = destino / "01_model/obj" / parte / obj.name
        pref = _prefijo_rig(obj.stem) or obj.stem.lower()
        grupo = _emparejar(pref, bases_textura)
        asociadas = [t for t in texturas_finales if grupo and _base_textura(t.stem) == grupo]
        if not asociadas:
            asociadas = por_parte[parte]
        material = _colocar_malla(final, obj, asociadas, raiz, _nombre_material(obj.stem))
        mallas_por_parte[parte].append(final.name)
        materiales.append({"malla": final.name, "material": material,
                           "texturas": [t.name for t in asociadas], "origen": "modelo_base"})

    # nota para quien abra la carpeta: de donde sale esto
    (destino / "LEEME.md").write_text(
        t("ex_leeme_base",
          info["nombre"], info["id"], ", ".join(info["grupo"]),
          ", ".join(t("ex_base_parte_linea", nombre_parte(p), len(mallas_por_parte[p]))
                    for p in bases.PIEZAS_BASE if mallas_por_parte[p]) or "-",
          ", ".join(str(f.relative_to(carpeta_bundles)) for f in ficheros)),
        encoding="utf-8")

    resultado = {
        "id": info["id"],
        "nombre": info["nombre"],
        "grupo": info["grupo"],
        "carpeta": CARPETA_BASE,
        "piezas": [p for p in bases.PIEZAS_BASE if mallas_por_parte[p]],
        "mallas": {p: mallas_por_parte[p] for p in PARTES if mallas_por_parte[p]},
        "texturas": {p: [t.name for t in por_parte[p]] for p in PARTES if por_parte[p]},
        "bundles": [str(f.relative_to(carpeta_bundles)) for f in ficheros],
        "n_mallas": len(mallas),
        "n_texturas": len(texturas_finales),
        "materiales": materiales,
        "grupos_textura": grupos_prefijo,
    }
    (destino / "origen.json").write_text(json.dumps(resultado, ensure_ascii=False, indent=1),
                                         encoding="utf-8")
    di(t("ex_del_base", len(mallas), len(texturas_finales)))
    return resultado


def _esqueleto_del_juego(raiz: Path, trabajo: Path, ficheros: list[Path], resumen: dict, di) -> None:
    """Plan B, sin Unity: los rigs sueltos que el motor de extraccion saque de los bundles.

    No es un modelo riggeado (los renderers no existen fuera de Unity), pero sirve de referencia de
    huesos y no cuesta nada intentarlo.
    """
    try:
        _ejecutar_motor_por_fichero(ficheros, trabajo / "rigs", "animator", "mesh", di)
        puestos = 0
        for fbx in sorted((trabajo / "rigs").rglob("*.fbx")):
            bajo = fbx.stem.lower()
            # las camaras y los efectos del juego no le sirven a nadie en un paquete de modelo
            if ("camera" in bajo or "vcam" in bajo or "shoteffect" in bajo
                    or bajo.startswith("t_") or bajo.startswith("ui-")):
                continue
            destino = raiz / "03_skeleton" / (_limpiar(fbx.stem) + ".fbx")
            shutil.copy2(fbx, destino)
            puestos += 1
        resumen["huesos"] = puestos
        di(t("ex_rigs_sueltos", puestos))
    except Exception as e:
        di(t("ex_no_rigs", e))
    if not resumen["huesos"]:
        di(t("ex_rigs_dentro"))


def _glb_desde_dump(raiz: Path, pid: str, etiqueta: str, dump: Path, resumen: dict, di,
                    datos: dict, origen: str) -> bool:
    """Monta el GLB riggeado a partir de un volcado (venga de Unity o de los bundles).

    El GLB se escribe en la RAIZ de la carpeta del modelo, junto al FBX: es la entrega principal
    (malla + UVs + texturas incrustadas + esqueleto + pesos en un solo fichero). `03_skeleton/` se
    queda con `esqueleto.json`, que es el detalle de huesos y el recuento medido.
    """
    marca_glb = _limpiar(etiqueta.replace(" ", "_"))
    salida_glb = raiz / ("%s.glb" % marca_glb)
    di(t("ex_ensamblando_glb"))
    try:
        st = glb_rig.construir(dump, salida_glb, pid.upper(), texturas=[raiz], log=di)
    except Exception as e:
        di(t("ex_aviso_glb", str(e)[:400]))
        return False

    info = {
        "origen": origen,
        "glb": salida_glb.name,
        "huesos": st["huesos"],
        "mallas": st["mallas"],
        "mallas_con_pesos": st["mallas_con_pesos"],
        "armaduras": st["armaduras"],
        "expresiones": st["expresiones"],
        "materiales": st["materiales"],
        "texturas": st["texturas"],
        "mb": st["mb"],
        "partes": datos.get("partes"),
    }
    if origen == "unity":
        info["unity"] = datos.get("unity")
        info["proyecto"] = datos.get("proyecto")
    (raiz / "03_skeleton" / "esqueleto.json").write_text(
        json.dumps(info, ensure_ascii=False, indent=1), encoding="utf-8")
    resumen["esqueleto"] = info
    resumen["huesos"] = st["huesos"]
    resumen["glb"] = salida_glb.name
    resumen["glb_mb"] = st["mb"]
    di(t("ex_esqueleto_listo", st["huesos"], st["mallas_con_pesos"], st["mallas"],
         salida_glb.name))
    return True


def _esqueleto_por_bundles(raiz: Path, pid: str, etiqueta: str, trabajo: Path,
                           ficheros: list[Path], base_id, resumen: dict, di,
                           filtro=None) -> bool:
    """Saca el esqueleto leyendo los propios bundles, SIN Unity.

    Los datos de piel estan en las mallas (pesos, indices e inversas de bind), la jerarquia de
    huesos en el prefab del actor y el orden de huesos por malla en el manifiesto del rig. Con eso
        `rig_unitypy` reconstruye el mismo volcado que Unity y `glb_rig` monta el GLB igual. Es la via
        general: funciona para cualquier personaje, aunque no este en el proyecto decompilado.
    """
    todos = list(ficheros)
    # OJO: los bundles del modelo base NO se añaden aqui. Traen otro prefab (otra jerarquia de
    # huesos) y mezclar dos rigs en un mismo volcado deja huesos sin padre. Las piezas del base ya
    # se extraen aparte, en `06_modelo_base/`.
    try:
        dump = trabajo / "skeleton_dump"
        datos = rig_unitypy.volcar(todos, dump, pid.upper(), log=di, texturas=[raiz],
                                   filtro=filtro)
    except Exception as e:
        di(t("ex_aviso_rig_bundles", str(e)[:400]))
        return False
    if not datos.get("partes"):
        return False
    return _glb_desde_dump(raiz, pid, etiqueta, dump, resumen, di, datos, "bundles")


def _esqueleto_por_unity(raiz: Path, pid: str, etiqueta: str, trabajo: Path, resumen: dict, di) -> bool:
    """Saca el modelo riggeado (huesos + pesos de piel) usando Unity en modo lote.

    Por que hace falta Unity: los bundles traen las mallas por un lado y el esqueleto por otro, sin
    jerarquia de renderers; los SkinnedMeshRenderer se montan en tiempo de ejecucion desde el
    manifiesto del rig, asi que ningun exportador externo puede dar un FBX riggeado. Solo Unity,
    abriendo el proyecto decompilado, tiene esa piel montada.

    Devuelve True si el GLB riggeado quedo en la raiz de la carpeta del modelo.
    """
    proyecto = unity.buscar_proyecto()
    if not unity.ruta_unity():
        di(t("ex_sin_unity_editor"))
        return False
    if not proyecto:
        di(t("ex_sin_proyecto_unity"))
        return False
    try:
        datos = unity.exportar_esqueleto(proyecto, pid, trabajo / "skeleton_dump", di)
    except Exception as e:
        di(t("ex_aviso_esqueleto_unity", str(e)[:400]))
        return False
    return _glb_desde_dump(raiz, pid, etiqueta, trabajo / "skeleton_dump", resumen, di, datos, "unity")


def extraer_personaje(p: dict, datos: dict, destino_raiz: Path, opciones: dict,
                      log=None, progreso=None, estado=None, base=None, traje=None) -> Path:
    """Extrae un personaje. Si `base` (o la base declarada en la configuracion) apunta a un modelo
    base, se traen tambien de alli la cara, los ojos y el pelo a la carpeta `06_modelo_base/`.

    `traje` elige UN traje concreto del actor (clave como `thief`, o la ficha que da el catalogo).
    Sin el, un actor con varios trajes devolvia todos a la vez, mezclados en la misma carpeta.
    """
    def di(texto):
        if log:
            log(texto)

    def marca(v, texto=None):
        if progreso:
            progreso(v)
        if estado and texto:
            estado(texto)

    # --- que traje: la clave y su lista de ficheros. Si no se pide ninguno, se usan los del catalogo
    clave_traje, nombre_traje, ficheros_rel = None, "", list(p["ficheros"])
    if traje:
        if isinstance(traje, dict):
            clave_traje = traje.get("clave")
            nombre_traje = traje.get("nombre") or clave_traje or ""
            if traje.get("ficheros"):
                ficheros_rel = list(traje["ficheros"])
        else:
            clave_traje = str(traje)
            for T in (p.get("trajes") or []):
                if T.get("clave") == clave_traje:
                    nombre_traje = T.get("nombre") or clave_traje
                    if T.get("ficheros"):
                        ficheros_rel = list(T["ficheros"])
                    break

    t0 = time.time()
    pid = p["id"]
    etiqueta = p.get("nombre") or pid.upper()
    # Los escenarios, props y efectos no tienen esqueleto de personaje ni modelo base: se tratan
    # igual que cualquier modelo (geometria, texturas, FBX, vistas previas) pero sin esos pasos.
    es_personaje = (p.get("categoria") or "personaje") == "personaje"
    sufijo = ("_%s" % clave_traje) if clave_traje else ""
    nombre_carpeta = _limpiar("%s_%s%s" % (pid, etiqueta.replace(" ", "_").replace("/", "-"),
                                           sufijo))
    raiz = Path(destino_raiz) / nombre_carpeta
    for sub in ("01_model/obj", "02_textures", "03_skeleton", "04_expressions",
                "05_materials", "preview"):
        (raiz / sub).mkdir(parents=True, exist_ok=True)

    marca(5, t("ex_localizando"))
    carpeta_bundles = ajustes.carpeta_bundles()
    ficheros = [carpeta_bundles / f for f in ficheros_rel]
    ficheros = [f for f in ficheros if f.is_file()]
    if not ficheros:
        raise RuntimeError(t("ex_sin_ficheros"))
    if clave_traje:
        di(t("ex_traje_elegido", nombre_traje, clave_traje))
    di(t("ex_vive_en", len(ficheros)))

    trabajo = raiz / "_temporal"
    shutil.rmtree(trabajo, ignore_errors=True)
    trabajo.mkdir(parents=True, exist_ok=True)

    # --- geometria y texturas
    marca(15, t("ex_geometria"))
    if opciones.get("mallas", True) or opciones.get("texturas", True):
        tipos = []
        if opciones.get("mallas", True):
            tipos.append("mesh")
        if opciones.get("texturas", True):
            tipos.append("tex2d")
        di(t("ex_extrayendo_de", ", ".join(tipos), len(ficheros)))
        _ejecutar_motor_por_fichero(ficheros, trabajo / "export", "export", ",".join(tipos), di)

    marca(45, t("ex_ordenando"))
    crudos_obj = sorted((trabajo / "export").rglob("*.obj"))
    crudos_png = sorted((trabajo / "export").rglob("*.png"))
    di(t("ex_motor_devolvio", len(crudos_obj), len(crudos_png)))

    texturas_parte: dict[str, list[Path]] = {k: [] for k in PARTES}
    # las bases de textura de cada parte: `pc077_01_body_lodlow`, `pc077_01_weapon_02`... sirven
    # para enlazar cada malla con SUS texturas y no con las de la pieza de al lado.
    bases_por_parte: dict[str, list[str]] = {
        k: sorted({_base_textura(p.stem) for p in crudos_png if _clasificar(p.stem) == k})
        for k in PARTES}

    # el atlas "principal" de cada parte: el grupo mas corto que trae color base. Es el que usa una
    # pieza que no tiene texturas propias (el tocado se pinta con el atlas del cuerpo).
    def _tiene_color(parte: str, base_tx: str) -> bool:
        return any(_clasificar(t.stem) == parte and _base_textura(t.stem) == base_tx
                   and any(t.stem.lower().endswith(s) for s in MAPAS_COLOR)
                   for t in crudos_png)

    principal_por_parte: dict[str, str | None] = {}
    for parte in PARTES:
        cands = [b for b in bases_por_parte[parte] if _tiene_color(parte, b)]
        principal_por_parte[parte] = min(cands, key=len) if cands else None

    incluir_armas = bool(opciones.get("armas", True))
    # las subcarpetas por pieza solo tienen sentido en un PERSONAJE: sus armas y sus props (la
    # guitarra, la estrella) van cada uno con sus texturas. Un escenario u objeto trae cientos de
    # piezas sueltas y ahi se quedan como estaban, en su carpeta por parte.
    partes_sueltas = PARTES_SUELTAS if es_personaje else ()

    # trajes conocidos del actor: sirven para descartar las piezas que el bundle trae de OTRO traje
    claves_actor = [T.get("clave") for T in (p.get("trajes") or []) if T.get("clave")]

    # --- reparto de las mallas: cada arma y cada prop en su propia subcarpeta, para que sus
    # texturas no se mezclen con las del cuerpo (criterio del paquete de referencia).
    piezas: list[tuple[Path, str, str, str | None]] = []
    for obj in crudos_obj:
        if _es_malla_hueso(obj.stem):
            continue
        if clave_traje and not _es_del_traje(obj.stem, pid, clave_traje, claves_actor):
            continue
        parte = _clasificar(obj.stem)
        if parte == "weapons" and not incluir_armas:
            continue
        sub = _nombre_pieza(obj.stem, pid) if parte in partes_sueltas else ""
        pref = _prefijo_rig(obj.stem) or obj.stem.lower()
        grupo = _emparejar(pref, bases_por_parte[parte])
        piezas.append((obj, parte, sub, grupo))

    # --- reparto de las texturas, cada una junto a su pieza
    for png in crudos_png:
        if clave_traje and not _es_del_traje(png.stem, pid, clave_traje, claves_actor):
            continue
        parte = _clasificar(png.stem)
        if parte == "weapons" and not incluir_armas:
            continue
        sub = ""
        if parte in partes_sueltas:
            base_tx = _base_textura(png.stem)
            for _obj, pt, s, g in piezas:
                if pt == parte and g and g == base_tx:
                    sub = s
                    break
        destino = raiz / "02_textures" / parte / sub
        destino.mkdir(parents=True, exist_ok=True)
        final = destino / png.name
        if not final.exists():
            shutil.copy2(png, final)
        texturas_parte[parte].append(final)

    resumen = {"id": pid, "nombre": etiqueta, "extraido": time.strftime("%Y-%m-%d %H:%M"),
               "traje": clave_traje, "traje_nombre": nombre_traje,
               "ficheros_origen": [str(f.relative_to(carpeta_bundles)) for f in ficheros],
               "partes": {k: {"mallas": [], "texturas": []} for k in PARTES},
               "materiales": [], "huesos": 0, "morphs": 0}
    for parte in PARTES:
        resumen["partes"][parte]["texturas"] = [
            str(t.relative_to(raiz / "02_textures" / parte)) for t in texturas_parte[parte]]

    for obj, parte, sub, grupo in piezas:
        if not opciones.get("mallas", True):
            continue
        final = raiz / "01_model/obj" / parte / sub / obj.name
        asociadas = [t for t in texturas_parte[parte]
                     if grupo and _base_textura(t.stem) == grupo]
        # si el grupo de la pieza no trae color base (una malla `lodlow` suele venir solo con la
        # normal), se completa con el atlas principal de la parte para no dejarla sin pintar
        if _elegir_mapa(asociadas, MAPAS_COLOR) is None and parte not in partes_sueltas:
            prin = principal_por_parte.get(parte)
            extra = [t for t in texturas_parte[parte]
                     if prin and _base_textura(t.stem) == prin]
            asociadas = extra or texturas_parte[parte]
        material = _colocar_malla(final, obj, asociadas, raiz, _nombre_material(obj.stem))
        rel = str(final.relative_to(raiz / "01_model/obj"))
        resumen["partes"][parte]["mallas"].append(rel)
        resumen["materiales"].append({"malla": rel, "material": material,
                                      "texturas": [t.name for t in asociadas],
                                      "origen": "skin"})

    # --- modelo base: si el personaje es una skin, la cara, los ojos y el pelo viven en otro
    # personaje. La relacion no esta en ningun fichero del juego, asi que se declara (o se propone
    # desde la interfaz) y aqui se traen esas piezas a una carpeta aparte, con sus texturas.
    base_id = None
    if base:
        base_id = base if isinstance(base, str) else (base.get("base") or base.get("id"))
    if not base_id and p.get("es_skin"):
        base_id = bases.base_de(pid)
    if base_id:
        marca(62, t("ex_trayendo_base"))
        try:
            info_base = _extraer_modelo_base(raiz, trabajo, base_id, opciones, di, marca)
            if info_base:
                info_base["declarado"] = bool(p.get("es_skin")) or True
                resumen["modelo_base"] = info_base
                resumen["materiales"].extend(info_base.get("materiales") or [])
        except Exception as e:
            di(t("ex_aviso_base", base_id, str(e)[:300]))
            resumen["modelo_base_error"] = {"id": base_id, "error": str(e)[:300]}

    # --- huesos y pesos de piel. Via principal: se leen de los propios bundles (rapido y general,
    # sirve para cualquier personaje). Respaldo: montarlo dentro de Unity, que solo cubre los
    # personajes que esten en el proyecto decompilado.
    if opciones.get("esqueleto", True) and es_personaje:
        marca(58, t("ex_esqueleto"))
        filtro_traje = None
        if clave_traje:
            claves_actor = [T.get("clave") for T in (p.get("trajes") or []) if T.get("clave")]
            filtro_traje = lambda n: _es_del_traje(n, pid, clave_traje, claves_actor)  # noqa: E731
        hecho = _esqueleto_por_bundles(raiz, pid, etiqueta, trabajo, ficheros, base_id, resumen, di,
                                       filtro=filtro_traje)
        if not hecho:
            di(t("ex_esqueleto_respaldo_unity"))
            if not _esqueleto_por_unity(raiz, pid, etiqueta, trabajo, resumen, di):
                marca(60, t("ex_rigs"))
                _esqueleto_del_juego(raiz, trabajo, ficheros, resumen, di)

    # las expresiones no viajan en el formato OBJ; se deja dicho para que nadie las busque
    (raiz / "04_expressions/LEEME.txt").write_text(t("ex_leeme"), encoding="utf-8")

    # --- tabla de materiales
    marca(68, t("ex_tabla"))
    (raiz / "05_materials/materiales.json").write_text(
        json.dumps(resumen["materiales"], ensure_ascii=False, indent=1), encoding="utf-8")
    lineas = [t("ex_tabla_titulo"), "", t("ex_tabla_cab"), "|---|---|---|---|"]
    for m in resumen["materiales"]:
        lineas.append("| %s | %s | %s | %s |" % (m["malla"], m.get("origen", "skin"),
                                                 m["material"],
                                                 ", ".join(m["texturas"]) or "-"))
    (raiz / "05_materials/tabla_texturas.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")

    # --- vistas previas
    dibujadas = []
    if opciones.get("previas", True):
        marca(78, t("ex_previas"))
        pendientes = []
        for parte in PARTES:
            carpeta_obj = raiz / "01_model/obj" / parte
            if not carpeta_obj.is_dir():
                continue
            for ruta_obj in sorted(carpeta_obj.rglob("*.obj")):
                if _es_descartable(ruta_obj.stem):
                    continue
                pendientes.append((parte, ruta_obj))
        # Un escenario puede traer mas de mil mallas: dibujarlas todas tarda minutos y la lamina
        # sale ilegible. Se dibujan las piezas mas grandes (las que se reconocen de un vistazo) y
        # se deja dicho en el resumen cuantas quedaron fuera.
        if not es_personaje and len(pendientes) > MAX_PREVIAS_ESCENA:
            pendientes.sort(key=lambda t: -t[1].stat().st_size)
            resumen["previas_limitadas"] = {"dibujadas": MAX_PREVIAS_ESCENA,
                                            "total": len(pendientes)}
            di(t("ex_escenario_mallas", len(pendientes), MAX_PREVIAS_ESCENA))
            pendientes = pendientes[:MAX_PREVIAS_ESCENA]
        for parte, ruta_obj in pendientes:
            salida = raiz / "preview" / ("%s_%s.png" % (parte, _limpiar(ruta_obj.stem)))
            try:
                dibujada = preview.dibujar(
                    ruta_obj, salida, ruta_mtl=ruta_obj.with_suffix(".mtl"),
                    texturas={t.stem: t for t in texturas_parte[parte]},
                    titulo=t("prev_titulo", etiqueta, ruta_obj.stem))
                if dibujada:
                    dibujadas.append(dibujada)
            except Exception as e:
                di(t("ex_no_dibujar", ruta_obj.name, e))
        if dibujadas:
            if es_personaje:
                preview.hoja_de_contacto(dibujadas, raiz / "preview/lamina_completa.png",
                                         titulo=t("prev_titulo_lamina", etiqueta, pid.upper()))
            else:
                # un escenario con decenas de mallas da una lamina altisima si va en 3 columnas
                preview.hoja_de_contacto(dibujadas, raiz / "preview/lamina_completa.png",
                                         titulo=t("prev_titulo_lamina", etiqueta, pid.upper()),
                                         columnas=6, celda=(240, 320))

    # las piezas del base tambien se dibujan, para poder comprobar de un vistazo que la cara llego
    if resumen.get("modelo_base") and opciones.get("previas", True):
        dibujadas_base = []
        for parte in bases.PIEZAS_BASE:
            carpeta_obj = raiz / CARPETA_BASE / "01_model/obj" / parte
            if not carpeta_obj.is_dir():
                continue
            for ruta_obj in sorted(carpeta_obj.glob("*.obj")):
                if _es_descartable(ruta_obj.stem):
                    continue
                salida = raiz / "preview" / ("base_%s_%s.png" % (parte, _limpiar(ruta_obj.stem)))
                try:
                    dibujada = preview.dibujar(
                        ruta_obj, salida, ruta_mtl=ruta_obj.with_suffix(".mtl"),
                        texturas={t.stem: t for t in
                                  (raiz / CARPETA_BASE / "02_textures" / parte).glob("*.png")},
                        titulo=t("prev_titulo_base", resumen["modelo_base"]["nombre"],
                                 ruta_obj.stem))
                    if dibujada:
                        dibujadas_base.append(dibujada)
                except Exception as e:
                    di(t("ex_no_dibujar", ruta_obj.name, e))
        if dibujadas_base:
            preview.hoja_de_contacto(dibujadas_base,
                                     raiz / "preview/lamina_modelo_base.png",
                                     titulo=t("prev_lamina_base", etiqueta,
                                              resumen["modelo_base"]["nombre"]))

    # el volcado de Unity deja su log abierto un instante: se reintenta el borrado, que si no la
    # carpeta `_temporal` se queda en el paquete con restos
    for _ in range(3):
        shutil.rmtree(trabajo, ignore_errors=True)
        if not trabajo.exists():
            break
        time.sleep(1)

    # --- FBX final: se monta desde el GLB riggeado, para que salga CON armadura y pesos
    if opciones.get("fbx", True):
        marca(72, t("ex_fbx"))
        blender = dependencias.ruta_blender()
        if not blender:
            di(t("ex_no_blender"))
        else:
            try:
                script = _ruta_recurso("fbx_blender.py")
                salida_fbx = raiz / ("%s_full.fbx" % _limpiar(etiqueta.replace(" ", "_")))
                # el GLB de la raiz ya trae esqueleto, pesos, expresiones y texturas: es el
                # unico origen del que puede salir un FBX riggeado. Los OBJ son geometria pura.
                glb = None
                if resumen.get("glb"):
                    cand = raiz / resumen["glb"]
                    if cand.is_file():
                        glb = cand
                orden = [str(blender), "--background", "--python", str(script), "--"]
                if glb:
                    orden += ["--glb", str(glb)]
                    di(t("ex_blender_glb"))
                else:
                    carpetas_obj = [str(raiz / "01_model/obj")]
                    # si hay modelo base, su cara y su pelo entran en el mismo FBX para tener el
                    # personaje entero de una sola pieza
                    if resumen.get("modelo_base"):
                        carpeta_base = raiz / CARPETA_BASE / "01_model/obj"
                        if carpeta_base.is_dir():
                            carpetas_obj.append(str(carpeta_base))
                    for carpeta in carpetas_obj:
                        orden += ["--obj", carpeta]
                    di(t("ex_blender_obj"))
                orden.append(str(salida_fbx))
                # el script de Blender no puede importar el paquete: se le pasa el idioma por entorno
                entorno_blender = dict(os.environ, P5X_IDIOMA=idioma_actual())
                r = subprocess.run(orden, capture_output=True, text=True, timeout=3600,
                                   env=entorno_blender,
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                if salida_fbx.is_file() and salida_fbx.stat().st_size > 0:
                    resumen["fbx"] = salida_fbx.name
                    resumen["fbx_mb"] = round(salida_fbx.stat().st_size / 1048576, 1)
                    resumen["fbx_con_esqueleto"] = bool(glb)
                    di(t("ex_fbx_listo", salida_fbx.name, resumen["fbx_mb"],
                         t("ex_con_esqueleto") if glb else t("ex_sin_esqueleto")))
                else:
                    di(t("ex_blender_no_escribio", (r.stderr or r.stdout or "")[-300:]))
            except Exception as e:
                di(t("ex_no_fbx", str(e)[:200]))

    # --- aviso si el modelo viene sin cara
    # Un personaje sin cara ni ojos casi siempre es una skin: su cara vive en el modelo base, que es
    # otro conjunto de bundles que el juego no enlaza por nombre. Conviene decirlo, porque si no el
    # usuario recibe un modelo incompleto sin saber por que.
    sin_cara = [n for n in ("face", "eyes") if not resumen["partes"].get(n, {}).get("mallas")]
    if es_personaje and len(sin_cara) == 2:
        base_info = resumen.get("modelo_base")
        if base_info and (base_info.get("mallas") or {}).get("face"):
            di(t("ex_skin_tomado", base_info["nombre"], CARPETA_BASE))
        else:
            resumen["sin_cara"] = True
            di(t("ex_aviso_sin_cara"))
            di(t("ex_aviso_skin"))
            di(t("ex_aviso_indicar_base"))

    # --- README y resumen
    marca(92, t("ex_escribiendo"))
    resumen["duracion_segundos"] = round(time.time() - t0, 1)
    resumen["carpeta"] = str(raiz)
    (raiz / "SUMMARY.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=1),
                                       encoding="utf-8")

    lineas = [
        "# %s (%s)" % (etiqueta, pid.upper()), "",
        t("ex_readme_intro", ajustes.VERSION, resumen["extraido"]), "",
    ]
    if clave_traje:
        lineas += [t("ex_readme_traje", nombre_traje or clave_traje, clave_traje), ""]
    if not es_personaje:
        tipo_llano = t("ex_readme_tipo_" + (p.get("categoria") or "modelo"))
        lineas += [t("ex_readme_tipo", tipo_llano), ""]
        if resumen.get("previas_limitadas"):
            pl = resumen["previas_limitadas"]
            lineas += [t("ex_readme_previas_lim", pl["total"], pl["dibujadas"]), ""]
    lineas += [
        t("ex_readme_que_hay"), "",
        t("ex_readme_carpeta_cont"), "|---|---|",
        t("ex_readme_glb_row"),
        t("ex_readme_fbx_all"),
        t("ex_readme_01"),
        t("ex_readme_02"),
        t("ex_readme_03"),
        t("ex_readme_04"),
        t("ex_readme_05"),
        t("ex_readme_prev"),
    ]
    if resumen["partes"]["weapons"]["mallas"]:
        lineas.append(t("ex_readme_weapons"))
    if resumen["partes"]["other"]["mallas"]:
        lineas.append(t("ex_readme_other"))
    if resumen.get("modelo_base"):
        b = resumen["modelo_base"]
        lineas.append(t("ex_readme_base_row", CARPETA_BASE, b["nombre"]))
    if resumen.get("fbx"):
        if resumen.get("fbx_con_esqueleto"):
            lineas.append(t("ex_readme_fbx_rig"))
        else:
            lineas.append(t("ex_readme_fbx_norig"))
    lineas += [
        "", t("ex_readme_piezas"), "",
        t("ex_readme_parte_cab"), "|---|---|---|",
    ]
    for parte in PARTES:
        d = resumen["partes"][parte]
        if not d["mallas"] and not d["texturas"]:
            continue
        lineas.append("| %s | %d | %d |" % (nombre_parte(parte), len(d["mallas"]),
                                            len(d["texturas"])))
    if resumen.get("modelo_base"):
        b = resumen["modelo_base"]
        lineas += ["", t("ex_readme_base_titulo"),
                   t("ex_readme_base_1"),
                   t("ex_readme_base_2", b["nombre"]),
                   t("ex_readme_base_3", CARPETA_BASE), ""]
        for f in b.get("bundles", []):
            lineas.append("- `%s`" % f)
        lineas.append("")
        for parte in bases.PIEZAS_BASE:
            if not (b.get("mallas") or {}).get(parte):
                continue
            lineas.append(t("ex_readme_base_parte", nombre_parte(parte), len(b["mallas"][parte]),
                            len((b.get("texturas") or {}).get(parte) or [])))
    lineas += ["", t("ex_readme_abrir"), "",
               t("ex_readme_abrir_txt"), "",
               t("ex_readme_lod"), ""]
    if resumen["partes"]["weapons"]["mallas"] or resumen["partes"]["other"]["mallas"]:
        lineas += [t("ex_readme_armas_props"), ""]
    if resumen.get("esqueleto"):
        e = resumen["esqueleto"]
        lineas += [t("ex_readme_esq_titulo"), "",
                   t("ex_readme_esq_1", e["glb"]), "",
                   t("ex_readme_huesos", e["huesos"]),
                   t("ex_readme_pesos", e["mallas_con_pesos"], e["mallas"]),
                   t("ex_readme_morphs", e.get("expresiones", 0)),
                   (t("ex_readme_hecho_unity", e["unity"]) if e.get("unity")
                    else t("ex_readme_hecho_bundles")),
                   ""]
        if resumen.get("fbx_con_esqueleto"):
            lineas += [t("ex_readme_fbx_rig2"), ""]
        lineas += [t("ex_readme_esq_2"), ""]
    lineas += [t("ex_readme_aviso"), "", t("ex_readme_aviso_txt"), ""]
    (raiz / "README.md").write_text("\n".join(lineas), encoding="utf-8")

    marca(100, t("ex_terminado"))
    di(t("ex_listo_en", resumen["duracion_segundos"]))
    return raiz