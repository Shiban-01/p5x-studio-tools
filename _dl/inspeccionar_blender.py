"""Abre un GLB o un FBX en Blender y cuenta lo que hay de verdad.

Uso:
  blender --background --python inspeccionar_blender.py -- --mode glb <fichero> <informe.json> [<render.png>]
  blender --background --python inspeccionar_blender.py -- --mode fbx <fichero> <informe.json> [<render.png>]
"""
import json
import os
import sys

import bpy


def _args():
    a = sys.argv[sys.argv.index("--") + 1:]
    modo = None
    ruta = None
    informe = None
    render = None
    i = 0
    while i < len(a):
        if a[i] == "--mode":
            i += 1
            modo = a[i]
        elif a[i] == "--out":
            i += 1
            informe = a[i]
        elif a[i] == "--render":
            i += 1
            render = a[i]
        else:
            ruta = a[i]
        i += 1
    return modo, ruta, informe, render


def main():
    modo, ruta, informe, render = _args()
    bpy.ops.wm.read_factory_settings(use_empty=True)

    if modo == "glb":
        bpy.ops.import_scene.gltf(filepath=ruta)
        # la esfera auxiliar del importador no es parte del modelo
        for o in list(bpy.data.objects):
            if any(c.name == "glTF_not_exported" for c in o.users_collection):
                bpy.data.objects.remove(o, do_unlink=True)
    else:
        bpy.ops.import_scene.fbx(filepath=ruta)

    armaduras = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    mallas = [o for o in bpy.data.objects if o.type == "MESH"]
    huesos = sum(len(a.data.bones) for a in armaduras)

    detalle_mallas = []
    con_pesos = 0
    con_uv = 0
    con_arm_mod = 0
    for m in mallas:
        vg = len(m.vertex_groups)
        if vg > 0:
            con_pesos += 1
        if m.data.uv_layers:
            con_uv += 1
        mods = [mo.type for mo in m.modifiers]
        if "ARMATURE" in mods:
            con_arm_mod += 1
        imgs = set()
        for slot in m.material_slots:
            mat = slot.material
            if not mat or not mat.use_nodes:
                continue
            for n in mat.node_tree.nodes:
                if n.type == "TEX_IMAGE" and n.image:
                    imgs.add(n.image.name)
        detalle_mallas.append({
            "nombre": m.name,
            "vertices": len(m.data.vertices),
            "grupos_vertices": vg,
            "uv": len(m.data.uv_layers),
            "modificadores": mods,
            "materiales": [s.material.name if s.material else None for s in m.material_slots],
            "imagenes": sorted(imgs),
        })

    imagenes = []
    for im in bpy.data.images:
        if im.name in ("Render Result", "Viewer Node"):
            continue
        tiene_datos = bool(im.packed_file) or bool(im.filepath) or im.size[0] > 0
        if not tiene_datos:
            continue
        imagenes.append({"nombre": im.name, "tam": list(im.size),
                         "empotrada": bool(im.packed_file),
                         "origen": im.filepath or "(packed)"})

    materiales = []
    for mat in bpy.data.materials:
        base = None
        norm = None
        if mat.use_nodes:
            for n in mat.node_tree.nodes:
                if n.type == "TEX_IMAGE" and n.image:
                    if n.outputs["Color"].links:
                        for l in n.outputs["Color"].links:
                            if l.to_socket.name == "Base Color":
                                base = n.image.name
                    for l in n.outputs["Color"].links:
                        if l.to_socket.name == "Normal":
                            norm = n.image.name
        materiales.append({"nombre": mat.name, "base_color": base, "normal": norm})

    datos = {
        "fichero": ruta,
        "modo": modo,
        "mb": round(os.path.getsize(ruta) / 1e6, 2),
        "armaduras": len(armaduras),
        "huesos": huesos,
        "huesos_por_armadura": [len(a.data.bones) for a in armaduras],
        "nombres_armaduras": [a.name for a in armaduras],
        "mallas": len(mallas),
        "mallas_con_pesos": con_pesos,
        "mallas_con_uv": con_uv,
        "mallas_con_mod_armadura": con_arm_mod,
        "imagenes": len(imagenes),
        "imagenes_detalle": imagenes[:60],
        "materiales": len(materiales),
        "materiales_detalle": materiales,
        "detalle_mallas": detalle_mallas,
    }

    # primeras muestras de nombres de hueso, para ver que son del personaje
    if armaduras:
        datos["huesos_muestra"] = [b.name for b in armaduras[0].data.bones[:12]]

    with open(informe, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=1)
    print("INFORME=%s" % informe)
    print("RESUMEN armaduras=%d huesos=%d mallas=%d con_pesos=%d con_uv=%d imagenes=%d materiales=%d"
          % (len(armaduras), huesos, len(mallas), con_pesos, con_uv, len(imagenes), len(materiales)))

    if render:
        _render(render)


def _render(destino):
    """Captura rapida del modelo: camara encuadrando todo y EEVEE con texturas."""
    import math
    from mathutils import Vector

    objetos = [o for o in bpy.data.objects if o.type == "MESH"]
    if not objetos:
        return
    mins = Vector((1e9, 1e9, 1e9))
    maxs = Vector((-1e9, -1e9, -1e9))
    for o in objetos:
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            for i in range(3):
                mins[i] = min(mins[i], w[i])
                maxs[i] = max(maxs[i], w[i])
    centro = (mins + maxs) / 2
    tam = max(maxs - mins)
    cam_data = bpy.data.cameras.new("cam")
    cam = bpy.data.objects.new("cam", cam_data)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = (centro.x, centro.y - tam * 1.9, centro.z + tam * 0.15)
    cam.rotation_euler = (math.radians(90), 0, 0)
    cam_data.lens = 50
    bpy.context.scene.camera = cam

    luz = bpy.data.lights.new("luz", type="SUN")
    luz.energy = 4.0
    lo = bpy.data.objects.new("luz", luz)
    bpy.context.scene.collection.objects.link(lo)
    lo.rotation_euler = (math.radians(50), math.radians(20), math.radians(30))

    esc = bpy.context.scene
    for motor in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "BLENDER_WORKBENCH"):
        try:
            esc.render.engine = motor
            break
        except Exception:
            continue
    esc.render.resolution_x = 900
    esc.render.resolution_y = 1100
    esc.render.filepath = destino
    esc.render.image_settings.file_format = "PNG"
    esc.world = bpy.data.worlds.new("w")
    esc.world.use_nodes = True
    esc.world.node_tree.nodes["Background"].inputs[0].default_value = (0.15, 0.15, 0.18, 1)
    try:
        bpy.ops.render.render(write_still=True)
        print("RENDER=%s" % destino)
    except Exception as e:
        print("RENDER_FALLO %s" % e)


if __name__ == "__main__":
    main()