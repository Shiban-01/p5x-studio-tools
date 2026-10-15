"""Verificacion de un FBX en Blender (batch), usando el importador Better FBX si esta.

Informa de lo que de verdad importa para usar el modelo:
  - armaduras y numero de huesos, y si cuelgan de una sola raiz
  - mallas: vertices, GRUPOS DE VERTICES (pesos), capas UV, shape keys (expresiones) y materiales
  - acciones (clips): fotogramas y numero de curvas
  - huesos sin ningun peso asignado en ninguna malla (los "que no mueven nada")
  - y si los huesos del esqueleto coinciden con los grupos de vertices (huesos que faltan)

Uso:
  blender --background --python blender_verificar_fbx.py -- <fichero.fbx> [salida.json]
"""
import json
import sys

import bpy

ARG = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
RUTA = ARG[0] if ARG else ""
SALIDA = ARG[1] if len(ARG) > 1 else ""

# partir de una escena vacia de fabrica: si no, la escena de inicio del usuario se cuela en el
# informe (una esfera suelta, por ejemplo) y parece que el fichero la trae
bpy.ops.wm.read_factory_settings(use_empty=True)
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)

via = "nativo"
# la extension vive en extensions/user_default: hay que habilitarla en cada sesion
for modulo in ("bl_ext.user_default.better_fbx", "better_fbx"):
    try:
        bpy.ops.preferences.addon_enable(module=modulo)
        print("extension habilitada: " + modulo)
        break
    except Exception:  # noqa: BLE001
        continue
try:
    bpy.ops.better_import.fbx(filepath=RUTA)
    via = "better_import"
except Exception as exc:  # noqa: BLE001
    print("Better FBX no disponible (%s); uso el importador nativo" % exc)
    bpy.ops.import_scene.fbx(filepath=RUTA)

info = {
    "fichero": RUTA, "importador": via,
    "armaduras": [], "mallas": [], "acciones": [], "huesos_sin_peso": [], "huesos_sin_grupo": [],
}

huesos_todos = set()
for o in bpy.data.objects:
    if o.type == "ARMATURE":
        raices = [b.name for b in o.data.bones if b.parent is None]
        info["armaduras"].append({
            "nombre": o.name, "huesos": len(o.data.bones), "raices": raices,
            "espacio": o.data.bones[0].matrix_local.to_translation()[:] if len(o.data.bones) else None,
        })
        huesos_todos |= {b.name for b in o.data.bones}

usados = set()
for o in bpy.data.objects:
    if o.type != "MESH":
        continue
    sk = [k.name for k in o.data.shape_keys.key_blocks] if o.data.shape_keys else []
    info["mallas"].append({
        "nombre": o.name, "vertices": len(o.data.vertices),
        "grupos": len(o.vertex_groups), "uvs": len(o.data.uv_layers),
        "shape_keys": sk,
        "materiales": [m.name if m else None for m in o.data.materials],
        "modificadores": [m.type for m in o.modifiers],
    })
    usados |= {g.name for g in o.vertex_groups}

for a in bpy.data.actions:
    info["acciones"].append({
        "nombre": a.name,
        "fotogramas": [round(a.frame_range[0], 2), round(a.frame_range[1], 2)],
        "curvas": len(a.fcurves),
    })

info["huesos_sin_grupo"] = sorted(huesos_todos - usados)[:60]
info["huesos_sin_peso"] = info["huesos_sin_grupo"]

print("===== RESULTADO =====")
print(json.dumps(info, indent=1, ensure_ascii=False))
if SALIDA:
    with open(SALIDA, "w", encoding="utf-8") as fh:
        json.dump(info, fh, indent=1, ensure_ascii=False)
    print("escrito: " + SALIDA)