"""Prueba de biseccion: con cuantas cajas de fisica deja studiomdl de quejarse.

Reescribe fisica.smd con las primeras N cajas (cada caja son 12 triangulos = 36 lineas) y recompila
el .qc de L4D2, que ya apunta a fisica.smd por nombre. No toca nada mas: sirve para saber si el
problema escala con el numero de cajas o es del formato del fichero.
"""
import os, re, subprocess, sys

RAIZ = r"C:\Users\Lukas\p5x-datamining\kotone_source"
MSRC = os.path.join(RAIZ, "gamedir", "modelsrc")
FISICA = os.path.join(MSRC, "fisica.smd")
ESTUDIOMDL = (r"C:\Program Files (x86)\Steam\steamapps\common\Portal 2 Community Edition"
              r"\bin\win64\studiomdl.exe")
GAMEDIR = os.path.join(RAIZ, "gamedir")

lineas = open(FISICA, encoding="utf-8").read().splitlines()
i_tri = lineas.index("triangles")
cabecera = lineas[:i_tri + 1]
cuerpo = lineas[i_tri + 1:]
material = cuerpo[0] if cuerpo and not cuerpo[0].strip()[0].isdigit() else None
if material:
    cuerpo = cuerpo[1:]
cuerpo = [l for l in cuerpo if l.strip() != "end"]
n_lineas_por_caja = 36
total_cajas = len(cuerpo) // n_lineas_por_caja
print("cajas en el fichero: %d | lineas: %d | material: %r" % (total_cajas, len(cuerpo), material))

PHY = os.path.join(GAMEDIR, "models", "survivors", "survivor_producer.phy")
original = open(FISICA, encoding="utf-8").read()

for n in (1, 4, 8, 12, 16, total_cajas):
    if n > total_cajas:
        continue
    trozos = ([material] if material else []) + cuerpo[:n * n_lineas_por_caja] + ["end"]
    with open(FISICA, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(cabecera + trozos) + "\n")
    if os.path.exists(PHY):
        os.remove(PHY)
    r = subprocess.run([ESTUDIOMDL, "-nop4", "-game", GAMEDIR,
                        os.path.join(MSRC, "kotone_l4d2_fisica.qc")],
                       capture_output=True, text=True, errors="replace", cwd=MSRC)
    salida = (r.stdout or "") + (r.stderr or "")
    err = [l.strip() for l in salida.splitlines()
           if re.search(r"ERROR|WARNING", l) and "joint" not in l.lower()]
    print("cajas=%-3d exit=%-4d phy=%-5s %s" % (
        n, r.returncode, "SI" if os.path.exists(PHY) else "no",
        " | ".join(err[:2]) if err else "sin errores"))
    if os.path.exists(PHY):
        print("           tamano del .phy: %d bytes" % os.path.getsize(PHY))

with open(FISICA, "w", encoding="utf-8", newline="\n") as f:   # dejar el original de 19 cajas
    f.write(original)
print("fisica.smd restaurado con las %d cajas" % total_cajas)