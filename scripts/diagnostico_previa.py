"""Localiza que fase de la vista previa se lleva el tiempo.

Imprime el tiempo de cada paso segun termina, con flush, de modo que si se cuelga se ve
exactamente en cual. Se ejecuta sobre la pieza mas pequena para que sea rapido.
"""
import math
import sys
import time
from pathlib import Path

sys.path.insert(0, r"C:\Users\Lukas\p5x-datamining\p5x_studio")
from p5x_studio import preview  # noqa: E402

raiz = Path(r"C:\Users\Lukas\p5x-datamining\_dl\prueba_herramienta\pc079_Kotone_Shiomi")
obj = raiz / "01_model/obj/weapons/PC079_01_gun_02_wholeexport_rig_wq_makpon_gun_02.obj"


def paso(texto, t0):
    print("   %-34s %6.2f s" % (texto, time.time() - t0), flush=True)
    return time.time()


t = time.time()
vertices, caras = preview._leer_obj(obj)
t = paso("leer OBJ (%d vert, %d caras)" % (len(vertices), len(caras)), t)

mtl = obj.with_suffix(".mtl")
colores, texturas = preview._leer_mtl(mtl)
t = paso("leer MTL (%d mat, %d text)" % (len(colores), len(texturas)), t)

# indice de texturas, que es lo que se construia una vez por material
indice = preview._indice_texturas(raiz)
t = paso("indice de texturas (%d)" % len(indice), t)

for nombre, ruta in list(texturas.items())[:3]:
    t0 = time.time()
    preview._color_textura(ruta, None)
    print("      color de %s: %.2f s" % (ruta.name[:40], time.time() - t0), flush=True)

# dibujo, fase a fase
t0 = time.time()
giro = math.radians(32)
cg, sg = math.cos(giro), math.sin(giro)
verts = [(v[0] * cg - v[2] * sg, v[1], v[0] * sg + v[2] * cg) for v in vertices]
t = paso("girar vertices", t0)

t0 = time.time()
orden = sorted(caras, key=lambda c: sum(verts[i][2] for i in c[0]) / 3.0)
t = paso("ordenar por profundidad", t0)

print("   total: %.2f s" % (time.time() - t), flush=True)
print("   ahora el dibujo completo:", flush=True)
t0 = time.time()
r = preview.dibujar(obj, raiz / "preview/prueba_gun.png", ruta_mtl=mtl, texturas={},
                    titulo="prueba")
print("   dibujar(): %.2f s -> %s" % (time.time() - t0, r), flush=True)