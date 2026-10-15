"""Visor de Bust-ups: monta los retratos del juego por capas leyendo la carpeta del bulk.

Un bust-up es uno de los JSON `UI-DialogShader-<ropa>-<personaje>` (los parametros del shader de la
interfaz). Sus capas son los sprites sueltos que saca el bulk de texturas: contorno, cuerpo, ropa,
ojos, boca y pelo, cada uno en su PNG.

La posicion de cada parte NO se lee del juego (los bundles instalados estan cifrados y el prefab no
es legible): se busca el sprite dentro de su hoja **comparando pixeles**, asi que el visor funciona
solo con la carpeta de texturas que el usuario ya tiene. El porque de cada decision esta en
`INFORME_SOMBREADO_BUSTUPS.md` (raiz del proyecto).

Sin numpy a proposito: esta en los EXCLUIDOS del .spec para que el ejecutable no engorde. La busqueda
va por piramide (÷16 -> ÷4 -> ÷1) con las operaciones de PIL, que son en C.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from PIL import Image, ImageChops

from . import ajustes, sombreado

# --------------------------------------------------------------------------- orden de apilado
# El PELO va ARRIBA de la cara: el flequillo tapa el borde de los ojos y de la piel. Si va debajo se
# ven pixeles de piel sobre el negro del pelo. La MASCARA va ARRIBA del pelo: en el juego se lleva
# puesta sobre el pelo (como la mascara de zorro de lizi). El contorno va DEBAJO de todo.
# La ROPA va DESPUES de la cara: `benti-tongchang` es el cuerpo completo (piel + bordes de ropa)
# y si la ropa se compone antes, el cuerpo tintado la tapona. Al poner `yifu` despues de `face`,
# la chaqueta limpia (sin tinte) pisa la ropa del cuerpo y se ve su color original.
ORDEN = [
    ("outline", ("lunkuo", "lunkuo1")),
    ("body", ("benti", "shenti", "zhengti")),
    ("arms", ("zhi", "shou", "bi")),
    ("blush", ("saihong", "haixiu", "hongyun", "saihonghunluan")),
    ("face", ("cara", "lian")),
    ("clothes", ("yifu", "yifu1", "fu")),
    ("eyes", ("yan", "yan1", "yan2", "yan3")),
    ("mouth", ("zui", "zui1", "zui2", "zui3")),
    ("marks", ("han", "lei")),
    ("hair", ("toufa", "toufa1")),
    ("mask", ("mask", "rmask", "lmask", "mianju", "mianju1", "mianju2")),
    ("glasses", ("yanjing", "mojing")),
    ("hat", ("maozi",)),
]
# partes del cuerpo: no dependen de la expresion, van siempre
PARTES_BASE = ("benti", "shenti", "zhengti")
# pasos de ESTRUCTURA: si la expresion elegida no trae esa parte, se cae al cuerpo base (el pelo, la
# ropa o la cara suelen venir una sola vez, y la cara del gesto por defecto se llama `tongchang`)
PASOS_ESTRUCTURA = ("outline", "body", "arms", "clothes", "face", "hair")

# Pasos que se pueden prestar de otra ropa del mismo personaje cuando la suya no los trae: la
# estructura y la cara (ojos y boca incluidos). Los adornos NO entran: el sombrero, la mascara o el
# rubor son de cada traje y prestarlos queda peor que dejarlos fuera.
PASOS_PRESTABLES = PASOS_ESTRUCTURA + ("eyes", "mouth")

# Pasos que reciben el shader de dialogo (el tinte cálido del juego). El juego NO tiñe todas las
# capas por igual: el uniforme conserva su color original mientras la piel y la cara se tiñen.
# Estos pasos se sombreaden ANTES de componer; los demás se pisan encima sin tocar.
# (Ajustado midiendo contra capturas del juego: la ropa NO se tiñe, la piel SI.)
PASOS_CON_SHADER = frozenset({"body", "arms", "face", "eyes", "mouth", "blush", "marks"})

# Sufijos de los assets UIMuitipleGradientParam que el juego asigna por slot de capa
# (ConfDialogMatParam): cada capa puede tener sus PROPIOS parametros de shader. Si existe un
# asset con ese sufijo para el bust-up, se usa en vez del base.
_SUFIJO_PASO = {"eyes": "-eye", "face": "-face", "hair": "-toufa", "mask": "-mianju"}
# Sufijos que marcan una VARIANTE de shader por capa, no un bust-up aparte: no deben aparecer
# en la lista del visor (son los parametros internos de -eye/-face/-toufa/-mianju de cada capa).
_SUFIJOS_VARIANTE_SHADER = frozenset({"-eye", "-face", "-toufa", "-mianju", "-tongfa"})

# nombre visible de cada paso (la interfaz va solo en ingles)
ETIQUETA = {"outline": "Outline", "body": "Body", "arms": "Arms", "clothes": "Clothes",
            "blush": "Blush", "face": "Face", "eyes": "Eyes", "mouth": "Mouth", "marks": "Marks",
            "mask": "Mask", "hair": "Hair", "glasses": "Glasses", "hat": "Hat"}


def _datos_empaquetados(nombre: str) -> Path:
    """Ruta del JSON que viaja dentro del ejecutable (o al lado, en el codigo fuente)."""
    if getattr(sys, "frozen", False) and getattr(sys, "_MEIPASS", None):
        return Path(sys._MEIPASS) / "p5x_studio" / "datos" / nombre
    return Path(__file__).resolve().parent / "datos" / nombre


_EMPAREJADO: dict = {}


def emparejado() -> dict:
    """El mapa JSON del shader -> capas, medido sobre el juego (`_dl/emparejado_bustups.json`).

    Se lee una sola vez: el fichero pesa ~200 KB y la lista del visor lo pide por cada bust-up.
    """
    if _EMPAREJADO:
        return _EMPAREJADO
    ruta = _datos_empaquetados("bustups.json")
    if not ruta.exists():
        return {}
    try:
        _EMPAREJADO.update(json.loads(ruta.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return {}
    return _EMPAREJADO


# --------------------------------------------------------------------------- nombres de capa
def partir_nombre(nombre: str, personaje: str, ropa: str) -> tuple[str, str]:
    """(expresion, parte) de un nombre de capa.

    El juego no es constante, asi que se admiten las dos convenciones que se midieron:
    `<personaje>-<ropa>-<capa>[-<expresion>]` y `<personaje>-<ropa>-<expresion>-<parte><n>`.
    """
    resto = nombre
    # la ropa puede venir con variante (`changfu01`) y los sprites ir sin ella (`xiachuanling-changfu-benti`),
    # pero hay ropas cuyo numero SI forma parte del nombre (`gaojuanxing-guaidao01-beiai-yan1`): se
    # prueban las dos formas, la exacta primero, o los ojos y la boca de esos bust-ups se pierden
    ropa_limpia = re.sub(r"\d+$", "", ropa or "")
    for prefijo in ("%s-%s-" % (personaje, ropa), "%s-%s-" % (personaje, ropa_limpia),
                    "%s-" % personaje, "%s_" % personaje):
        if resto.startswith(prefijo):
            resto = resto[len(prefijo):]
            break
    trozos = [t for t in resto.split("-") if t]
    if not trozos:
        return "base", nombre
    if _sin_copia(trozos[0]) in PARTES_BASE:
        # `benti-toufa` -> parte `toufa`; `benti` -> parte `benti`
        if len(trozos) == 1:
            return "base", trozos[0]
        ultimo = trozos[-1]
        if paso_de(ultimo) is not None:
            return "base", ultimo
        # `benti-tongchang`: no es una parte, es la CARA de esa expresion (el cuerpo base no lleva
        # expresion). Sin esta regla la cara se cae y el retrato sale con la cabeza en negra.
        return trozos[1], "cara"
    if len(trozos) >= 2:
        return trozos[0], trozos[1]
    return "base", trozos[0]


def _sin_copia(parte: str) -> str:
    """Quita el sufijo de copia con que el motor vuelve a exportar el mismo asset (`lunkuo_2`).

    El juego saca varias copias del mismo dibujo (una por variante de ropa, por estado...). Sin
    limpiarlo, `benti-lunkuo_2` no se reconocia como contorno y caia en la regla de la CARA: el visor
    pintaba encima un contorno entero (el dibujo completo de la variante, o sea otro busto) creyendo
    que era el rostro. Es el mismo lio de texturas compartidas que ya salio con los modelos.
    """
    return re.sub(r"_\d+$", "", parte or "")


def paso_de(parte: str) -> str | None:
    """A que paso del orden de apilado pertenece una parte (`yan1` -> `eyes`)."""
    limpio = "".join(c for c in _sin_copia(parte).lower() if not c.isdigit())
    for paso, nombres in ORDEN:
        if limpio in nombres:
            return paso
    return None


# --------------------------------------------------------------------------- busqueda por pixeles
def _mascara(im: Image.Image) -> Image.Image:
    """Silueta: blanco donde el pixel se ve, negro donde es transparente."""
    return im.getchannel("A").point(lambda v: 255 if v > 20 else 0)


def _puntua(hoja: Image.Image, sprite: Image.Image, x: int, y: int) -> int:
    """Pixeles que no coinciden al poner `sprite` en (x, y) de `hoja` (menos es mejor)."""
    w, h = sprite.size
    recorte = hoja.crop((x, y, x + w, y + h))
    hist = ImageChops.difference(recorte, sprite).histogram()
    return sum(i * c for i, c in enumerate(hist))


def _etapa(hoja_m, sprite_m, escala, ventana=None, candidatos=6):
    """Puntua la rejilla a una escala (dentro de `ventana`, en pixeles de esa escala).

    Devuelve las mejores posiciones EN PIXELES DE LA IMAGEN ORIGINAL, de mejor a peor.
    """
    W = max(1, hoja_m.width // escala)
    H = max(1, hoja_m.height // escala)
    hoja = hoja_m.resize((W, H), Image.BILINEAR)
    sprite = sprite_m.resize((max(1, sprite_m.width // escala),
                              max(1, sprite_m.height // escala)), Image.BILINEAR)
    w, h = sprite.size
    if w > W or h > H:
        return []
    x0, y0, x1, y1 = ventana or (0, 0, W - w, H - h)
    puntos = []
    for y in range(max(0, y0), min(H - h, y1) + 1):
        for x in range(max(0, x0), min(W - w, x1) + 1):
            puntos.append((_puntua(hoja, sprite, x, y), x * escala, y * escala))
    puntos.sort()
    return puntos[:candidatos]


def localizar(hoja: Image.Image, sprite: Image.Image) -> tuple[tuple[int, int] | None, float]:
    """(x, y) del sprite dentro de la hoja y fraccion de pixeles que no coinciden.

    Piramide de tres etapas: primero toda la hoja a ÷16, luego una ventana a ÷4 alrededor de los
    mejores, y por ultimo el pixel exacto. Se prueban varios candidatos porque muchas expresiones
    comparten silueta y el pico mas alto no siempre es el bueno.
    """
    hoja_m, sprite_m = _mascara(hoja), _mascara(sprite)
    if sprite_m.width > hoja_m.width or sprite_m.height > hoja_m.height:
        return None, 1.0
    gruesos = _etapa(hoja_m, sprite_m, 16, candidatos=6)
    if not gruesos:
        return None, 1.0
    medios = []
    for _, x, y in gruesos[:3]:
        cx, cy = x // 4, y // 4
        medios += _etapa(hoja_m, sprite_m, 4, (cx - 16, cy - 16, cx + 16, cy + 16), candidatos=4)
    medios.sort()
    if not medios:
        medios = gruesos
    sprite_px = sprite.convert("RGBA")
    mejor, mejor_dif = None, None
    for _, x, y in medios[:4]:
        for _, xx, yy in _etapa(hoja_m, sprite_m, 1, (x - 5, y - 5, x + 5, y + 5), candidatos=4):
            w, h = sprite_px.size
            if xx < 0 or yy < 0 or xx + w > hoja.width or yy + h > hoja.height:
                continue
            recorte = hoja.crop((xx, yy, xx + w, yy + h)).convert("RGBA")
            # solo cuentan los pixeles que se ven: bajo un transparente el RGB de la hoja es basura
            alfa = ImageChops.lighter(recorte.getchannel("A"), sprite_px.getchannel("A"))
            alfa = alfa.point(lambda v: 255 if v > 0 else 0)
            visibles = sum(c for v, c in enumerate(alfa.histogram()) if v > 0)
            # la diferencia se mide en L sobre RGB (mezclar el alfa daria valores sin sentido) y se
            # apaga fuera de la silueta, para que no cuenten los pixeles transparentes
            dif = ImageChops.difference(recorte.convert("RGB"), sprite_px.convert("RGB")).convert("L")
            dif = Image.composite(dif, Image.new("L", dif.size, 0), alfa)
            malos = sum(c for v, c in enumerate(dif.histogram()) if v > 3)
            frac = (malos / float(visibles)) if visibles else 0.0
            if mejor_dif is None or frac < mejor_dif:
                mejor, mejor_dif = (xx, yy), frac
            if frac <= 0.002:
                return mejor, mejor_dif
    return mejor, mejor_dif


# --------------------------------------------------------------------------- indice de texturas
# carpeta del extracto de retratos (lo que saca el boton del visor), dentro de la carpeta de salida
CARPETA_RETRATOS = "portraits"


def carpeta_texturas(elegida: Path | None = None) -> Path:
    """Carpeta donde el visor busca los sprites.

    Prefiere el extracto de retratos (`portraits`, unos 170 MB) al bulk entero (63 GB): el visor no
    necesita mas y asi funciona sin haberse pasado por el bulk. Si no hay ninguna de las dos, se
    devuelve la de retratos para que el mensaje de la interfaz diga donde se pondrian.
    """
    from . import motor
    base = Path(motor.carpeta_extraidas())
    if elegida:
        return Path(elegida)
    retratos = base / CARPETA_RETRATOS
    bulk = base / "textures"

    def _tiene_png(c: Path) -> bool:
        try:
            return c.is_dir() and any(c.rglob("*.png"))
        except OSError:
            return False

    # el extracto de retratos solo manda si esta COMPLETO: con media extraccion, el bulk (que esta
    # entero) da mejores retratos que una carpeta a medias
    from . import lote
    if _tiene_png(retratos) and (lote.retratos_listos(retratos) or not _tiene_png(bulk)):
        return retratos
    if _tiene_png(bulk):
        return bulk
    return retratos


def prefijos_retratos() -> tuple:
    """Prefijos de nombre de los bust-ups emparejados: TODO lo que el visor necesita de las texturas.

    Se saca del mapa (personaje + ropa de cada bust-up, con el alias de las erratas aplicado), asi
    que el extracto de retratos no guarda ni una textura de mas... salvo el personaje entero cuando
    su cara vive en otra ropa: esos casos necesitan las texturas de la familia completa.
    """
    salida = set()
    for info in (emparejado().get("emparejados") or {}).values():
        personaje = ALIAS_PERSONAJE.get(info.get("personaje") or "", info.get("personaje") or "")
        ropa = info.get("ropa") or ""
        salida.update(_prefijos(personaje, ropa))
        if not personaje:
            continue
        # La cara puede vivir en OTRA ropa del mismo personaje (los trajes de ladron fantasma llevan
        # los ojos y la boca bajo `changfu` aunque el bust-up sea `guaidaofu`), asi que hay que guardar
        # el personaje entero. Pero SOLO cuando su propia ropa no trae cara: hacerlo siempre multiplica
        # el extracto por veinte (de 5.400 ficheros a 130.000).
        pasos = set()
        for capa in (info.get("capas") or {}).values():
            nombre = capa.get("nombre") if isinstance(capa, dict) else capa
            if nombre:
                pasos.add(paso_de(partir_nombre(nombre, personaje, ropa or "")[1]))
        if not {"face", "eyes", "mouth"} <= pasos:
            salida.add("%s-" % personaje)
    return tuple(sorted(salida))


def bundles_retratos() -> list:
    """Bundles donde viven las texturas de los retratos, medidos al emparejar.

    Van aparte del mapa porque este se recorta para el ejecutable (el visor no los necesita) y sin
    ellos el extracto tendria que mirar las 1.506 familias de texturas de interfaz en vez de 80.
    """
    ruta = _datos_empaquetados("retratos.json")
    try:
        return list(json.loads(ruta.read_text(encoding="utf-8")).get("bundles") or [])
    except (OSError, ValueError):
        return []


def indice(carpeta: Path | None = None, refrescar: bool = False) -> dict[str, list[str]]:
    """Nombre de asset -> lista de PNG (el lienzo y los recortes), medido una vez y cacheado.

    El bulk deja 118.230 PNG y recorrerlos cada vez cuesta segundos: el indice se guarda en `cache`
    y solo se rehace si la carpeta cambia de nombre o de tamano.
    """
    carpeta = Path(carpeta or carpeta_texturas())
    # `v` sube cuando cambia la forma de indexar: sin eso se reutilizaria un indice viejo
    marca = {"carpeta": str(carpeta), "n": 0, "v": 2}
    try:
        marca["n"] = sum(1 for _ in carpeta.rglob("*.png"))
    except OSError:
        return {}
    cache = ajustes.CACHE / "indice_texturas.json"
    if not refrescar and cache.exists():
        try:
            guardado = json.loads(cache.read_text(encoding="utf-8"))
            if guardado.get("marca") == marca:
                return guardado["indice"]
        except (OSError, ValueError):
            pass
    salida: dict[str, list[str]] = {}
    for ruta in carpeta.rglob("*.png"):
        # el juego exporta el mismo asset dos veces: `<nombre>.png` y `<nombre>_#NN.png` (una es el
        # lienzo entero y la otra el sprite recortado). El sufijo NO dice cual es cual, asi que los
        # dos van bajo la misma clave y luego se distinguen por tamano.
        clave = re.sub(r"_#\d+$", "", ruta.stem)
        salida.setdefault(clave, []).append(str(ruta))
    ajustes.CACHE.mkdir(parents=True, exist_ok=True)
    try:
        cache.write_text(json.dumps({"marca": marca, "indice": salida}, ensure_ascii=False),
                         encoding="utf-8")
    except OSError:
        pass
    return salida


def _par(idx: dict, nombre: str) -> tuple[Image.Image, Image.Image] | None:
    """(hoja, sprite) de un nombre: el PNG mas grande es el lienzo y el mas pequeno el recorte."""
    rutas = idx.get(nombre)
    if not rutas:
        return None
    try:
        rutas = sorted(rutas, key=lambda r: Path(r).stat().st_size)
        with Image.open(rutas[0]) as peque, Image.open(rutas[-1]) as grande:
            return grande.convert("RGBA"), peque.convert("RGBA")
    except (OSError, ValueError):
        return None


# --------------------------------------------------------------------------- montaje
def _info(clave: str) -> dict:
    """Ficha del emparejado: personaje, ropa y las capas de expresion (ojos y boca)."""
    return (emparejado().get("emparejados") or {}).get(clave) or {}


# El juego tiene erratas en los nombres de sus propios assets: el shader y tres mascaras de esta
# chica se llaman `aochuncun`, y TODO el resto de sus sprites (cuerpo, pelo, ropa, ojos, boca) se
# llama `aocunchun`. Sin el alias, su retrato salia con una mascara suelta y nada mas.
ALIAS_PERSONAJE = {"aochuncun": "aocunchun"}


def _prefijos(personaje: str, ropa: str) -> tuple:
    """Prefijos posibles de los nombres de capa de un bust-up.

    La ropa lleva variante en el JSON (`changfu01`) y hay conjuntos cuyos sprites van sin ella
    (`xiachuanling-changfu-benti`), pero otros la conservan (`gaojuanxing-guaidao01-beiai-yan1`): hay
    que mirar las dos formas.
    """
    limpia = re.sub(r"\d+$", "", ropa or "")
    # TODO: los prefijos cierran con guion a proposito, es lo que corta el nombre del sprite (si no,
    # `bainiao` casaria tambien con `bainiaox`). Se probo a admitir el nombre pelado para alcanzar los
    # personajes cuyo nombre en el mapa es el corto y en los assets el completo (`guaidao01-bainiao` ->
    # `bainiaochengsi-guaidaofu-...`), pero NO arregla los bust-ups sin rostro: esos montan bien y lo que
    # falta es el rostro compartido, que no sale de su propio nombre. Ver RETOMAR.md.
    return tuple(dict.fromkeys(["%s-%s-" % (personaje, ropa), "%s-%s-" % (personaje, limpia)]))


def capas_de(clave: str, idx: dict | None = None) -> list[dict]:
    """Capas de un bust-up: las del emparejado (expresiones) mas las que hay en la carpeta.

    El emparejado solo lista ojos y boca (son las que dependen de la expresion); el cuerpo, el pelo,
    la ropa y el contorno no vienen ahi, se sacan de los nombres que haya en la carpeta de texturas.
    """
    info = _info(clave)
    personaje = ALIAS_PERSONAJE.get(info.get("personaje") or "", info.get("personaje") or "")
    ropa = info.get("ropa") or ""
    vistas: dict[str, dict] = {}
    for capa in (info.get("capas") or {}).values():
        nombre = capa.get("nombre") if isinstance(capa, dict) else capa
        if not nombre:
            continue
        expresion, parte = partir_nombre(nombre, personaje, ropa)
        paso = paso_de(parte)
        if paso:
            vistas[nombre] = {"nombre": nombre, "expresion": expresion, "parte": parte, "paso": paso}
    if idx is not None:
        prefijos = _prefijos(personaje, ropa)
        for nombre in idx:
            if nombre in vistas or not nombre.startswith(prefijos):
                continue
            expresion, parte = partir_nombre(nombre, personaje, ropa)
            paso = paso_de(parte)
            if paso:
                vistas[nombre] = {"nombre": nombre, "expresion": expresion, "parte": parte,
                                  "paso": paso}
        # Respaldo por FAMILIA: el mismo personaje con OTRA ropa. Los trajes de ladron fantasma llevan
        # la cara fuera: `guaidao01-bainiao` se empareja a `bainiaochengsi`/`guaidaofu`, y de ahi solo
        # salen cuerpo, mascara, pelo y ropa; los ojos y la boca estan en `bainiaochengsi-changfu-beiai-*`.
        # Solo se rellenan los pasos que los prefijos exactos han dejado vacios (asi nada que ya
        # funcionaba cambia). Las capas de EXPRESION (ojos, boca) conservan su nombre de expresion
        # original para que el usuario pueda elegir gestos; las de estructura entran como base.
        familia = "%s-" % personaje
        faltan = set(PASOS_PRESTABLES) - {c["paso"] for c in vistas.values()}
        # Si ya hay un sprite `benti-*` en la propia ropa (que es el cuerpo completo con cara,
        # aunque lo mapee como "face"), NO pedir "body" prestado a otra ropa: el cuerpo de otra
        # ropa trae sus propios adornos (un lazo azul de `dagongfu` se colaba al fondo de
        # `guaidaofu` como cuerpo prestado).
        if any("benti" in (c.get("nombre") or "") for c in vistas.values()):
            faltan.discard("body")
        if faltan:
            for nombre in idx:
                if nombre in vistas or not nombre.startswith(familia):
                    continue
                trozos = nombre[len(familia):].split("-", 1)
                ropa_real = trozos[0] if len(trozos) > 1 else ""
                expresion, parte = partir_nombre(nombre, personaje, ropa_real)
                paso = paso_de(parte)
                if paso and paso in faltan:
                    # Para ojos y boca se conserva la expresion original (para poder elegir gestos);
                    # para estructura se marca como base
                    exp = expresion if paso in ("eyes", "mouth") else "base"
                    vistas[nombre] = {"nombre": nombre, "expresion": exp, "parte": parte,
                                      "paso": paso}
    return list(vistas.values())


def expresiones(clave: str, idx: dict | None = None) -> list[str]:
    """Expresiones disponibles en un bust-up (`base` y `0` son el cuerpo, van siempre)."""
    vistas = []
    for capa in capas_de(clave, idx):
        if capa["expresion"] not in ("base", "0") and capa["expresion"] not in vistas:
            vistas.append(capa["expresion"])
    return sorted(vistas)


def _variante(parte: str) -> int:
    """Numero de variante de una parte (`zui2` -> 2), para elegir siempre la misma."""
    m = re.search(r"(\d+)$", parte or "")
    return int(m.group(1)) if m else 0


def _elegir_capa(capas: list, paso: str, expresion: str | None) -> dict | None:
    """La capa de un paso: primero la de la expresion elegida, y si no la hay, la base.

    Los ojos, la boca y los adornos (rubor, sudor, mascara, gafas, sombrero) son POR EXPRESION: si
    esa expresion no los trae, no se inventan (colar el sudor de `juewang` en un retrato `beiai`
    queda fatal). La estructura (contorno, cuerpo, brazos, ropa, cara, pelo) cae a la capa base,
    porque suele venir una sola vez y la cara del gesto por defecto se llama `tongchang`.
    """
    del_paso = [c for c in capas if c["paso"] == paso]
    if not del_paso:
        return None
    # `0` es la capa del cuerpo por defecto (los sprites van `<personaje>-<ropa>-0-benti`) y
    # `tongchang` la cara del gesto neutro: las dos valen como respaldo de la expresion elegida
    if paso in PASOS_ESTRUCTURA:
        orden: list = [expresion, "tongchang", "0", "base", None] if expresion else ["0", "tongchang", "base", None]
    else:
        orden = [expresion, "tongchang", "0", "base"] if expresion else ["0", "tongchang", "base"]
    for exp in orden:
        elegidas = [c for c in del_paso if exp is None or c["expresion"] == exp]
        if elegidas:
            # si hay varias variantes de la misma parte (zui1, zui2) se coge siempre la primera
            elegidas.sort(key=lambda c: (_variante(c["parte"]), c["nombre"]))
            return elegidas[0]
    return None


# Unity anade 1 px de extrude al recortar y hay hojas que difieren en 2-4 px: son el mismo lienzo
TOLERANCIA_LIENZO = 4


def _encaja(tam, lienzo, tolerancia: int = TOLERANCIA_LIENZO) -> bool:
    """Si una hoja es (casi) el lienzo, con el margen del extrude."""
    return abs(tam[0] - lienzo[0]) <= tolerancia and abs(tam[1] - lienzo[1]) <= tolerancia


def _lienzo_dominante(tamanos: list) -> tuple:
    """El lienzo del retrato: el grupo de tamanos que comparten mas capas.

    Hay bust-ups con DOS lienzos: el retrato del dialogo y una silueta de CUERPO ENTERO (1076x2020)
    que va en las mismas texturas. El cuerpo entero lo comparten un par de capas y el retrato
    decenas, asi que gana el retrato. Del grupo ganador se usa el tamano MAYOR, para que ninguna
    capa se salga del lienzo.
    """
    grupos: list = []
    for tam in tamanos:
        for g in grupos:
            if _encaja(tam, g[0]):
                g[1].append(tam)
                break
        else:
            grupos.append((tam, [tam]))
    mejor = max(grupos, key=lambda g: (len(g[1]), -g[0][0] * g[0][1]))
    return max(mejor[1], key=lambda t: t[0] * t[1])


def _parametros_paso(clave: str, paso: str) -> dict | None:
    """Parametros de shader para un paso concreto: busca la variante por capa y cae al base.

    El juego asigna un UIMuitipleGradientParam por slot (head/eye/mouth/peishiN): los assets
    UI-DialogShader-<traje>-<personaje>-eye / -face / -toufa / -mianju son las variantes por capa.
    Si no hay variante para ese paso, se usan los parametros base del bust-up.
    """
    sufijo = _SUFIJO_PASO.get(paso)
    if sufijo:
        p = sombreado.parametros(clave + sufijo)
        if p:
            return p
    return sombreado.parametros(clave)


def _volcar_lote(lienzo: Image.Image, capas: list, parametros: dict | None,
                  sin_tinte: bool = False) -> None:
    """Compone un lote de capas sobre el lienzo. Si `parametros` no es None, les aplica el shader.

    El shader se aplica al lote COMPLETO (todas las capas del lote compuestas juntas) antes de
    pisarlas sobre el lienzo, para que el degradado use las coordenadas del lienzo completo y no
    las de un sprite suelto.
    """
    if not capas:
        return
    if parametros is None:
        for capa in capas:
            lienzo.alpha_composite(capa["imagen"], tuple(capa["offset"]))
        return
    # componer el lote en un lienzo temporal del tamano del lienzo final
    tmp = Image.new("RGBA", lienzo.size, (0, 0, 0, 0))
    for capa in capas:
        tmp.alpha_composite(capa["imagen"], tuple(capa["offset"]))
    tmp = sombreado.sombrear(tmp, parametros, sin_tinte=sin_tinte)
    lienzo.alpha_composite(tmp, (0, 0))


def montar(clave: str, expresion: str | None = None, carpeta: Path | None = None,
           guardar: bool = True, shader: bool = False, sin_tinte: bool = False) -> dict:
    """Monta un bust-up y devuelve el PNG, el lienzo y el detalle de cada capa.

    La expresion elige los ojos y la boca; el resto de capas (cuerpo, pelo, ropa) van siempre. Si la
    expresion pedida no existe se usa la primera que haya y se avisa.

    Con shader=True el retrato se pasa por el shader de dialogo del juego (`sombreado`), que es lo que
    le da el tono calido de las conversaciones; el PNG se guarda aparte para poder ver los dos.
    Con sin_tinte=True se aplica el tono del shader pero SIN el degradado (el tinte ambiental):
    util para ver los colores originales del personaje.
    """
    idx = indice(carpeta)
    capas = capas_de(clave, idx)
    if not capas:
        return {"ok": False, "error": "no such bust-up", "ruta": "", "capas": []}
    disponibles = expresiones(clave, idx)
    avisos = []
    if expresion and disponibles and expresion not in disponibles:
        avisos.append("expression %s not available, using %s" % (expresion, disponibles[0]))
        expresion = disponibles[0]
    if not expresion:
        # sin expresion, o con la opcion Default de la interfaz, se monta el gesto neutro del juego:
        # la cadena de eleccion cae a `tongchang` sola. Elegir `disponibles[0]` daria una cara triste
        # por defecto, que no es lo que muestra el juego al abrir el dialogo
        expresion = None

    # 1) una capa candidata por paso (la eleccion mira la expresion y cae a la base si no la hay)
    candidatas = []
    for paso, _ in ORDEN:
        capa = _elegir_capa(capas, paso, expresion)
        if capa:
            candidatas.append((paso, capa))

    # 2) leer el par hoja/sprite de cada candidata y votar el LIENZO entre todas
    leidas = []
    for paso, capa in candidatas:
        par = _par(idx, capa["nombre"])
        if not par:
            avisos.append("%s: no sprite in the textures folder" % capa["nombre"])
            continue
        leidas.append({"paso": paso, "capa": capa, "hoja": par[0], "sprite": par[1]})
    if not leidas:
        return {"ok": False, "error": "no layer could be read", "ruta": "", "capas": []}
    lienzo = _lienzo_dominante([x["hoja"].size for x in leidas])

    # 3) colocar las que caen en ese lienzo
    detalle = []
    for x in leidas:
        paso, capa, hoja, sprite = x["paso"], x["capa"], x["hoja"], x["sprite"]
        if not _encaja(hoja.size, lienzo):
            # su hoja no es el lienzo del retrato (hay bust-ups con una silueta de cuerpo entero
            # aparte): el offset seria dentro de SU hoja y sin el prefab no se puede colocar, asi que
            # se deja fuera en vez de pegarla arriba y ensuciar el montaje
            avisos.append("%s: different sheet, left out" % capa["nombre"])
            continue
        offset, dif = localizar(hoja, sprite)
        if offset is None:
            avisos.append("%s: could not be located" % capa["nombre"])
            continue
        detalle.append({"paso": paso, "etiqueta": ETIQUETA.get(paso, paso), "nombre": capa["nombre"],
                        "expresion": capa["expresion"], "offset": list(offset),
                        "hoja": list(hoja.size), "sprite": list(sprite.size),
                        "difiere": round((dif or 0) * 100, 3), "fiable": True, "imagen": sprite})

    if not detalle:
        return {"ok": False, "error": "no layer could be placed", "ruta": "", "capas": []}
    lienzo_im = Image.new("RGBA", lienzo, (0, 0, 0, 0))
    aplicado = False
    # Composicion por LOTES: las capas consecutivas con los MISMOS parametros de shader se
    # componen juntas y el shader se aplica una vez por lote. Cada capa puede tener sus propios
    # parametros (variante -eye/-face/-toufa/-mianju del asset UIMuitipleGradientParam), como
    # hace el juego con UIMultipleMaterial por slot. La ropa NO se tiñe, la piel SI.
    lote: list = []
    lote_params: dict | None = None
    lote_sombreado: bool = False
    for capa in detalle:
        paso = capa.get("paso", "")
        if shader and paso in PASOS_CON_SHADER:
            params = _parametros_paso(clave, paso)
        else:
            params = None
        somb = params is not None
        # agrupar por identidad de parametros (el cache de sombreado devuelve el mismo dict)
        misma = (params is lote_params) or (params is None and lote_params is None)
        if not lote or (somb == lote_sombreado and misma):
            lote.append(capa)
            lote_params = params
            lote_sombreado = somb
            continue
        _volcar_lote(lienzo_im, lote, lote_params, sin_tinte)
        if lote_sombreado:
            aplicado = True
        lote = [capa]
        lote_params = params
        lote_sombreado = somb
    if lote:
        _volcar_lote(lienzo_im, lote, lote_params, sin_tinte)
        if lote_sombreado:
            aplicado = True
    if shader and not aplicado:
        avisos.append("no shader parameters for this bust-up")
    ruta = ""
    if guardar:
        destino = ajustes.CACHE / "bustups"
        destino.mkdir(parents=True, exist_ok=True)
        fichero = "%s_%s%s.png" % (clave.replace("/", "-").replace("\\", "-"), expresion or "base",
                                   "_shader" if aplicado else "")
        ruta = str(destino / fichero)
        lienzo_im.save(ruta)
    return {"ok": True, "error": "", "ruta": ruta, "lienzo": list(lienzo), "expresion": expresion,
            "expresiones": disponibles, "avisos": avisos, "shader": aplicado,
            "capas": [{k: v for k, v in c.items() if k != "imagen"} for c in detalle]}