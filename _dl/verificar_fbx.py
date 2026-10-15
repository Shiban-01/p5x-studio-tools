"""Cuenta lo que hay de verdad dentro de un fichero (FBX o GLB) al abrirlo en Blender.

Uso:  blender --background --python verificar_fbx.py -- <fichero> [<fichero> ...]

Imprime, por fichero: armaduras, huesos, mallas, mallas con grupos de vertices, shape keys,
imagenes y materiales. Es la medida, no una estimacion.
"""
import os
import sys

import bpy


def medir(ruta):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    ext = os.path.splitext(ruta)[1].lower()
    if ext == ".glb" or ext == ".gltf":
        bpy.ops.import_scene.gltf(filepath=ruta)
    else:
        bpy.ops.import_scene.fbx(filepath=ruta, use_anim=False)

    armaduras = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    mallas = [o for o in bpy.data.objects if o.type == "MESH"]
    huesos = sum(len(a.data.bones) for a in armaduras)
    con_grupos = sum(1 for m in mallas if len(m.vertex_groups) > 0)
    sk = sum(1 for m in mallas if m.data.shape_keys is not None)
    print("=== MEDIDA %s ===" % os.path.basename(ruta))
    print("  armaduras: %d" % len(armaduras))
    for a in armaduras:
        print("    - %s: %d huesos" % (a.name, len(a.data.bones)))
    print("  huesos totales: %d" % huesos)
    print("  mallas: %d" % len(mallas))
    print("  mallas con grupos de vertices: %d de %d" % (con_grupos, len(mallas)))
    print("  mallas con shape keys: %d" % sk)
    print("  imagenes: %d" % len(bpy.data.images))
    print("  materiales: %d" % len(bpy.data.materials))
    for m in mallas:
        print("    malla %-45s grupos %3d  verts %6d  mats %s"
              % (m.name[:45], len(m.vertex_groups), len(m.data.vertices),
                 [mm.name for mm in m.data.materials]))


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if not args:
        raise SystemExit("faltan ficheros")
    for ruta in args:
        if os.path.isfile(ruta):
            try:
                medir(ruta)
            except Exception as e:
                print("=== ERROR %s: %s ===" % (ruta, e))
        else:
            print("=== NO EXISTE %s ===" % ruta)


main()