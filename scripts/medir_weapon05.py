"""Mide donde esta la cabeza del arma en weapon_05: el extremo grueso del asta.

La hoja y su guarnicion ocupan mucho mas ancho que el mastil, asi que midiendo el ancho de la
seccion a lo largo del eje Z se ve en que extremo esta la cabeza. Con eso se decide el sentido.
"""
import os

RUTA = r"C:\Users\Lukas\p5x-datamining\kotone_shiomi\01_model\obj\weapons\weapon_05.obj"

vs = []
for linea in open(RUTA, encoding="utf-8", errors="replace"):
    if linea.startswith("v "):
        p = linea.split()
        vs.append((float(p[1]), float(p[2]), float(p[3])))
print("vertices: %d" % len(vs))
zs = [v[2] for v in vs]
z0, z1 = min(zs), max(zs)
print("eje Z (el asta corre por aqui): de %.3f a %.3f  = %.3f m" % (z0, z1, z1 - z0))
xs = [v[0] for v in vs]; ys = [v[1] for v in vs]
print("ancho total: X %.3f  Y %.3f" % (max(xs) - min(xs), max(ys) - min(ys)))

print("\n=== ancho de la seccion a lo largo del asta ===")
print("   tramo de Z      ancho X   ancho Y   vertices")
N = 10
for i in range(N):
    a = z0 + (z1 - z0) * i / N
    b = z0 + (z1 - z0) * (i + 1) / N
    sel = [v for v in vs if a <= v[2] <= b]
    if not sel:
        print("   %.2f-%.2f      (vacio)" % (a, b))
        continue
    ax = max(v[0] for v in sel) - min(v[0] for v in sel)
    ay = max(v[1] for v in sel) - min(v[1] for v in sel)
    print("   %.2f-%.2f      %.3f     %.3f     %5d  %s" % (a, b, ax, ay, len(sel),
          "<<< GRUESO (cabeza/hoja)" if max(ax, ay) > 0.12 else ""))
print("\n   z=0.00 es el extremo MINIMO de Z. Si el tramo grueso esta arriba, la cabeza")
print("   queda en el extremo de Z maximo.")