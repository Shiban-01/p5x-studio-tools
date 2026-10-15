# -*- coding: utf-8 -*-
"""Verifica emparejamientos nuevos de punta a punta: extrae el MP4 con el MISMO
`extraer_video` de la app (wannacri + wav del banco + mux ffmpeg), mira la pista con
ffprobe y mide la PLANITUD ESPECTRAL (ffmpeg aspectralstats) para descartar basura.
Uso: python verificar_ganadores.py stem1 stem2 ..."""
import sys, json, subprocess, statistics, shutil
from pathlib import Path

sys.path.insert(0, r"C:/Users/Lukas/p5x-datamining/p5x_studio")
from p5x_studio import herramientas as H  # noqa: E402

CLIENT = Path(r"C:/Users/Lukas/Downloads/P5X/Client")
SRCS = [CLIENT / "OuterPackage/Media/Windows", CLIENT / "bin/Media/Windows"]
DEST = Path(r"C:/Users/Lukas/p5x-datamining/_dl/_verif_video")
FFPROBE = shutil.which("ffprobe") or "ffprobe"
FFMPEG = shutil.which("ffmpeg") or "ffmpeg"


def ruta_usm(stem):
    for d in SRCS:
        p = d / (stem + ".usm")
        if p.is_file():
            return p
    return None


def ffprobe_audio(mp4):
    r = subprocess.run([FFPROBE, "-v", "error", "-show_entries",
                        "stream=index,codec_type,codec_name,channels,sample_rate,duration",
                        "-of", "json", str(mp4)], capture_output=True, text=True)
    try:
        d = json.loads(r.stdout)
    except Exception:
        return {}
    a = [s for s in d.get("streams", []) if s.get("codec_type") == "audio"]
    return a[0] if a else {}


def planitud(mp4):
    """mediana de la planitud espectral por trama (ffmpeg aspectralstats), ignorando ceros."""
    r = subprocess.run([FFMPEG, "-hide_banner", "-v", "error", "-i", str(mp4),
                        "-af", "aspectralstats=measure=flatness,"
                               "ametadata=print:key=lavfi.aspectralstats.1.flatness:file=-",
                        "-f", "null", "-"], capture_output=True, text=True)
    vals = []
    for ln in r.stdout.splitlines():
        if "flatness=" in ln:
            try:
                v = float(ln.split("=", 1)[1])
                if v > 0:
                    vals.append(v)
            except ValueError:
                pass
    if not vals:
        return None
    return {"mediana": round(statistics.median(vals), 4),
            "media": round(sum(vals) / len(vals), 4),
            "min": round(min(vals), 4), "max": round(max(vals), 4),
            "n": len(vals)}


def main():
    stems = sys.argv[1:]
    DEST.mkdir(parents=True, exist_ok=True)
    for stem in stems:
        u = ruta_usm(stem)
        print("=" * 90)
        if not u:
            print("SIN USM:", stem)
            continue
        salida = DEST / stem
        try:
            mp4 = H.extraer_video(str(u), salida)
        except Exception as e:
            print("ERROR extrayendo", stem, ":", e)
            continue
        a = ffprobe_audio(mp4)
        pl = planitud(mp4)
        print("%s" % stem)
        print("  mp4    : %s (%.2f MB)" % (mp4, mp4.stat().st_size / 1e6))
        print("  ffprobe: codec=%s canales=%s sr=%s dur=%ss" %
              (a.get("codec_name"), a.get("channels"), a.get("sample_rate"), a.get("duration")))
        print("  planitud espectral:", pl, "  ->", ("AUDIO OK" if pl and pl["mediana"] < 0.1
              else ("SOSPECHOSO(ruido?)" if pl and pl["mediana"] > 0.4 else "revisar")))


if __name__ == "__main__":
    main()