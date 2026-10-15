"""Monta un bust-up localizando cada sprite dentro de su hoja POR PIXELES.

Idea del usuario: las hojas llevan TODAS las expresiones del personaje, asi que no hay que fiarse de
los rects del dump (que obligan a volcar cada bundle). Se coge el sprite suelto de la carpeta del
bulk, se busca su trozo dentro de la hoja grande y se compone el lienzo. Asi el visor funciona solo
con la carpeta del bulk, que es lo que ya esta repartido.

Optimizacion (lo que la hace viable): en vez de probar todas las posiciones comparando ventanas
(cientos de miles de comparaciones), se correlacionan las mascaras de alfa con FFT (numpy), que da
el pico en un par de transformadas por capa; luego se refina al pixel en un entorno pequeno y se
comprueba que los pixeles coinciden de verdad. Una capa de 572x732 tarda milisegundos.

Uso:
  montar_por_pixeles.py <personaje/ropa | nombre del JSON> [--json] [-o salida.png]
  montar_por_pixeles.py xiachuanling/changfu --listar      # que expresiones hay y que va con que
"""
import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image

DL = Path(r"C:\Users\Lukas\p5x-datamining\_dl")
BULK = Path(r"C:\Users\Lukas\Desktop\P5X Studio Tools\extracted\textures")
INDICE = DL / "indice_bulk.json"

# el contorno abajo y el PELO arriba de todo
ORDEN = [
    ("contorno", ["benti-lunkuo", "shenti-lunkuo", "lunkuo"]),
    ("cuerpo", ["benti", "shenti", "zhengti"]),
    ("brazos", ["benti-zhi", "shenti-zhi", "zhi"]),
    ("ropa", ["benti-yifu", "shenti-yifu", "yifu"]),
    ("ojos", ["tongchang-yan1"]),
    ("boca", ["tongchang-zui1"]),
    ("pelo", ["benti-toufa", "shenti-toufa", "toufa"]),
]


def cargar_indice():
    """nombre de asset -> lista de PNG de la carpeta del bulk (cacheado)."""
    if INDICE.exists():
        return json.loads(INDICE.read_text(encoding="utf-8"))
    print("indexando la carpeta del bulk (una vez)...")
    idx = defaultdict(list)
    for p in BULK.rglob("*.png"):
        idx[re.sub(r"_#\d+$", "", p.stem)].append(str(p))
    idx = dict(idx)
    INDICE.write_text(json.dumps(idx), encoding="utf-8")
    return idx


def mascara(im, umbral=20):
    return (np.asarray(im.getchannel("A"), dtype=np.uint8) > umbral).astype(np.float32)


def localizar(hoja, sprite, candidatos=10):
    """Offset (x, y) del sprite dentro de la hoja.

    Correlacion de las mascaras de alfa por FFT (el pico da la posicion), probando los N picos mas
    altos y quedandose con el que de verdad coincide pixel a pixel: devuelve (offset, error_maximo).
    Se prueban varios picos porque muchas expresiones tienen la misma silueta.
    """
    H, S = mascara(hoja), mascara(sprite)
    h, w = S.shape
    Hh, Hw = H.shape
    if h > Hh or w > Hw:
        return None, None
    forma = (Hh + h - 1, Hw + w - 1)
    corr = np.fft.irfft2(np.fft.rfft2(H, forma) * np.fft.rfft2(S[::-1, ::-1], forma), forma)
    valida = corr[h - 1:Hh, w - 1:Hw]          # solo las posiciones donde el sprite cabe entero
    if not valida.size:
        return None, None

    sprite_px = np.asarray(sprite.convert("RGBA"), dtype=np.int16)
    orden = np.argsort(valida, axis=None)[::-1][:candidatos]
    mejor, mejor_error = None, None
    for k in orden:
        y, x = np.unravel_index(int(k), valida.shape)
        recorte = np.asarray(hoja.crop((int(x), int(y), int(x) + w, int(y) + h))
                             .convert("RGBA"), dtype=np.int16)
        # se comparan solo los pixeles que se ven: bajo un pixel transparente el RGB no significa
        # nada y la hoja guarda basura ahi, que daba errores falsos
        if h > 4 and w > 4:
            recorte, sp = recorte[2:-2, 2:-2], sprite_px[2:-2, 2:-2]
        else:
            recorte, sp = recorte, sprite_px
        visibles = (recorte[..., 3] > 0) | (sp[..., 3] > 0)
        # se mide la FRACCION de pixeles que no coinciden (el maximo solo da 255 por un borde
        # suelto y no dice nada): asi se ve si la posicion es buena o si se ha enganchado otra
        # expresion con la misma silueta
        if visibles.any():
            dif = np.abs(recorte - sp).max(-1)
            d = float(((dif > 3) & visibles).sum()) / float(visibles.sum())
        else:
            d = 0.0
        if mejor_error is None or d < mejor_error:
            mejor, mejor_error = (int(x), int(y)), d
        if d <= 0.02:                           # casi identico: no hace falta mirar mas picos
            break
    return mejor, mejor_error


def partes_del_bustup(clave, idx):
    """Nombres de capa del bust-up, sacados del emparejado (es el mapa de que va con que)."""
    datos = json.loads((DL / "emparejado_bustups.json").read_text(encoding="utf-8"))["emparejados"]
    if clave in datos:
        info = datos[clave]
    elif "/" in clave:
        personaje, ropa = clave.split("/", 1)
        info = next((v for v in datos.values()
                     if v["personaje"] == personaje and v["ropa"] == ropa), None)
        if info is None:
            raise SystemExit("%s no esta emparejado" % clave)
    else:
        raise SystemExit("no encuentro %r; usa el nombre del JSON o personaje/ropa" % clave)
    capas = info["capas"]
    partes = []
    for paso, nombres in ORDEN:
        nombre = next((capas[n]["nombre"] for n in nombres if n in capas), None)
        if nombre:
            partes.append((paso, nombre))
    return info, partes


def abrir_hoja_y_sprite(idx, nombre):
    """De la carpeta del bulk: la hoja (el PNG mas grande del nombre) y el sprite suelto."""
    rutas = idx.get(nombre)
    if not rutas:
        return None, None
    info = []
    for r in rutas:
        with Image.open(r) as im:
            info.append((im.width * im.height, r))
    info.sort()
    if len(info) < 2:
        return None, None
    with Image.open(info[-1][1]) as ih, Image.open(info[0][1]) as isp:
        return ih.convert("RGBA").copy(), isp.convert("RGBA").copy()


def listar_expresiones(idx, personaje, ropa):
    """Que expresiones y que partes hay para ese personaje/ropa (que cosas van juntas)."""
    patron = re.compile(r"^(?P<p>%s)-(?P<r>%s)-(?P<resto>.+)$" % (re.escape(personaje),
                                                                  re.escape(ropa)))
    partes, expresiones = defaultdict(list), defaultdict(set)
    for nombre in idx:
        m = patron.match(nombre)
        if not m:
            continue
        resto = m.group("resto")
        ult = re.sub(r"\d+$", "", resto.split("-")[-1])
        if ult in ("yan", "zui"):
            tokens = resto.split("-")
            expresiones[ult].add(tokens[-2] if len(tokens) >= 2 else "?")
            partes["ojos" if ult == "yan" else "boca"].append(nombre)
        else:
            partes[resto].append(nombre)
    print("%s-%s" % (personaje, ropa))
    print("   partes del cuerpo: %s" % ", ".join(sorted(k for k in partes if k not in ("ojos", "boca"))))
    for k in ("ojos", "boca"):
        if partes.get(k):
            print("   %s: %d variantes | expresiones: %s"
                  % (k, len(partes[k]), ", ".join(sorted(expresiones[k.replace("ojos", "yan")
                                                                       .replace("boca", "zui")]))))
    return partes


def montar(clave, salida=None, volcar_json=False, silencio=False):
    di = (lambda *a: None) if silencio else print
    idx = cargar_indice()
    info, partes = partes_del_bustup(clave, idx)
    titulo = clave if "/" not in clave else clave.replace("/", "-")
    print("bust-up %s (%s/%s) | %d capas" % (titulo, info["personaje"], info["ropa"], len(partes)))

    leidas, lienzo = [], None
    for paso, nombre in partes:
        hoja, sprite = abrir_hoja_y_sprite(idx, nombre)
        if hoja is None:
            print("   %-9s %-44s sin par hoja/sprite en el bulk" % (paso, nombre[:44]))
            continue
        offset, error = localizar(hoja, sprite)
        if offset is None:
            print("   %-9s %-44s no se pudo localizar" % (paso, nombre[:44]))
            continue
        leidas.append({"paso": paso, "nombre": nombre, "sprite": sprite, "hoja": hoja.size,
                       "offset_hoja": offset, "error": error})
        if paso == "cuerpo":
            lienzo = hoja.size

    # ahora que se sabe el lienzo: las capas cuya hoja NO es el lienzo tienen el offset dentro de su
    # propia hoja y no se pueden colocar sin el prefab -> se dejan arriba y se marcan no fiables
    for p in leidas:
        p["fiable"] = tuple(p["hoja"]) == tuple(lienzo)
        p["offset"] = p["offset_hoja"] if p["fiable"] else (0, 0)
        print("   %-9s %-44s hoja %-11s sprite %-11s offset %-9s difiere %.2f%%%s"
              % (p["paso"], p["nombre"][:44], "%dx%d" % tuple(p["hoja"]),
                 "%dx%d" % p["sprite"].size, "%d,%d" % p["offset"], p["error"] * 100,
                 "" if p["fiable"] else "  <- hoja propia, no fiable"))
    if lienzo is None:
        raise SystemExit("este bust-up no tiene capa de cuerpo")

    lona = Image.new("RGBA", lienzo, (0, 0, 0, 0))
    for p in leidas:
        lona.alpha_composite(p["sprite"], dest=p["offset"])

    salida = Path(salida) if salida else DL / "bustups_pixeles" / ("%s.png" % titulo)
    salida.parent.mkdir(parents=True, exist_ok=True)
    lona.save(salida)
    print("lienzo %dx%d -> %s" % (lienzo[0], lienzo[1], salida))
    if volcar_json:
        dest = salida.with_suffix(".json")
        dest.write_text(json.dumps({
            "titulo": titulo, "lienzo": list(lienzo),
            "capas": [{"paso": p["paso"], "nombre": p["nombre"], "hoja": list(p["hoja"]),
                       "offset": list(p["offset"]), "difiere_porcentaje": round(p["error"] * 100, 3)} for p in leidas],
        }, ensure_ascii=False, indent=1), encoding="utf-8")
        print("coordenadas -> %s" % dest)
    return salida


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Monta un bust-up localizando cada sprite por pixeles")
    ap.add_argument("clave", nargs="?", help="personaje/ropa o nombre del JSON")
    ap.add_argument("-o", "--salida")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--todos", action="store_true", help="montar los 120 emparejados y resumir")
    ap.add_argument("--listar", action="store_true", help="solo listar que expresiones y partes hay")
    a = ap.parse_args()
    if a.listar:
        personaje, ropa = (a.clave.split("/", 1) if "/" in a.clave else (a.clave, ""))
        listar_expresiones(cargar_indice(), personaje, ropa)
        sys.exit(0)
    if a.todos:
        import contextlib
        import io
        import time
        datos = json.loads((DL / "emparejado_bustups.json").read_text(encoding="utf-8"))["emparejados"]
        hechos = fallos = no_fiables = capas_total = 0
        peores = []
        t0 = time.time()
        for i, clave in enumerate(sorted(datos), 1):
            try:
                with contextlib.redirect_stdout(io.StringIO()) as buf:
                    montar(clave, volcar_json=True, silencio=True)
                hechos += 1
                salida = buf.getvalue()
                malas = salida.count("no fiable")
                no_fiables += malas
                capas_total += salida.count("offset ")
                if malas:
                    peores.append((clave, malas))
                print("[%3d/%d] %-52s capas con hoja propia: %d" % (i, len(datos), clave[:52], malas))
            except SystemExit as e:
                fallos += 1
                print("[%3d/%d] %-52s FALLO: %s" % (i, len(datos), clave[:52], e))
            except Exception as e:  # noqa: BLE001
                fallos += 1
                print("[%3d/%d] %-52s ERROR: %s: %s" % (i, len(datos), clave[:52],
                                                        type(e).__name__, str(e)[:60]))
        print()
        print("montados: %d | fallos: %d | capas colocadas: %d | capas con hoja propia (no fiables): %d"
              % (hechos, fallos, capas_total, no_fiables))
        print("tiempo total: %.1f s (%.2f s por bust-up)" % (time.time() - t0,
                                                            (time.time() - t0) / max(hechos, 1)))
        sys.exit(0)
    sys.exit(0 if montar(a.clave, a.salida, a.json) else 1)