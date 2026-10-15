"""Compara los huesos del FBX entregado con los del rig nuevo, usando Blender de verdad.

El FBX binario tiene los nombres comprimidos, asi que leerlo a mano da basura. Aqui se importan los
dos y se comparan las listas de huesos.
"""
import sys
from pathlib import Path

import bpy

VIEJO = Path(r"C:\Users\Lukas\p5x-datamining\kotone_shiomi\Kotone_Shiomi_full.fbx")
NUEVO = Path(r"C:\Users\Lukas\p5x-datamining\_dl\kotone_rig_completo\pc079_01_PC079_01\03_skeleton\PC079_01_riggeado.glb")
SALIDA = Path(r"C:\Users\Lukas\p5x-datamining\_dl\kotone_rig_completo")


def limpiar():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def huesos(ruta: Path, importar) -> list[str]:
    limpiar()
    try:
        importar(ruta)
    except Exception as e:
        print("   ERROR importando %s: %s" % (ruta.name, e))
        return []
    nombres = []
    for o in bpy.data.objects:
        if o.type == "ARMATURE":
            nombres += [h.name for h in o.data.bones]
    return sorted(set(nombres))


def main() -> None:
    print("   --- FBX entregado ---")
    viejos = huesos(VIEJO, lambda p: bpy.ops.import_scene.fbx(filepath=str(p)))
    print("   huesos: %d" % len(viejos))

    print("   --- rig nuevo (GLB) ---")
    nuevos = huesos(NUEVO, lambda p: bpy.ops.import_scene.gltf(filepath=str(p)))
    print("   huesos: %d" % len(nuevos))

    if viejos and nuevos:
        sv, sn = set(viejos), set(nuevos)
        print()
        print("   solo en el FBX entregado (perdidos): %d" % len(sv - sn))
        for n in sorted(sv - sn)[:30]:
            print("      %s" % n)
        print("   solo en el nuevo (anadidos): %d" % len(sn - sv))
        for n in sorted(sn - sv)[:30]:
            print("      %s" % n)

    print()
    print("   --- IK y Ring en cada uno ---")
    for etiqueta, lista in (("FBX entregado", viejos), ("rig nuevo", nuevos)):
        raros = [n for n in lista if "ik" in n.lower() or "ring" in n.lower()]
        print("   %s: %s" % (etiqueta, raros))

    (SALIDA / "huesos_fbx_entregado.txt").write_text("\n".join(viejos), encoding="utf-8")
    (SALIDA / "huesos_rig_nuevo.txt").write_text("\n".join(nuevos), encoding="utf-8")


main()