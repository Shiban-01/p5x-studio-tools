#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Monta el MP4 final: frames PNG + BGM y SFX del timeline en su segundo exacto.

Los tiempos y nombres salen de _dl/audio_events.json (generado por
build_timeline_script.py leyendo los tracks 音频* del propio PlayableDirector),
y los WAV de media/soundtrack_wav (BGM) y media/sfx_wav (SFX, ver extract_sfx.py).

Uso:
  python mux_audio.py <carpeta_frames> <salida.mp4> [--sin-audio]
"""
import json, subprocess, sys, glob
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FPS = 30
DUR = 52.77                      # duracion del timeline (P5XTimelineData.Duracion)
BGM = ROOT / "media" / "soundtrack_wav" / "BGM_P3R_TheVoiceSomeoneCalls" / "BGM_P3R_TheVoiceSomeoneCalls_000.wav"
SFX_DIR = ROOT / "media" / "sfx_wav"
EVENTOS = ROOT / "_dl" / "audio_events.json"


def busca_sfx(nombre):
    """WAV mas parecido al nombre del cue (substring, sin extension)."""
    if not nombre or not SFX_DIR.exists():
        return None
    clave = nombre.lower()
    wavs = sorted(glob.glob(str(SFX_DIR / "*.wav")))
    exacto = [w for w in wavs if Path(w).stem.lower() == clave]
    if exacto:
        return exacto[0]
    parecidos = [w for w in wavs if clave in Path(w).stem.lower() or Path(w).stem.lower() in clave]
    return parecidos[0] if parecidos else None


def main():
    frames = sys.argv[1] if len(sys.argv) > 1 else "media/cinematics_capture/scene_p3p_kotone_bg"
    salida = sys.argv[2] if len(sys.argv) > 2 else "media/p5x_kotone_timeline.mp4"
    sin_audio = "--sin-audio" in sys.argv
    fdir = (ROOT / frames) if not Path(frames).is_absolute() else Path(frames)
    n = len(glob.glob(str(fdir / "*.png")))
    if n == 0:
        print(f"[!] no hay PNG en {fdir}")
        return 1
    print(f"frames: {n} ({n / FPS:.2f}s a {FPS}fps)")

    entradas = ["-framerate", str(FPS), "-i", str(fdir / "f_%03d.png")]
    filtros, etiquetas = [], []
    if not sin_audio:
        # BGM: recortado a la duracion del timeline y con fundido de salida
        if BGM.exists():
            entradas += ["-i", str(BGM)]
            filtros.append(f"[1:a]atrim=0:{DUR},asetpts=N/SR/TB,afade=t=out:st={DUR - 2:.2f}:d=2,"
                           f"volume=0.85[bgm]")
            etiquetas.append("[bgm]")
            print(f"BGM: {BGM.name} (recorte {DUR:.2f}s + fade)")
        else:
            print(f"[!] BGM no encontrado: {BGM}")
        # SFX en su segundo exacto
        ev = json.loads(EVENTOS.read_text(encoding="utf-8")) if EVENTOS.exists() else []
        idx = 2 if BGM.exists() else 1
        puestos = 0
        for e in ev:
            if "BGM" in e.get("disp", "") or e.get("loop"):
                continue
            w = busca_sfx(e.get("disp") or e.get("asset", ""))
            if not w:
                print(f"  [sfx sin wav] t={e['t']:6.2f}  {e.get('disp', '')[:44]}")
                continue
            entradas += ["-i", w]
            ms = int(round(e["t"] * 1000))
            filtros.append(f"[{idx}:a]adelay={ms}|{ms},volume=0.9[sfx{puestos}]")
            etiquetas.append(f"[sfx{puestos}]")
            print(f"  sfx t={e['t']:6.2f}  {Path(w).name}  ({Path(w).stat().st_size // 1024} KB)")
            idx += 1
            puestos += 1
        if puestos:
            filtros.append(f"{''.join(etiquetas)}amix=inputs={len(etiquetas)}:duration=longest:"
                           f"normalize=0,alimiter=limit=0.95[aout]")

    cmd = ["ffmpeg", "-y", *entradas]
    if filtros:
        cmd += ["-filter_complex", ";".join(filtros), "-map", "0:v", "-map", "[aout]"]
    cmd += ["-c:v", "libx264", "-crf", "17", "-pix_fmt", "yuv420p", "-r", str(FPS)]
    if filtros:
        cmd += ["-c:a", "aac", "-b:a", "192k"]
    cmd += ["-t", f"{min(DUR, n / FPS):.3f}", str(ROOT / salida if not Path(salida).is_absolute() else salida)]

    print("\n--- ffmpeg ---")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("[!] ffmpeg fallo:\n", r.stderr[-2500:])
        return 1
    out = ROOT / salida if not Path(salida).is_absolute() else Path(salida)
    print(f"OK -> {out}  ({out.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())