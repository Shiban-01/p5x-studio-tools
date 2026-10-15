"""¿De donde sale la zona negra de la cara en el montaje de xiachuanling?

Se monta dos veces (con y sin la capa de contorno) y se cuenta el negro opaco del tercio superior,
que es la cara. Si el negro desaparece al quitar el contorno, el problema es el orden de apilado;
si sigue, el negro viene del cuerpo (diseño del personaje) o de una capa que falta.
"""
import json
from pathlib import Path

from PIL import Image

DL = Path(r"C:\Users\Lukas\p5x-datamining\_dl")
co = json.loads((DL / "bustups_montados" / "UI-DialogShader-changfu01-xiachuanling.json")
                .read_text(encoding="utf-8"))
lienzo = tuple(co["lienzo"])

con = Image.new("RGBA", lienzo, (0, 0, 0, 0))
sin = Image.new("RGBA", lienzo, (0, 0, 0, 0))
for c in co["capas"]:
    im = Image.open(c["png"]).convert("RGBA")
    con.alpha_composite(im, dest=tuple(c["offset"]))
    if c["paso"] != "contorno":
        sin.alpha_composite(im, dest=tuple(c["offset"]))


def negro(im, recorte):
    a = im.crop(recorte)
    px = a.load()
    tot = neg = 0
    for y in range(0, a.height, 3):
        for x in range(0, a.width, 3):
            r, g, b, al = px[x, y]
            if al > 128:
                tot += 1
                if r < 40 and g < 40 and b < 40:
                    neg += 1
    return neg, tot


recorte = (0, 0, lienzo[0], lienzo[1] // 3)
print("lienzo", lienzo, "| tercio superior (cara):")
print("   con contorno:  negro opaco %d de %d opacos" % negro(con, recorte))
print("   sin contorno:  negro opaco %d de %d opacos" % negro(sin, recorte))

# ¿la capa de contorno es la que mete el negro?
cont = next(c for c in co["capas"] if c["paso"] == "contorno")
imc = Image.open(cont["png"]).convert("RGBA")
print("   la capa de contorno por si sola:", negro(imc, (0, 0, imc.width, imc.height)))

con.save(DL / "bustups_montados" / "_con_contorno.png")
sin.save(DL / "bustups_montados" / "_sin_contorno.png")