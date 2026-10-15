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

for o in bpy.data.objects:
    if o.type != "MESH":
        continue
    vs = [o.matrix_world @ v.co for v in o.data.vertices]
    if not vs:
        continue
    xs = [v.x for v in vs]
    ys = [v.y for v in vs]
    zs = [v.z for v in vs]
    print("MESH %-46s v=%6d  x[%7.2f %7.2f]  y[%7.2f %7.2f]  z[%7.2f %7.2f]  vg=%d mods=%s"
          % (o.name[:46], len(vs), min(xs), max(xs), min(ys), max(ys), min(zs), max(zs),
             len(o.vertex_groups), [m.type for m in o.modifiers]))

for o in bpy.data.objects:
    if o.type == "ARMATURE":
        print("ARMATURA", o.name, "huesos", len(o.data.bones), "escala", tuple(round(x, 3) for x in o.scale))
        for b in list(o.data.bones)[:6]:
            print("   ", b.name, "head_local", tuple(round(x, 3) for x in b.head_local))