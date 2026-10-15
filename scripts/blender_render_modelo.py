"""Renderiza el modelo en Blender (batch) para comprobarlo de un vistazo.

Importa el GLB (que ya trae las texturas), encuadra el modelo, pone luces y saca varias vistas:
frente, perfil, espalda y primer plano de la cara. Uso EEVEE (rapido) y 900x1350.

Uso:
  blender --background --python blender_render_modelo.py -- <modelo.glb> <carpeta_salida>
"""
import math
import os
import sys

import bpy
from mathutils import Vector

ARG = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
GLB = ARG[0]
SAL = ARG[1] if len(ARG) > 1 else os.path.dirname(GLB)
# "oscuro" = mismo aspecto que los renders anteriores del paquete, para poder compararlos
OSCURO = len(ARG) > 2 and ARG[2] == "oscuro"
os.makedirs(SAL, exist_ok=True)

for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)

bpy.ops.import_scene.gltf(filepath=GLB)

# el fichero de arranque de Blender puede traer objetos propios: fuera todo lo que no sea el modelo
for o in list(bpy.data.objects):
    if not o.name.startswith("PC079"):
        bpy.data.objects.remove(o, do_unlink=True)

# --- encuadre ---
mn = [1e9] * 3
mx = [-1e9] * 3
for o in bpy.data.objects:
    if o.type != "MESH" or not o.data.vertices:
        continue
    for v in o.data.vertices:
        w = o.matrix_world @ v.co
        for i in range(3):
            mn[i] = min(mn[i], w[i])
            mx[i] = max(mx[i], w[i])
centro = [(mn[i] + mx[i]) / 2 for i in range(3)]
alto = mx[2] - mn[2]
ancho = max(mx[0] - mn[0], mx[1] - mn[1])
print(f"encuadre: centro {[round(c,3) for c in centro]}  alto {alto:.3f}  ancho {ancho:.3f}")

# --- luces ---
def lampara(nombre, energia, tam, loc, rot_grados):
    dat = bpy.data.lights.new(nombre, type="AREA")
    dat.energy = energia
    dat.size = tam
    o = bpy.data.objects.new(nombre, dat)
    bpy.context.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = tuple(math.radians(g) for g in rot_grados)
    return o


# tres puntos suaves: si una sola luz dura pega de frente, la cuenca del ojo queda negra
lampara("key", 260, 4, (centro[0] + 1.6, centro[1] - 3.0, centro[2] + alto * 0.7), (60, 0, 28))
lampara("relleno", 140, 5, (centro[0] - 2.2, centro[1] - 2.6, centro[2] + alto * 0.2), (78, 0, -40))
lampara("contra", 200, 3, (centro[0] + 0.4, centro[1] + 3.0, centro[2] + alto * 0.8), (60, 0, 175))

# --- camara ---
cam_data = bpy.data.cameras.new("cam")
cam_data.lens = 60
cam = bpy.data.objects.new("cam", cam_data)
bpy.context.collection.objects.link(cam)
bpy.context.scene.camera = cam

esc = bpy.context.scene
esc.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in \
    [i.identifier for i in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items] else "BLENDER_EEVEE"
esc.render.resolution_x = 900
esc.render.resolution_y = 1350
esc.render.film_transparent = False
esc.view_settings.view_transform = "Standard"

MUNDO = bpy.data.worlds.new("w")
bpy.context.scene.world = MUNDO
try:
    MUNDO.use_nodes = True
    fondo = next((n for n in MUNDO.node_tree.nodes if n.type == "BACKGROUND"), None)
    if fondo:
        fondo.inputs[0].default_value = (0.02, 0.02, 0.03, 1) if OSCURO else (0.35, 0.37, 0.42, 1)
        fondo.inputs[1].default_value = 1.0
except Exception as exc:  # noqa: BLE001
    print("mundo sin nodos:", exc)
    MUNDO.color = (0.02, 0.02, 0.03) if OSCURO else (0.35, 0.37, 0.42)


# el apuntado se hace con una restriccion TRACK_TO a un objeto vacio en el objetivo
blanco = bpy.data.objects.new("blanco", None)
bpy.context.collection.objects.link(blanco)
restr = cam.constraints.new("TRACK_TO")
restr.target = blanco
restr.track_axis = "TRACK_NEGATIVE_Z"
restr.up_axis = "UP_Y"


def proyectar(etiqueta):
    """Imprime donde caen las esquinas de la caja del modelo en el encuadre (0-1)."""
    from bpy_extras.object_utils import world_to_camera_view
    esc2 = bpy.context.scene
    esq = [(x, y, z) for x in (mn[0], mx[0]) for y in (mn[1], mx[1]) for z in (mn[2], mx[2])]
    us = [world_to_camera_view(esc2, cam, Vector(p)) for p in esq]
    print(f"   {etiqueta}: proyeccion x {min(u.x for u in us):.3f}..{max(u.x for u in us):.3f} "
          f" y {min(u.y for u in us):.3f}..{max(u.y for u in us):.3f}  (0..1 = dentro)")
    print(f"      camara {tuple(round(x,3) for x in cam.location)}  "
          f"rot {tuple(round(math.degrees(x),1) for x in cam.rotation_euler)}  "
          f"sensor_fit {cam.data.sensor_fit} sensor {cam.data.sensor_width}")


def mirar(ang, dist, altura, objetivo, nombre, lens=60, orto=None):
    """orto = alto que debe cubrir la vista (camara ortografica, encuadre exacto y predecible)."""
    if orto:
        cam.data.type = "ORTHO"
        cam.data.ortho_scale = orto
    else:
        cam.data.type = "PERSP"
        cam.data.lens = lens
    cam.data.clip_start = 0.005
    cam.data.clip_end = 500
    cam.location = (objetivo[0] + dist * math.sin(math.radians(ang)),
                    objetivo[1] - dist * math.cos(math.radians(ang)),
                    objetivo[2] + altura)
    # la restriccion TRACK_TO manda sobre rotation_euler: hay que mover TAMBIEN el blanco, o la
    # camara se queda mirando al origen (los pies) y el encuadre sale desplazado
    blanco.location = Vector(objetivo)
    direccion = Vector(objetivo) - cam.location
    cam.rotation_euler = direccion.to_track_quat("-Z", "Y").to_euler()
    bpy.context.view_layer.update()
    visibles = [o.name for o in bpy.data.objects
                if o.type == "MESH" and not o.hide_render and o.visible_get()]
    if not visibles:
        print("AVISO: ninguna malla visible para el render")
    print(f"   camara {tuple(round(x,3) for x in cam.location)} rot "
          f"{tuple(round(math.degrees(x),1) for x in cam.rotation_euler)} mallas visibles {len(visibles)}")
    esc.render.filepath = os.path.join(SAL, nombre)
    bpy.ops.render.render(write_still=True)
    print("render: " + esc.render.filepath)


def distancia_para(alto_cubrir, lens, sensor=36.0):
    """Distancia a la que el alto dado entra completo en el encuadre (sensor AUTO: el lado mayor)."""
    fov = 2 * math.atan(sensor / (2.0 * lens))
    return (alto_cubrir / 2.0) / math.tan(fov / 2.0) * 1.12


def calibrar(ang, dist, lens=60, iteraciones=8):
    """Ajusta la altura del objetivo hasta que la caja del modelo quede centrada en el encuadre.

    No me fio de la cuenta del campo de vision (el sensor AUTO cambia segun la orientacion de la
    imagen): mido la proyeccion real y corrijo el objetivo con el error, en bucle.
    """
    from bpy_extras.object_utils import world_to_camera_view
    objetivo = list(centro)
    alto_visible = alto / 0.85            # estimacion inicial de lo que abarca el encuadre
    for _ in range(iteraciones):
        mirar(ang, dist, 0.0, objetivo, "calibracion_tmp.png", lens=lens)
        us = [world_to_camera_view(esc, cam, Vector((x, y, z)))
              for x in (mn[0], mx[0]) for y in (mn[1], mx[1]) for z in (mn[2], mx[2])]
        y0, y1 = min(u.y for u in us), max(u.y for u in us)
        alto_visible = alto / max(y1 - y0, 1e-6)
        error = (y0 + y1) / 2.0 - 0.5
        if abs(error) < 0.005:
            break
        # ojo con el signo: si el modelo sale alto en el encuadre (error > 0) hay que apuntar MAS
        # arriba para bajarlo en la imagen; al reves el bucle diverge
        objetivo[2] += error * alto_visible
    return objetivo, alto_visible


# Vista ortografica: encuadre exacto (el alto cubierto es ortho_scale), sin lios de sensor/FOV.
dist = max(alto, ancho) * 1.6
orto = alto * 1.12
print(f"vista ortografica: escala {orto:.3f} m a distancia {dist:.3f} m")
# el modelo mira a -Y (frente en +Z en el GLB): la camara a -Y (ang 0) ve la CARA
for ang, nom in ((0, "blender_01_frente.png"), (90, "blender_02_perfil_der.png"),
                 (180, "blender_03_espalda.png"), (270, "blender_04_perfil_izq.png")):
    mirar(ang, dist, 0.0, centro, nom, orto=orto)
    proyectar(nom)
if len(ARG) > 2 and ARG[2] == "cabeza":
    # primeros planos de la cabeza desde tres angulos, para revisarla de cerca
    z_cab = mx[2] - alto * 0.085
    for ang, nom in ((0, "cabeza_frente.png"), (45, "cabeza_tres_cuartos.png"),
                     (90, "cabeza_perfil.png")):
        mirar(ang, dist * 0.5, 0.0, (centro[0], centro[1], z_cab), nom, orto=alto * 0.24)
    print("TERMINADO")
    raise SystemExit(0)

# primer plano de la cara (ortografico tambien, centrado en la cabeza)
mirar(0, dist * 0.5, 0.0, (centro[0], centro[1], mx[2] - alto * 0.055), "blender_05_cara.png",
      orto=alto * 0.20)
print("TERMINADO")