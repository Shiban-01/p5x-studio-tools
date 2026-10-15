# -*- coding: utf-8 -*-
"""ffprobe de cada pista de audio de un MP4 + planitud espectral FFT (numpy).
Uso: python verificar_pistas.py <mp4> [<mp4> ...]"""
import sys, os, json, subprocess, wave
import numpy as np

FFPROBE = "ffprobe"
FFMPEG = "ffmpeg"


def ffprobe(path):
    r = subprocess.run([FFPROBE, "-v", "error", "-show_streams", "-show_format",
                        "-of", "json", path], capture_output=True, text=True)
    return json.loads(r.stdout)


def extrae_pista(path, idx, dst):
    subprocess.run([FFMPEG, "-v", "error", "-y", "-i", path, "-map", "0:a:%d" % idx,
                    "-ac", "1", "-ar", "48000", "-c:a", "pcm_s16le", dst],
                   capture_output=True, text=True)


def planitud(wav):
    with wave.open(wav, "rb") as w:
        sr = w.getframerate()
        n = w.getnframes()
        a = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float64)
    ps = []
    for i in range(0, len(a) - 4096, 4096):
        seg = a[i:i + 4096] * np.hanning(4096)
        P = np.abs(np.fft.rfft(seg)) ** 2 + 1e-12
        ps.append(float(np.exp(np.mean(np.log(P))) / np.mean(P)))
    return (float(np.mean(ps)) if ps else 0.0), n / sr


def main():
    for path in sys.argv[1:]:
        print("=" * 78)
        print(path)
        info = ffprobe(path)
        streams = [s for s in info.get("streams", []) if s.get("codec_type") == "audio"]
        print("  pistas de audio: %d   (duracion contenedor %ss)" %
              (len(streams), info.get("format", {}).get("duration")))
        for k, s in enumerate(streams):
            tags = s.get("tags", {})
            dur = s.get("duration") or info.get("format", {}).get("duration")
            tmp = os.path.join(os.environ.get("TMPDIR", "."), "_vp_%d.wav" % k)
            extrae_pista(path, k, tmp)
            fl, adur = planitud(tmp)
            try:
                os.remove(tmp)
            except OSError:
                pass
            print("    [%d] codec=%s sr=%s ch=%s lang=%-4s name=%-16s dur=%ss  planitudFFT=%.4f" %
                  (k, s.get("codec_name"), s.get("sample_rate"), s.get("channels"),
                   tags.get("language", "?"), tags.get("handler_name", tags.get("title", "?")),
                   (dur or "?")[:7], fl))


if __name__ == "__main__":
    main()
