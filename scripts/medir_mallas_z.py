
import bpy
bpy.ops.wm.open_mainfile(filepath=r"C:\Users\Lukas\p5x-datamining\kotone_artista\Kotone_Shiomi.blend")
print("%-22s %-28s %8s %8s %8s %8s" % ("objeto", "materiales", "z_min", "z_max", "x_min", "x_max"))
for ob in sorted([o for o in bpy.data.objects if o.type == "MESH"], key=lambda o: o.name):
    if not ob.data.vertices:
        continue
    vs = [ob.matrix_world @ v.co for v in ob.data.vertices]
    mats = [m.name for m in ob.data.materials]
    print("%-22s %-28s %8.3f %8.3f %8.3f %8.3f" % (ob.name, ",".join(mats)[:28],
          min(v.z for v in vs), max(v.z for v in vs), min(v.x for v in vs), max(v.x for v in vs)))
