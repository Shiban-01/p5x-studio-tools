"""Sonda: que objetos y que mallas existen de verdad al importar el GLB, en una sesion limpia.

Sirve para localizar de donde sale una esfera suelta que no esta en el GLB (9 mallas, todas con
nombre) pero que aparece en el FBX exportado.
"""
import bpy

GLB = r"C:\Users\Lukas\p5x-datamining\kotone_shiomi\01_model\glb\Kotone_Shiomi_full.glb"

print("=== antes de limpiar ===")
print("  objetos: %s" % [o.name for o in bpy.data.objects])
print("  mallas (datablocks): %s" % [m.name for m in bpy.data.meshes])

bpy.ops.wm.read_factory_settings(use_empty=True)

print("\n=== tras read_factory_settings(use_empty=True) ===")
print("  objetos: %s" % [o.name for o in bpy.data.objects])
print("  mallas (datablocks): %s" % [m.name for m in bpy.data.meshes])

bpy.ops.import_scene.gltf(filepath=GLB)

print("\n=== tras importar el GLB ===")
for o in bpy.data.objects:
    extra = ""
    if o.type == "MESH":
        extra = "  %d verts, %d materiales" % (len(o.data.vertices), len(o.data.materials))
    print("  %-8s %-62s%s" % (o.type, o.name, extra))
print("\n  mallas (datablocks): %d -> %s" % (len(bpy.data.meshes), [m.name for m in bpy.data.meshes]))
print("  total objetos: %d" % len(bpy.data.objects))
print("  objetos en la escena: %d" % len(bpy.context.scene.objects))