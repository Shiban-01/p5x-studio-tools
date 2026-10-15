"""Vistas previas: dibuja los OBJ extraidos para que el usuario vea lo que ha sacado.

No usa motor 3D. Proyecta los vertices en ortogonal, pinta los triangulos ordenados por profundidad
(el mas lejano primero) y los sombrea con la luz segun su normal. El color de cada pieza sale del
color medio de su textura, o del color difuso del MTL si no hay textura. Es suficiente para
reconocer un modelo de un vistazo y no necesita ninguna dependencia pesada.
"""
from __future__ import annotations

import math
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONDO = (34, 34, 40)
LUZ = (-0.35, -0.55, 0.75)

# buscar la textura recorriendo la carpeta entera, una vez por material, es carisimo: con ~30
# materiales sobre un modelo de 80 MB la vista previa pasaba de 40 segundos a nada. Se construye
# un indice de nombres una sola vez y se reutiliza.
_INDICE_TEXTURAS: dict = {}


def _indice_texturas(raiz: Path) -> dict:
    raiz = Path(raiz)
    if raiz not in _INDICE_TEXTURAS:
        indice = {}
        for png in raiz.rglob("*.png"):
            indice.setdefault(png.name.lower(), png)
        _INDICE_TEXTURAS[raiz] = indice
    return _INDICE_TEXTURAS[raiz]


def _leer_mtl(ruta: Path) -> tuple[dict, dict]:
    """Del MTL saca (color difuso por material, textura por material).

    La textura es lo importante: el color medio de la textura es lo que hace que la vista previa
    se parezca al modelo en vez de salir toda gris.
    """
    colores = {}
    texturas = {}
    if not ruta or not Path(ruta).is_file():
        return colores, texturas
    carpeta = Path(ruta).parent
    actual = None
    for linea in Path(ruta).read_text(encoding="utf-8", errors="replace").splitlines():
        t = linea.split()
        if not t:
            continue
        if t[0] == "newmtl" and len(t) > 1:
            actual = t[1]
            colores[actual] = (190, 190, 190)
        elif t[0] == "Kd" and actual and len(t) >= 4:
            try:
                colores[actual] = tuple(max(0, min(255, int(float(x) * 255))) for x in t[1:4])
            except ValueError:
                pass
        elif t[0] == "map_Kd" and actual and len(t) > 1:
            candidata = carpeta / " ".join(t[1:]).strip()
            if not candidata.is_file():
                # el MTL vive en 01_model/obj/<parte>/, asi que la raiz del modelo queda tres
                # niveles por encima: de ahi cuelga 02_textures
                raiz_modelo = carpeta.parents[2] if len(carpeta.parents) > 2 else carpeta
                hallada = _indice_texturas(raiz_modelo).get(candidata.name.lower())
                if hallada:
                    candidata = hallada
            if candidata.is_file():
                texturas[actual] = candidata
    return colores, texturas


def _leer_obj(ruta: Path):
    """Devuelve (vertices, caras) donde cada cara es (indices, material)."""
    vertices = []
    caras = []
    material = None
    for linea in Path(ruta).read_text(encoding="utf-8", errors="replace").splitlines():
        t = linea.split()
        if not t:
            continue
        if t[0] == "v" and len(t) >= 4:
            vertices.append((float(t[1]), float(t[2]), float(t[3])))
        elif t[0] == "usemtl" and len(t) > 1:
            material = t[1]
        elif t[0] == "f" and len(t) >= 4:
            idx = []
            for trozo in t[1:]:
                n = trozo.split("/")[0]
                try:
                    i = int(n)
                except ValueError:
                    continue
                idx.append(i - 1 if i > 0 else len(vertices) + i)
            # abanico de triangulos para caras de mas de tres vertices
            for k in range(1, len(idx) - 1):
                caras.append(((idx[0], idx[k], idx[k + 1]), material))
    return vertices, caras


def _color_textura(ruta_png: Path, por_defecto) -> tuple:
    if not ruta_png or not Path(ruta_png).is_file():
        return por_defecto
    try:
        im = Image.open(ruta_png).convert("RGBA").resize((32, 32))
        px = list(im.getdata())
        validos = [p for p in px if p[3] > 40]
        if not validos:
            return por_defecto
        n = len(validos)
        return tuple(sum(p[i] for p in validos) // n for i in range(3))
    except Exception:
        return por_defecto


def dibujar(ruta_obj: Path, salida: Path, ancho=520, alto=720,
            ruta_mtl: Path | None = None, texturas: dict | None = None,
            titulo: str = "") -> Path | None:
    """Dibuja un OBJ y guarda el PNG. Devuelve la ruta o None si el OBJ no tiene caras."""
    vertices, caras = _leer_obj(ruta_obj)
    if not vertices or not caras:
        return None
    colores_mtl, texturas_mtl = _leer_mtl(ruta_mtl) if ruta_mtl else ({}, {})
    texturas = texturas or {}

    # se gira la pieza para verla a tres cuartos: de frente, muchas partes planas (la cara, las
    # hojas de las armas) quedan de canto y no se leen
    # el giro va alrededor del eje vertical, que en estos OBJ es Z
    giro = math.radians(32)
    cg, sg = math.cos(giro), math.sin(giro)
    vertices = [(v[0] * cg - v[1] * sg, v[0] * sg + v[1] * cg, v[2]) for v in vertices]

    # encuadre: X a lo ancho, Z de arriba abajo (los OBJ del juego son Z-arriba)
    xs = [v[0] for v in vertices]
    zs = [v[2] for v in vertices]
    cx = (min(xs) + max(xs)) / 2
    cz = (min(zs) + max(zs)) / 2
    alto_modelo = max(max(zs) - min(zs), 1e-6)
    ancho_modelo = max(max(xs) - min(xs), 1e-6)
    escala = min((alto - 60) / alto_modelo, (ancho - 40) / ancho_modelo)

    def proyecta(v):
        return (ancho / 2 + (v[0] - cx) * escala, alto - 30 - (v[2] - cz) * escala)

    imagen = Image.new("RGB", (ancho, alto), FONDO)
    lapiz = ImageDraw.Draw(imagen)

    # orden por profundidad media: primero lo lejano
    def profundidad(cara):
        idx, _ = cara
        return sum(vertices[i][1] for i in idx) / 3.0

    caras_ordenadas = sorted(caras, key=profundidad)

    # una vista previa no necesita las 30.000 caras de una malla de juego: se toma una de cada
    # tantas para que el dibujo sea instantaneo y el resultado se siga leyendo igual
    MAXIMO_CARAS = 20000
    if len(caras_ordenadas) > MAXIMO_CARAS:
        paso = len(caras_ordenadas) // MAXIMO_CARAS + 1
        caras_ordenadas = caras_ordenadas[::paso]

    # una malla de juego puede tener decenas de miles de triangulos y dibujarlos todos uno a uno
    # con Pillow tarda minutos. Para una vista previa basta con una muestra regular: se conserva
    # el orden por profundidad, asi que el sombreado y el solapamiento siguen siendo correctos.
    MAXIMO_CARAS = 20000
    if len(caras_ordenadas) > MAXIMO_CARAS:
        paso = len(caras_ordenadas) // MAXIMO_CARAS + 1
        caras_ordenadas = caras_ordenadas[::paso]

    # color de cada material, resuelto UNA vez: dentro del bucle costaba 45 s por pieza
    color_por_material = {}
    for nombre_mat in {m for _, m in caras_ordenadas}:
        base = None
        if nombre_mat and nombre_mat in texturas_mtl:
            base = _color_textura(texturas_mtl[nombre_mat], None)
        if base is None and nombre_mat and nombre_mat in texturas:
            base = _color_textura(texturas[nombre_mat], None)
        if base is None:
            base = colores_mtl.get(nombre_mat, (188, 188, 196))
        color_por_material[nombre_mat] = base

    for idx, material in caras_ordenadas:
        a, b, c = (vertices[i] for i in idx)
        u = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
        v = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
        nx = u[1] * v[2] - u[2] * v[1]
        ny = u[2] * v[0] - u[0] * v[2]
        nz = u[0] * v[1] - u[1] * v[0]
        norma = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
        nx, ny, nz = nx / norma, ny / norma, nz / norma
        luz = max(0.0, abs(nx * LUZ[0] + ny * LUZ[1] + nz * LUZ[2]))
        factor = 0.35 + 0.65 * luz

        base = color_por_material.get(material, (188, 188, 196))
        color = tuple(max(0, min(255, int(canal * factor))) for canal in base)
        lapiz.polygon([proyecta(vertices[i]) for i in idx], fill=color)

    if titulo:
        try:
            fuente = ImageFont.truetype("segoeui.ttf", 22)
        except Exception:
            fuente = ImageFont.load_default()
        lapiz.text((14, 10), titulo, fill=(225, 225, 232), font=fuente)

    salida.parent.mkdir(parents=True, exist_ok=True)
    imagen.save(salida)
    return salida


def hoja_de_contacto(rutas: list[Path], salida: Path, titulo: str = "",
                     columnas: int = 3, celda=(300, 400)) -> Path | None:
    """Reune varias vistas previas en una sola imagen, tipo lamina de contactos."""
    existentes = [r for r in rutas if r and Path(r).is_file()]
    if not existentes:
        return None
    filas = (len(existentes) + columnas - 1) // columnas
    margen = 12
    cabecera = 52 if titulo else 10
    ancho = columnas * celda[0] + margen * (columnas + 1)
    alto = cabecera + filas * celda[1] + margen * (filas + 1)
    lamina = Image.new("RGB", (ancho, alto), (24, 24, 28))
    lapiz = ImageDraw.Draw(lamina)
    if titulo:
        try:
            fuente = ImageFont.truetype("segoeui.ttf", 30)
        except Exception:
            fuente = ImageFont.load_default()
        lapiz.text((margen + 6, 14), titulo, fill=(240, 240, 245), font=fuente)
    for i, ruta in enumerate(existentes):
        fila, col = divmod(i, columnas)
        x = margen + col * (celda[0] + margen)
        y = cabecera + margen + fila * (celda[1] + margen)
        try:
            im = Image.open(ruta).convert("RGB")
            im.thumbnail(celda, Image.LANCZOS)
            lamina.paste(im, (x + (celda[0] - im.width) // 2,
                              y + (celda[1] - im.height) // 2))
        except Exception:
            continue
    salida.parent.mkdir(parents=True, exist_ok=True)
    lamina.save(salida)
    return salida