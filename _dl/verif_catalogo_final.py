"""Comprobacion final del catalogo: numeros por categoria y casos clave intactos."""
import sys
from collections import Counter

sys.path.insert(0, r"C:\Users\Lukas\p5x-datamining\p5x_studio")
from p5x_studio import catalogo, trajes  # noqa: E402

ent = catalogo.personajes()
cats = Counter(a["categoria"] for a in ent)
print("ENTRADAS POR CATEGORIA:", dict(sorted(cats.items(), key=lambda x: -x[1])))
print("TOTAL:", len(ent))

tr = trajes.datos()["bundles"]
n_scn = sum(1 for v in tr.values() if v.get("tipo") == "scn")
n_scn_geo = sum(1 for v in tr.values() if v.get("tipo") == "scn" and v.get("mallas"))
n_efx = sum(1 for v in tr.values() if v.get("tipo") == "efx")
n_efx_geo = sum(1 for v in tr.values() if v.get("tipo") == "efx" and v.get("mallas"))
n_prop = sum(1 for v in tr.values() if v.get("papel") == "escenario" and v.get("mallas"))
print("bundles scn_: %d (con geometria: %d)   efx_: %d (con geometria: %d)   props role_: %d"
      % (n_scn, n_scn_geo, n_efx, n_efx_geo, n_prop))

print("\nCASOS CLAVE:")
for pid in ("pc079_01", "pc077_01", "skull"):
    a = [e for e in ent if e["id"] == pid][0]
    print("  %-9s cat=%-9s fic=%d trajes=%s es_skin=%s"
          % (pid, a["categoria"], len(a["ficheros"]),
             [T["clave"] for T in a.get("trajes") or []], a["es_skin"]))

print("\nEJEMPLOS DE ESCENARIO:")
for e in [x for x in ent if x["categoria"] == "escenario"][:3]:
    print("  ", e["etiqueta"], "->", e["ficheros"])
print("EJEMPLOS DE OBJETO:")
for e in [x for x in ent if x["categoria"] == "objeto"][:3]:
    print("  ", e["etiqueta"], "->", e["ficheros"])
print("EJEMPLOS DE EFECTO:")
for e in [x for x in ent if x["categoria"] == "efecto"][:3]:
    print("  ", e["etiqueta"], "->", e["ficheros"])