#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Genera el guion del timeline como datos para Unity + los eventos de audio para ffmpeg.

Lee los .asset de Assets/MonoBehaviour/ (tracks del PlayableDirector exportado), resuelve
cada clip -> AnimationPlayableAsset -> AnimationClip real, y agrupa por actor usando el
prefijo del nombre del clip (`PC079_01@stand_story` -> actor `PC079_01`).

Salidas:
  unity_projects/kotone/ExportedProject/Assets/Editor/P5XTimelineData.cs   (tabla para Unity)
  _dl/audio_events.json                                                    (BGM y SFX con tiempos)
  _dl/guion.txt                                                            (lectura humana)
"""
import os, re, json, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJ = os.path.join(ROOT, "unity_projects", "kotone", "ExportedProject", "Assets")
MB = os.path.join(PROJ, "MonoBehaviour")

# tracks que NO son de actor (cámara, audio, UI, props, sub-playable anidado)
EXCLUIR = ("主摄像机", "持续震动", "音频", "UI", "Activation", "虚拟挂载", "自动跳播",
           "Animation Track", "轨迹动画", "Prefab", "分组", "Group")
# el sub-playable anidado (5,58 s) es otro director: se detecta por duración
DUR_ANIDADO = 5.583333333333333


def index_guids():
    """guid -> ruta de fichero (sin el .meta)."""
    g = {}
    for root, dirs, files in os.walk(PROJ):
        for f in files:
            if not f.endswith(".meta"):
                continue
            p = os.path.join(root, f)
            try:
                t = open(p, encoding="utf-8", errors="ignore").read(400)
            except Exception:
                continue
            m = re.search(r"guid:\s*([0-9a-f]{32})", t)
            if m:
                g[m.group(1)] = os.path.join(root, f[:-5])
    return g


def parse_tracks(mb_dir, guid2path):
    """Devuelve [{file, track, clips:[{disp,start,dur,clipin,blendin,blendout,clip_path}]}]"""
    out = []
    for f in sorted(os.listdir(mb_dir)):
        if not f.endswith(".asset"):
            continue
        p = os.path.join(mb_dir, f)
        t = open(p, encoding="utf-8", errors="ignore").read()
        nom = re.search(r"m_Name:\s*(.+)", t)
        track = nom.group(1).strip() if nom else f
        if "m_Clips:" not in t:
            continue
        if any(x in track for x in EXCLUIR):
            continue
        sec = t.split("m_Clips:", 1)[1]
        clips = []
        for blk in re.split(r"\n  - m_Version:", sec)[1:]:
            def g(k):
                m = re.search(rf"{k}:\s*([-\d.e+]+)", blk)
                return float(m.group(1)) if m else 0.0
            guid = re.search(r"m_Asset:\s*\{fileID:\s*\d+,\s*guid:\s*([0-9a-f]{32})", blk)
            disp = re.search(r"m_DisplayName:\s*(.*)", blk)
            ruta = guid2path.get(guid.group(1)) if guid else None
            # envoltorio AnimationPlayableAsset -> clip de animación real
            clip_path = ruta
            if ruta and os.path.basename(ruta).startswith("AnimationPlayableAsset"):
                tt = open(ruta, encoding="utf-8", errors="ignore").read()
                m2 = re.search(r"m_Clip:\s*\{fileID:\s*\d+,\s*guid:\s*([0-9a-f]{32})", tt)
                if m2:
                    clip_path = guid2path.get(m2.group(1))
            clips.append(dict(disp=(disp.group(1).strip().strip("'") if disp else ""),
                              start=g("m_Start"), dur=g("m_Duration"), clipin=g("m_ClipIn"),
                              blendin=g("m_BlendInDuration"), blendout=g("m_BlendOutDuration"),
                              env=ruta, clip=clip_path))
        if clips:
            out.append(dict(file=f, track=track, clips=clips))
    return out


def nombre_clip(path):
    return os.path.splitext(os.path.basename(path))[0] if path else ""


def actor_de(clip_name):
    """`PC079_01@stand_story` -> PC079_01"""
    return clip_name.split("@", 1)[0] if "@" in clip_name else ""


def main():
    g2p = index_guids()
    tracks = parse_tracks(MB, g2p)

    print("=== tracks de actor ===")
    actor_clips = []   # (actor, clip, start, dur, clipin, blendin, blendout, fichero_track)
    for tr in tracks:
        for c in tr["clips"]:
            nm = nombre_clip(c["clip"])
            act = actor_de(nm)
            if not act:
                continue
            if abs(c["dur"] - DUR_ANIDADO) < 0.01:
                continue                      # sub-playable anidado
            actor_clips.append(dict(actor=act, clip=nm, start=c["start"], dur=c["dur"],
                                    clipin=c["clipin"], blendin=c["blendin"],
                                    blendout=c["blendout"], env=c["env"], track=tr["track"]))
    actor_clips.sort(key=lambda c: (c["actor"], c["start"]))

    actores = sorted(set(c["actor"] for c in actor_clips))
    for a in actores:
        cs = [c for c in actor_clips if c["actor"] == a]
        print(f"\n## {a}: {len(cs)} clips, hasta t={max(c['start']+c['dur'] for c in cs):.2f}s")
        for c in cs:
            print(f"   t={c['start']:7.3f} dur={c['dur']:6.2f} clipIn={c['clipin']:6.2f} "
                  f"blendIn={c['blendin']:6.2f} blendOut={c['blendout']:6.2f}  {c['clip']}")

    # ---- C# para Unity ----
    lineas = []
    for c in actor_clips:
        clip_cs = c["clip"].replace('"', '')
        lineas.append(f'        new Track {{ actor = "{c["actor"]}", clip = "{clip_cs}", '
                      f'start = {c["start"]:.4f}f, dur = {c["dur"]:.4f}f, clipIn = {c["clipin"]:.4f}f, '
                      f'blendIn = {max(c["blendin"], 0.0):.4f}f, blendOut = {max(c["blendout"], 0.0):.4f}f }},')
    fin = max(c["start"] + c["dur"] for c in actor_clips)
    cs_src = (
        "// GENERADO por scripts/build_timeline_script.py — NO editar a mano.\n"
        "// Guion real del timeline TL_P3P_Event_side_prologue_04_04 (tracks 角色动画 / 角色动画_0).\n"
        "using UnityEngine;\n\n"
        "public static class P5XTimelineData\n{\n"
        "    public struct Track\n    {\n"
        "        public string actor;\n        public string clip;\n"
        "        public float start;     // segundo del timeline en que arranca el clip\n"
        "        public float dur;       // duración dentro del timeline\n"
        "        public float clipIn;    // segundo del clip por el que entra\n"
        "        public float blendIn;   // mezcla de entrada (s); <0 = ninguna\n"
        "        public float blendOut;  // mezcla de salida (s); <0 = ninguna\n"
        "    }\n\n"
        f"    public const float Duracion = {fin:.4f}f;\n\n"
        "    public static readonly Track[] Clips =\n    {\n"
        + "\n".join(lineas) + "\n    };\n\n"
        "    /// Estado de un actor en el segundo t: clip vigente y tiempo dentro del clip.\n"
        "    /// Reproduce la extrapolacion de Timeline: si el clip ya acabo pero el siguiente aun no\n"
        "    /// ha empezado (hay huecos de hasta 0,73 s en este guion), se MANTIENE su pose final.\n"
        "    public static bool Activo(string actor, float t, out Track track, out float tiempoDeClip)\n"
        "    {\n"
        "        track = default; tiempoDeClip = 0f;\n"
        "        bool hay = false;\n"
        "        for (int i = 0; i < Clips.Length; i++)\n"
        "        {\n"
        "            var c = Clips[i];\n"
        "            if (c.actor != actor || t < c.start) continue;\n"
        "            if (!hay || c.start > track.start) { track = c; hay = true; }\n"
        "        }\n"
        "        if (!hay) return false;\n"
        "        float dentro = t - track.start;\n"
        "        if (dentro > track.dur) dentro = track.dur;\n"
        "        tiempoDeClip = track.clipIn + dentro;\n"
        "        return true;\n"
        "    }\n\n"
        "    /// Actores distintos que aparecen en el guion.\n"
        "    public static string[] Actores()\n    {\n"
        "        var lista = new System.Collections.Generic.List<string>();\n"
        "        foreach (var c in Clips) if (!lista.Contains(c.actor)) lista.Add(c.actor);\n"
        "        return lista.ToArray();\n    }\n"
        "}\n")
    dst = os.path.join(PROJ, "Editor", "P5XTimelineData.cs")
    open(dst, "w", encoding="utf-8").write(cs_src)
    print(f"\n-> {dst}  ({len(cs_src)} bytes, {len(actor_clips)} clips, duracion {fin:.2f}s)")

    # ---- eventos de audio ----
    audio = []
    for tr in parse_tracks(MB, g2p):
        for c in tr["clips"]:
            nm = c["disp"]
            marca = "BGM " if "BGM" in nm else ("SFX " if "SFX" in nm or "Foley" in nm else "?? ")
            audio.append(dict(track=tr["track"], t=c["start"], dur=c["dur"], nombre=nm, tipo=marca.strip()))
    # los tracks de audio se excluyeron del parse de actores: los releo sin filtro
    audio = []
    for f in sorted(os.listdir(MB)):
        if not f.endswith(".asset") or not f.startswith("音频"):
            continue
        t = open(os.path.join(MB, f), encoding="utf-8", errors="ignore").read()
        if "m_Clips:" not in t:
            continue
        sec = t.split("m_Clips:", 1)[1]
        for blk in re.split(r"\n  - m_Version:", sec)[1:]:
            def g(k):
                m = re.search(rf"{k}:\s*([-\d.e+]+)", blk)
                return float(m.group(1)) if m else 0.0
            disp = re.search(r"m_DisplayName:\s*(.*)", blk)
            guid = re.search(r"m_Asset:\s*\{fileID:\s*\d+,\s*guid:\s*([0-9a-f]{32})", blk)
            ruta = g2p.get(guid.group(1)) if guid else None
            txt = open(ruta, encoding="utf-8", errors="ignore").read() if ruta else ""
            nom = re.search(r"m_Name:\s*(.+)", txt)
            audio.append(dict(fichero=f, t=g("m_Start"), dur=g("m_Duration"),
                              disp=(disp.group(1).strip().strip("'") if disp else ""),
                              asset=(nom.group(1).strip() if nom else os.path.basename(ruta or "")),
                              ruta=ruta, loop=("(循环)" in (disp.group(1) if disp else ""))))
    audio.sort(key=lambda a: a["t"])
    json.dump(audio, open(os.path.join(ROOT, "_dl", "audio_events.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("\n=== eventos de audio ===")
    for a in audio:
        print(f"   t={a['t']:7.3f} dur={a['dur']:6.2f} {'LOOP' if a['loop'] else '    '} "
              f"{a['disp'][:34]:34} -> {a['asset'][:52]}")

    # ---- guion legible ----
    with open(os.path.join(ROOT, "_dl", "guion.txt"), "w", encoding="utf-8") as fh:
        for a in actores:
            fh.write(f"\n## {a}\n")
            for c in [x for x in actor_clips if x["actor"] == a]:
                fh.write(f"  t={c['start']:7.3f} dur={c['dur']:6.2f} clipIn={c['clipin']:6.2f}  {c['clip']}\n")
    print(f"\n-> {os.path.join(ROOT, '_dl', 'audio_events.json')}")
    print(f"-> {os.path.join(ROOT, '_dl', 'guion.txt')}")


if __name__ == "__main__":
    main()