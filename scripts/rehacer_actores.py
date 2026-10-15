"""Rehace el campo `contiene` del indice de contenido, sin volver a abrir los bundles.

El nombre del personaje se sacaba cortando por el primer `_`, y eso daba basura: `n_GuitarGirl_...`
quedaba como «N». Aqui se deduce bien, a partir del nombre de la malla:

    n_GuitarGirl_body_02_wholeexport_rig_chord_normal_body   ->  n_GuitarGirl
    PC079_01_body_wholeexport_rig_pc079_01_body              ->  PC079_01
    fengbandadi_normal_body_wholeexport_rig_...              ->  fengbandadi
    chord_gun_02_wholeexport_rig_wq_chord_gun_02             ->  chord

La regla: el nombre de la malla lleva dentro `<personaje>_<pieza>_wholeexport_...`. Se corta por
`_wholeexport` y se toma el personaje, que son dos tokens cuando empieza por `n_` o por un codigo
`PCnnn_nn`, y uno cuando es un nombre suelto.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
INDICE = RAIZ / "_dl/indice_juego/indice_contenido.json"

CODIGO = re.compile(r"^(?P<quien>(?:pc|n|m|s|r)\d{2,3}_?\d*)_", re.I)
CODIGO_NOMBRE = re.compile(r"^(?P<quien>n_[A-Za-z][A-Za-z0-9]+|PC\d{3}_\d{2})_", re.I)


def personaje_de(malla: str) -> str | None:
    """Deduce a que personaje pertenece una malla, a partir de su nombre."""
    base = malla.split("_wholeexport")[0]
    if not base:
        return None
    # n_GuitarGirl_body_02  /  PC079_01_body  -> dos tokens
    m = CODIGO_NOMBRE.match(base)
    if m:
        return m.group("quien")
    # chord_gun_02 / fengbandadi_normal_body  -> un token
    return base.split("_")[0] or None


def main() -> None:
    datos = json.loads(INDICE.read_text(encoding="utf-8"))
    actores: dict[str, dict] = {}
    cambiados = 0
    for clave, v in datos.items():
        mallas = v.get("mallas") or []
        quien = sorted({p for p in (personaje_de(m) for m in mallas) if p})
        if quien != v.get("contiene"):
            cambiados += 1
        v["contiene"] = quien
        # que piezas trae: cara, ojos, pelo, cuerpo...
        piezas = set()
        for m in mallas:
            bajo = m.lower()
            for pista, nombre in (("face", "cara"), ("eye", "ojos"), ("hair", "pelo"),
                                  ("body", "cuerpo"), ("headwear", "sombrero"),
                                  ("headset", "auricular"), ("gun", "pistola"),
                                  ("weapon", "arma")):
                if pista in bajo:
                    piezas.add(nombre)
        v["piezas"] = sorted(piezas)
        for q in quien:
            e = actores.setdefault(q, {"bundles": 0, "piezas": set()})
            e["bundles"] += 1
            e["piezas"] |= piezas

    resumen = {q: {"bundles": e["bundles"], "piezas": sorted(e["piezas"])}
               for q, e in sorted(actores.items())}
    INDICE.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
    (INDICE.parent / "actores.json").write_text(
        json.dumps(resumen, ensure_ascii=False, indent=1), encoding="utf-8")

    print("   bundles revisados: %d  (corregidos: %d)" % (len(datos), cambiados))
    print("   actores distintos: %d" % len(resumen))
    print()
    print("   los 15 con mas bundles:")
    for q, e in sorted(resumen.items(), key=lambda x: -x[1]["bundles"])[:15]:
        print("      %-18s %3d bundles   piezas: %s" % (q, e["bundles"], ", ".join(e["piezas"])))
    con_cara = [q for q, e in resumen.items() if "cara" in e["piezas"]]
    print()
    print("   actores con cara: %d de %d" % (len(con_cara), len(resumen)))
    print("   ejemplo sin cara:", [q for q, e in resumen.items() if "cara" not in e["piezas"]][:8])


if __name__ == "__main__":
    main()