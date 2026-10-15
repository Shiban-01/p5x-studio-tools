"""Mide los OBJ de armas extraidos: tamano, centro y numero de vertices."""
import os

D = r"C:\Users\Lukas\p5x-datamining\_dl\armas_pc079"

for f in sorted(os.listdir(D)):
    if not f.endswith(".obj"):
        continue
    vs = []
    mats = []
    for linea in open(os.path.join(D, f), encoding="utf-8", errors="replace"):
        if linea.startswith("v "):
            p = linea.split()
            vs.append((float(p[1]), float(p[2]), float(p[3])))
        elif linea.startswith("usemtl"):
            m = linea.split(None, 1)[1].strip()
            if m not in mats:
                mats.append(m)
    xs = [v[0] for v in vs]
    ys = [v[1] for v in vs]
    zs = [v[2] for v in vs]
    nombre = f.replace("PC079_01_", "").replace("_wholeexport_rig", "").replace(".obj", "")
    print("%-22s %6d v   %.3f x %.3f x %.3f m   centro=(%.2f, %.2f, %.2f)"
          % (nombre, len(vs), max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs),
             (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, (min(zs) + max(zs)) / 2))
    print("   materiales: %s" % ", ".join(mats))