"""Exporta el modelo completo a FBX, para quien no quiera tratar con GLB.

Importa el GLB del paquete en una escena vacia y lo exporta a FBX con las texturas incrustadas,
de forma que el fichero valga por si solo. Deja el resultado en la raiz del paquete.

Uso:  blender --background --python scripts/exportar_fbx.py
"""
import os
import bpy

GLB = r"C:\Users\Lukas\p5x-datamining\kotone_shiomi\01_model\glb\Kotone_Shiomi_full.glb"
FBX = r"C:\Users\Lukas\p5x-datamining\kotone_shiomi\Kotone_Shiomi_full.fbx"

print("=== exportar a FBX ===")
bpy.ops.wm.read_factory_settings(use_empty=True)
print("importando:", GLB)
bpy.ops.import_scene.gltf(filepath=GLB)

objetos = [o for o in bpy.data.objects]
mallas = [o for o in objetos if o.type == "MESH"]
armaduras = [o for o in objetos if o.type == "ARMATURE"]
huesos = sum(len(a.data.bones) for a in armaduras)
verts = sum(len(o.data.vertices) for o in mallas)
print("  objetos: %d (%d mallas, %d armaduras)" % (len(objetos), len(mallas), len(armaduras)))
print("  huesos: %d   vertices: %d" % (huesos, verts))

# El importador de glTF de Blender deja una esfera suelta de 42 vertices ("Icosphere") que no
# viene en el GLB: es un resto suyo, sin material ni pesos. Si se exporta, viaja al FBX.
sobran = [o for o in bpy.data.objects if o.name.split(".")[0] == "Icosphere"]
for o in sobran:
    print("  quitando objeto suelto del importador: %s (%s)"
          % (o.name, "%d vertices" % len(o.data.vertices) if o.type == "MESH" else o.type))
    bpy.data.objects.remove(o, do_unlink=True)
if sobran:
    print("  objetos ahora: %d (%d mallas, %d armaduras)"
          % (len(bpy.data.objects),
             len([o for o in bpy.data.objects if o.type == "MESH"]),
             len([o for o in bpy.data.objects if o.type == "ARMATURE"])))

bpy.ops.export_scene.fbx(
    filepath=FBX,
    path_mode="COPY",
    embed_textures=True,
    add_leaf_bones=False,
    use_selection=False,
    apply_unit_scale=True,
    object_types={"EMPTY", "ARMATURE", "MESH"},
)
print("  ->", FBX, "%.1f MB" % (os.path.getsize(FBX) / 1048576))