#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
F3 — Sondea bundles buscando el RIG DE CAMARA de las cinemáticas.

Dos cosas que no se pueden ver con grep (los bundles van comprimidos y ofuscados):
  * GameObjects con nombre de camara (CM001/002/003, 主摄像机, VirtualCamera, DollyTrack...)
  * AnimationClips cuyo nombre suene a camara
Tambien lista los TIPOS de componente presentes, para detectar CinemachineBrain,
CinemachineVirtualCamera, CameraShakeControlClip, etc.

Uso:
  python scripts/probe_camera_bundles.py <bundle> [<bundle> ...]
  python scripts/probe_camera_bundles.py --camera-family [n]   # primeros n bundles anim_camera*
"""
import sys
from pathlib import Path

import UnityPy

UnityPy.config.FALLBACK_UNITY_VERSION = "2022.3.49f1"
B = Path("C:/Users/Lukas/Downloads/P5X/Client/OuterPackage/Bundles/Windows")

CAM_TXT = ("cm00", "camera", "摄像", "vcam", "virtualcamera", "dolly", "brain", "cine")


def es_camara(nombre):
    n = nombre.lower()
    return any(t in n for t in CAM_TXT)


def sondear(ruta):
    print(f"\n═══ {Path(ruta).name} ({Path(ruta).stat().st_size / 1e6:.1f} MB)")
    try:
        env = UnityPy.load(str(ruta))
    except Exception as e:
        print(f"  FALLO al cargar: {e}")
        return
    gos, clips, tipos = [], [], {}
    for o in env.objects:
        t = o.type.name
        tipos[t] = tipos.get(t, 0) + 1
        if t == "GameObject":
            try:
                d = o.read()
                nom = d.m_Name
                if "Camera" in tipos or True:
                    comps = [c.type.name for c in d.m_Components] if getattr(d, "m_Components", None) else []
                    gos.append((nom, comps))
            except Exception:
                pass
        elif t == "AnimationClip":
            try:
                nom = o.read().m_Name
                if nom:
                    clips.append(nom)
            except Exception:
                pass

    print(f"  componentes: " + ", ".join(f"{k}={v}" for k, v in sorted(tipos.items(), key=lambda x: -x[1])[:12]))
    cam_gos = [(n, c) for n, c in gos if es_camara(n)]
    print(f"  GameObjects: {len(gos)} ({len(cam_gos)} con nombre de camara)")
    for n, c in cam_gos[:15]:
        print(f"     • {n}   comps={c}")
    if not cam_gos:
        nombres = sorted({n for n, _ in gos})[:12]
        print(f"     (muestra de nombres: {nombres})")
    cam_clips = [c for c in clips if es_camara(c)]
    print(f"  AnimationClips: {len(clips)} ({len(cam_clips)} de camara)")
    for c in cam_clips[:25]:
        print(f"     ▸ {c}")
    if not cam_clips and clips:
        print(f"     (muestra: {sorted(clips)[:10]})")


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 1
    if args[0] == "--camera-family":
        n = int(args[1]) if len(args) > 1 else 4
        for f in sorted(B.rglob("anim_camera*.bundle"))[:n]:
            sondear(f)
        return 0
    for a in args:
        sondear(a)
    return 0


if __name__ == "__main__":
    sys.exit(main())