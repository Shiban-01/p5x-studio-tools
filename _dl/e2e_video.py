# -*- coding: utf-8 -*-
"""End-to-end: usm -> mp4 con sonido. Prueba sobre varios videos y mide con ffprobe + FFT."""
import os, sys, json, wave, subprocess, shutil
import numpy as np

CLIENT = r"C:/Users/Lukas/Downloads/P5X/Client"
MEDIA = CLIENT + "/OuterPackage/Media/Windows"
BIN = CLIENT + "/bin/Media/Windows"
VGM = r"C:/Users/Lukas/p5x-datamining/tools/vgmstream/vgmstream-cli.exe"
WANNA = r"C:/Users/Lukas/p5x-datamining/tools/env/Scripts/wannacri.exe"
FFMPEG = r"C:/Users/Lukas/AppData/Local/hermes/tools/ffmpeg-9.0.1-win32-x64/bin/ffmpeg.exe"
FFPROBE = r"C:/Users/Lukas/AppData/Local/hermes/tools/ffmpeg-9.0.1-win32-x64/bin/ffprobe.exe"
CLAVE = "1729401234202"
NO_WIN = 0x08000000
BASE = r"C:/Users/Lukas/p5x-datamining/_dl/e2e_video"


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, creationflags=NO_WIN, **kw)


def flatness(wav):
    with wave.open(wav, "rb") as w:
        n, ch, sr, nf = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
        raw = w.readframes(min(nf, sr * 20))
    a = np.frombuffer(raw, dtype=np.int16).astype(np.float64)
    if ch == 2:
        a = a.reshape(-1, 2).mean(axis=1)
    if a.size < 4096:
        return None, sr, n / sr
    a = a - a.mean()
    # ventanas de 4096, media de planitud espectral (media geometrica / aritmetica)
    ps = []
    for i in range(0, len(a) - 4096, 4096):
        seg = a[i:i + 4096] * np.hanning(4096)
        P = np.abs(np.fft.rfft(seg)) ** 2 + 1e-12
        ps.append(np.exp(np.mean(np.log(P))) / np.mean(P))
    return float(np.mean(ps)), sr, n / sr


def extrae_video(usm, out):
    crudo = os.path.join(out, "_crudo")
    shutil.rmtree(crudo, ignore_errors=True)
    os.makedirs(crudo, exist_ok=True)
    def _piezas():
        return [os.path.join(dp, f) for dp, _, fs in os.walk(crudo) for f in fs
                if f.lower().rsplit(".", 1)[-1] in ("ivf", "avi", "mpg", "m2v")]
    r = run([WANNA, "extractusm", usm, "-k", CLAVE, "-o", crudo])
    piezas = _piezas()
    if not piezas:  # build CN: literales en GBK, no shift-jis (WannaCRI no da exit-code)
        r = run([WANNA, "extractusm", usm, "-k", CLAVE, "-e", "gbk", "-o", crudo])
        piezas = _piezas()
    if not piezas:
        raise RuntimeError("sin pista de video: " + (r.stdout or "")[-300:] + (r.stderr or "")[-300:])
    return max(piezas, key=os.path.getsize)


def saca_audio(acb, subsong, out):
    wav = os.path.join(out, "audio.wav")
    r = run([VGM, "-s", str(subsong), "-o", wav, acb])
    if not os.path.isfile(wav):
        raise RuntimeError("vgmstream fallo: " + (r.stdout or "") + (r.stderr or ""))
    return wav


def mux(video, wav, mp4):
    r = run([FFMPEG, "-y", "-i", video, "-i", wav, "-map", "0:v:0", "-map", "1:a:0",
             "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest",
             "-movflags", "+faststart", mp4])
    if not os.path.isfile(mp4):
        raise RuntimeError("ffmpeg fallo: " + (r.stdout or "")[-400:] + (r.stderr or "")[-400:])
    return mp4


def probe(f):
    r = run([FFPROBE, "-v", "error", "-show_entries",
             "stream=index,codec_type,codec_name,channels,sample_rate,duration",
             "-show_entries", "format=duration,size", "-of", "json", f])
    return json.loads(r.stdout)


def main():
    idx = json.load(open(r"C:/Users/Lukas/p5x-datamining/_dl/indice_audio.json", encoding="utf-8"))
    elegidos = ["Activity_2025zhounian_1", "CG_wonder_swimsuit", "PC068_transition",
                "CG_LD_PC068_PV_01", "CG_zx_Event_05_28_03", "CG_yugao_2_1"]
    os.makedirs(BASE, exist_ok=True)
    informe = []
    for stem in elegidos:
        v = idx.get(stem)
        if not v or "subsong" not in v:
            print("!! sin audio para", stem, v); continue
        usm = os.path.join(MEDIA, stem + ".usm")
        if not os.path.isfile(usm):
            usm = os.path.join(BIN, stem + ".usm")
        out = os.path.join(BASE, stem)
        shutil.rmtree(out, ignore_errors=True)
        os.makedirs(out, exist_ok=True)
        print("\n=== %s ===" % stem)
        try:
            video = extrae_video(usm, out)
            wav = saca_audio(v["acb"], v["subsong"], out)
            mp4 = mux(video, wav, os.path.join(BASE, stem + ".mp4"))
            fl, sr, adur = flatness(wav)
            p = probe(mp4)
            fmt = p.get("format", {})
            print("  banco=%s cue=%s pista=%s subsong=%s" % (v["banco"], v["cue"], v["pista"], v["subsong"]))
            print("  mp4=%s  %.2f MB  dur=%ss" % (mp4, int(fmt.get("size", 0)) / 1e6, fmt.get("duration")))
            for s in p["streams"]:
                print("   stream", s["codec_type"], s.get("codec_name"),
                      "ch=%s" % s.get("channels"), "sr=%s" % s.get("sample_rate"),
                      "dur=%s" % s.get("duration"))
            print("  planitud espectral FFT = %.4f  (audio %.2fs @ %d Hz)" % (fl, adur, sr))
            informe.append({"usm": stem, "banco": v["banco"], "cue": v["cue"], "pista": v["pista"],
                            "subsong": v["subsong"], "mp4_mb": round(int(fmt.get("size", 0)) / 1e6, 2),
                            "dur_mp4": fmt.get("duration"), "planitud": round(fl, 4),
                            "streams": p["streams"]})
        except Exception as e:
            print("  ERROR:", e)
            informe.append({"usm": stem, "error": str(e)})
    json.dump(informe, open(r"C:/Users/Lukas/p5x-datamining/_dl/informe_e2e_video.json", "w",
                            encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\ninforme -> _dl/informe_e2e_video.json")


if __name__ == "__main__":
    main()