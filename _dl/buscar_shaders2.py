
import sys
from collections import Counter
from pathlib import Path
sys.path.insert(0, r"C:\Users\Lukas\p5x-datamining\p5x_studio")
from p5x_studio import ajustes, herramientas

for b in ["031/program_mat.bundle", "007/postprocess_common7db2a534.bundle",
          "144/postprocess_akephoto3f69d8a.bundle"]:
    try:
        filas = herramientas.listar_bundle(b)
    except Exception as e:
        print("%s -> ERROR %s" % (b, e)); continue
    print("=" * 74)
    print("%s: %d recursos  %s" % (b, len(filas), dict(Counter(f["tipo"] for f in filas))))
    for t in ("Shader", "Material"):
        sel = [f for f in filas if f["tipo"].lower() == t.lower()]
        if sel:
            print("  %s (%d):" % (t, len(sel)))
            for f in sel[:25]:
                print("     %-38s %8d B" % (f["nombre"][:38], f["tamano"]))
    otros = sorted({f["nombre"] for f in filas if f["tipo"].lower() not in ("shader", "material")})
    print("  otros nombres:", ", ".join(otros[:14]))
