"""Compara la silueta del render con la de la referencia: IoU, imagen lado a lado y superposicion.

Normaliza las dos siluetas (recorta a su caja y las escala a la misma altura) para que la
comparacion no dependa del encuadre. Devuelve un numero (IoU) y dos imagenes para mirar.
"""
import os
import sys
from PIL import Image, ImageChops

REF = r"C:\Users\Lukas\AppData\Roaming\Hermes\composer-images\image_827048.png"
RENDER = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\Lukas\p5x-datamining\media\toon_pose\pose_00.png"
SAL = r"C:\Users\Lukas\p5x-datamining\media\toon_pose"
ALTO = 800


def silueta(ruta, umbral=128):
    im = Image.open(ruta)
    if "A" in im.getbands():
        a = im.getchannel("A")
        if a.getextrema()[1] > 0:
            m = a.point(lambda v: 255 if v > umbral else 0)
            if m.getbbox():
                return m
    # sin alfa util: fondo = color de la esquina
    rgb = im.convert("RGB")
    fondo = rgb.getpixel((0, 0))
    px = rgb.load()
    m = Image.new("L", rgb.size, 0)
    mp = m.load()
    for y in range(rgb.height):
        for x in range(rgb.width):
            r, g, b = px[x, y]
            if abs(r - fondo[0]) + abs(g - fondo[1]) + abs(b - fondo[2]) > 60:
                mp[x, y] = 255
    return m


def normaliza(m, alto=ALTO):
    caja = m.getbbox()
    if not caja:
        return None
    m = m.crop(caja)
    ancho = max(1, int(m.width * alto / m.height))
    return m.resize((ancho, alto))


mr = normaliza(silueta(REF))
mm = normaliza(silueta(RENDER))
print("referencia: %s   render: %s" % (mr.size if mr else None, mm.size if mm else None))
if mr is None or mm is None:
    print("no hay silueta en alguna de las dos")
    raise SystemExit

# lienzo comun, centradas horizontalmente
ancho = max(mr.width, mm.width)
lienzo_r = Image.new("L", (ancho, ALTO), 0)
lienzo_m = Image.new("L", (ancho, ALTO), 0)
lienzo_r.paste(mr, ((ancho - mr.width) // 2, 0))
lienzo_m.paste(mm, ((ancho - mm.width) // 2, 0))

inter = ImageChops.multiply(lienzo_r, lienzo_m)
union = ImageChops.lighter(lienzo_r, lienzo_m)
pi = sum(inter.point(lambda v: 1 if v else 0).getdata())
pu = sum(union.point(lambda v: 1 if v else 0).getdata())
print("\n   IoU de silueta: %.3f   (1.0 = identicas, 0.0 = nada en comun)" % (pi / max(1, pu)))
print("   area referencia: %d   area render: %d" % (
    sum(lienzo_r.point(lambda v: 1 if v else 0).getdata()),
    sum(lienzo_m.point(lambda v: 1 if v else 0).getdata())))

# lado a lado
lado = Image.new("RGB", (ancho * 2 + 20, ALTO), (30, 30, 30))
lado.paste(Image.merge("RGB", (lienzo_r, lienzo_r, lienzo_r)), (0, 0))
lado.paste(Image.merge("RGB", (lienzo_m, lienzo_m, lienzo_m)), (ancho + 20, 0))
lado.save(os.path.join(SAL, "comparacion_siluetas.png"))

# superposicion: referencia en rojo, render en cian
sup = Image.new("RGB", (ancho, ALTO), (0, 0, 0))
sp = sup.load()
pr, pm = lienzo_r.load(), lienzo_m.load()
for y in range(ALTO):
    for x in range(ancho):
        r = pr[x, y] > 0
        m = pm[x, y] > 0
        sp[x, y] = (255, 60, 60) if (r and not m) else ((60, 200, 255) if (m and not r) else ((255, 255, 255) if r else (0, 0, 0)))
sup.save(os.path.join(SAL, "superposicion.png"))

# por bandas: donde falla mas
print("\n   error por bandas de altura (%% de la referencia que no cubre el render):")
for f in range(0, 100, 10):
    ya, yb = ALTO * f // 100, ALTO * (f + 10) // 100
    tot = falta = 0
    for y in range(ya, yb):
        for x in range(ancho):
            if pr[x, y]:
                tot += 1
                if not pm[x, y]:
                    falta += 1
    print("      %3d%%-%3d%%  %s" % (f, f + 10, "%3d%%" % (100 * falta // tot) if tot else "  -"))
print("\n   guardado: comparacion_siluetas.png y superposicion.png (rojo = solo referencia, cian = solo render)")