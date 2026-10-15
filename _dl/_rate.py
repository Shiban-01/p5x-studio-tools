import sys, time
sys.path.insert(0, r"C:\Users\Lukas\p5x-datamining\_dl")
from pilotar_exe import Piloto
def leer(p):
    t = p.texto("#bulk-estado").strip()
    return t, int(t.split("/")[0].replace(",", "").strip().split()[-1])
with Piloto(9226) as p:
    t0, n0 = leer(p); time.sleep(60); t1, n1 = leer(p)
    print("t0:", t0); print("t1:", t1)
    print("bundles en 60 s: %d  ->  %.1f por minuto" % (n1 - n0, (n1 - n0) * 1.0))
    if n1 > n0:
        print("ETA de los 14.431: %.1f horas" % ((14431 - n1) / ((n1 - n0) * 60.0) / 60.0 + 0.0))
    else:
        print("sin avance en 60 s: el lote esta en el motor (bloque de 120 bundles)")
