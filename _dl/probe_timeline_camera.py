#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
F3 — Radiografia del bundle de un timeline: quien es quien.

Resuelve, sobre el bundle YA DE-OFUSCADO:
  * MonoScript PathID -> nombre de clase (para identificar componentes)
  * jerarquia de GameObjects (nombre + padre + componentes)
  * los m_SceneBindings del PlayableDirector: a que objeto REAL esta bindeado cada track
    (esto es lo que el export a Unity perdio: en el bundle las referencias son PPtr resueltas)
  * los campos de los MonoBehaviour de camara (CinemachineVirtualCamera / Brain / Shake)

Uso: python scripts/probe_timeline_camera.py <bundle_deofuscado>
"""
import collections
import sys
import UnityPy

UnityPy.config.FALLBACK_UNITY_VERSION = "2022.3.49f1"


def nombre_script(obj, cache):
    """PathID del MonoScript -> nombre de clase."""
    try:
        d = obj.read()
    except Exception:
        return "?"
    return getattr(d, "m_ClassName", None) or getattr(d, "m_Name", "?")


def main():
    ruta = sys.argv[1]
    env = UnityPy.load(ruta)

    # --- MonoScripts: pathID -> clase
    scripts = {}
    for o in env.objects:
        if o.type.name == "MonoScript":
            try:
                scripts[o.path_id] = o.read().m_ClassName or o.read().m_Name
            except Exception:
                scripts[o.path_id] = "?"

    def clase_de(mb):
        try:
            sg = mb.m_Script
            pid = sg.m_PathID if hasattr(sg, "m_PathID") else None
        except Exception:
            pid = None
        return scripts.get(pid, f"script#{pid}")

    # --- GameObjects y sus componentes
    gos = {}
    for o in env.objects:
        if o.type.name == "GameObject":
            try:
                d = o.read()
            except Exception:
                continue
            comps = []
            for c in getattr(d, "m_Components", []) or []:
                pid = getattr(c, "m_PathID", None)
                # el tipo real lo buscamos luego
                comps.append(pid)
            gos[o.path_id] = {"nombre": d.m_Name, "comps_pid": comps,
                              "go_pid": getattr(d.m_GameObject, "m_PathID", 0) if hasattr(d, "m_GameObject") else 0}

    # mapa pathID -> tipo/nombre de componente
    por_pid = {}
    for o in env.objects:
        t = o.type.name
        if t == "MonoBehaviour":
            por_pid[o.path_id] = f"MB:{clase_de(o)}"
        else:
            por_pid[o.path_id] = t

    print(f"═══ {ruta}")
    print(f"GameObjects: {len(gos)}")
    for pid, g in sorted(gos.items(), key=lambda x: x[1]["nombre"]):
        comps = [por_pid.get(p, str(p)) for p in g["comps_pid"]]
        cam = "  <<< CAMARA" if any(("camera" in c.lower() or "cine" in c.lower()) for c in comps) else ""
        print(f"  • {g['nombre']:<42} {comps}{cam}")

    # --- PlayableDirector y sus bindings
    for o in env.objects:
        if o.type.name != "PlayableDirector":
            continue
        print("\n── PlayableDirector")
        try:
            d = o.read_typetree()
        except Exception as e:
            print(f"  no se pudo leer el typetree: {e}")
            continue
        for k in ("m_Duration", "m_InitialTime", "m_SceneBindings", "m_ExposedReferences"):
            if k in d:
                print(f"  {k}: {d[k]}")
        pa = d.get("m_PlayableAsset", {})
        print(f"  m_PlayableAsset: {pa}")

    # --- componentes de camara con sus campos
    for o in env.objects:
        if o.type.name != "MonoBehaviour":
            continue
        cl = clase_de(o)
        if not any(t in cl.lower() for t in ("virtualcamera", "brain", "shake", "camera")):
            continue
        print(f"\n── MonoBehaviour [{cl}] pid={o.path_id}")
        try:
            tt = o.read_typetree()
            for k, v in list(tt.items())[:40]:
                s = str(v)
                print(f"   {k}: {s[:110]}")
        except Exception as e:
            print(f"   (typetree no disponible: {str(e)[:70]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())