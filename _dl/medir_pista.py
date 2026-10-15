#!/usr/bin/env python
"""Decodifica una pista de un .acb a WAV y saca metricas simples (RMS por ventana, pico).
Uso: python medir_pista.py <acb> <subsong> <salida.wav>
Imprime: duracion, RMS global, pico, y una linea de tiempo con el RMS por ventana de 1 s.
"""
import json, subprocess, sys, wave
from array import array
from pathlib import Path

VGM = "C:/Users/Lukas/p5x-datamining/tools/vgmstream/vgmstream-cli.exe"


def decodifica(acb, sub, out):
    subprocess.run([VGM, "-s", str(sub), "-o", out, acb], capture_output=True, text=True, timeout=600)
    return Path(out)


def metricas(wav):
    with wave.open(str(wav), "rb") as w:
        sr = w.getframerate()
        nch = w.getnchannels()
        sw = w.getsampwidth()
        n = w.getnframes()
        datos = w.readframes(n)
    a = array("h")
    a.frombytes(datos)
    if nch > 1:
        # promedia canales en mono para la envolvente
        mono = [0.0] * (len(a) // nch)
        for i in range(len(mono)):
            mono[i] = sum(a[i * nch + c] for c in range(nch)) / nch
    else:
        mono = [float(x) for x in a]
    dur = n / sr
    rms = (sum(x * x for x in mono) / max(len(mono), 1)) ** 0.5
    pico = max((abs(x) for x in mono), default=0)
    # RMS por ventana de 1 s
    vent = sr
    win = []
    for i in range(0, len(mono), vent):
        trozo = mono[i:i + vent]
        if not trozo:
            continue
        win.append((sum(x * x for x in trozo) / len(trozo)) ** 0.5)
    return sr, nch, dur, rms, pico, win


def main():
    acb, sub, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    wav = decodifica(acb, sub, out)
    sr, nch, dur, rms, pico, win = metricas(wav)
    print("WAV: %s" % wav)
    print("dur=%.3fs  sr=%d  ch=%d  RMS=%.1f  pico=%d" % (dur, sr, nch, rms, pico))
    print("RMS/s: " + " ".join("%d" % round(v) for v in win))


if __name__ == "__main__":
    main()