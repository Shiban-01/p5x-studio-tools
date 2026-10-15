"""Prueba A/B del aviso de Aaron: ¿las capas se dibujan a su tamano o estiradas al de la base?

A: como lo hace el script ahora -> la capa se pega a su tamano, alineada arriba.
B: como dice Aaron -> la capa se estira al tamano de la capa base (lienzo).

Se generan las dos y se ponen lado a lado para poder juzgar cual da una cara con proporciones
correctas (si se estira, los ojos de 984x788 al lienzo 984x988 se alargan un 25%).
"""
import json
from pathlib import Path

from PIL import Image

DL = Path(r"C:\Users\Lukas\p5x-datamining\_dl")
CLAVE = "UI-DialogShader-guaidaofu01-jianajun"
co = json.loads((DL / "bustups_montados" / ("%s.json" % CLAVE)).read_text(encoding="utf-8"))
lienzo = tuple(co["lienzo"])

a = Image.new("RGBA", lienzo, (0, 0, 0, 0))
b = Image.new("RGBA", lienzo, (0, 0, 0, 0))
for c in co["capas"]:
    im = Image.open(c["png"]).convert("RGBA")
    # A: tal cual (si es mas pequena, arriba)
    a.alpha_composite(im, dest=tuple(c["offset"]))
    # B: estirada al lienzo
    if im.size != lienzo:
        im = im.resize(lienzo, Image.LANCZOS)
    b.alpha_composite(im)

alto = 700
def plano(im):
    e = alto / im.height
    im = im.resize((int(im.width * e), alto), Image.LANCZOS)
    f = Image.new("RGBA", im.size, (60, 60, 66, 255))
    f.alpha_composite(im)
    return f.convert("RGB")

pa, pb = plano(a), plano(b)
# recorte de la cara (tercio superior) ampliado, que es donde se nota
def cara(im):
    c = im.crop((0, 0, im.width, im.height // 2)).resize((im.width * 2, im.height), Image.LANCZOS)
    return c
comp = Image.new("RGB", (pa.width + pb.width + 20, 700), (25, 25, 28))
comp.paste(pa, (0, 0))
comp.paste(pb, (pa.width + 20, 0))
comp.save(DL / "bustups_montados" / "_ab_tamano.png")
print("A/B guardado:", comp.size)

# y las caras ampliadas x2
ca, cb = cara(pa), cara(pb)
comp2 = Image.new("RGB", (ca.width + cb.width + 20, ca.height), (25, 25, 28))
comp2.paste(ca, (0, 0))
comp2.paste(cb, (ca.width + 20, 0))
comp2.save(DL / "bustups_montados" / "_ab_caras.png")
print("caras guardadas:", comp2.size)