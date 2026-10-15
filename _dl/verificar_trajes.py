"""Verificacion del indice de trajes y de la extraccion por traje.

Comprueba, con extraccion REAL (nada simulado):
  1. que `skull` da a elegir entre sus trajes y que cada uno sale solo (sin el otro, y sin el
     edificio `skull` que antes se colaba),
  2. que PC079_01 (Kotone, con cara propia) y PC077_01 (skin de n_GuitarGirl) siguen extrayendose,
  3. los numeros del reparto de trajes.

Uso:
    python _dl/verificar_trajes.py
"""
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, r"C:\Users\Lukas\p5x-datamining\p5x_studio")
from p5x_studio import bases, catalogo, extractor, trajes  # noqa: E402

DESTINO = Path(r"C:\Users\Lukas\p5x-datamining\_dl\verif_trajes")
OPCIONES = {"mallas": True, "texturas": True, "materiales": True, "esqueleto": False,
            "previas": False, "fbx": False, "armas": True}


def listar(raiz: Path):
    """Cuenta y lista lo que ha salido, por tipo."""
    obj = sorted(raiz.rglob("*.obj"))
    png = sorted(raiz.rglob("*.png"))
    return obj, png


def extraer(p, clave_traje):
    ficha = None
    for t in (p.get("trajes") or []):
        if t["clave"] == clave_traje:
            ficha = t
    print("\n>>> EXTRAER %s traje=%s  ficheros=%s" % (p["id"], clave_traje,
                                                      ficha["ficheros"] if ficha else "?"))
    destino = extractor.extraer_personaje(
        p, {}, DESTINO, OPCIONES, log=lambda s: print("    " + s),
        base=bases.base_de(p["id"]), traje=ficha)
    obj, png = listar(destino)
    print("    DESTINO: %s" % destino)
    print("    OBJ: %d" % len(obj))
    for o in obj:
        print("       %s" % o.relative_to(destino))
    print("    PNG: %d" % len(png))
    for t in png[:8]:
        print("       %s" % t.relative_to(destino))
    return destino, obj, png


def main() -> None:
    if DESTINO.exists():
        shutil.rmtree(DESTINO)
    DESTINO.mkdir(parents=True, exist_ok=True)
    ps = {p["id"]: p for p in catalogo.personajes()}

    print("=" * 70)
    print("1) ACTORES CON MAS DE UN TRAJE")
    con = [(p["id"], p["trajes"]) for p in catalogo.personajes() if len(p.get("trajes") or []) > 1]
    con.sort(key=lambda x: -len(x[1]))
    print("   actores con mas de un traje: %d de %d" % (len(con), len(ps)))
    for pid, ts in con[:12]:
        print("      %-16s %2d trajes: %s" % (pid, len(ts), ", ".join(t["clave"] for t in ts)))

    print("=" * 70)
    print("2) SKULL: cada traje por separado")
    skull = ps["skull"]
    print("   trajes de skull:", [t["clave"] for t in skull["trajes"]])
    print("   ficheros del actor (modelo):", skull["ficheros"])
    print("   ficheros apartados (NO modelo):", skull["ficheros_otros"])
    d1, o1, t1 = extraer(skull, "thief")
    d2, o2, t2 = extraer(skull, "uniform")
    nombres1 = {o.name.lower() for o in o1}
    nombres2 = {o.name.lower() for o in o2}
    print("\n   --- comprobacion ---")
    print("   thief trae mallas 'skull_thief_*' :", all("thief" in n for n in nombres1))
    print("   uniform trae mallas 'skull_uniform_*':", all("uniform" in n for n in nombres2))
    print("   sin mezcla (interseccion de OBJ):", sorted(nombres1 & nombres2))
    print("   el edificio (skull_lunchuan/wuding/paodao) aparece:",
          any(x in n for n in nombres1 | nombres2
              for x in ("lunchuan", "wuding", "paodao", "diban")))

    print("=" * 70)
    print("3) PC079_01 (Kotone, cara propia) y PC077_01 (skin de n_GuitarGirl)")
    for pid in ("pc079_01", "pc077_01"):
        p = ps[pid]
        print("\n   %s: trajes=%s  es_skin=%s  base=%s"
              % (pid, [t["clave"] for t in p["trajes"]], p["es_skin"], bases.base_de(pid)))
        extraer(p, p["traje_por_defecto"])

    print("=" * 70)
    print("4) REPARTO DE TRAJES")
    todos = [t["clave"] for p in ps.values() for t in (p.get("trajes") or [])]
    import collections
    print("   actores en el indice de trajes:", len(trajes.datos()["actores"]))
    print("   trajes distintos en el catalogo:", len(set(todos)))
    for k, v in collections.Counter(todos).most_common(15):
        print("      %-18s %d actores" % (k, v))


if __name__ == "__main__":
    main()