"""Busca quien llama a UIMultipleMaterial.Update() y con que valor de xmm7.

El Update() lee `_GradientAlphaTopPosition` de xmm7, que es un registro no volatil: se lo tuvo que
poner el que llama. Aqui se desensamblan los dos candidatos (UIMultipleGradient.UpdateMaterials y
UIMultipleGradient.Update) siguiendo xmm6/xmm7 y las llamadas, para saber si vale 1.0 o si sale de
los datos del degradado.
"""
import sys
from pathlib import Path

import capstone
import pefile

DLL = r"C:/Users/Lukas/Downloads/P5X/Client/pc/GameAssembly.dll"
LLAMADA = 0x1823C3DA0  # UIMultipleMaterial.Update
CANDIDATOS = [("UIMultipleGradient.UpdateMaterials", 0x23C3430, 0x200),
              ("UIMultipleGradient.Update", 0x23C35A0, 0x100),
              ("UIMultipleGradient.Start", 0x23C3190, 0x200)]


def main():
    pe = pefile.PE(DLL, fast_load=True)
    base = pe.OPTIONAL_HEADER.ImageBase
    datos = Path(DLL).read_bytes()
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
    for nombre, rva, largo in CANDIDATOS:
        off = pe.get_offset_from_rva(rva)
        print("=" * 90)
        print(nombre, " RVA %#x" % rva)
        print("=" * 90)
        for ins in md.disasm(datos[off:off + largo], base + rva):
            m = ins.mnemonic + " " + ins.op_str
            interesante = ("xmm6" in m or "xmm7" in m or "movss" in m or ins.mnemonic.startswith("call")
                           or ins.mnemonic.startswith("j"))
            if interesante:
                marca = "   <=== llama a Update()" if ("call" in ins.mnemonic and
                                                       ("0x%x" % LLAMADA) in m) else ""
                print("  %#012x  %-32s %s%s" % (ins.address, ins.bytes.hex(), m, marca))
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())