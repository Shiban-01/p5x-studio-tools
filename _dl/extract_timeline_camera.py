#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
F3 — Extrae el RIG DE CAMARA de un bundle de timeline (ya de-ofuscado).

El bundle trae los objetos reales de camara del evento (CM001/CM002/CM003 + los `cm` que son
las virtual cameras de Cinemachine) y los AnimationClips "Recorded (NN)" que los animan.
Aqui se resuelve:
  1. pathID -> (tipo, nombre, script) de TODO el bundle
  2. los GameObjects de camara: transform (pos/rot/escala), padre, y componentes con sus campos
  3. cada AnimationClip: sample rate, duracion, y las RUTAS que anima (para saber cual mueve la camara)
  4. que clip anima cada objeto de camara

Salida: texto legible + JSON en _dl/camera_rig_<bundle>.json
Uso: python scripts/extract_timeline_camera.py <bundle>
"""
import json
import os
import sys

import UnityPy

UnityPy.config.FALLBACK_UNITY_VERSION = "2022.3.49f1"
CLAVES_CAMARA = ("cm", "camera", "cine")


def es_camara(nombre):
    n = (nombre or "").lower()
    return n.startswith("cm") or "camera" in n or "cam" in n


def main():
    ruta = sys.argv[1]
    env = UnityPy.load(ruta)

    # ---------- 1. inventario: pathID -> tipo/nombre/script ----------
    info, scripts = {}, {}
    for o in env.objects:
        if o.type.name == "MonoScript":
            try:
                d = o.read_typetree()
                scripts[o.path_id] = d.get("m_ClassName") or d.get("m_Name") or "?"
            except Exception:
                scripts[o.path_id] = "?"
    for o in env.objects:
        info[o.path_id] = {"tipo": o.type.name, "obj": o}

    def script_de_mb(o):
        try:
            d = o.read_typetree()
            sg = d.get("m_Script") or {}
            return scripts.get(sg.get("m_PathID"), f"script#{sg.get('m_PathID')}")
        except Exception:
            return "?"

    # ---------- 2. GameObjects y sus componentes ----------
    gos = {}
    for pid, v in info.items():
        if v["tipo"] != "GameObject":
            continue
        try:
            d = v["obj"].read()
        except Exception:
            continue
        comps = []
        for c in getattr(d, "m_Components", []) or []:
            cpid = getattr(c, "m_PathID", None)
            cv = info.get(cpid)
            if not cv:
                continue
            if cv["tipo"] == "MonoBehaviour":
                comps.append(f"{cv['tipo']}:{script_de_mb(cv['obj'])}")
            else:
                comps.append(cv["tipo"])
        gos[pid] = {"nombre": d.m_Name, "comps": comps,
                    "go_pid": getattr(getattr(d, "m_GameObject", None), "m_PathID", None)}

    # ---------- 3. transforms (posicion/rotacion) ----------
    transforms = {}
    for pid, v in info.items():
        if v["tipo"] != "Transform":
            continue
        try:
            d = v["obj"].read_typetree()
        except Exception:
            continue
        transforms[pid] = {
            "go": (d.get("m_GameObject") or {}).get("m_PathID"),
            "padre": (d.get("m_Father") or {}).get("m_PathID"),
            "pos": d.get("m_LocalPosition"), "rot": d.get("m_LocalRotation"),
            "escala": d.get("m_LocalScale"),
        }
    # pathID del GameObject -> transform
    go_a_tr = {t["go"]: t for t in transforms.values() if t.get("go")}

    print(f"═══ {os.path.basename(ruta)}")
    print(f"GameObjects de camara encontrados:")
    cam_rig = {}
    for pid, g in sorted(gos.items(), key=lambda x: x[1]["nombre"]):
        if not es_camara(g["nombre"]):
            continue
        tr = go_a_tr.get(pid, {})
        cam_rig[g["nombre"]] = {"go": pid, "comps": g["comps"], "transform": tr}
        print(f"  • {g['nombre']:<24} pos={tr.get('pos')} rot={tr.get('rot')}")
        print(f"      componentes: {g['comps']}")

    # ---------- 4. AnimationClips: que animan ----------
    clips = []
    for pid, v in info.items():
        if v["tipo"] != "AnimationClip":
            continue
        try:
            d = v["obj"].read_typetree()
        except Exception:
            try:
                d = {"m_Name": v["obj"].read().m_Name}
            except Exception:
                d = {"m_Name": "?"}
        rutas = set()
        for campo in ("m_EditorCurves", "m_FloatCurves", "m_PositionCurves", "m_EulerCurves",
                      "m_RotationCurves"):
            for c in d.get(campo, []) or []:
                p = c.get("path") if isinstance(c, dict) else None
                if p is not None:
                    rutas.add(p)
        clips.append({"name": d.get("m_Name"), "pid": pid,
                      "sample_rate": d.get("m_SampleRate"), "legacy": d.get("m_Legacy"),
                      "n_rutas": len(rutas), "rutas": sorted(rutas)[:40]})

    print(f"\nAnimationClips: {len(clips)}")
    for c in sorted(clips, key=lambda x: str(x["name"])):
        cam = "  <<< ANIMA CAMARA" if any(es_camara(r.strip("/").split("/")[0]) for r in c["rutas"]) else ""
        print(f"  ▸ {c['name']}  sr={c['sample_rate']}  rutas={c['n_rutas']}{cam}")
        for r in c["rutas"][:12]:
            print(f"      {r}")

    out = os.path.join("_dl", f"camera_rig_{os.path.basename(ruta).split('.')[0]}.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump({"gameobjects_camara": {k: {kk: (str(vv) if kk == 'transform' else vv)
                                             for kk, vv in v.items()} for k, v in cam_rig.items()},
                   "clips": clips}, fh, indent=1, ensure_ascii=False)
    print(f"\nescrito {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())