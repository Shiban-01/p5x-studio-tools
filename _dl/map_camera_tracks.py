#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
F3.1 — Mapea los tracks de un PlayableDirector (.playable) exportado por AssetRipper.

El .playable es un MonoBehaviour con TODOS los sub-tracks serializados en linea como documentos
YAML (`--- !u!114 &<fileID>`), con referencias por fileID local. Aqui se reconstruye:
  * el arbol de tracks (m_Parent / m_Children)
  * el tipo de cada track (m_Script guid -> nombre del .cs, resuelto por los .cs.meta del proyecto)
  * los clips de cada track: nombre del clip, m_Start, m_Duration y el guid/PathID del AnimationClip
    al que apunta (que es lo que hay que ir a buscar en los bundles cuando no se exporto)

Uso:
  python scripts/map_camera_tracks.py <ruta.playable> [--proyecto <raiz del proyecto Unity>]
Escribe JSON en _dl/camera_tracks_<nombre>.json
"""
import json
import os
import re
import sys

RE_DOC = re.compile(r"^--- !u!(\d+) &(\d+)(.*)$", re.M)
RE_SCRIPT = re.compile(r"m_Script: \{fileID: \d+, guid: ([0-9a-f]{32})")
RE_GUID = re.compile(r"guid: ([0-9a-f]{32})")


def guid_a_script(proyecto):
    """guid del .cs.meta -> nombre del script (para saber que tipo de track es)."""
    mapa = {}
    for raiz, _, ficheros in os.walk(os.path.join(proyecto, "Assets", "Scripts")):
        for f in ficheros:
            if f.endswith(".cs.meta"):
                p = os.path.join(raiz, f)
                try:
                    txt = open(p, encoding="utf-8", errors="ignore").read()
                except OSError:
                    continue
                m = re.search(r"guid: ([0-9a-f]{32})", txt)
                if m:
                    mapa[m.group(1)] = f[:-8]  # quitar '.cs.meta'
    return mapa


def parsear(ruta, scripts):
    txt = open(ruta, encoding="utf-8", errors="ignore").read()
    docs = {}
    partes = list(RE_DOC.finditer(txt))
    for i, m in enumerate(partes):
        fid = m.group(2)
        fin = partes[i + 1].start() if i + 1 < len(partes) else len(txt)
        docs[fid] = txt[m.start():fin]

    def campo(bloque, nombre):
        m = re.search(r"^(\s*)%s:[ \t]*(.*)$" % re.escape(nombre), bloque, re.M)
        if not m:
            return None
        sangria, mismo = len(m.group(1)), m.group(2).strip()
        if mismo:
            return mismo
        # valor multilinea: capturar hasta la siguiente clave de la MISMA indentacion o menor
        resto = bloque[m.end():]
        lineas, out = resto.split("\n"), []
        for ln in lineas:
            if not ln.strip():
                continue
            sang = len(ln) - len(ln.lstrip())
            if sang <= sangria and re.match(r"^\s*[A-Za-z_]\w*:", ln):
                break
            out.append(ln)
        return "\n".join(out)

    def fileIDs(texto):
        return re.findall(r"- \{fileID: (\d+)\}", texto or "")

    tracks, clips, raiz = [], [], None
    for fid, bloque in docs.items():
        nombre = campo(bloque, "m_Name") or ""
        sg = RE_SCRIPT.search(bloque)
        tipo = scripts.get(sg.group(1), sg.group(1) if sg else "?") if sg else "?"
        padre = campo(bloque, "m_Parent") or ""
        pm = re.search(r"fileID: (\d+)", padre)
        padre = pm.group(1) if pm else "0"

        # clips del track: cada entrada tiene m_Start, m_Duration y el AnimationClip referenciado
        mics = []
        texto_clips = campo(bloque, "m_Clips") or ""
        for entrada in re.split(r"^\s*-\s+m_Version", texto_clips, flags=re.M)[1:]:
            def sub(clave):
                m = re.search(r"%s:\s*([^\n]+)" % re.escape(clave), entrada)
                return m.group(1).strip() if m else None
            start, dur = sub("m_Start"), sub("m_Duration")
            ref = re.search(r"m_AnimClip: \{fileID: (-?\d+)(?:, guid: ([0-9a-f]{32}))?", entrada)
            nom = re.search(r"m_DisplayName:\s*(.+)", entrada) or re.search(r"m_Name:\s*(.+)", entrada)
            mics.append({
                "clip": (nom.group(1).strip() if nom else None),
                "start": float(start) if start else None,
                "duration": float(dur) if dur else None,
                "animclip_fileID": ref.group(1) if ref else None,
                "animclip_guid": ref.group(2) if ref else None,
            })

        hijos = fileIDs(campo(bloque, "m_Children"))
        proto = re.search(r"m_Prototype: \{fileID: (\d+)(?:, guid: ([0-9a-f]{32}))?", bloque)
        marca = campo(bloque, "m_Markers") or ""

        # el primer documento con m_Tracks es el PlayableDirector (la raiz)
        if "m_Tracks:" in bloque and raiz is None:
            raiz = fid
            tracks_raiz = re.findall(r"- \{fileID: (\d+)\}", campo(bloque, "m_Tracks") or "")
            dir_txt = bloque
        elif "m_Name:" in bloque:
            tracks.append({"fileID": fid, "nombre": nombre, "tipo": tipo, "padre": padre,
                           "hijos": hijos, "clips": mics,
                           "prototipo_guid": proto.group(2) if proto else None,
                           "n_marcadores": len(fileIDs(marca))})

    arquitectura = {"playable": os.path.basename(ruta), "fileID_raiz": raiz,
                    "duracion_s": None, "fps": None, "tracks": tracks}
    if raiz:
        d = re.search(r"m_FixedDuration:\s*([\d.]+)", dir_txt)
        f = re.search(r"m_Framerate:\s*(\d+)", dir_txt)
        arquitectura["duracion_s"] = float(d.group(1)) if d else None
        arquitectura["fps"] = int(f.group(1)) if f else None
        arquitectura["fileIDs_raiz"] = tracks_raiz
    return arquitectura


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    playable = sys.argv[1]
    proyecto = "unity_projects/kotone/ExportedProject"
    if "--proyecto" in sys.argv:
        proyecto = sys.argv[sys.argv.index("--proyecto") + 1]

    scripts = guid_a_script(proyecto)
    arq = parsear(playable, scripts)

    print(f"playable: {arq['playable']}  duracion={arq['duracion_s']}s  fps={arq['fps']}")
    print(f"{len(arq['tracks'])} tracks:\n")
    por_fid = {t["fileID"]: t for t in arq["tracks"]}

    def profundidad(t):
        d, p = 0, t["padre"]
        while p in por_fid and d < 8:
            d += 1
            p = por_fid[p]["padre"]
        return d

    for t in sorted(arq["tracks"], key=lambda x: (profundidad(x), x["nombre"])):
        pad = "  " * profundidad(t)
        sospecha = "  <<< CAMARA?" if re.search(r"cam|cinemachine|cine|摄像", t["tipo"] + t["nombre"], re.I) else ""
        print(f"{pad}- [{t['tipo']}] \"{t['nombre']}\"  fid={t['fileID']} padre={t['padre']} "
              f"hijos={len(t['hijos'])} clips={len(t['clips'])}"
              f"{' marcadores=' + str(t['n_marcadores']) if t['n_marcadores'] else ''}{sospecha}")
        for c in t["clips"]:
            g = c["animclip_guid"] or f"(fileID interno {c['animclip_fileID']})"
            print(f"{pad}    clip \"{c['clip']}\"  t={c['start']}..{(c['start'] or 0) + (c['duration'] or 0):.2f} "
                  f"guid={g}")

    out = os.path.join("_dl", f"camera_tracks_{os.path.basename(playable).split('.')[0]}.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(arq, fh, indent=1, ensure_ascii=False)
    print(f"\nescrito {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
