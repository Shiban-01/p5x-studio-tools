#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
F3.1c — Parametros de las CinemachineVirtualCamera del evento.

La camara de las cinematicas P5X NO va animada por curvas: va con un rig de Cinemachine
(Transposer + Composer) que SIGUE a los actores. Para reproducirla hay que sacar:
  * CinemachineVirtualCamera: Follow / LookAt (a quien sigue y a quien mira) y prioridad
  * CinemachineTransposer: m_BindingMode, m_FollowOffset, damping
  * CinemachineComposer: m_TrackedObjectOffset, m_ScreenX/Y, FOV
  * CinemachineBasicMultiChannelPerlin: amplitud/frecuencia del temblor

Resuelve los PPtr contra los GameObjects del bundle para dar NOMBRES, no pathIDs.

Uso: python scripts/extract_vcam_params.py <bundle_deofuscado>
"""
import json
import os
import sys

import UnityPy

UnityPy.config.FALLBACK_UNITY_VERSION = "2022.3.49f1"
INTERESAN = ("CinemachineVirtualCamera", "CinemachineTransposer", "CinemachineComposer",
             "CinemachineBasicMultiChannelPerlin", "CinemachinePipeline", "CinemachineBrain",
             "CinemachineStoryboard")


def main():
    ruta = sys.argv[1]
    env = UnityPy.load(ruta)

    # inventario minimo
    gos, scripts, mb_por_pid, tr_por_pid = {}, {}, {}, {}
    for o in env.objects:
        t = o.type.name
        if t == "GameObject":
            try:
                d = o.read()
                gos[o.path_id] = d.m_Name
            except Exception:
                pass
        elif t == "MonoScript":
            try:
                d = o.read_typetree()
                scripts[o.path_id] = d.get("m_ClassName") or d.get("m_Name") or "?"
            except Exception:
                scripts[o.path_id] = "?"
        elif t == "MonoBehaviour":
            mb_por_pid[o.path_id] = o
        elif t == "Transform":
            try:
                d = o.read_typetree()
                tr_por_pid[o.path_id] = {
                    "go": (d.get("m_GameObject") or {}).get("m_PathID"),
                    "pos": d.get("m_LocalPosition"),
                    "rot": d.get("m_LocalRotation"),
                }
            except Exception:
                pass

    def go_de_mb(o):
        try:
            d = o.read_typetree()
        except Exception:
            return None
        return (d.get("m_GameObject") or {}).get("m_PathID")

    def nombre_go(pid):
        return gos.get(pid, f"<go#{pid}>")

    def resolver_pptr(d, clave):
        v = d.get(clave)
        if not isinstance(v, dict):
            return None
        pid = v.get("m_PathID")
        if not pid:
            return None
        return nombre_go(pid) if pid in gos else f"<obj#{pid}>"

    # guion -> lista de MBehaviours
    out = {"vcams": {}, "brain": None, "storyboards": []}
    print(f"═══ {os.path.basename(ruta)} — componentes Cinemachine\n")
    for pid, o in mb_por_pid.items():
        try:
            d = o.read_typetree()
        except Exception:
            continue
        sg = (d.get("m_Script") or {}).get("m_PathID")
        cl = scripts.get(sg, "")
        if cl not in INTERESAN:
            continue
        gpid = (d.get("m_GameObject") or {}).get("m_PathID")
        gnom = nombre_go(gpid)
        tr = tr_por_pid.get(next((k for k, v in tr_por_pid.items() if v["go"] == gpid), None), {})
        campos = {k: v for k, v in d.items()
                  if not k.startswith("m_Object") and k not in ("m_Script", "m_GameObject",
                                                               "m_PrefabInstance", "m_PrefabAsset",
                                                               "m_CorrespondingSourceObject",
                                                               "m_EditorHideFlags", "m_EditorClassIdentifier")}
        print(f"── [{cl}] en '{gnom}'")
        if tr:
            print(f"     local_pos={tr.get('pos')} local_rot={tr.get('rot')}")
        for k, v in campos.items():
            if isinstance(v, dict) and "m_PathID" in v:
                ref = resolver_pptr(d, k)
                print(f"     {k}: -> {ref}")
            elif isinstance(v, list) and v and isinstance(v[0], dict) and "m_PathID" in v[0]:
                print(f"     {k}: {[resolver_pptr({'x': e}, 'x') for e in v]}")
            else:
                s = str(v)
                print(f"     {k}: {s[:90]}")

        registro = {"go": gnom, "transform": tr, "campos": campos}
        if cl == "CinemachineVirtualCamera":
            out["vcams"][gnom] = registro
        elif cl == "CinemachineBrain":
            out["brain"] = registro
        elif cl == "CinemachineStoryboard":
            out["storyboards"].append(registro)
        out.setdefault(cl, []).append(registro)

    salida = os.path.join("_dl", f"vcam_{os.path.basename(ruta).split('.')[0]}.json")
    with open(salida, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False)
    print(f"\nescrito {salida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())