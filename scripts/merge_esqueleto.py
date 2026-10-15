"""Fusiona los esqueletos de todas las piezas de Kotone en uno solo, por NOMBRE de hueso.

El aviso de la guía de la comunidad es que a veces un hueso sale desalineado (sobre todo en la
cara). Aqui se comparan las posiciones/rotaciones que trae cada pieza para el MISMO hueso: si dos
piezas no coinciden, se avisa (esos son los candidatos a estar torcidos) y se queda el valor de
la pieza principal (cuerpo > cara > pelo > armas).

Salida: _dl/esqueleto_completo.json  { "huesos": {nombre: {padre, pos, rot, esc, origen}},
                                       "conflictos": [...], "piezas": {...} }
"""
import json
import os

RAIZ = r"C:\Users\Lukas\p5x-datamining"
DUMP = os.path.join(RAIZ, "_dl", "kotone_dump")
SAL = os.path.join(RAIZ, "_dl", "esqueleto_completo.json")

# orden de preferencia: la pieza principal manda
PREFERENCIA = [
    "PC079_01_body_wholeexport_rig_PC079_01_body",
    "PC079_01_face_wholeexport_rig_bs_PC079_01_face",
    "PC079_01_face_wholeexport_rig_bs_PC079_01_eye",
    "PC079_01_face_wholeexport_rig_bs_PC079_01_eyelid",
    "PC079_01_hair_wholeexport_rig_PC079_01_hair",
    "PC079_01_gun_02_wholeexport_rig_wq_makpon_gun_02",
    "PC079_01_body_wholeexport_rig_PC079_01_qiang",
    "PC079_01_body_wholeexport_rig_PC079_01_qiangtao",
    "PC079_01_body_wholeexport_rig_PC079_01_xiuzhang",
]


def main():
    piezas = []
    for f in sorted(os.listdir(DUMP)):
        if f.endswith(".json") and f != "resumen.json":
            piezas.append(f[:-5])
    orden = [p for p in PREFERENCIA if p in piezas] + [p for p in piezas if p not in PREFERENCIA]

    huesos = {}       # nombre -> datos
    origen = {}       # nombre -> pieza que lo aporto
    conflictos = []
    por_pieza = {}

    for p in orden:
        meta = json.load(open(os.path.join(DUMP, p + ".json"), encoding="utf-8"))
        lista = meta["lista_huesos"]
        nombres = [h.get("nombre") for h in lista]
        n_validos = 0
        for i, h in enumerate(lista):
            nom = h.get("nombre")
            if not nom:
                continue
            n_validos += 1
            pa = h.get("padre", -1)
            padre_nom = nombres[pa] if (pa is not None and 0 <= pa < len(nombres)) else None
            dato = {"padre": padre_nom, "pos": h["pos"], "rot": h["rot"], "esc": h["esc"]}
            if nom in huesos:
                prev = huesos[nom]
                dpos = max(abs(a - b) for a, b in zip(prev["pos"], dato["pos"]))
                dmax = max(abs(a - b) for a, b in zip(prev["rot"], dato["rot"]))
                if dpos > 1e-4 or dmax > 1e-4:
                    conflictos.append({
                        "hueso": nom, "pieza_ok": origen[nom], "pieza_dudosa": p,
                        "dif_pos_max": round(dpos, 6), "dif_rot_max": round(dmax, 6)})
            else:
                huesos[nom] = dato
                origen[nom] = p
        por_pieza[p] = {"huesos": len(lista), "con_nombre": n_validos,
                        "vacios": len(lista) - n_validos}

    # orden estable: padres antes que hijos (recorrido del arbol)
    hijos = {}
    for nom, d in huesos.items():
        hijos.setdefault(d["padre"], []).append(nom)
    secuencia = []

    def rec(padre, prof):
        for nom in sorted(hijos.get(padre, [])):
            secuencia.append(nom)
            rec(nom, prof + 1)

    rec(None, 0)
    for nom in sorted(huesos):
        if nom not in secuencia:
            secuencia.append(nom)

    salida = {
        "total": len(huesos),
        "piezas": por_pieza,
        "orden": secuencia,
        "huesos": {n: dict(huesos[n], origen=origen[n]) for n in secuencia},
        "conflictos": conflictos,
        "nota": "pos/rot/esc locales respecto al padre; rot en cuaternion (x,y,z,w). "
                "Los 'conflictos' son huesos donde dos piezas del juego no coinciden: candidatos "
                "a estar desalineados; aqui se conserva el valor de la pieza principal.",
    }
    json.dump(salida, open(SAL, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # version para Unity: JsonUtility no entiende diccionarios -> array de huesos
    para_unity = {"huesos": [dict(huesos[n], nombre=n) for n in secuencia]}
    SAL2 = os.path.join(RAIZ, "_dl", "esqueleto_unity.json")
    json.dump(para_unity, open(SAL2, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"escrito (Unity): {SAL2}")

    print(f"huesos unicos: {len(huesos)}   (orden jefe->hijos)")
    print(f"conflictos entre piezas: {len(conflictos)}")
    for c in conflictos[:25]:
        print(f"   {c['hueso']:28s} {c['pieza_ok'][:28]:28s} vs {c['pieza_dudosa'][:28]:28s}  "
              f"pos {c['dif_pos_max']:.5f}  rot {c['dif_rot_max']:.5f}")
    print("\npor pieza:")
    for p, d in por_pieza.items():
        print(f"   {p[:52]:52s} huesos {d['huesos']:3d}  con nombre {d['con_nombre']:3d}  sin nombre {d['vacios']}")
    print(f"\nescrito: {SAL}")
    # raices
    raices = [n for n in secuencia if huesos[n]["padre"] is None]
    print(f"raices: {raices}")


if __name__ == "__main__":
    main()