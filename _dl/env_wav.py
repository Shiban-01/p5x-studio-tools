#!/usr/bin/env python
"""Envolvente RMS por ventana configurable. Uso:
   python env_wav.py <wav> [ventana_s] [salto_s]
Imprime valores normalizados (0-9) para ver donde hay actividad.
"""
import sys, wave
from array import array


def main():
    w_ = float(sys.argv[2]) if len(sys.argv) > 2 else 0.1
    hop = float(sys.argv[3]) if len(sys.argv) > 3 else 0.1
    with wave.open(sys.argv[1], "rb") as w:
        sr, nch, n = w.getframerate(), w.getnchannels(), w.getnframes()
        a = array("h"); a.frombytes(w.readframes(n))
    ns = len(a)//nch
    mono = [sum(a[i*nch+c] for c in range(nch))/nch for i in range(ns)]
    vw, vh = int(sr*w_), int(sr*hop)
    vals = []
    for i in range(0, len(mono)-vw, vh):
        t = mono[i:i+vw]
        vals.append((sum(x*x for x in t)/len(t))**0.5)
    pico = max(vals) or 1
    print("ventana=%.2fs pico=%.0f" % (w_, pico))
    # renglones de 0.5 s por caracter
    linea = ""
    for j, v in enumerate(vals):
        linea += str(min(9, int(v/pico*10)))
    for k in range(0, len(linea), 100):
        print("%6.1fs %s" % (k*hop, linea[k:k+100]))


if __name__ == "__main__":
    main()