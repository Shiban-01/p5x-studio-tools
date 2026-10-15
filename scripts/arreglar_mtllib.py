"""Anade la linea mtllib (y el usemtl) que AssetStudio no escribe en los OBJ de armas.

Sin mtllib, Blender importa la malla pero no lee el material, y el arma sale sin textura. El MTL
existe y esta bien: solo falta que el OBJ lo nombre. El usemtl asigna ese material a las caras.
"""
import os

D = r"C:\Users\Lukas\p5x-datamining\kotone_shiomi\01_model\obj\weapons"

for f in sorted(os.listdir(D)):
    if not f.endswith(".obj"):
        continue
    p = os.path.join(D, f)
    lineas = open(p, encoding="utf-8", errors="replace").read().splitlines()
    mtl = f[:-4] + ".mtl"

    tiene_mtllib = any(l.startswith("mtllib") for l in lineas)
    tiene_usemtl = any(l.startswith("usemtl") for l in lineas)

    salida = []
    for i, l in enumerate(lineas):
        salida.append(l)
        if i == 0 and not tiene_mtllib:
            salida.append("mtllib " + mtl)
    if not tiene_usemtl:
        # el usemtl va justo antes de la primera cara
        for i, l in enumerate(salida):
            if l.startswith("f "):
                salida.insert(i, "usemtl mat0")
                break

    if not tiene_mtllib or not tiene_usemtl:
        with open(p, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(salida) + "\n")
        print("%-20s  mtllib %s   usemtl %s" % (f, "anadido" if not tiene_mtllib else "ya estaba",
                                                "anadido" if not tiene_usemtl else "ya estaba"))
    else:
        print("%-20s  ya estaba completo" % f)

print("\n=== cabeceras resultantes ===")
for f in sorted(os.listdir(D)):
    if f.endswith(".obj"):
        cab = [l for l in open(os.path.join(D, f), encoding="utf-8", errors="replace").readlines()[:6]]
        print("   %s" % f)
        for l in cab[:4]:
            print("      " + l.rstrip()[:70])