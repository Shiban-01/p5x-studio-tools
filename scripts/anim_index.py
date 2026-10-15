#!/usr/bin/env python3
"""Scanner de bundles P5X: lee cabeceras UnityFS + BlocksInfo y reporta
nombres de contenedores/typetrees sin descomprimir assets.

Uso: python anim_index.py          -> escanea anim_* y muestra tipos/clips
"""
import os, re, struct, sys
from pathlib import Path
import lz4.block

B = Path("C:/Users/Lukas/Downloads/P5X/Client/OuterPackage/Bundles/Windows")

def hc(s):
    n = 0
    for c in s: n = (n * 131 + ord(c)) & 0xFFFFFFFF
    return n & 0x7FFFFFFF

def parse_bundle(p: Path):
    d = p.read_bytes()
    name = p.name
    off = hc(name) % 32 + 8
    i = d.find(b"UnityFS", off, off + 8)
    if i < 0: i = d.find(b"UnityFS")
    if i < 0: return None
    d = d[i:]
    e = d.index(b"\x00"); o = e + 1
    fmtver = struct.unpack(">I", d[o:o+4])[0]; o += 4
    s = d.index(b"\x00", o); o = s + 1          # "5.x.x"
    s = d.index(b"\x00", o); o = s + 1          # unity ver
    size, cbi, ubi, flags = struct.unpack(">qqqI", d[o:o+28]); o += 28
    comp = flags & 0x3F
    bi = d[o:o+cbi]
    if comp in (3,):   # LZ4HC blocks
        # blocksinfo: [u32 uncompressed size][payload lz4 block]
        usize = struct.unpack(">I", bi[:4])[0]
        try: data = lz4.block.decompress(bi[4:], uncompressed_size=usize)
        except Exception: return ("lz4err", comp)
    elif comp == 1:
        import lzma; data = lzma.decompress(bi[4:])
    else:
        data = bi
    # BlocksInfo: aligned(1u32) + count(1i32) + uncompressed blocks(8/blk) + compressed(8/blk) + flags(1)
    algn, cnt = struct.unpack(">Ii", data[:8])
    p = 8 + cnt*8 + cnt*8
    # Typetrees info (fmtver>=21): u16? -> version u32 + ref count u32
    ver = struct.unpack(">I", data[p:p+4])[0]; p += 4
    refs = struct.unpack(">I", data[p:p+4])[0]; p += 4
    names = []
    for _ in range(refs):
        st = data.index(b"\x00", p); names.append(data[p:st].decode("utf-8", "replace")); p = st + 1
    ser = struct.unpack(">H", data[p:p+2])[0]; p += 2
    strings = []
    for _ in range(ser):
        st = data.index(b"\x00", p); strings.append(data[p:st].decode("utf-8", "replace")); p = st + 1
    # tras strings: blocks de datos (no tocamos)
    return {"comp": comp, "types": strings[:40], "names": names}

if __name__ == "__main__":
    anims = sorted(B.rglob("anim_*.bundle"))
    print(f"{len(anims)} bundles anim_*", file=sys.stderr)
    from collections import Counter
    kinds = Counter(); clipnames = Counter()
    only = sys.argv[1] if len(sys.argv) > 1 else None
    for k, p in enumerate(anims):
        if only and only not in p.name: continue
        try: r = parse_bundle(p)
        except Exception as e: continue
        if not r or isinstance(r, tuple): continue
        t = "|".join(sorted(set(x.split(",")[0] for x in r["types"] if x.split(",")[0] not in ("TypeTree","NodeBase"))))
        kinds[t[:70]] += 1
        for n in r["names"]:
            if "@" in n or "stand" in n or "idle" in n: clipnames[n] += 1
        if k % 200 == 0: print(f"  {k}/{len(anims)}", file=sys.stderr)
    print("\n== combinaciones de tipos ==")
    for c, n in kinds.most_common(15): print(f"{n:5d}  {c}")
    print("\n== nombres con anim (muestra) ==")
    for c, n in clipnames.most_common(20): print(f"{n:5d}  {c}")
    if only:
        for p in anims:
            if only in p.name:
                print("\n== detalle", p.name, "==")
                r = parse_bundle(p)
                print(r)
