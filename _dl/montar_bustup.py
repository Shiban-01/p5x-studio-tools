"""Monta un bust-up leyendo las COORDENADAS de cada parte, para el futuro visor de Bust-ups.

De donde salen las coordenadas (todo esto SI se puede leer):
  - del dump del Sprite: `m_Rect` (el rect del sprite dentro de su textura), `m_Pivot`,
    `m_PixelsToUnits` y a que textura apunta (`m_RD.texture` PathID);
  - del dump del Texture2D: `m_Width`/`m_Height`.
El desplazamiento dentro del LIENZO no esta en los ficheros legibles (vive en el prefab, y los
bundles instalados estan cifrados), asi que se deduce:
  - si la textura de la capa ES el lienzo (mismo tamano) -> offset (0,0). Exacto.
  - si el sprite apunta a la MISMA textura que el cuerpo -> offset = m_Rect.x/y. Exacto.
  - si la capa tiene textura propia mas pequena -> se alinea arriba (la cara esta arriba) y se
    marca como deducido en el JSON de coordenadas.

Uso:  montar_bustup.py <nombre del JSON | personaje/ropa> [-o salida.png] [--json]
      montar_bustup.py UI-DialogShader-changfu01-xiachuanling
      montar_bustup.py xiachuanling/changfu
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image

RAIZ = Path(r"C:\Users\Lukas\p5x-datamining")
DL = RAIZ / "_dl"
JUEGO = Path(r"C:\Users\Lukas\Downloads\P5X\Client\OuterPackage\Bundles\Windows")
MOTOR = RAIZ / "p5x_studio/engine/AssetStudioModCLI_net9_win64/AssetStudioModCLI.exe"
CACHE = DL / "bustups_cache"
DUMPS = DL / "dumps_coords"
UNITY = "2022.3.49f1"

# orden de apilado: el contorno va debajo de todo y el PELO arriba de todo (el flequillo tapa el
# borde de los ojos y la piel; si va debajo, se ven los pixeles de piel sobre el negro del pelo)
ORDEN = [
    ("contorno", ["benti-lunkuo", "shenti-lunkuo", "lunkuo"]),
    ("cuerpo", ["benti", "shenti", "zhengti"]),
    ("brazos", ["benti-zhi", "shenti-zhi", "zhi"]),
    ("ropa", ["benti-yifu", "shenti-yifu", "yifu"]),
    ("ojos", ["tongchang-yan1"]),
    ("boca", ["tongchang-zui1"]),
    ("pelo", ["benti-toufa", "shenti-toufa", "toufa"]),
]


def extraer(bundle):
    """Extrae texturas y sprites del bundle (cacheado) y devuelve la carpeta."""
    destino = CACHE / Path(bundle).stem
    falta = not destino.exists() or not any(destino.rglob("*.png"))
    if falta:
        if destino.exists():
            shutil.rmtree(destino, ignore_errors=True)
        destino.mkdir(parents=True, exist_ok=True)
        subprocess.run([str(MOTOR), str(JUEGO / bundle), "-t", "tex2d,sprite", "-o", str(destino),
                        "-g", "none", "--unity-version", UNITY],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=900)
    return destino


def volcar(bundle):
    """Vuelca los assets del bundle a texto (cacheado) y devuelve la carpeta de dumps."""
    destino = DUMPS / Path(bundle).stem
    if not destino.exists() or not any(destino.glob("*.txt")):
        shutil.rmtree(destino, ignore_errors=True)
        destino.mkdir(parents=True, exist_ok=True)
        subprocess.run([str(MOTOR), str(JUEGO / bundle), "-m", "dump", "-o", str(destino),
                        "-g", "none", "--unity-version", UNITY],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=900)
    return destino


def bloque(texto, clave, cuantos=4):
    """Saca los `cuantos` primeros numeros que siguen a una clave del dump."""
    i = texto.find(clave)
    if i < 0:
        return None
    trozo = texto[i:i + 400]
    nums = re.findall(r"float (\w+) = (-?[\d.]+)", trozo)
    if len(nums) < cuantos:
        return None
    return {n: float(v) for n, v in nums[:cuantos]}


def leer_sprite(carpeta, nombre):
    """Del dump del Sprite: rect dentro de su textura, pivot y textura a la que apunta."""
    for f in carpeta.glob("*.txt"):
        t = f.read_text(encoding="utf-8", errors="replace")
        if not t.startswith("Sprite") or 'm_Name = "%s"' % nombre not in t:
            continue
        rect = bloque(t, "m_Rect")
        piv = bloque(t, "m_Pivot", 2)
        ptu = re.search(r"m_PixelsToUnits = ([\d.]+)", t)
        i = t.find("PPtr<Texture2D> texture")
        tex = re.search(r"m_PathID = (-?\d+)", t[i:i + 200]) if i >= 0 else None
        return {"rect": rect, "pivot": piv,
                "pixels_to_units": float(ptu.group(1)) if ptu else None,
                "textura": tex.group(1) if tex else None}
    return None


def leer_textura(carpeta, nombre):
    """Del dump del Texture2D: su tamano, y la ruta del PNG exportado."""
    for f in carpeta.glob("*.txt"):
        t = f.read_text(encoding="utf-8", errors="replace")
        if not t.startswith("Texture2D") or 'm_Name = "%s"' % nombre not in t:
            continue
        w = re.search(r"m_Width = (\d+)", t)
        h = re.search(r"m_Height = (\d+)", t)
        return {"tamano": (int(w.group(1)), int(h.group(1))), "dump": f}
    return None


def leer_malla(carpeta, nombre, tamano_png):
    """El rect de la MALLA del sprite, en pixeles de su textura.

    Esto es lo que pidio Aaron: el sprite exportado va recortado a su malla ajustada (la boca sale
    60x36 en vez del lienzo 572x732), y la posicion de ese recorte dentro de la textura es justo
    este rect. Se busca entre todos los rectangulos del dump el que mide lo que el PNG exportado.
    """
    for f in carpeta.glob("*.txt"):
        t = f.read_text(encoding="utf-8", errors="replace")
        if not t.startswith("Sprite") or 'm_Name = "%s"' % nombre not in t:
            continue
        quads = re.findall(r"float x = (-?[\d.]+)\s*\r?\n\s*float y = (-?[\d.]+)\s*\r?\n"
                           r"\s*float width = (-?[\d.]+)\s*\r?\n\s*float height = (-?[\d.]+)", t)
        for x, y, w, h in quads:
            if abs(float(w) - tamano_png[0]) <= 1.5 and abs(float(h) - tamano_png[1]) <= 1.5:
                return (float(x), float(y), float(w), float(h))
    return None


def buscar_png(carpeta, nombre, tamano, preferir_recortado=False):
    """El PNG de la textura entera (lienzo) o el del sprite recortado.

    Devuelve (ruta, imagen, es_el_lienzo). El lienzo se reconoce porque mide exactamente lo que
    declara el Texture2D en el dump (`m_Width`/`m_Height`); el sprite recortado mide menos y su
    posicion la da `leer_malla`. Con `preferir_recortado` se coge el recortado aunque exista el
    lienzo (pesa mucho menos y da el mismo montaje si el rect de la malla es correcto).
    """
    candidatos = sorted(carpeta.glob("%s.png" % nombre)) + sorted(carpeta.glob("%s_#*.png" % nombre))
    lienzo = recortados = None
    for p in candidatos:
        with Image.open(p) as im:
            if im.size == tuple(tamano):
                lienzo = (p, im.convert("RGBA").copy(), True)
            else:
                recortados = recortados or []
                recortados.append((p, im.convert("RGBA").copy()))
    if preferir_recortado and recortados:
        p, im = max(recortados, key=lambda t: t[1].width * t[1].height)
        return p, im, False
    if lienzo:
        return lienzo
    if recortados:
        p, im = max(recortados, key=lambda t: t[1].width * t[1].height)
        return p, im, False
    return None, None, None


def montar(clave, salida=None, volcar_json=False, usar_recortados=True):
    datos = json.loads((DL / "emparejado_bustups.json").read_text(encoding="utf-8"))["emparejados"]
    if clave in datos:
        info, titulo = datos[clave], clave
    else:
        if "/" not in clave:
            raise SystemExit("no encuentro %r; usa el nombre del JSON o personaje/ropa" % clave)
        personaje, ropa = clave.split("/", 1)
        info = next((v for v in datos.values() if v["personaje"] == personaje and v["ropa"] == ropa),
                    None)
        if info is None:
            raise SystemExit("%s/%s no esta emparejado" % (personaje, ropa))
        titulo = "%s-%s" % (personaje, ropa)

    capas = info["capas"]
    carpetas = {b: extraer(b) for b in info["bundles"]}
    dumps = {b: volcar(b) for b in info["bundles"]}

    partes, lienzo, textura_cuerpo = [], None, None
    for paso, nombres in ORDEN:
        nombre = next((capas[n]["nombre"] for n in nombres if n in capas), None)
        if nombre is None:
            continue
        bundle = next(capas[n]["bundle"] for n in nombres if n in capas)
        spr = leer_sprite(dumps[bundle], nombre)
        tex = leer_textura(dumps[bundle], nombre)
        if spr is None or tex is None:
            print("   aviso: sin datos de %s" % nombre)
            continue
        png, im, es_lienzo = buscar_png(carpetas[bundle], nombre, tex["tamano"], usar_recortados)
        if im is None:
            print("   aviso: no encuentro el PNG de %s" % nombre)
            continue
        malla = leer_malla(dumps[bundle], nombre, im.size)
        partes.append({"paso": paso, "nombre": nombre, "imagen": im, "textura": tex["tamano"],
                       "rect": spr["rect"], "pivot": spr["pivot"], "sprite_textura": spr["textura"],
                       "pixels_to_units": spr["pixels_to_units"], "png": str(png),
                       "es_lienzo": es_lienzo, "malla": malla})
        if paso == "cuerpo":
            lienzo, textura_cuerpo = tex["tamano"], spr["textura"]

    if lienzo is None:
        raise SystemExit("este bust-up no tiene capa de cuerpo")

    # coordenadas: exactas cuando la textura es el lienzo o es la misma textura que el cuerpo
    for p in partes:
        rect = p["rect"] or {"x": 0.0, "y": 0.0}
        if tuple(p["textura"]) == tuple(lienzo):
            if p["malla"] and (usar_recortados or not p["es_lienzo"]):
                # se usa el sprite recortado, colocado en el rect de su malla (lo que pidio Aaron).
                # OJO: en Unity la Y del rect se mide desde ABAJO y en el PNG desde arriba, asi que
                # hay que darle la vuelta: y_arriba = alto_de_la_textura - y_abajo - alto_del_sprite
                mx, my, mw, mh = p["malla"]
                alto_textura = p["textura"][1]
                p["offset"] = (round(mx), round(alto_textura - my - mh))
                p["exacto"], p["como"] = True, "rect de la malla"
            elif p["es_lienzo"]:
                # se usa la textura entera: ya trae cada parte en su sitio del lienzo
                p["offset"], p["exacto"], p["como"] = (0, 0), True, "lienzo entero"
            else:
                p["offset"], p["exacto"], p["como"] = (0, 0), False, "deducida"
        elif p["sprite_textura"] == textura_cuerpo:
            p["offset"] = (int(rect["x"]), int(rect["y"]))
            p["exacto"], p["como"] = True, "m_Rect en la textura del cuerpo"
        else:
            p["offset"], p["exacto"], p["como"] = (0, 0), False, "deducida (arriba)"

    montaje = Image.new("RGBA", tuple(lienzo), (0, 0, 0, 0))
    for p in partes:
        montaje.alpha_composite(p["imagen"], dest=p["offset"])

    salida = Path(salida) if salida else DL / "bustups_montados" / ("%s.png" % titulo)
    salida.parent.mkdir(parents=True, exist_ok=True)
    montaje.save(salida)

    print("lienzo %dx%d  ->  %s" % (lienzo[0], lienzo[1], salida))
    print("   %-9s %-46s %-12s %-10s %s" % ("capa", "fichero", "textura", "offset", "coordenada"))
    for p in partes:
        print("   %-9s %-46s %-12s %-10s %s"
              % (p["paso"], p["nombre"][:46], "%dx%d" % tuple(p["textura"]),
                 "%d,%d" % p["offset"], p["como"]))

    if volcar_json:
        dest = salida.with_suffix(".json")
        dest.write_text(json.dumps({
            "titulo": titulo, "lienzo": list(lienzo),
            "capas": [{"paso": p["paso"], "nombre": p["nombre"], "png": p["png"],
                       "textura": list(p["textura"]), "offset": list(p["offset"]),
                       "exacto": p["exacto"], "como": p["como"],
                       "rect_de_la_malla": list(p["malla"]) if p["malla"] else None,
                       "rect_en_textura": p["rect"], "pivote": p["pivot"],
                       "pixels_to_units": p["pixels_to_units"]} for p in partes],
        }, ensure_ascii=False, indent=1), encoding="utf-8")
        print("   coordenadas -> %s" % dest)
    return salida


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Monta un bust-up leyendo las coordenadas de cada parte")
    ap.add_argument("clave", help="nombre del JSON o personaje/ropa")
    ap.add_argument("-o", "--salida", help="PNG de salida")
    ap.add_argument("--json", action="store_true", help="escribir tambien el JSON de coordenadas")
    ap.add_argument("--hojas", action="store_true",
                    help="pegar las hojas enteras en vez de los sprites recortados (trae contenido de mas)")
    a = ap.parse_args()
    sys.exit(0 if montar(a.clave, a.salida, a.json, not a.hojas) else 1)