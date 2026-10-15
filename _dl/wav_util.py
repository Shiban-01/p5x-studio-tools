#!/usr/bin/env python
"""Utilidades WAV simples: restar dos wav iguales y recortar un wav.
Uso: python wav_util.py restar a.wav b.wav salida.wav
     python wav_util.py copia in.wav out.wav
"""
import sys, wave
from array import array


def lee(p):
    with wave.open(p, "rb") as w:
        return w.getframerate(), w.getnchannels(), w.getsampwidth(), w.readframes(w.getnframes())


def escribe(p, sr, nch, sw, datos):
    with wave.open(p, "wb") as w:
        w.setnchannels(nch); w.setsampwidth(sw); w.setframerate(sr)
        w.writeframes(datos)


def main():
    modo, a, b, out = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
    sr, nch, sw, da = lee(a)
    sr2, nch2, sw2, db = lee(b)
    assert (sr, nch, sw) == (sr2, nch2, sw2), "wav incompatibles"
    A = array("h"); A.frombytes(da)
    B = array("h"); B.frombytes(db)
    n = min(len(A), len(B))
    D = array("h", (max(-32768, min(32767, A[i] - B[i])) for i in range(n)))
    escribe(out, sr, nch, sw, D.tobytes())
    print("escrito", out, "frames", n)


if __name__ == "__main__":
    main()