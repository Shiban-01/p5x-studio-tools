"""Cuenta, en el .blend del paquete de artista, que huesos llevan de verdad la malla.

Uso: blender --background --python analizar_rig.py -- <blend>
Imprime: objetos del fichero, huesos usados, huesos sin ningun vertice y la cadena de ancestros.
"""
import bpy
import sys
import json

ruta = sys.argv[sys.argv.index("--") + 1]
bpy.ops.wm.open_mainfile(filepath=ruta)

print("=== OBJETOS DEL FICHERO ===")
for o in bpy.data.objects:
    extra = ""
    if o.type == "MESH":
        extra = "  %d vertices, %d grupos" % (len(o.data.vertices), len(o.vertex_groups))
    elif o.type == "ARMATURE":
        extra = "  %d huesos" % len(o.data.bones)
    print("   %-28s %-10s%s" % (o.name, o.type, extra))

arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
mallas = [o for o in bpy.data.objects if o.type == "MESH" and o.vertex_groups]

# peso maximo y numero de vertices por grupo, sumando TODAS las mallas
peso_max, cuantos = {}, {}
for ob in mallas:
    for v in ob.data.vertices:
        for g in v.groups:
            nombre = ob.vertex_groups[g.group].name
            if g.weight > 0:
                cuantos[nombre] = cuantos.get(nombre, 0) + 1
                peso_max[nombre] = max(peso_max.get(nombre, 0.0), g.weight)

print("=== HUESOS DEL ARMATURE: %d ===" % len(arm.data.bones))
sin_peso, con_peso = [], []
for b in arm.data.bones:
    n = b.name
    if n in cuantos:
        con_peso.append((cuantos[n], peso_max[n], n, b.parent.name if b.parent else "-"))
    else:
        sin_peso.append((n, b.parent.name if b.parent else "-"))
print("   con vertices: %d   |   sin ningun vertice: %d" % (len(con_peso), len(sin_peso)))
print()
print("--- SIN NINGUN VERTICE (candidatos a quitar) ---")
for n, p in sorted(sin_peso):
    print("   %-26s padre %s" % (n, p))
print()
print("--- CON VERTICES, los que menos ---")
for c, w, n, p in sorted(con_peso)[:12]:
    print("   %-26s %5d vertices, peso maximo %.2f" % (n, c, w))

# ancestros que hay que conservar para no romper la jerarquia
usados = {n for _, _, n, _ in con_peso}
padres = {b.name: (b.parent.name if b.parent else None) for b in arm.data.bones}
necesarios = set()
for n in usados:
    a = n
    while a:
        necesarios.add(a)
        a = padres[a]
print()
print("=== PLAN DE OPTIMIZACION ===")
print("   huesos que llevan la malla            : %d" % len(usados))
print("   + ancestros necesarios para la cadena : %d" % len(necesarios - usados))
print("   = huesos en el rig optimizado         : %d  (de %d)" % (len(necesarios), len(arm.data.bones)))
print("   se quitarian                          : %d" % (len(arm.data.bones) - len(necesarios)))
print("   de los que se quitan, sin vertices    : %d" % len(set(sin_peso) - necesarios))
sobran = [b.name for b in arm.data.bones if b.name not in necesarios]
print("   lista de los que se quitan: %s" % ", ".join(sorted(sobran)))
json.dump({"necesarios": sorted(necesarios), "sobran": sorted(sobran),
           "usados": sorted(usados), "sin_peso": sorted(n for n, _ in sin_peso),
           "padres": padres, "vertices": {n: cuantos[n] for n in cuantos}},
          open(r"C:\Users\Lukas\p5x-datamining\_dl\rig_optimizado.json", "w"), indent=1)
print("plan guardado en _dl/rig_optimizado.json")
