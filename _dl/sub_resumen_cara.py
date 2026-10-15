"""Resumen: para cada bust-up, en que bundle vive la CARA y si el visor extrae ese bundle."""
import json
import re
from collections import defaultdict
from pathlib import Path

DL = Path(r"C:\Users\Lukas\p5x-datamining\_dl")
REPO = Path(r"C:\Users\Lukas\p5x-datamining")
filas = json.loads((DL / "censo_texturas.json").read_text(encoding="utf-8"))["filas"]
info = json.loads((DL / "bustups_indice_informe.json").read_text(encoding="utf-8"))
retratos = set(json.loads((REPO / "p5x_studio/p5x_studio/datos/retratos.json")
                          .read_text(encoding="utf-8"))["bundles"])
ALIAS = {"aochuncun": "aocunchun"}

# assets de cara (ojos/boca) o cara-base (benti-<expr>) por primer token
cara_por_token = defaultdict(list)
for f in filas:
    if f["tipo"] != "Sprite":
        continue
    nm = f["nombre"]; tok = nm.split("-")[0]
    if re.search(r"-(yan|zui)\d$", nm):
        cara_por_token[tok].append((nm, f["bundle"], "ojos/boca"))
    elif re.search(r"-(benti|shenti|zhengti)-[a-z0-9]+$", nm) and not re.search(
            r"-(lunkuo|toufa|yifu|zhi|mianju|mask|zhi\d)", nm):
        cara_por_token[tok].append((nm, f["bundle"], "cara-base"))

fuera, dentro = [], []
for clave, d in info["bustups"].items():
    per = ALIAS.get(d["personaje"], d["personaje"])
    cats = cara_por_token.get(per, [])
    bs = sorted({b for _, b, _ in cats})
    if not bs:
        continue
    faltan = [b for b in bs if b not in retratos]
    reg = {"clave": clave.replace("UI-DialogShader-", ""), "personaje": d["personaje"],
           "ropa": d["ropa"], "n_cara": len(cats),
           "bundles_cara": bs, "bundles_cara_fuera_de_visor": faltan}
    (fuera if faltan else dentro).append(reg)

print("bust-ups con assets de cara localizados:", len(fuera) + len(dentro))
print("  con TODOS los bundles de cara en el visor:", len(dentro))
print("  con algun bundle de cara FUERA del visor:", len(fuera))
print()
print("%-42s %-22s %-5s %s" % ("bust-up", "personaje/ropa", "#cara", "bundles de cara fuera del visor"))
for r in fuera:
    print("%-42s %-22s %-5d %s" % (r["clave"], "%s/%s" % (r["personaje"], r["ropa"]),
                                    r["n_cara"], [b.split("/")[-1][:26] for b in r["bundles_cara_fuera_de_visor"]]))

# bundles concretos que faltan y cuantos bust-ups afectan
cuenta = defaultdict(int)
for r in fuera:
    for b in r["bundles_cara_fuera_de_visor"]:
        cuenta[b] += 1
print()
print("BUNDLES CON CARA QUE EL VISOR NO EXTRAE (%d):" % len(cuenta))
for b, n in sorted(cuenta.items(), key=lambda kv: -kv[1]):
    print("   %-46s afecta a %d bust-ups" % (b, n))
(DL / "cara_fuera_del_visor.json").write_text(json.dumps(fuera, ensure_ascii=False, indent=1),
                                              encoding="utf-8")