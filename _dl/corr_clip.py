#!/usr/bin/env python
"""Correlacion cruzada por FFT (sin numpy) para localizar un clip dentro de una senal.

Hipotesis: ja_Anim_LD_P3R s7 = ch_Anim_LD_P3R s7 + voces japonesas. Si es cierto, cada
clip VO japones debe aparecer dentro de la DIFERENCIA (ja - ch) en un instante concreto.

Uso: python corr_clip.py <senal.wav> <clip.wav> [fs_min]
Imprime el mejor desfase (s), el coeficiente normalizado del pico y los 3 mejores picos.
"""
import sys, wave, cmath
from array import array


def lee_mono(p):
    with wave.open(p, "rb") as w:
        sr, nch, n = w.getframerate(), w.getnchannels(), w.getnframes()
        a = array("h"); a.frombytes(w.readframes(n))
    if nch > 1:
        return sr, [sum(a[i*nch+c] for c in range(nch))/nch for i in range(n//nch)]
    return sr, [float(x) for x in a]


def diezma(x, f):
    if f <= 1:
        return x
    return [sum(x[i:i+f])/f for i in range(0, len(x), f)]


def fft(a, inv=False):
    n = len(a)
    j = 0
    for i in range(1, n):
        bit = n >> 1
        while j & bit:
            j ^= bit; bit >>= 1
        j |= bit
        if i < j:
            a[i], a[j] = a[j], a[i]
    ln = 2
    while ln <= n:
        ang = (2 if inv else -2) * cmath.pi / ln
        wl = cmath.exp(1j * ang)
        for i in range(0, n, ln):
            w = 1 + 0j
            for k in range(i, i + ln // 2):
                u = a[k]; v = a[k + ln // 2] * w
                a[k] = u + v; a[k + ln // 2] = u - v
                w *= wl
        ln <<= 1
    if inv:
        for i in range(n):
            a[i] /= n
    return a


def correlacion(señal, clip):
    n = 1
    while n < len(señal) + len(clip):
        n <<= 1
    A = [complex(x) for x in señal] + [0j] * (n - len(señal))
    B = [complex(x) for x in reversed(clip)] + [0j] * (n - len(clip))
    fa, fb = fft(A), fft(B)
    C = [fa[i] * fb[i] for i in range(n)]
    fft(C, inv=True)
    return [c.real for c in C[:len(señal)]]


def main():
    senal_p, clip_p = sys.argv[1], sys.argv[2]
    fsmin = int(sys.argv[3]) if len(sys.argv) > 3 else 8000
    sr_s, s = lee_mono(senal_p)
    sr_c, c = lee_mono(clip_p)
    if sr_s != sr_c:
        print("sample rates distintos"); return
    f = max(1, sr_s // fsmin)
    s2, c2 = diezma(s, f), diezma(c, f)
    sr2 = sr_s / f
    # normaliza (quita media, escala a unitario) para que el pico sea un coef. de correlacion
    def norm(x):
        m = sum(x)/len(x)
        x = [v - m for v in x]
        e = (sum(v*v for v in x)/max(len(x), 1))**0.5 or 1.0
        return [v/e for v in x]
    s2n, c2n = norm(s2), norm(c2)
    cor = correlacion(s2n, c2n)
    # coef. normalizado: divido por sqrt(len(clip)) (clip ya unitario)
    import math
    k = math.sqrt(len(c2n))
    coef = [v/k for v in cor]
    idx = sorted(range(len(coef)), key=lambda i: -coef[i])[:3]
    print("clip=%s  len=%.3fs  fs2=%d" % (clip_p, len(c)/sr_c, round(sr2)))
    for i in idx:
        print("   t=%.3f s   coef=%.3f" % (i/sr2, coef[i]))


if __name__ == "__main__":
    main()