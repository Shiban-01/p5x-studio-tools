#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
F3 — Jerarquia mundial del bundle de timeline + contenido real de los AnimationClips.

Resuelve dos dudas que bloquean el bake de la camara:
  1. donde esta cada objeto de camara en coordenadas MUNDIALES (y si caen dentro del espacio de
     la escena inyectada), resolviendo la cadena de padres.
  2. que llevan dentro los AnimationClips "Recorded (NN)": que campos del typetree traen curvas,
     cuantas, y a que rutas apuntan. (UnityPy a veces no rellena m_FloatCurves: hay que mirar
     los campos crudos y m_CompressedMotion/m_StreamedClip.)

Uso: python scripts/dump_timeline_hierarchy.py <bundle>
"""
import json
import os
import sys

import UnityPy

UnityPy.config.FALLBACK_UNITY_VERSION = "2022.3.49f1"


def quat_a_euler(q):
    import math
    x, y, z, w = q.get("x", 0), q.get("y", 0), q.get("z", 0), q.get("w", 1)
    sinr = 2 * (w * x + y * z); cosr = 1 - 2 * (x * x + y * y)
    roll = math.degrees(math.atan2(sinr, cosr))
    sinp = 2 * (w * y - z * x)
    pitch = math.degrees(math.asin(max(-1, min(1, sinp))))
    siny = 2 * (w * z + x * y); cosy = 1 - 2 * (y * y + z * z)
    yaw = math.degrees(math.atan2(siny, cosy))
    return (round(pitch, 1), round(yaw, 1), round(roll, 1))


def main():
    ruta = sys.argv[1]
    env = UnityPy.load(ruta)

    gos, trs = {}, {}
    for o in env.objects:
        if o.type.name == "GameObject":
            try:
                d = o.read()
                gos[o.path_id] = {"nombre": d.m_Name, "comps": [],
                                  "comps_pid": [getattr(c, "m_PathID", None) for c in (getattr(d, "m_Components", []) or [])]}
            except Exception:
                pass
        elif o.type.name == "Transform":
            try:
                d = o.read_typetree()
                trs[o.path_id] = {"go": (d.get("m_GameObject") or {}).get("m_PathID"),
                                  "padre": (d.get("m_Father") or {}).get("m_PathID"),
                                  "pos": d.get("m_LocalPosition") or {},
                                  "rot": d.get("m_LocalRotation") or {}}
            except Exception:
                pass
    go_a_tr = {t["go"]: t for t in trs.values() if t.get("go")}
    tr_pid_de_go = {}
    for pid, t in trs.items():
        if t.get("go"):
            tr_pid_de_go[t["go"]] = pid

    def mundo(go_pid, prof=0):
        """suma las posiciones locales subiendo por los padres (sin rotar: basta para orientarse)"""
        t = go_a_tr.get(go_pid)
        if not t or prof > 12:
            return {"x": 0, "y": 0, "z": 0}, ""
        p, cadena = t["pos"], []
        padre_go = None
        if t["padre"]:
            padre_tr = trs.get(t["padre"]) or {}
            padre_go = padre_tr.get("go")
        if padre_go:
            ps, pcadena = mundo(padre_go, prof + 1)
            p = {"x": p.get("x", 0) + ps["x"], "y": p.get("y", 0) + ps["y"], "z": p.get("z", 0) + ps["z"]}
            cadena = pcadena
        nom = gos.get(padre_go, {}).get("nombre") if padre_go else None
        if nom:
            cadena = cadena + [nom]
        return p, cadena

    print(f"═══ {os.path.basename(ruta)} — jerarquia (34 objetos)")
    for pid, g in sorted(gos.items(), key=lambda x: x[1]["nombre"]):
        p, cadena = mundo(pid)
        padre_go = None
        t = go_a_tr.get(pid)
        if t and t["padre"]:
            padre_go = (trs.get(t["padre"]) or {}).get("go")
        pnom = gos.get(padre_go, {}).get("nombre", "—")
        print(f"  • {g['nombre']:<30} padre={pnom:<26} mundo=({p['x']:.2f}, {p['y']:.2f}, {p['z']:.2f})")

    print("\n── AnimationClips: contenido crudo")
    for o in env.objects:
        if o.type.name != "AnimationClip":
            continue
        try:
            d = o.read_typetree()
        except Exception as e:
            print(f"  ▸ typetree FALLO: {e}")
            continue
        resumen = {}
        for k, v in d.items():
            if isinstance(v, list):
                if v:
                    resumen[k] = f"{len(v)} elementos"
            elif k in ("m_Name", "m_SampleRate", "m_Legacy", "m_AnimationType", "m_WrapMode",
                       "m_Compressed", "m_UseHighQualityCurve", "m_StreamedClip"):
                resumen[k] = v
        print(f"  ▸ {d.get('m_Name')}: {json.dumps(resumen, ensure_ascii=False)[:400]}")
        # rutas: probar todos los campos de curvas conocidos
        rutas = []
        for campo in ("m_EditorCurves", "m_FloatCurves", "m_PositionCurves", "m_EulerCurves",
                      "m_RotationCurves", "m_ScaleCurves", "m_PPtrCurves"):
            cur = d.get(campo) or []
            for c in cur:
                if isinstance(c, dict):
                    at = c.get("attribute")
                    pa = c.get("path")
                    rutas.append((campo, pa, at))
        if rutas:
            print(f"      curvas con ruta: {len(rutas)}; primeras:")
            for campo, pa, at in rutas[:10]:
                print(f"        {campo} path='{pa}' attr={at}")
        else:
            print("      SIN curvas legibles por ruta (probablemente comprimidas/streamed)")

    out = os.path.join("_dl", f"hierarchy_{os.path.basename(ruta).split('.')[0]}.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump({str(pid): {"nombre": g["nombre"], "mundo": mundo(pid)[0]} for pid, g in gos.items()},
                  fh, indent=1, ensure_ascii=False)
    print(f"\nescrito {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())