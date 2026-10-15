"""Para cada asignacion de propiedad del shader en UIMultipleMaterial.Update(), de donde sale el valor.

Los nombres se piden con `mov rdx,[rip+..]` y el valor va en xmm2 (float) o r8d (entero), asi que
imprimiendo las instrucciones anteriores a cada `call` a Material.SetFloat/SetInt se ve que campo se
esta usando. Eso resuelve, por fin, de donde sale `_GradientAlphaBottomPosition`.
"""
import json
import sys
from pathlib import Path

import capstone
import pefile

DLL = r"C:/Users/Lukas/Downloads/P5X/Client/pc/GameAssembly.dll"
LITS = Path(r"C:/Users/Lukas/p5x-datamining/_dl/il2cpp_out/stringliteral.json")

# UIMultipleMaterial.Update  RVA 0x23C3DA0
RVA = 0x23C3DA0
LARGO = 0x1400


def main():
    pe = pefile.PE(DLL, fast_load=True)
    base = pe.OPTIONAL_HEADER.ImageBase
    datos = Path(DLL).read_bytes()
    d = json.loads(LITS.read_text(encoding="utf-8"))
    lit = {}
    for x in d:
        a = x["address"]
        lit[int(a, 16) if isinstance(a, str) else int(a)] = x["value"]

    off = pe.get_offset_from_rva(RVA)
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
    md.detail = True
    instrucciones = list(md.disasm(datos[off:off + LARGO], base + RVA))

    def anota(ins):
        extra = ""
        for op in ins.operands:
            if op.type == capstone.x86.X86_OP_MEM and op.mem.base == capstone.x86.X86_REG_RIP:
                destino = ins.address + ins.size + op.mem.disp
                v = lit.get(destino - base)
                if v is not None:
                    extra = "   ; %r" % (v[:60],)
        return extra

    # indice de la instruccion que carga cada nombre
    carga_nombre = {}
    for i, ins in enumerate(instrucciones):
        for op in ins.operands:
            if (op.type == capstone.x86.X86_OP_MEM and op.mem.base == capstone.x86.X86_REG_RIP
                    and ins.mnemonic == "mov" and ins.op_str.startswith("rdx")):
                destino = ins.address + ins.size + op.mem.disp
                v = lit.get(destino - base)
                if v and v.startswith("_"):
                    carga_nombre[i] = v

    print("asignaciones encontradas en Update():", len(carga_nombre))
    for i in sorted(carga_nombre):
        nombre = carga_nombre[i]
        siguientes = instrucciones[i:i + 12]
        usa_float = any(x.mnemonic.startswith("movss") or "xmm" in x.op_str for x in siguientes[1:6])
        print()
        print("--- %s ---" % nombre)
        for j, ins in enumerate(instrucciones[max(0, i - 9):i + 4]):
            print("    %#012x  %-22s %s %s%s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str, anota(ins)))
    return 0


if __name__ == "__main__":
    sys.exit(main())