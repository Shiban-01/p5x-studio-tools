import sys, json, time
from pathlib import Path
RAIZ = Path("C:/Users/Lukas/Downloads/P5X/Client/OuterPackage/Bundles/Windows")
sys.path.insert(0, str(Path("C:/Users/Lukas/p5x-datamining/p5x_studio")))
from p5x_studio import rig_unitypy

def ruta(rel):
    return RAIZ / rel.replace("\\", "/")

casos = {
    "A_normal_solo (lo que hizo la app)": ["166\\part__uniformddcbdc1.bundle"],
    "B_uniform+role": ["054\\part_s__uniformddcbdc1.bundle", "066\\shared_2fb0a348.bundle",
                        "166\\part__uniformddcbdc1.bundle", "192\\shared_merged_9c38bc5.bundle",
                        "140\\role__uniform5f23c883.bundle"],
}
for etq, rels in casos.items():
    print("=" * 70)
    print(etq)
    dump = Path("C:/Users/Lukas/p5x-datamining/_dl/probe_closer/" + etq.split()[0])
    fich = [ruta(r) for r in rels]
    for f in fich:
        print("   existe", f.is_file(), f.name)
    try:
        r = rig_unitypy.volcar(fich, dump, "CLOSER", log=lambda s: print("   ", s))
        print("   RESULTADO:", r)
    except Exception as e:
        print("   EXCEPCION:", type(e).__name__, e)