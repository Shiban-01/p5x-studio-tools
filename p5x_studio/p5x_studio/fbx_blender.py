"""Script de Blender que escribe el FBX final del modelo.

Hay DOS formas de montarlo, y la primera es la buena:

  1. **Desde el GLB riggeado** (`03_skeleton/<personaje>_riggeado.glb`). Ese fichero ya trae el
     esqueleto, los pesos de piel, las expresiones y las texturas incrustadas, asi que el FBX sale
     con armadura y grupos de vertices, igual que el GLB. Es la via que se usa siempre que el GLB
     existe.

  2. **Desde los OBJ sueltos**, solo como plan B cuando no hay GLB (no habia Unity). Los OBJ son
     geometria pura: no tienen huesos ni pesos, asi que el FBX sale SIN esqueleto. Es lo unico que
     se puede hacer en ese caso, y el extractor lo avisa.

Uso:

    blender --background --python fbx_blender.py -- --glb <modelo.glb> <salida.fbx>
    blender --background --python fbx_blender.py -- --obj <carpeta> [--obj <carpeta2> ...] <salida.fbx>

Los OBJ del juego vienen Z-arriba; al importarlos se declara Y adelante y Z arriba, que es como se
escribieron. El GLB, en cambio, ya viene en convencion glTF (Y arriba) y el importador de Blender lo
coloca solo.
"""
import os
import sys

import bpy

# Blender no tiene el paquete de la herramienta en el PATH, asi que este script no puede importar
# `idiomas`: el idioma llega por la variable de entorno P5X_IDIOMA y aqui se traduce lo poco que
# este script le puede decir al usuario (lo demas lo cuenta el extractor, ya traducido).
_MENSAJES = {
    "es": {
        "args": "faltan argumentos: -- [--glb <glb>] [--obj <carpeta>]... <salida.fbx>",
        "salida": "falta la ruta del FBX de salida",
        "sin_malla_glb": "el GLB no trajo ninguna malla",
        "sin_origen": "no hay GLB ni OBJ que importar",
        "sin_piezas": "no se importo ninguna pieza",
        "resumen": "[fbx] armaduras %d  huesos %d  mallas %d  con grupos de vertices %d",
        "importando_glb": "[fbx] importando el GLB riggeado: %s",
        "exportado_glb": "[fbx] exportado desde el GLB: %s",
        "sin_glb": "[fbx] sin GLB: importando %d piezas OBJ (el FBX saldra sin esqueleto)",
        "no_importar": "[fbx] no se pudo importar %s (%s)",
        "exportado_obj": "[fbx] exportado desde OBJ (sin esqueleto): %s",
    },
    "en": {
        "args": "missing arguments: -- [--glb <glb>] [--obj <folder>]... <output.fbx>",
        "salida": "the output FBX path is missing",
        "sin_malla_glb": "the GLB brought no meshes",
        "sin_origen": "there is no GLB or OBJ to import",
        "sin_piezas": "no part was imported",
        "resumen": "[fbx] armatures %d  bones %d  meshes %d  with vertex groups %d",
        "importando_glb": "[fbx] importing the rigged GLB: %s",
        "exportado_glb": "[fbx] exported from the GLB: %s",
        "sin_glb": "[fbx] no GLB: importing %d OBJ parts (the FBX will come out without a skeleton)",
        "no_importar": "[fbx] could not import %s (%s)",
        "exportado_obj": "[fbx] exported from OBJ (without skeleton): %s",
    },
}
_IDIOMA = "en" if os.environ.get("P5X_IDIOMA", "es").lower().startswith("en") else "es"


def tr(clave: str) -> str:
    return _MENSAJES[_IDIOMA][clave]

# las piezas de baja calidad y las sombras no interesan en el FBX final
DESCARTABLES = ("_lod", "_lodlow", "_lodhigh", "_shadow")


def _argumentos() -> tuple:
    if "--" not in sys.argv:
        raise SystemExit(tr("args"))
    args = sys.argv[sys.argv.index("--") + 1:]
    glb, carpetas, salida = None, [], None
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--glb":
            i += 1
            glb = args[i] if i < len(args) else None
        elif a == "--obj":
            i += 1
            if i < len(args):
                carpetas.append(args[i])
        else:
            salida = a
        i += 1
    if not salida:
        raise SystemExit(tr("salida"))
    return glb, carpetas, salida


def _exportar(salida: str, con_rig: bool) -> None:
    os.makedirs(os.path.dirname(salida) or ".", exist_ok=True)
    opciones = dict(
        filepath=salida,
        use_selection=False,
        apply_unit_scale=True,
        bake_space_transform=False,
        mesh_smooth_type="FACE",
        path_mode="COPY",
        embed_textures=True,
        # sin huesos hoja: el exportador anade uno por cada hueso sin hijos, y eso falsearia el
        # recuento respecto al GLB (329 huesos tienen que seguir siendo 329).
        add_leaf_bones=False,
    )
    if con_rig:
        # con armadura hay que exportar tambien los modificadores (la piel) y las formas
        # (expresiones). El exportador de Blender 5 ya vuelca la piel por defecto cuando la malla
        # lleva su modificador de armadura; lo que no hay que dejar es que se cuele luz o camara.
        opciones.update(use_mesh_modifiers=True, use_mesh_modifiers_render=False,
                        bake_anim=False, object_types={"MESH", "ARMATURE"})
    bpy.ops.export_scene.fbx(**opciones)


def _resumen() -> None:
    armaduras = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    mallas = [o for o in bpy.data.objects if o.type == "MESH"]
    huesos = sum(len(a.data.bones) for a in armaduras)
    con_grupos = sum(1 for m in mallas if len(m.vertex_groups) > 0)
    print(tr("resumen")
          % (len(armaduras), huesos, len(mallas), con_grupos))


def main() -> None:
    glb, carpetas, salida = _argumentos()

    # escena vacia: la de fabrica trae cubo, luz y camara, que acabarian dentro del FBX
    bpy.ops.wm.read_factory_settings(use_empty=True)

    if glb and os.path.isfile(glb):
        print(tr("importando_glb") % os.path.basename(glb))
        bpy.ops.import_scene.gltf(filepath=glb)
        # el importador de glTF de Blender crea una esfera en la coleccion `glTF_not_exported`
        # para usarla como forma de los huesos; no es parte del modelo y no debe acabar en el FBX
        for obj in list(bpy.data.objects):
            if any(c.name == "glTF_not_exported" for c in obj.users_collection):
                bpy.data.objects.remove(obj, do_unlink=True)
        if not any(o.type == "MESH" for o in bpy.data.objects):
            raise SystemExit(tr("sin_malla_glb"))
        _exportar(salida, con_rig=True)
        print(tr("exportado_glb") % salida)
        _resumen()
        return

    # --- plan B: unir los OBJ (sin esqueleto; los OBJ no lo llevan)
    ficheros = []
    for carpeta in carpetas:
        for raiz, _, nombres in os.walk(carpeta):
            for nombre in sorted(nombres):
                if not nombre.lower().endswith(".obj"):
                    continue
                if any(nombre.lower().endswith(s) or (s + ".") in nombre.lower()
                       for s in DESCARTABLES):
                    continue
                ficheros.append(os.path.join(raiz, nombre))
    if not ficheros:
        raise SystemExit(tr("sin_origen"))

    print(tr("sin_glb") % len(ficheros))
    importadas = 0
    for ruta in ficheros:
        try:
            # los OBJ del juego son Z-arriba: se declara al importar
            bpy.ops.wm.obj_import(filepath=ruta, forward_axis="Y", up_axis="Z")
            importadas += 1
        except Exception as e:
            print(tr("no_importar") % (os.path.basename(ruta), e))
    if not importadas:
        raise SystemExit(tr("sin_piezas"))

    # el importador puede dejar objetos sueltos sin malla: se quitan antes de exportar
    for obj in list(bpy.data.objects):
        if obj.type != "MESH":
            bpy.data.objects.remove(obj, do_unlink=True)

    _exportar(salida, con_rig=False)
    print(tr("exportado_obj") % salida)
    _resumen()


if __name__ == "__main__":
    main()