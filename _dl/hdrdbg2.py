import struct, lz4.block
d = open(r"_dl/test_anim/anim_playable14d1c564.bundle", "rb").read()
o = d.index(b"\x00") + 1 + 4
o = d.index(b"\x00", o) + 1
o = d.index(b"\x00", o) + 1
size, cbi, ubi, flags = struct.unpack(">qIII", d[o:o + 20])
bi = d[o + 20:o + 20 + cbi]
print("cbi", cbi, "ubi", ubi)
for label, payload, hint in [
    ("[4:] ubi", bi[4:], ubi),
    ("[4:] big", bi[4:], 65536),
    ("full ubi", bi, ubi),
    ("full big", bi, 65536),
    ("full cbi*4", bi, cbi * 4),
]:
    try:
        out = lz4.block.decompress(payload, uncompressed_size=hint)
        print(label, "OK ->", len(out), out[:40].hex())
        break
    except Exception as e:
        print(label, "fail", str(e)[:48])
EOF_MARKER
