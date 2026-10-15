"""Busca en GameAssembly.dll que codigo referencia cada literal de cadena del shader.

Los `lea reg,[rip+disp]` de x64 apuntan al literal: barriendo los bytes `48 8d ??`, calculando el
destino y comparandolo con la direccion del literal se sabe si ALGUIEN lo usa. Si nadie escribe
`_GradientAlphaBottomPosition`, el shader usa su valor por defecto y hay que mirarlo en el asset del
Shader, no en el codigo.
"""
import json
import sys
from pathlib import Path

import pefile

DLL = r"C:/Users/Lukas/Downloads/P5X/Client/pc/GameAssembly.dll"
LITS = Path(r"C:/Users/Lukas/p5x-datamining/_dl/il2cpp_out/stringliteral.json")

BUSCADOS = [
    "_GradientAlphaBottomPosition", "_GradientAlphaTopPosition",
    "_GradientColors", "_GradientPositions", "_ColorCount", "_AlphaCount",
    "_GradientAlphaTop", "_GradientAlphaBottom",
]


def main():
    pe = pefile.PE(DLL, fast_load=True)
    base = pe.OPTIONAL_HEADER.ImageBase
    datos = Path(DLL).read_bytes()
    d = json.loads(LITS.read_text(encoding="utf-8"))
    por_valor = {}
    for x in d:
        if x["value"] in BUSCADOS:
            a = x["address"]
            por_valor[x["value"]] = int(a, 16) if isinstance(a, str) else int(a)
    print("literales localizados:", {k: hex(v) for k, v in por_valor.items()})
    if not por_valor:
        return 1
    objetivo = {v: k for k, v in por_valor.items()}

    # secciones de codigo
    secciones = [(s.Name.rstrip(b"\x00").decode(), s.PointerToRawData, s.SizeOfRawData, s.VirtualAddress)
                 for s in pe.sections]
    print("secciones:", [(n, hex(va), "%.1f MB" % (sr / 1048576.0)) for n, _, sr, va in secciones])

    encontrados = {}
    total = 0
    for nombre, crudo_off, tam, va_sec in secciones:
        if crudo_off == 0 or tam == 0:
            continue
        bloque = datos[crudo_off:crudo_off + tam]
        # patron: 48 8d <modrm con mod=00 y rm=101 (rip)> -> 0x0d,0x15,0x1d,0x25,0x2d,0x35,0x3d,0x05
        i = 0
        while True:
            i = bloque.find(b"\x48\x8d", i)
            if i < 0 or i + 7 > len(bloque):
                break
            modrm = bloque[i + 2]
            if modrm & 0xC7 == 0x05:  # rip-relative
                va_ins = base + va_sec + i
                disp = int.from_bytes(bloque[i + 3:i + 7], "little", signed=True)
                destino = va_ins + 7 + disp
                rva_destino = destino - base
                if rva_destino in objetivo:
                    total += 1
                    nombre_lit = objetivo[rva_destino]
                    encontrados.setdefault(nombre_lit, []).append(va_ins)
            i += 1

    print()
    print("referencias encontradas: %d" % total)
    for lit in BUSCADOS:
        sitios = encontrados.get(lit, [])
        print("  %-30s %s" % (lit, ("%d sitios: %s" % (len(sitios), ", ".join(hex(s) for s in sitios[:6])))
                              if sitios else "NADIE lo referencia"))
    return 0


if __name__ == "__main__":
    sys.exit(main())