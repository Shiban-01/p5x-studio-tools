#!/usr/bin/env python
"""Compara dos WAV del mismo tamano: RMS de la DIFERENCIA por ventana de 1 s.
Si un canal lleva voz y el otro no (o lleva otra voz), la diferencia marca donde.
Uso: python dif_wav.py a.wav b.wav
"""
import sys, wave
from array import array


def lee(p):
    with wave.open(p, "rb") as w:
        sr, nch, n = w.getframerate(), w.getnchannels(), w.getnframes()
        a = array("h"); a.frombytes(w.readframes(n))
    return sr, nch, a


def main():
    sr, nch, a = lee(sys.argv[1])
    sr2, nch2, b = lee(sys.argv[2])
    n = min(len(a), len(b))
    print("A=%s (%d frames)  B=%s (%d frames)  sr=%d" % (sys.argv[1], len(a), sys.argv[2], len(b), sr))
    dif = [a[i] - b[i] for i in range(n)]
    vent = sr * nch
    rms_a, rms_b, rms_d = [], [], []
    for i in range(0, n, vent):
        ta, tb, td = a[i:i+vent], b[i:i+vent], dif[i:i+vent]
        if not ta:
            continue
        rms_a.append((sum(x*x for x in ta)/len(ta))**0.5)
        rms_b.append((sum(x*x for x in tb)/len(tb))**0.5)
        rms_d.append((sum(x*x for x in td)/len(td))**0.5)
    print("RMS/s A: " + " ".join("%5d" % round(v) for v in rms_a))
    print("RMS/s B: " + " ".join("%5d" % round(v) for v in rms_b))
    print("RMS/s D: " + " ".join("%5d" % round(v) for v in rms_d))
    tot = (sum(x*x for x in dif)/max(n,1))**0.5
    print("RMS global de la diferencia = %.1f" % tot)


if __name__ == "__main__":
    main()