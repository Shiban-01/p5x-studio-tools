import sys, math
import bpy
from mathutils import Vector
a = sys.argv[sys.argv.index("--") + 1:]
carpeta, salida = a[0], a[1]
bpy.ops.wm.read_factory_settings(use_empty=True)
import glob, os
for obj in glob.glob(os.path.join(carpeta, "**", "*.obj"), recursive=True):
    try:
        bpy.ops.wm.obj_import(filepath=obj)
    except Exception as e:
        print("no", obj, e)
objs = [o for o in bpy.data.objects if o.type == "MESH"]
mins = Vector((1e9,)*3); maxs = Vector((-1e9,)*3)
for o in objs:
    for c in o.bound_box:
        w = o.matrix_world @ Vector(c)
        for i in range(3):
            mins[i] = min(mins[i], w[i]); maxs[i] = max(maxs[i], w[i])
centro = (mins+maxs)/2; tam = max((maxs-mins)[i] for i in range(3))
print("BBOX", tuple(round(v,2) for v in mins), tuple(round(v,2) for v in maxs), round(tam,2))
esc = bpy.context.scene
esc.render.engine = "BLENDER_EEVEE"
esc.render.resolution_x = 900; esc.render.resolution_y = 1300
esc.view_settings.view_transform = "Standard"
w = bpy.data.worlds.new("w"); w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.62,0.63,0.66,1)
w.node_tree.nodes["Background"].inputs[1].default_value = 1.6
esc.world = w
for nombre, loc, en in (("key",(2,-3,2.4),260.0),("fill",(-2.6,-2,1),120.0),("rim",(0,3,2),150.0)):
    d = bpy.data.lights.new(nombre, type="AREA"); d.energy=en; d.size=4.0
    o = bpy.data.objects.new(nombre, d); esc.collection.objects.link(o)
    o.location = Vector(loc)*(tam/1.8) + Vector((centro.x,centro.y,centro.z))
    o.rotation_euler = (Vector((centro.x,centro.y,centro.z))-o.location).to_track_quat("-Z","Y").to_euler()
cd = bpy.data.cameras.new("cam"); cd.type="ORTHO"; cd.ortho_scale=tam*1.15
cam = bpy.data.objects.new("cam", cd); esc.collection.objects.link(cam); esc.camera=cam
cam.location=(centro.x, centro.y-tam*3, centro.z); cam.rotation_euler=(math.radians(90),0,0)
esc.render.filepath=salida; esc.render.image_settings.file_format="PNG"
bpy.ops.render.render(write_still=True); print("RENDER", salida)
