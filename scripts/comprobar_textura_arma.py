"""Comprueba que el arma larga entra en Blender CON su textura, no solo con el material.

Importa solo el OBJ y mira: el material, si tiene nodo de imagen, y si la imagen tiene datos
(una textura que no se encuentra entra como imagen vacia de 0x0, y el arma sale gris).
"""
import bpy

OBJ = r"C:\Users\Lukas\p5x-datamining\kotone_shiomi\01_model\obj\weapons\weapon_02.obj"

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.obj_import(filepath=OBJ, forward_axis="Y", up_axis="Z")

for o in bpy.data.objects:
    if o.type != "MESH":
        continue
    print("objeto: %s   vertices: %d" % (o.name, len(o.data.vertices)))
    for m in o.data.materials:
        print("  material: %s" % m.name)
        if not m.use_nodes:
            print("     (sin nodos)")
            continue
        for n in m.node_tree.nodes:
            if n.type == "TEX_IMAGE":
                im = n.image
                if im is None:
                    print("     nodo de imagen SIN fichero")
                else:
                    print("     nodo de imagen: %-34s %sx%s  %s"
                          % (im.name, im.size[0], im.size[1],
                             "CON datos" if im.size[0] else "VACIA (no encontro el fichero)"))
                    print("        ruta: %s" % (im.filepath or "(incrustada)"))

print("\nimagenes cargadas: %d" % len(bpy.data.images))
for im in bpy.data.images:
    print("   %-40s %sx%s" % (im.name, im.size[0], im.size[1]))