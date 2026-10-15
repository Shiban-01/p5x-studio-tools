"""Sombreado de los bust-ups: el shader UIMultipleGradient del juego, sin numpy.

Los pasos son los del GLSL del juego, en este orden:

  1. tono base           brillo -> saturacion -> contraste sobre la textura.
  2. tono del degradado  lo mismo sobre el color del degradado que toca en ese pixel.
  3. multiplicacion      degradado x base.
  4. rampa de alfa       entre GradientAlphaBottom y GradientAlphaTop, segun la parada del degradado.
  5. mezcla y factor     la mezcla se pesa con la rampa y el EffectFactor la acerca al original.

Dos decisiones que no estan en el GLSL y conviene tener presentes:

  * Las paradas del degradado son las que el C# le pasa al shader: las del Gradient de Unity tal
    cual (sus propios tiempos) y las ranuras de sobra repiten la ultima. Reconstruirlo con paradas
    equiespaciadas solo coincide con degradados de 2 paradas, y de los 120 retratos 100 tienen 3 o
    mas.
  * La rampa de alfa va de la posicion 0 a la 1 con los valores `GradientAlphaBottom` y
    `GradientAlphaTop` del JSON. Esas dos posiciones no estan en ningun fichero: las escribe el
    codigo del juego, y leyendolas en GameAssembly.dll (UIMultipleMaterial.Update, RVA 0x23C3DA0)
    resultan ser 0.0 (un `xorps xmm2, xmm2`) y 1.0 (una constante del .rdata). Antes se deducian a
    ojo y estaban mal, que es de donde venia el tono raro.
  * El GLSL no recorta el tono del degradado a [0,1]; durante un tiempo se recortaba aqui para tapar
    justamente el error de la rampa. Ya no hace falta: el tono base se deja tal cual (como el GLSL)
    y el resultado final se acota al guardar, como el framebuffer del juego.

El tono base es `A*color + D*luminancia + E`, asi que no necesita tabla: sale exacto en el bucle. El
degradado si (depende de la coordenada) y se resuelve con una tabla de 1024 niveles por canal. Un
retrato de 600x700 se pinta en torno a un segundo, y el resultado se guarda aparte del montaje para
poder alternar con y sin shader.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

from PIL import Image

NIVELES = 1024
LUMA = (0.2125, 0.7154, 0.0721)
TOPE = False                     # [0,1] al tono del degradado: el juego no lo hace (ver arriba)

_datos = None
_cache_tablas = {}


def _ruta_datos() -> Path:
    """El JSON que viaja dentro del ejecutable (o al lado, en el codigo fuente)."""
    if getattr(sys, "frozen", False) and getattr(sys, "_MEIPASS", None):
        return Path(sys._MEIPASS) / "p5x_studio" / "datos" / "shaders.json"
    return Path(__file__).resolve().parent / "datos" / "shaders.json"


def parametros(clave: str) -> dict | None:
    """Parametros del shader de un bust-up (o None si no se volcaron)."""
    global _datos
    if _datos is None:
        try:
            _datos = json.loads(_ruta_datos().read_text(encoding="utf-8")).get("por_bustup", {})
        except (OSError, ValueError):
            _datos = {}
    return _datos.get(clave)


def _recortar(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def _tono(r: float, g: float, b: float, brillo: float, saturacion: float, contraste: float,
          tope: bool = False):
    """Brillo -> saturacion -> contraste, como el shader. Con tope=True se recorta a [0,1]."""
    lum = r * LUMA[0] + g * LUMA[1] + b * LUMA[2]
    if tope:
        return (_recortar(contraste * (saturacion * (r * brillo - lum) + lum - 0.5) + 0.5),
                _recortar(contraste * (saturacion * (g * brillo - lum) + lum - 0.5) + 0.5),
                _recortar(contraste * (saturacion * (b * brillo - lum) + lum - 0.5) + 0.5))
    return (contraste * (saturacion * (r * brillo - lum) + lum - 0.5) + 0.5,
            contraste * (saturacion * (g * brillo - lum) + lum - 0.5) + 0.5,
            contraste * (saturacion * (b * brillo - lum) + lum - 0.5) + 0.5)


def tablas_degradado(p: dict) -> tuple:
    """Tablas del degradado, una por nivel de coordenada: color (0..1) y rampa de alfa.

    Son baratas de construir y se cachean por parametros. El tono base no lleva tabla: es
    `A*color + D*luminancia + E`, que sale exacto en el bucle.
    """
    clave_cache = (p.get("gra_brillo"), p.get("gra_saturacion"), p.get("gra_contraste"),
                   tuple((t, tuple(c)) for t, c in p.get("paradas") or []),
                   p.get("alfa_abajo"), p.get("alfa_arriba"),
                   p.get("alfa_pos_abajo"), p.get("alfa_pos_arriba"),
                   tuple((t, a) for t, a in p.get("alfa_gradiente") or []))
    if clave_cache in _cache_tablas:
        return _cache_tablas[clave_cache]
    gra_brillo = float(p.get("gra_brillo", 1.0))
    gra_saturacion = float(p.get("gra_saturacion", 1.0))
    gra_contraste = float(p.get("gra_contraste", 1.0))
    paradas = [(float(t), (float(c[0]), float(c[1]), float(c[2]))) for t, c in p.get("paradas") or []]
    if not paradas:
        return None

    btm = float(p.get("alfa_abajo", 1.0))
    top = float(p.get("alfa_arriba", 1.0))
    alfab = float(p.get("alfa_pos_abajo", 0.0))
    alfat = float(p.get("alfa_pos_arriba", 1.0))
    col_r, col_g, col_b, rampa = [], [], [], []
    for q in range(NIVELES):
        coord = q / (NIVELES - 1.0)
        c = _degradado(paradas, coord)
        gt = _tono(c[0] * gra_brillo, c[1] * gra_brillo, c[2] * gra_brillo,
                   1.0, gra_saturacion, gra_contraste, tope=TOPE)
        col_r.append(gt[0])
        col_g.append(gt[1])
        col_b.append(gt[2])
        if coord <= alfab:
            rampa.append(btm)
        elif coord >= alfat:
            rampa.append(top)
        else:
            t = (coord - alfab) / max(alfat - alfab, 0.001)
            rampa.append(t * (top - btm) + btm)
        # El alfa del gradiente (claves de alfa del Gradient de Unity) modula la fuerza del efecto.
        # Antes no se tenia en cuenta: Gradient.Evaluate(t) devuelve (r, g, b, a) y el shader usa
        # 'a' para pesar la mezcla entre el original y el degradado multiplicado.
    # aplicar el alfa del gradiente sobre la rampa
    alfa_grad = p.get("alfa_gradiente") or []
    if alfa_grad:
        ag_tiempos = [float(t) for t, _ in alfa_grad]
        ag_valores = [float(a) for _, a in alfa_grad]
        for q in range(NIVELES):
            coord = q / (NIVELES - 1.0)
            # interpolar el alfa del gradiente en esta posicion
            if coord <= ag_tiempos[0]:
                ga_val = ag_valores[0]
            elif coord >= ag_tiempos[-1]:
                ga_val = ag_valores[-1]
            else:
                ga_val = ag_valores[-1]
                for j in range(len(ag_tiempos) - 1):
                    if coord <= ag_tiempos[j + 1]:
                        f = (coord - ag_tiempos[j]) / max(ag_tiempos[j + 1] - ag_tiempos[j], 0.001)
                        ga_val = ag_valores[j] + f * (ag_valores[j + 1] - ag_valores[j])
                        break
            rampa[q] = rampa[q] * ga_val
    tablas = (col_r, col_g, col_b, rampa)
    _cache_tablas[clave_cache] = tablas
    return tablas


def _degradado(paradas: list, coord: float):
    """Consulta del degradado: por tramos, y plano fuera de los extremos."""
    if coord <= paradas[0][0]:
        return paradas[0][1]
    if coord >= paradas[-1][0]:
        return paradas[-1][1]
    for (t0, c0), (t1, c1) in zip(paradas, paradas[1:]):
        if coord <= t1:
            f = (coord - t0) / max(t1 - t0, 0.001)
            return (c0[0] + f * (c1[0] - c0[0]),
                    c0[1] + f * (c1[1] - c0[1]),
                    c0[2] + f * (c1[2] - c0[2]))
    return paradas[-1][1]


def coordenadas(ancho: int, alto: int, p: dict) -> list:
    """La coordenada del degradado (0..255) de cada pixel, en el mismo orden que los bytes RGBA.

    La v crece hacia arriba, como en la textura. Lineal si gradientMode es 0, radial si es 1.
    """
    angulo = math.radians(float(p.get("angulo", 0.0)))
    sen, cos = math.sin(-angulo), math.cos(angulo)
    modo = float(p.get("modo", 0.0))
    cx, cy = p.get("centro") or (0.5, 0.5)
    rx, ry = p.get("proporcion") or (1.0, 1.0)
    fila = [0] * ancho
    salida = []
    w = max(ancho, 1)
    h = max(alto, 1)
    for y in range(alto):
        v = 1.0 - (y + 0.5) / h
        base = (v - 0.5) * cos + 0.5
        dv = (v - cy) * ry
        if modo == 0.0:
            for x in range(ancho):
                u = (x + 0.5) / w
                lin = (u - 0.5) * sen + base
                fila[x] = min(NIVELES - 1, max(0, int(lin * (NIVELES - 1) + 0.5)))
        else:
            for x in range(ancho):
                u = (x + 0.5) / w
                lin = (u - 0.5) * sen + base
                du = (u - cx) * rx
                rad = math.sqrt(du * du + dv * dv) * 2.0
                c = lin + modo * (rad - lin)
                fila[x] = min(NIVELES - 1, max(0, int(c * (NIVELES - 1) + 0.5)))
        salida.extend(fila)
    return salida


def sombrear(imagen: Image.Image, p: dict, sin_tinte: bool = False) -> Image.Image:
    """Devuelve el retrato sombreado con los parametros dados (o el mismo si no hay degradado).

    Con sin_tinte=True se aplica el tono base pero NO el degradado (el tinte cálido del shader):
    util para ver los colores originales del personaje sin el filtro ambiental de la escena.
    """
    tablas = tablas_degradado(p)
    if tablas is None:
        return imagen
    col_r, col_g, col_b, rampa = tablas
    factor = float(p.get("effect_factor", 1.0))
    # tono base: base_c = A*color + D*luminancia + E, en la escala del pixel (0..255)
    a_ = float(p.get("contraste", 1.0)) * float(p.get("saturacion", 1.0)) * float(p.get("brillo", 1.0))
    d_ = float(p.get("contraste", 1.0)) * (1.0 - float(p.get("saturacion", 1.0)))
    e_ = 255.0 * (0.5 - 0.5 * float(p.get("contraste", 1.0)))
    lr, lg, lb = LUMA

    imagen = imagen.convert("RGBA")
    ancho, alto = imagen.size
    datos = bytearray(imagen.tobytes())
    coord = coordenadas(ancho, alto, p)

    n = len(datos)
    for i in range(0, n, 4):
        r = datos[i]
        g = datos[i + 1]
        b = datos[i + 2]
        q = coord[i >> 2]
        ga = 0.0 if sin_tinte else rampa[q]
        k = 1.0 - ga
        lum = lr * r + lg * g + lb * b
        # el degradado se multiplica por la base: (1-ga)*base + ga*degradado*base
        br = a_ * r + d_ * lum + e_
        bg = a_ * g + d_ * lum + e_
        bb = a_ * b + d_ * lum + e_
        vr = br * (k + ga * col_r[q])
        vg = bg * (k + ga * col_g[q])
        vb = bb * (k + ga * col_b[q])
        # el resultado se acota como el framebuffer del juego
        sal_r = int(r + factor * (vr - r) + 0.5)
        sal_g = int(g + factor * (vg - g) + 0.5)
        sal_b = int(b + factor * (vb - b) + 0.5)
        datos[i] = 0 if sal_r < 0 else (255 if sal_r > 255 else sal_r)
        datos[i + 1] = 0 if sal_g < 0 else (255 if sal_g > 255 else sal_g)
        datos[i + 2] = 0 if sal_b < 0 else (255 if sal_b > 255 else sal_b)

    return Image.frombytes("RGBA", (ancho, alto), bytes(datos))


def sombrear_fichero(origen: Path, destino: Path, clave: str) -> bool:
    """Sombrea un PNG ya montado y lo guarda. Devuelve False si ese bust-up no tiene parametros."""
    p = parametros(clave)
    if not p:
        return False
    with Image.open(origen) as im:
        res = sombrear(im, p)
    destino.parent.mkdir(parents=True, exist_ok=True)
    res.save(destino)
    return True


def disponible(clave: str) -> bool:
    return parametros(clave) is not None