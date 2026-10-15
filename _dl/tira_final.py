"""Tira limpia de dos paneles para entregar: la captura del juego y el bust-up sombreado aqui."""
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, r"C:\Users\Lukas\p5x-datamining\_dl")
import sombreado_lihui as S  # noqa: E402
import comparar_captura as C  # noqa: E402

SALIDA = Path(r"C:\Users\Lukas\p5x-datamining\_dl\prueba_xiachuanling")
montaje = C.montar()
p = S.leer_parametros(C.JSON_CHANGFU)
mio = C.sobre(S.sombrear_imagen(montaje, p))

alto = 700
trozos = []
for im in (C.pers, mio):
    esc = alto / im.height
    trozos.append(im.resize((int(im.width * esc), alto), Image.LANCZOS))

lona = Image.new("RGBA", (sum(t.width for t in trozos) + 24, alto), (12, 12, 14, 255))
x = 0
for t in trozos:
    lona.alpha_composite(t, (x, 0))
    x += t.width + 24
lona.save(SALIDA / "captura_vs_sombreado.png")
print("guardado", SALIDA / "captura_vs_sombreado.png", lona.size)
print("parametros usados:", p["nombre"])
print("  EffectFactor %.2f | degradado %.2f/%.2f/%.2f | angulo %.2f | modo %s | alfa %.2f..%.2f"
      % (p["effect_factor"], p["gra_brillo"], p["gra_saturacion"], p["gra_contraste"],
         p["angulo"], "radial" if p["modo"] else "lineal", p["alfa_abajo"], p["alfa_arriba"]))
print("  claves de color:", [(round(t, 3), tuple(round(x, 3) for x in c)) for t, c in p["claves_color"]])