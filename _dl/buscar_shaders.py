
import sys
sys.path.insert(0, r"C:\Users\Lukas\p5x-datamining\p5x_studio")
from p5x_studio import herramientas
print("UNITY:", herramientas.UNITY)
for b in ["106/shaders.bundle", "130/uitex_a-chouka23f26de7.bundle"]:
    try:
        filas = herramientas.listar_bundle(b)
    except Exception as e:
        print("%s -> ERROR %s" % (b, e)); continue
    print("=" * 70)
    print("%s: %d recursos" % (b, len(filas)))
    from collections import Counter
    print("  por tipo:", dict(Counter(f["tipo"] for f in filas)))
    shaders = [f for f in filas if f["tipo"].lower() in ("shader", "material")]
    if shaders:
        print("  shaders/materiales:")
        for f in shaders:
            print("     %-12s %s" % (f["tipo"], f["nombre"]))
    otros = [f["nombre"] for f in filas if f["tipo"].lower() not in ("shader", "material")]
    if otros and len(otros) < 40:
        print("  otros:", ", ".join(sorted(set(otros))[:30]))
