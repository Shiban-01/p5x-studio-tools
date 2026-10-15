#!/usr/bin/env python
"""Correlacion cruzada NORMALIZADA (NCC) por FFT, sin numpy.

coef(t) = sum_lag(senal[t+i]*clip[i]) / sqrt( sum(senal[t+i]^2) * sum(clip[i]^2) )
Encuentra donde el clip encaja mejor dentro de la senal (0..1).

Uso: python ncc.py <senal.wav> <clip.wav> [fs_min] [n_picos]
"""
import sys, wave, cmath, math
from array import array


def lee_mono(p):
    with wave.open(p, "rb") as w:
        sr, nch, n = w.getframerate(), w.getnchannels(), w.getnframes()
        a = array("h"); a.frombytes(w.readframes(n))
    if nch > 1:
        return sr, [sum(a[i*nch+c] for c in range(nch))/(nch*32768.0) for i in range(n//nch)]
    return sr, [x/32768.0 for x in a]


def diezma(x, f):
    return x if f <= 1 else [sum(x[i:i+f])/f for i in range(0, len(x), f)]


def fft(a, inv=False):
    n = len(a); j = 0
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
            half = ln // 2
            for k in range(i, i + half):
                u = a[k]; v = a[k + half] * w
                a[k] = u + v; a[k + half] = u - v
                w *= wl
        ln <<= 1
    if inv:
        for i in range(n):
            a[i] /= n
    return a


def conv_fft(x, k):
    """convolucion lineal x * k (k es el kernel, se correlaciona invertido por fuera)."""
    n = 1
    while n < len(x) + len(k):
        n <<= 1
    A = [complex(v) for v in x] + [0j]*(n-len(x))
    K = [complex(v) for v in k] + [0j]*(n-len(k))
    fa, fk = fft(A), fft(K)
    C = [fa[i]*fk[i] for i in range(n)]
    fft(C, inv=True)
    return [c.real for c in C]


def correlacion_fft(x, k):
    """correlacion (x ⋆ k): devuelve r[lag] = sum_i x[lag+i]*k[i], para lag=0..len(x)-1."""
    return conv_fft(x, k[::-1])


def main():
    spa, clp = sys.argv[1], sys.argv[2]
    fsmin = int(sys.argv[3]) if len(sys.argv) > 3 else 8000
    ntop = int(sys.argv[4]) if len(sys.argv) > 4 else 4
    sr, s = lee_mono(spa)
    sr2_, c = lee_mono(clp)
    f = max(1, sr // fsmin)
    s, c = diezma(s, f), diezma(c, f)
    sr2 = sr / f
    L = len(c)
    # numerador: (s ⋆ c)
    num = correlacion_fft(s, c)
    # energia local de s en ventana L: conv(s^2, unos(L))
    unos = [1.0]*L
    e2 = conv_fft([v*v for v in s], unos)
    ec = sum(v*v for v in c)
    coef = []
    for t in range(len(s) - L):
        den = math.sqrt(max(e2[t], 1e-9) * max(ec, 1e-9))
        coef.append(num[t]/den if den else 0.0)
    idx = sorted(range(len(coef)), key=lambda i: -coef[i])
    # picos separados >= 1 s
    elegidos = []
    for i in idx:
        if all(abs(i-j) > sr2 for j in elegidos):
            elegidos.append(i)
        if len(elegidos) >= ntop:
            break
    print("clip=%-28s len=%.3fs  fs2=%d" % (clp.split('/')[-1], len(c)/sr2, round(sr2)))
    for i in elegidos:
        print("    t=%7.3f s   NCC=%.3f" % (i/sr2, coef[i]))


if __name__ == "__main__":
    main()