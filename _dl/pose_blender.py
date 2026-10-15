import sys, bpy
from mathutils import Matrix
ruta = sys.argv[sys.argv.index("--") + 1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=ruta)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
malos = []
for pb in arm.pose.bones:
    d = max(abs(pb.matrix_basis[r][c] - (1.0 if r == c else 0.0)) for r in range(4) for c in range(4))
    if d > 1e-4:
        malos.append((d, pb.name))
malos.sort(reverse=True)
print("pose bones con matrix_basis != identidad: %d de %d" % (len(malos), len(arm.pose.bones)))
for d, n in malos[:12]:
    print("   %.4f  %s" % (d, n))
print("escala de huesos con scale != 1 en la armadura:")
for b in arm.data.bones:
    s = b.matrix_local.to_scale()
    if any(abs(x - 1) > 1e-3 for x in s):
        print("   %-30s %s" % (b.name, [round(x, 4) for x in s]))
