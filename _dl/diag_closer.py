import json, sys, os
from pathlib import Path
sys.path.insert(0, str(Path("C:/Users/Lukas/p5x-datamining/p5x_studio")))
from p5x_studio import catalogo, trajes

d = trajes.datos()
print("=== PC077_01 trajes ===")
A = d["actores"].get("PC077_01") or d["actores"].get("pc077_01")
for k, v in (A["trajes"].items() if A else []):
    print(" ", k, v["bundles"])

print()
print("=== catalogo: closer ===")
for e in catalogo.personajes():
    if e["id"].lower() == "closer":
        print("id", e["id"], "cat", e["categoria"], "piezas", e["piezas"])
        print("ficheros", e["ficheros"])
        print("ficheros_otros", e.get("ficheros_otros"))
        print("traje_por_defecto", e.get("traje_por_defecto"))
        for T in e.get("trajes") or []:
            print("   traje", T["clave"], "->", T["ficheros"])
        break

print()
print("=== bundles role_ con closer (papel) ===")
for k, v in d["bundles"].items():
    if k.split("/")[-1].startswith("role_") and v.get("papel") in ("montaje", "escenario"):
        pass
for cand in ["140/role__uniform5f23c883.bundle", "049/role_swimsuit1d754547.bundle",
             "125/role_er_thiefeba4741.bundle", "092/role_swimsuit3b8c3cd.bundle"]:
    v = d["bundles"].get(cand)
    if v:
        print(cand, "papel=", v.get("papel"), "actores=", v.get("actores"), "trajes=", v.get("trajes"))