"""Monta el bust-up de xiachuanling (capas de lienzo completo), lo sombrea y saca comparaciones.

Las capas del juego son cada una un lienzo completo de 572x732, asi que se apilan tal cual. En el
juego cada capa se dibuja con el mismo material, pero como la cuenta del sombreado es lineal en el
color, sombrear el montaje da lo mismo que sombrear cada capa y luego montarlas (no hay desenfoque
activo en este personaje).
"""
import json
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, r"C:\Users\Lukas\p5x-datamining\_dl")
import sombreado_lihui as S  # noqa: E402

O = Path(r"C:\Users\Lukas\AppData\Local\hermes\cache\scratch\xiachuanling")
JSON = Path(r"C:\Users\Lukas\p5x-datamining\_dl\lihui_shader_json"
            r"\UI-DialogShader-changfu01-xiachuanling.json")
SALIDA = Path(r"C:\Users\Lukas\p5x-datamining\_dl\prueba_xiachuanling")
SALIDA.mkdir(parents=True, exist_ok=True)

FONDO = (22, 26, 38, 255)   # parecido al fondo del juego en el dialogo


def capa(nombre):
    """Devuelve la capa de lienzo completo (el Texture2D, no el Sprite recortado)."""
    f = sorted(O.glob("xiachuanling-changfu-%s_#*.png" % nombre))
    if not f:
        raise SystemExit("no encuentro la capa %s" % nombre)
    return Image.open(f[0]).convert("RGBA")


def montar(zui="tongchang-zui1", con_contorno=False):
    """Apila las capas en el orden del juego."""
    orden = ["benti", "benti-zhi", "benti-yifu", "benti-toufa"]
    if con_contorno:
        orden.insert(0, "benti-lunkuo")
    orden += ["tongchang-yan1", zui]
    base = Image.new("RGBA", capa("benti").size, (0, 0, 0, 0))
    for n in orden:
        base.alpha_composite(capa(n))
    return base


def sobre_fondo(im, fondo=FONDO):
    lona = Image.new("RGBA", im.size, fondo)
    lona.alpha_composite(im)
    return lona


def tira(imagenes, etiquetas=None):
    """Tira horizontal con las imagenes sobre fondo oscuro."""
    ancho = sum(i.width for i in imagenes) + 20 * (len(imagenes) - 1)
    alto = max(i.height for i in imagenes)
    lona = Image.new("RGBA", (ancho, alto), (16, 16, 20, 255))
    x = 0
    for i in imagenes:
        lona.alpha_composite(sobre_fondo(i), (x, (alto - i.height) // 2))
        x += i.width + 20
    return lona


p = S.leer_parametros(JSON)
print("bust-up:", p["nombre"])
print("   EffectFactor %.3f | base %.2f/%.2f/%.2f | degradado %.2f/%.2f/%.2f | modo %s | angulo %.2f"
      % (p["effect_factor"], p["brillo"], p["saturacion"], p["contraste"],
         p["gra_brillo"], p["gra_saturacion"], p["gra_contraste"],
         "radial" if p["modo"] else "lineal", p["angulo"]))

montaje = montar()
print("   montaje:", montaje.size)
montaje.save(SALIDA / "montaje_sin_sombra.png")

sombreado = S.sombrear_imagen(montaje, p)
sombreado.save(SALIDA / "montaje_sombreado.png")
S.sombrear_imagen(montaje, p, solo_degradado=True).save(SALIDA / "montaje_solo_degradado.png")

# tira: sin sombra | solo degradado | sombreado exacto
tira([montaje, S.sombrear_imagen(montaje, p, solo_degradado=True), sombreado]).save(
    SALIDA / "comparacion.png")

# tira de bocas, ya sombreadas, para elegir la que sale en la captura
bocas = [S.sombrear_imagen(montar(zui="tongchang-zui%d" % n), p) for n in (1, 2, 3)]
tira(bocas).save(SALIDA / "bocas_sombreadas.png")

# variante con el contorno dibujado debajo
S.sombrear_imagen(montar(con_contorno=True), p).save(SALIDA / "montaje_con_contorno.png")

print("   guardado en", SALIDA)
for f in sorted(SALIDA.glob("*.png")):
    print("      %-28s %s" % (f.name, Image.open(f).size))