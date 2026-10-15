"""Comprueba el enlace malla<->textura y el reparto en carpetas, con los nombres reales."""
import os
import sys

sys.path.insert(0, r"C:/Users/Lukas/p5x-datamining/p5x_studio")
from p5x_studio import extractor as X

CASOS = {
    "pc077": ("PC077_01", r"C:/Users/Lukas/p5x-datamining/p5x_studio/modelos_extraidos/pc077_PC077"),
    "pc079": ("PC079_01", r"C:/Users/Lukas/p5x-datamining/_dl/kotone_rig_completo/pc079_01_PC079_01"),
    "skull": ("skull", r"C:/Users/Lukas/p5x-datamining/p5x_studio/modelos_extraidos/skull_skull"),
}

for k, (actor, r) in CASOS.items():
    objs, pngs = [], []
    for dp, _, fs in os.walk(os.path.join(r, "01_model")):
        objs += [f for f in fs if f.lower().endswith(".obj")]
    for dp, _, fs in os.walk(os.path.join(r, "02_textures")):
        pngs += [f for f in fs if f.lower().endswith(".png")]
    print("=" * 30, k)
    bases_por_parte = {p: sorted({X._base_textura(os.path.splitext(f)[0])
                                  for f in pngs if X._clasificar(f) == p}) for p in X.PARTES}
    for f in sorted(objs):
        stem = os.path.splitext(f)[0]
        parte = X._clasificar(stem)
        sub = X._nombre_pieza(stem, actor) if parte in X.PARTES_SUELTAS else ""
        pref = X._prefijo_rig(stem) or stem.lower()
        grupo = X._emparejar(pref, bases_por_parte[parte])
        asoc = sorted(os.path.splitext(t)[0] for t in pngs
                      if grupo and X._base_textura(os.path.splitext(t)[0]) == grupo)
        if not asoc and parte not in X.PARTES_SUELTAS:
            asoc = ["<todas las de %s>" % parte]
        print("  %-8s %-52s sub=%-16s -> %s" % (parte, stem[:52], sub or "-", asoc or "(sin textura)"))