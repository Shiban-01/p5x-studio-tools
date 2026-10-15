import sys, json
sys.path.insert(0, r"C:/Users/Lukas/p5x-datamining/p5x_studio")
from pathlib import Path
from p5x_studio import ajustes, rig_unitypy

carpeta = ajustes.carpeta_bundles()
ficheros = [carpeta / f for f in (
    "032/role_pc077_01132c9d31.bundle",
    "089/shared_merged_3400dc06.bundle",
    "103/part_pc077_011eadf551.bundle",
)]
dump = Path(r"C:/Users/Lukas/p5x-datamining/_dl/dump_pc077")
import shutil; shutil.rmtree(dump, ignore_errors=True)
rig_unitypy.volcar([f for f in ficheros if f.is_file()], dump, "PC077_01", log=lambda s: None)

# catalogo de materiales crudo
entornos = [rig_unitypy._abrir(f) for f in ficheros if f.is_file()]
cat = rig_unitypy._catalogo_materiales(entornos)
print("=== MATERIALES EN LOS BUNDLES (%d) ===" % len(cat))
for k, v in sorted(cat.items()):
    print("  %-40s -> %d texturas %s" % (k, len(v["texturas"]),
          [t["slot"] + ":" + t["textura"] for t in v["texturas"]]))

print()
print("=== MATERIALES ASIGNADOS POR PARTE ===")
for p in sorted(dump.glob("*.json")):
    if p.stem in ("resumen", "esqueleto", "log"):
        continue
    meta = json.loads(p.read_text(encoding="utf-8"))
    print("  %-46s token=%r" % (p.stem[-46:], rig_unitypy._token_rig(meta["malla"])))
    for m in meta.get("materiales", []):
        print("      sub%d -> %r  texturas=%s" % (m["indice"], m.get("nombre"),
              [t["slot"] + ":" + t["textura"] for t in m.get("texturas", [])]))