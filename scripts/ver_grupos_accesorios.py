import bpy
import sys

ruta = sys.argv[sys.argv.index("--") + 1]
bpy.ops.wm.open_mainfile(filepath=ruta)
print("=== %s ===" % ruta.rsplit("\\", 1)[-1])
for ob in bpy.data.objects:
    if ob.type != "MESH":
        continue
    if ob.name not in ("Kotone_Brazalete", "Kotone_Lanza", "Kotone_Pistola", "Kotone_Vaina"):
        continue
    usados = {}
    for v in ob.data.vertices:
        for e in v.groups:
            if e.weight > 0:
                n = ob.vertex_groups[e.group].name
                usados[n] = usados.get(n, 0) + 1
    orden = sorted(usados.items(), key=lambda x: -x[1])
    print("   %-18s %s" % (ob.name, ", ".join("%s(%d)" % (n, c) for n, c in orden[:6])))
