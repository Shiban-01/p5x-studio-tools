import struct, lz4.block
d = open(r"_dl/test_anim/anim_playable14d1c564.bundle", "rb").read()
o = d.index(b"\x00") + 1 + 4
o = d.index(b"\x00", o) + 1
o = d.index(b"\x00", o) + 1
size, cbi, ubi, flags = struct.unpack(">qIII", d[o:o + 20])
bi = d[o + 20:o + 20 + cbi]
out = lz4.block.decompress(bi[4:], uncompressed_size=ubi)
algn, cnt = struct.unpack(">Ii", out[:8]); q = 8
usz = [int.from_bytes(out[q + 8 * k:q + 8 * k + 8], "big") for k in range(cnt)]; q += 8 * cnt
csz = [int.from_bytes(out[q + 8 * k:q + 8 * k + 8], "big") for k in range(cnt)]; q += 8 * cnt
bf = out[q]; q += 1
dcomp = bf % 64
print(f"aligned={algn} blocks={cnt} usize={usz} csize={csz} bflags=0x{bf:x} dcomp={dcomp}")
if len(out) > q + 8:
    ver, refs = struct.unpack(">II", out[q:q + 8]); q += 8
    names = []
    for _ in range(min(refs, 10)):
        e2 = out.index(b"\x00", q); names.append(out[q:e2].decode(errors="replace")); q = e2 + 1
    print("typetree ver", ver, "refs", refs, "->", names[:6])
else:
    print("blocksinfo trailer:", out[q:q + 64].hex())
# descomprimir el bloque de datos 0
p = o + 20 + cbi
blk = d[p:p + csz[0]]
if dcomp == 3:
    data = lz4.block.decompress(blk, uncompressed_size=usz[0])
elif dcomp == 0x40 % 64 and bf >= 64:
    data = blk
else:
    data = blk
print("data block0:", len(data), "| tiene ps_set@fight:", b"ps_set@fight" in data)
