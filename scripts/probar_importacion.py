"""Prueba real de importacion: el personaje (GLB), un arma larga (OBJ) y un arma corta (GLB).

Comprueba donde cae cada cosa y si comparten el mismo espacio, que es lo que hace falta para que
el arma se pueda emparentar a la mano sin escalar ni rotar nada a mano.
"""
import bpy

PAQUETE = r"C:\Users\Lukas\p5x-datamining\kotone_shiomi"
FULL = PAQUETE + r"\01_model\glb\Kotone_Shiomi_full.glb"
LARGA = PAQUETE + r"\01_model\obj\weapons\weapon_02.obj"
CORTA = PAQUETE + r"\01_model\glb\Kotone_Shiomi_weapon_gun_01.glb"


def limites(objetos):
    xs, ys, zs = [], [], []
    for o in objetos:
        if o.type != "MESH":
            continue
        for v in o.bound_box:
            p = o.matrix_world @ __import__("mathutils").Vector(v)
            xs.append(p.x)
            ys.append(p.y)
            zs.append(p.z)
    if not xs:
        return None
    return (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs))


def resumen(etiqueta, objetos):
    b = limites(objetos)
    if not b:
        print("  %-22s (nada que medir)" % etiqueta)
        return
    print("  %-22s X %6.2f..%6.2f   Y %6.2f..%6.2f   Z %6.2f..%6.2f   (%.2f x %.2f x %.2f m)"
          % (etiqueta, b[0], b[1], b[2], b[3], b[4], b[5],
             b[1] - b[0], b[3] - b[2], b[5] - b[4]))


bpy.ops.wm.read_factory_settings(use_empty=True)

print("=== 1) personaje, import_scene.gltf(por defecto) ===")
bpy.ops.import_scene.gltf(filepath=FULL)
personaje = [o for o in bpy.data.objects]
resumen("personaje", personaje)
huesos = [o for o in personaje if o.type == "ARMATURE"]
print("  objetos: %d   armaduras: %d   huesos: %d"
      % (len(personaje), len(huesos), len(huesos[0].data.bones) if huesos else 0))

print("\n=== 2) arma larga (OBJ), con forward=Y up=Z ===")
antes = set(o.name for o in bpy.data.objects)
bpy.ops.wm.obj_import(filepath=LARGA, forward_axis="Y", up_axis="Z")
nuevos = [o for o in bpy.data.objects if o.name not in antes]
resumen("arma larga", nuevos)
for o in nuevos:
    print("  objeto: %-24s materiales: %s" % (o.name, [m.name for m in o.data.materials]))

print("\n=== 3) arma corta (GLB) ===")
antes = set(o.name for o in bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=CORTA)
nuevos = [o for o in bpy.data.objects if o.name not in antes]
resumen("arma corta", nuevos)
for o in nuevos:
    print("  objeto: %-46s tipo: %s" % (o.name, o.type))

print("\n=== 4) huesos de mano disponibles ===")
for a in huesos:
    for b in a.data.bones:
        if "Hand" in b.name and b.name.startswith("Bip01"):
            p = a.matrix_world @ b.head_local
            print("  %-18s cabeza en (%.3f, %.3f, %.3f)" % (b.name, p.x, p.y, p.z))

print("\n=== 5) texturas que han entrado ===")
for im in bpy.data.images:
    print("  %-40s %sx%s" % (im.name[:40], im.size[0], im.size[1]))