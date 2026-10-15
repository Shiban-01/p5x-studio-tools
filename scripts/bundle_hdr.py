import struct, sys
p = sys.argv[1]
d = open(p, "rb").read()
print("magic+tail:", d[:9].hex())
off = d.index(b"\x00", 0, 12) + 1
fmtver = struct.unpack(">i", d[off:off+4])[0]; off += 4
s = d.index(b"\x00", off); uv = d[off:s].decode(errors="replace"); off = s + 1
size, cbi, ubi, flags = struct.unpack(">qqqI", d[off:off+28])
comp = flags % 64
names = {0: "None", 1: "LZMA", 2: "LZ4-legacy", 3: "LZ4HC", 6: "LZ4-block"}
print(f"bundle_format={fmtver} unity={uv} total={size} blocksinfo={cbi}/{ubi} flags=0x{flags:x} -> {names.get(comp,comp)}")
print("blockInfoAtEnd:", (flags // 128) % 2, "| hasDirInfo:", (flags // 256) % 2)
