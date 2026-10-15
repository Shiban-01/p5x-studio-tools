"""Desensambla los metodos de UIMultipleGradient que reparten los parametros al Material.

El dump.cs de Il2CppDumper solo trae las firmas. Aqui se lee el codigo nativo de GameAssembly.dll y
se anotan los `lea reg,[rip+disp]` con el literal de cadena que apuntan (stringliteral.json), para ver
que propiedad del shader recibe que campo de UIMuitipleGradientParam / UIMultipleMaterial.

Metodos:
  b__1                    0x23C2C10  el callback (string name, Object obj) de SetMaterialParam
  SetMaterialParam        0x23C2FD0
  SetParamDefault         0x23C3630  de UIMultipleMaterial
  UIMultipleMaterial.Update 0x23C3DA0
"""
import json
import sys
from pathlib import Path

import capstone
import pefile

DLL = r"C:/Users/Lukas/Downloads/P5X/Client/pc/GameAssembly.dll"
LITS = Path(r"C:/Users/Lukas/p5x-datamining/_dl/il2cpp_out/stringliteral.json")

METODOS = [
    ("UIMultipleGradient.<>c__DisplayClass5_0.<SetMaterialParam>b__1", 0x23C2C10, 900),
    ("UIMultipleGradient.SetMaterialParam", 0x23C2FD0, 700),
    ("UIMultipleMaterial.SetParamDefault", 0x23C3630, 900),
    ("UIMultipleMaterial.Update", 0x23C3DA0, 700),
]


def literales():
    d = json.loads(LITS.read_text(encoding="utf-8"))
    return {int(x["address"], 16) if isinstance(x["address"], str) else int(x["address"]): x["value"]
            for x in d}


def main():
    pe = pefile.PE(DLL, fast_load=True)
    base = pe.OPTIONAL_HEADER.ImageBase
    datos = Path(DLL).read_bytes()
    lit = literales()
    print("literales cargados: %d" % len(lit))

    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
    md.detail = True

    for nombre, rva, largo in METODOS:
        va = base + rva
        off = pe.get_offset_from_rva(rva)
        print()
        print("=" * 100)
        print("%s   RVA %#x  VA %#x" % (nombre, rva, va))
        print("=" * 100)
        codigo = datos[off:off + largo]
        for ins in md.disasm(codigo, va):
            linea = "  %#012x  %-24s %s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str)
            # anotar los lea a literales
            for op in ins.operands:
                if op.type == capstone.x86.X86_OP_MEM and op.mem.base == capstone.x86.X86_REG_RIP:
                    destino = ins.address + ins.size + op.mem.disp
                    # stringliteral.json trae las direcciones en RVA; y tambien se prueban como
                    # desplazamiento de fichero, por si acaso
                    valor = lit.get(destino - base)
                    if valor is None:
                        try:
                            valor = lit.get(pe.get_offset_from_rva(destino - base))
                        except Exception:
                            valor = None
                    if valor is not None:
                        linea += "        ; %r" % (valor[:70],)
                    else:
                        linea += "        ; (dato %#x)" % destino
            print(linea)
    return 0


if __name__ == "__main__":
    sys.exit(main())