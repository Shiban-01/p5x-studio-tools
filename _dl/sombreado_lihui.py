"""Aplica el sombreado del shader UI/UIMultipleGradient a un bust-up, tal cual lo hace el juego.

La cuenta esta sacada del GLSL compilado que paso la comunidad (la version movil del shader), linea
por linea. Orden real de operaciones:

  1. color = textura * color de vertice   (el color del Image; aqui se asume blanco)
  2. si `EnableFastBlur`: desenfoque 3x3 con nucleo fijo (0.4566, 1, 0.4566), paso = texel * BlurStrength * 2
  3. descarte si alfa < 0.001
  4. tono base: brillo -> saturacion -> contraste (luminancia 0.2125/0.7154/0.0721)
  5. coordenada del degradado: lineal (proyectada por `Angle` sobre el centro 0.5,0.5) o radial
     (distancia desde `Center` escalada por `Ratio`, multiplicada por 2), mezcladas por `gradientMode`
  6. degradado de 8 paradas sacado del `Gradient` del JSON
  7. tono del degradado (`GraBrightness`, `GraSaturation`, `GraContrast`)
  8. el degradado se MULTIPLICA por el color base (no se superpone)
  9. rampa de alfa entre GradientAlphaBottom/Position y GradientAlphaTop/Position
 10. mezcla por `gradAlpha`, y despues `EffectFactor` sobre el color original

Uso:  sombreado_lihui.py <json> <png> [carpeta_salida]
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

LUM = np.array([0.2125, 0.7153999, 0.0721], dtype=np.float32)
NUCLEO_DESENFOQUE = np.array([0.45660001, 1.0, 0.45660001], dtype=np.float32)


def leer_parametros(ruta):
    """Lee el JSON del bust-up y deja los parametros del shader listos (todo en 0..1 / grados)."""
    d = json.loads(Path(ruta).read_text(encoding="utf-8", errors="replace"))
    g = d["gradient"]
    n = int(g["m_NumColorKeys"])

    # el Gradient de Unity guarda las paradas en 16 bits (0..65535)
    # Las claves de COLOR usan los indices 0..m_NumColorKeys-1 del array `key`, con tiempos `ctime`.
    # Las claves de ALFA usan los indices m_NumColorKeys..m_NumColorKeys+m_NumAlphaKeys-1, con
    # tiempos `atime`. Antes se leian de key0..key(m_NumAlphaKeys-1), que son las claves de COLOR
    # (su `a` es 1.0 y no dice nada): el alfa real del gradiente estaba en las claves de alfa.
    nc = n
    na = int(g["m_NumAlphaKeys"])
    claves_color = sorted((g["ctime%d" % i] / 65535.0,
                           (g["key%d" % i]["r"], g["key%d" % i]["g"], g["key%d" % i]["b"]))
                          for i in range(nc))
    claves_alfa = sorted((g["atime%d" % i] / 65535.0, g["key%d" % (nc + i)]["a"])
                         for i in range(na) if (nc + i) < 8)
    return {
        "nombre": d.get("m_Name", ""),
        "effect_factor": float(d.get("EffectFactor", 1.0)),
        "brillo": float(d.get("Brightness", 1.0)),
        "saturacion": float(d.get("Saturation", 1.0)),
        "contraste": float(d.get("Contrast", 1.0)),
        "alfa_arriba": float(d.get("GradientAlphaTop", 1.0)),
        "alfa_abajo": float(d.get("GradientAlphaBottom", 1.0)),
        "gra_brillo": float(d.get("GraBrightness", 1.0)),
        "gra_saturacion": float(d.get("GraSaturation", 1.0)),
        "gra_contraste": float(d.get("GraContrast", 1.0)),
        "desenfoque": int(d.get("EnableFastBlur", 0)) == 1,
        "fuerza_desenfoque": float(d.get("BlurStrength", 0.0)),
        "modo": float(d.get("gradientMode", 0.0)),          # 0 lineal, 1 radial
        "angulo": float(d.get("Angle", 0.0)),
        "centro": (float(d["Center"]["x"]), float(d["Center"]["y"])),
        "proporcion": (float(d["Ratio"]["x"]), float(d["Ratio"]["y"])),
        "claves_color": claves_color,
        "claves_alfa": claves_alfa,
        # De donde arranca y acaba la rampa de alfa. El GLSL usa dos posiciones
        # (`_GradientAlphaBottomPosition` / `_GradientAlphaTopPosition`) que el JSON no trae: las
        # escribe el codigo del juego. Leidas en GameAssembly.dll (UIMultipleMaterial.Update,
        # RVA 0x23C3DA0): la de abajo se pone con `xorps xmm2, xmm2` (0.0) y la de arriba se carga de
        # una constante del .rdata que vale 1.0. O sea: la rampa va de 0 a 1 con los valores
        # `GradientAlphaBottom` y `GradientAlphaTop` del JSON. No hay que deducirlo de los ficheros.
        "pos_alfa_abajo": 0.0,
        "pos_alfa_arriba": 1.0,
    }


def evaluar_degradado(claves, t):
    """Interpola el degradado en la posicion t (0..1), con recorte en los extremos."""
    if t <= claves[0][0]:
        return np.array(claves[0][1], dtype=np.float32)
    if t >= claves[-1][0]:
        return np.array(claves[-1][1], dtype=np.float32)
    for (t0, c0), (t1, c1) in zip(claves, claves[1:]):
        if t <= t1:
            f = (t - t0) / max(t1 - t0, 1e-6)
            return np.array(c0, dtype=np.float32) + f * (np.array(c1, dtype=np.float32) - np.array(c0, dtype=np.float32))
    return np.array(claves[-1][1], dtype=np.float32)


def muestrear_8(claves, cuantas=8):
    """Las 8 paradas que el material le pasa al shader (_GradientColors/_GradientPositions).

    El C# las rellena con las paradas del Gradient de Unity tal cual (sus propios tiempos) y las
    ranuras que sobran repiten la ultima parada. Antes se evaluaba el degradado en 8 puntos
    equiespaciados, que solo coincide con degradados de 2 paradas: con 3 o mas (lo normal: hay de
    hasta 7) desplazaba los tramos y el shader pintaba colores que el material no le manda.
    """
    posiciones = np.array([t for t, _ in claves[:cuantas]], dtype=np.float32)
    colores = np.stack([np.array(c, dtype=np.float32) for _, c in claves[:cuantas]])
    # el shader tiene 8 ranuras fijas: las de sobra repiten la ultima parada
    while len(posiciones) < cuantas:
        posiciones = np.append(posiciones, posiciones[-1])
        colores = np.vstack([colores, colores[-1:]])
    return posiciones, colores


def tono(c, brillo, saturacion, contraste):
    """Brillo -> saturacion -> contraste, exactamente como el shader."""
    lum = (c * LUM).sum(-1, keepdims=True)
    x = c * brillo - lum
    x = saturacion * x + lum
    x = (x - 0.5) * contraste + 0.5
    return x


def degradado_8(coord, posiciones, colores):
    """Consulta del degradado de 8 paradas: por tramos, y plano fuera de los extremos."""
    salida = np.tile(colores[0], coord.shape + (1,))
    for i in range(7):
        dentro = (coord > posiciones[i]) & (coord <= posiciones[i + 1])
        f = (coord - posiciones[i]) / max(float(posiciones[i + 1] - posiciones[i]), 0.001)
        tramo = colores[i] + f[..., None] * (colores[i + 1] - colores[i])
        salida = np.where(dentro[..., None], tramo, salida)
    salida = np.where((coord > posiciones[7])[..., None], colores[7], salida)
    return salida


def desenfocar(im, fuerza):
    """Desenfoque 3x3 del shader: nucleo fijo y paso en texeles (el doble de la fuerza)."""
    paso = fuerza * 2.0
    ancho, alto = im.size
    acum = np.zeros((alto, ancho, 4), dtype=np.float32)
    suma = 0.0
    for j in range(3):
        for k in range(3):
            w = float(NUCLEO_DESENFOQUE[j] * NUCLEO_DESENFOQUE[k])
            # desplazamiento en pixeles: el eje y de la imagen va al reves que la v de la textura
            desplazada = im.transform(im.size, Image.AFFINE,
                                      (1, 0, (j - 1) * paso, 0, 1, -(k - 1) * paso),
                                      resample=Image.BILINEAR)
            acum += np.asarray(desplazada, dtype=np.float32) * w
            suma += w
    return Image.fromarray(np.clip(acum / suma, 0, 255).astype(np.uint8), "RGBA")


def a_lineal(x):
    """sRGB -> lineal (lo que hace el hardware al muestrear una textura sRGB)."""
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def a_srgb(x):
    """Lineal -> sRGB (lo que hace el hardware al escribir en el framebuffer)."""
    x = np.clip(x, 0.0, 1.0)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * (x ** (1.0 / 2.4)) - 0.055)


def sombrear_imagen(im, p, solo_degradado=False, v_invertida=False, lineal=False, tope=False):
    """Devuelve el bust-up sombreado. Con solo_degradado=True aplica unicamente el degradado.

    Con v_invertida=True la coordenada del degradado crece hacia abajo (la rampa de alfa se lee al
    reves). Con lineal=True la cuenta se hace en espacio lineal (textura sRGB -> lineal, cuentas,
    -> sRGB), que es lo que hace el juego si el proyecto va en espacio de color lineal.
    Con tope=False el tono del degradado se deja salir de rango, como estrictamente dice el GLSL.
    """
    im = im.convert("RGBA")
    if v_invertida:
        im = im.transpose(Image.FLIP_TOP_BOTTOM)
    if p["desenfoque"]:
        im = desenfocar(im, p["fuerza_desenfoque"])
    ancho, alto = im.size
    rgba = np.asarray(im, dtype=np.float32) / 255.0
    if lineal:
        rgba = np.concatenate([a_lineal(rgba[..., :3]), rgba[..., 3:]], axis=-1)
    col = rgba[..., :3]
    alfa = rgba[..., 3]

    # coordenadas en el espacio UV de la imagen (la v crece hacia arriba)
    u = (np.arange(ancho, dtype=np.float32) + 0.5) / ancho
    v = 1.0 - (np.arange(alto, dtype=np.float32) + 0.5) / alto
    U, V = np.meshgrid(u, v)

    a = np.radians(p["angulo"])
    lin = (U - 0.5) * np.sin(-a) + (V - 0.5) * np.cos(a) + 0.5
    radial = np.sqrt(((U - p["centro"][0]) * p["proporcion"][0]) ** 2
                     + ((V - p["centro"][1]) * p["proporcion"][1]) ** 2) * 2.0
    coord = lin + p["modo"] * (radial - lin)

    posiciones, colores = muestrear_8(p["claves_color"])
    g = degradado_8(coord, posiciones, colores)

    base = tono(col, p["brillo"], p["saturacion"], p["contraste"])
    g_t = tono(g * p["gra_brillo"], 1.0, p["gra_saturacion"], p["gra_contraste"])
    if tope:
        # El juego NO hace este recorte (comprobado en el codigo: nadie acota el tono del degradado).
        # Se deja como opcion porque hubo una temporada en que el retrato salia tostado y el tope lo
        # tapaba, pero la causa era otra: la rampa de alfa estaba mal puesta. Con la rampa correcta
        # (posiciones 0 y 1, del codigo) este recorte sobra.
        g_t = np.clip(g_t, 0.0, 1.0)
    gra = g_t * base

    # rampa de alfa del degradado: las dos posiciones que calcula el C# (medidas contra la captura:
    # salen de las paradas de las claves de color) y los dos valores del JSON.
    btm_pos = float(p["pos_alfa_abajo"])
    top_pos = float(p["pos_alfa_arriba"])
    t = np.minimum(np.maximum(coord - btm_pos, 0.001) / max(top_pos - btm_pos, 0.001), 1.0)
    t = t * (p["alfa_arriba"] - p["alfa_abajo"]) + p["alfa_abajo"]
    ga = np.where(coord <= btm_pos, p["alfa_abajo"],
                  np.where(coord >= top_pos, p["alfa_arriba"], t)).astype(np.float32)

    # El alfa del gradiente (claves de alfa del Gradient de Unity) modula la fuerza del efecto.
    # Gradient.Evaluate(t) devuelve (r, g, b, a) y el shader usa 'a' para pesar la mezcla.
    claves_alfa = p.get("claves_alfa") or []
    if claves_alfa:
        tiempos_a = np.array([t for t, _ in claves_alfa], dtype=np.float32)
        valores_a = np.array([a for _, a in claves_alfa], dtype=np.float32)
        g_alfa = np.interp(coord, tiempos_a, valores_a).astype(np.float32)
        ga = ga * g_alfa

    if solo_degradado:
        mezcla = gra
    else:
        mezcla = base + ga[..., None] * (gra - base)
        mezcla = col + p["effect_factor"] * (mezcla - col)

    if lineal:
        mezcla = a_srgb(mezcla)
    salida = np.concatenate([np.clip(mezcla, 0, 1), alfa[..., None]], axis=-1)
    res = Image.fromarray((salida * 255.0 + 0.5).astype(np.uint8), "RGBA")
    if v_invertida:
        res = res.transpose(Image.FLIP_TOP_BOTTOM)
    return res


def sombrear(ruta_png, p, solo_degradado=False, v_invertida=False, lineal=False):
    """Igual que sombrear_imagen, pero partiendo de un fichero."""
    return sombrear_imagen(Image.open(ruta_png), p, solo_degradado, v_invertida, lineal)


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    ruta_json, ruta_png = sys.argv[1], sys.argv[2]
    destino = Path(sys.argv[3]) if len(sys.argv) > 3 else Path(ruta_png).parent / "sombreado"
    destino.mkdir(parents=True, exist_ok=True)

    p = leer_parametros(ruta_json)
    print("bust-up: %s" % p["nombre"])
    print("   EffectFactor %.3f | base brillo %.2f sat %.2f cont %.2f | degradado brillo %.2f sat %.2f cont %.2f"
          % (p["effect_factor"], p["brillo"], p["saturacion"], p["contraste"],
             p["gra_brillo"], p["gra_saturacion"], p["gra_contraste"]))
    print("   modo %s | angulo %.1f | alfa %.3f..%.3f | claves color %d | tramo de alfa %.3f..%.3f"
          % ("radial" if p["modo"] else "lineal", p["angulo"], p["alfa_abajo"], p["alfa_arriba"],
             len(p["claves_color"]), p["claves_alfa"][0][0], p["claves_alfa"][-1][0]))

    original = Image.open(ruta_png).convert("RGBA")
    exacto = sombrear(ruta_png, p)
    solo_grad = sombrear(ruta_png, p, solo_degradado=True)

    # tira de comparacion: original | solo degradado | sombreado exacto
    fondo = Image.new("RGBA", (original.width * 3 + 40, original.height), (24, 24, 28, 255))
    for i, im in enumerate((original, solo_grad, exacto)):
        fondo.alpha_composite(im, (i * (original.width + 20), 0))
    nombre = Path(ruta_png).stem
    salida = destino / ("%s_comparacion.png" % nombre)
    fondo.save(salida)
    exacto.save(destino / ("%s_sombreado.png" % nombre))
    solo_grad.save(destino / ("%s_solo_degradado.png" % nombre))
    print()
    print("comparacion guardada en", salida)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())