#!/usr/bin/env python3
"""Busca un clip/asset concreto dentro de bundles P5X descomprimiendo sus data blocks.

Uso: python find_in_bundles.py <patron> [subcarpeta_filtro]
ej:  python find_in_bundles.py PC063_thief anim_story
"""
import os, re, struct, sys
from pathlib import Path
import lz4.block

B = Path("C:/Users/Lukas/Downloads/P5X/Client/OuterPackage/Bundles/Windows")

def hc(s):
    n = 0
    for c in s: n = (n * 131 + ord(c)) & 0xFFFFFFFF
    return n & 0x7FFFFFFF

def unpack(p: Path):
    d = p.read_bytes()
    off = hc(p.name) % 32 + 8
    i = d.find(b"UnityFS", off, off + 8)
    if i < 0: i = d.find(b"UnityFS")
    if i < 0: return None
    d = d[i:]
    e = d.index(b"\x00"); o = e + 1
    fmtver = struct.unpack(">I", d[o:o+4])[0]; o += 4
    s = d.index(b"\x00", o); o = s + 1
    s = d.index(b"\x00", o); o = s + 1
    size, cbi, ubi, flags = struct.unpack(">qIII", d[o:o+20]); o += 20
    comp = flags & 0x3F
    bi_off = o; bi = d[bi_off:bi_off+cbi]
    if comp in (2, 3, 6):
        usize = struct.unpack(">I", bi[:4])[0]
        bi = lz4.block.decompress(bi[4:], uncompressed_size=usize)
    elif comp == 1:
        import lzma; bi = lzma.decompress(bi[4:])
    algn, cnt = struct.unpack(">Ii", bi[:8]); q = 8
    usz = [int.from_bytes(bi[q+8*k:q+8*k+8], "big") for k in range(cnt)]; q += 8*cnt
    csz = [int.from_bytes(bi[q+8*k:q+8*k+8], "big") for k in range(cnt)]; q += 8*cnt
    bflags = bi[q]; q += 1
    data_flags = bflags & 0x3F
    p = bi_off + cbi
    out = []
    for k in range(cnt):
        blk = d[p:p+csz[k]]; p += csz[k]
        out.append(blk)
    # banderas: 0x40 = blocks SIN comprimir; 0x21/0x22 etc = lz4 por bloque
    if data_flags == 0x40:
        return b"".join(out)
    try:
        return b"".join(lz4.block.decompress(b_, uncompressed_size=u_) for b_, u_ in zip(out, usz))
    except Exception:
        return b"".join(out)

pat = sys.argv[1].encode()
filt = sys.argv[2] if len(sys.argv) > 2 else None
hits = 0
files = [f for f in B.rglob("*.bundle") if (filt or "anim") in f.name]
print(f"{len(files)} bundles a escanear", file=sys.stderr)
for i, f in enumerate(files):
    try: data = unpack(f)
    except Exception: continue
    if data and pat in data:
        n = data.count(pat)
        print(f"HIT {f}  ({n} veces, {len(data):,} bytes unpacked)")
        hits += 1
    if i % 50 == 0: print(f"  {i}/{len(files)}", file=sys.stderr)
print("total hits:", hits)
