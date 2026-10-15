#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
F3.1b — Extrae las CURVAS DE CAMARA de los clips `Recorded*.anim` exportados.

Los clips de camara van en tracks AnimationTrack en modo "infinite clip" (m_InfiniteClip):
un unico clip continuo por rig, con curvas de POSICION (m_PositionCurves) y EULER
(m_EulerCurves) y `path:` vacio (animan al propio objeto bindeado).

Salida: _dl/camera_curves.json  con, por clip: duracion, fps, y las listas de keyframes
(t, x, y, z) de posicion y rotacion. Ademas imprime un resumen legible.

Uso: python scripts/extract_camera_curves.py [dir_de_clips]
"""
import glob
import json
import os
import re
import sys

POR_DEFECTO = "unity_projects/kotone/ExportedProject/Assets/AnimationClip"
RE_KEY = re.compile(r"time:\s*(-?[\d.eE+-]+)\s*\n\s*value:\s*\{x:\s*(-?[\d.eE+inf-]+),\s*y:\s*(-?[\d.eE+inf-]+),\s*z:\s*(-?[\d.eE+inf-]+)\}")


def bloque(txt, clave):
    """texto del bloque multilinea de una clave de primer nivel (2 espacios)."""
    m = re.search(r"^  %s:\s*$" % re.escape(clave), txt, re.M)
    if not m:
        return ""
    resto = txt[m.end():]
    out = []
    for ln in resto.split("\n"):
        if re.match(r"^  [A-Za-z_]\w*:", ln):   # siguiente clave del mismo nivel
            break
        out.append(ln)
    return "\n".join(out)


def curvas(bloque_txt):
    return [(float(t), float(x), float(y), float(z)) for t, x, y, z in RE_KEY.findall(bloque_txt)]


def main():
    d = sys.argv[1] if len(sys.argv) > 1 else POR_DEFECTO
    datos = {}
    for f in sorted(glob.glob(os.path.join(d, "Recorded*.anim"))):
        txt = open(f, encoding="utf-8", errors="ignore").read()
        if "\n" not in txt:
            continue
        if "m_PositionCurves" not in txt and "m_EulerCurves" not in txt:
            continue
        pos = curvas(bloque(txt, "m_PositionCurves"))
        eul = curvas(bloque(txt, "m_EulerCurves"))
        sr = re.search(r"m_SampleRate:\s*([\d.]+)", txt)
        nom = re.search(r"m_Name:\s*(.+)", txt).group(1).strip()
        if not pos and not eul:
            continue
        datos[nom] = {"fichero": os.path.basename(f),
                      "sample_rate": float(sr.group(1)) if sr else None,
                      "posicion": pos, "euler": eul}

    print(f"clips de camara con curvas: {len(datos)}\n")
    for nom, c in sorted(datos.items()):
        def rango(k):
            v = c[k]
            if not v:
                return "—"
            tmin, tmax = v[0][0], v[-1][0]
            cambia = len({(round(x, 3), round(y, 3), round(z, 3)) for _, x, y, z in v})
            return f"t={tmin:.2f}..{tmax:.2f}s  {len(v)} keys  valores_distintos={cambia}"
        print(f"▸ {nom}  (fps {c['sample_rate']})")
        print(f"    posicion: {rango('posicion')}")
        print(f"    euler   : {rango('euler')}")
        for etiqueta, k in (("pos", "posicion"), ("rot", "euler")):
            v = c[k]
            if not v:
                continue
            muestra = v if len(v) <= 8 else v[:4] + v[-2:]
            for t, x, y, z in muestra:
                print(f"      {etiqueta} t={t:7.2f}  ({x:9.3f}, {y:9.3f}, {z:9.3f})")
    out = "_dl/camera_curves.json"
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(datos, fh, indent=1)
    print(f"\nescrito {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())