"""Vuelca los huesos de Kotone con su cabeza/cola y cuantos vertices lleva cada uno.

Es la lista de trabajo para decidir a que hueso de VALVE (ValveBiped) corresponde cada uno.

Uso: blender --background --python dump_huesos_source.py -- <salida.txt>
"""
import sys

import bpy

ruta = r"C:\Users\Lukas\p5x-datamining\kotone_artista\Kotone_Shiomi.blend"
salida = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "huesos.txt"
bpy.ops.wm.open_mainfile(filepath=ruta)

arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
mallas = [o for o in bpy.data.objects if o.type == "MESH"]

# vertices por hueso (solo los que tienen piel)
cuenta = {}
for ob in mallas:
    for g in ob.vertex_groups:
        cuenta[g.name] = cuenta.get(g.name, 0)
    for v in ob.data.vertices:
        for ge in v.groups:
            if ge.weight > 0.01:
                nombre = ob.vertex_groups[ge.group].name
                cuenta[nombre] = cuenta.get(nombre, 0) + 1

lineas = []
lineas.append("ARMATURE: %s | %d huesos" % (arm.name, len(arm.data.bones)))
lineas.append("matriz del armature: %s" % (list(map(lambda r: [round(v, 4) for v in r], arm.matrix_world))))
lineas.append("")
lineas.append("%-40s %9s %9s %9s %9s %9s %9s %8s %7s %s" %
              ("hueso", "cab_x", "cab_y", "cab_z", "cola_x", "cola_y", "cola_z", "largo", "verts", "coleccion"))
for b in sorted(arm.data.bones, key=lambda x: (x.name)):
    h = arm.matrix_world @ b.head_local
    t = arm.matrix_world @ b.tail_local
    col = b.collections[0].name if b.collections else ""
    lineas.append("%-40s %9.4f %9.4f %9.4f %9.4f %9.4f %9.4f %8.4f %7d %s" %
                  (b.name, h.x, h.y, h.z, t.x, t.y, t.z, b.length, cuenta.get(b.name, 0), col))

# hacia donde mira: centro de la malla de la cara y de los ojos frente al hueso de la cabeza
lineas.append("")
lineas.append("--- hacia donde mira el modelo (coordenadas de mundo, metros) ---")
for nombre_malla, etiqueta in [(m.name, m.name) for m in mallas]:
    ob = bpy.data.objects[nombre_malla]
    if not ob.data.vertices:
        continue
    xs = [ob.matrix_world @ v.co for v in ob.data.vertices]
    cx = sum(v.x for v in xs) / len(xs)
    cy = sum(v.y for v in xs) / len(xs)
    cz = sum(v.z for v in xs) / len(xs)
    zmin = min(v.z for v in xs)
    zmax = max(v.z for v in xs)
    lineas.append("  %-22s centro (%7.3f %7.3f %7.3f)  z de %6.3f a %6.3f  %d verts" %
                  (etiqueta, cx, cy, cz, zmin, zmax, len(xs)))
cabeza = arm.data.bones.get("Bip01 Head")
if cabeza:
    h = arm.matrix_world @ cabeza.head_local
    lineas.append("  hueso Bip01 Head en (%7.3f %7.3f %7.3f)" % (h.x, h.y, h.z))

open(salida, "w", encoding="utf-8").write("\n".join(lineas))
print("escrito:", salida, len(lineas), "lineas")