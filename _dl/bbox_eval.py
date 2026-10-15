import sys
import bpy
from mathutils import Vector

a = sys.argv[sys.argv.index("--") + 1:]
modo, ruta = a[0], a[1]
bpy.ops.wm.read_factory_settings(use_empty=True)
if modo == "glb":
    bpy.ops.import_scene.gltf(filepath=ruta)
else:
    bpy.ops.import_scene.fbx(filepath=ruta)

dg = bpy.context.evaluated_depsgraph_get()
mins = Vector((1e9, 1e9, 1e9))
maxs = Vector((-1e9, -1e9, -1e9))
for o in bpy.data.objects:
    if o.type != "MESH" or o.name.startswith("Icosphere"):
        continue
    ev = o.evaluated_get(dg)
    me = ev.to_mesh()
    vs = [o.matrix_world @ v.co for v in me.vertices]
    ev.to_mesh_clear()
    if not vs:
        continue
    xs = [v.x for v in vs]
    ys = [v.y for v in vs]
    zs = [v.z for v in vs]
    for i, lo, hi in ((0, min(xs), max(xs)), (1, min(ys), max(ys)), (2, min(zs), max(zs))):
        mins[i] = min(mins[i], lo)
        maxs[i] = max(maxs[i], hi)
    print("MESH %-44s x[%6.2f %6.2f] y[%6.2f %6.2f] z[%6.2f %6.2f]"
          % (o.name[:44], min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)))
print("TOTAL  x[%.2f %.2f] y[%.2f %.2f] z[%.2f %.2f]  ancho=%.2f alto=%.2f"
      % (mins.x, maxs.x, mins.y, maxs.y, mins.z, maxs.z, maxs.x - mins.x, maxs.z - mins.z))