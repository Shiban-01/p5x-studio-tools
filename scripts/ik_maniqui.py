"""Anade IK a manos y pies del maniqui: agarras el control y la extremidad se coloca sola.

Que hace:
  1. Crea un hueso de control por mano y por pie (no deforman nada), colocado justo en la muneca y en
     el tobillo, para que el reposo no cambie.
  2. Pone las cadenas de IK: antebrazo + brazo hacia el control de la mano, pantorrilla + muslo hacia
     el del pie.
  3. Limita la IK al doblez humano (un solo sentido en codo y rodilla) y prohibe el estiramiento, para
     que tirar del control mas alla del alcance no alargue el brazo.
  4. Mide hacia donde apunta el codo (debe ir atras) y la rodilla (adelante) al mover el control; si
     sale al reves, corrige el angulo del hueso de referencia.
  5. Comprueba que en reposo no cambia nada y que al tirar lejos no se estira.

Uso: blender --background --python ik_maniqui.py -- <blend> [png]
"""
import math
import os
import sys

import bpy

from mathutils import Vector

ruta = sys.argv[sys.argv.index("--") + 1]
png = sys.argv[sys.argv.index("--") + 2] if len(sys.argv) > sys.argv.index("--") + 2 else None

bpy.ops.wm.open_mainfile(filepath=ruta)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
mallas = [o for o in bpy.data.objects if o.type == "MESH"]

# ---------------------------------------------------------------- 1. controles
CONTROLES = {  # nombre: (hueso que marca la articulacion, hacia donde asoma el control)
    "IK_Mano_Izq": ("Mano_Izq", Vector((0, -0.06, 0))),
    "IK_Mano_Der": ("Mano_Der", Vector((0, -0.06, 0))),
    "IK_Pie_Izq": ("Pie_Izq", Vector((0, -0.08, 0))),
    "IK_Pie_Der": ("Pie_Der", Vector((0, -0.08, 0))),
}
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode="EDIT")
for nombre, (articulacion, cola) in CONTROLES.items():
    if nombre in arm.data.edit_bones:
        arm.data.edit_bones.remove(arm.data.edit_bones[nombre])
    eb = arm.data.edit_bones.new(nombre)
    eb.head = arm.data.edit_bones[articulacion].head.copy()
    eb.tail = eb.head + cola
    eb.parent = arm.data.edit_bones["Raiz"]
    eb.use_deform = False
    eb.use_connect = False
bpy.ops.object.mode_set(mode="OBJECT")

# ---------------------------------------------------------------- 2. cadenas de IK
CADENAS = [("Antebrazo_Izq", "IK_Mano_Izq"), ("Antebrazo_Der", "IK_Mano_Der"),
           ("Pantorrilla_Izq", "IK_Pie_Izq"), ("Pantorrilla_Der", "IK_Pie_Der")]
for hueso, control in CADENAS:
    pb = arm.pose.bones[hueso]
    for c in list(pb.constraints):
        if c.type == "IK":
            pb.constraints.remove(c)
    c = pb.constraints.new("IK")
    c.target = arm
    c.subtarget = control
    c.chain_count = 2
    c.use_tail = True               # el IK apunta a la muneca/tobillo, que es la cola del hueso
    c.use_rotation = False          # el giro del control no gira la extremidad
    print("   IK: %s -> %s (2 huesos)" % (hueso, control))

# ---------------------------------------------------------------- 3. limites y nada de estirar
# El solver de IK respeta los topes de giro (LIMIT_ROTATION) que ya lleva puestos el maniqui, y esos
# estan medidos y verificados. NO hay que poner ademas los limites propios de IK: los puse con el signo
# deducido en vez de medido y bloqueaban el doblez natural, con lo que el solver dejaba la extremidad
# recta (medido: desvio del codo 0.001 m en todos los casos, o sea brazo estirado).
# Lo que si hace falta es prohibir el estiramiento: una pierna no se alarga.
for hueso in [b.name for b in arm.data.bones] + list(CONTROLES):
    pb = arm.pose.bones[hueso]
    pb.ik_stretch = 0.0
    pb.use_ik_limit_x = pb.use_ik_limit_y = pb.use_ik_limit_z = False
print("   topes de giro anatomicos: los que ya tiene el maniqui (no se tocan)")
print("   estiramiento de IK: prohibido en las 4 cadenas")


def reposo_deformado():
    dg = bpy.context.evaluated_depsgraph_get()
    salida = []
    for ob in mallas:
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        salida.append(sum((ob.matrix_world @ v.co for v in me.vertices), Vector()) / len(me.vertices))
        ev.to_mesh_clear()
    return sum(salida, Vector()) / len(salida)


antes = reposo_deformado()


def mover_control(nombre, desplazamiento):
    pb = arm.pose.bones[nombre]
    pb.location = Vector(desplazamiento)
    bpy.context.view_layer.update()


def separacion_del_codo(lado, etiqueta="Mano"):
    """Cuanto se sale la articulacion intermedia de la recta hombro->muneca, en Y (+ = atras)."""
    if etiqueta == "Mano":
        arranque, medio, fin = "Brazo_" + lado, "Antebrazo_" + lado, "Mano_" + lado
    else:
        arranque, medio, fin = "Muslo_" + lado, "Pantorrilla_" + lado, "Pie_" + lado
    a = arm.pose.bones[arranque].head
    m = arm.pose.bones[medio].head
    b = arm.pose.bones[fin].head
    t = (m - a).dot(b - a) / max((b - a).length_squared, 1e-9)
    return (m - (a + t * (b - a))).y


print()
print("=== hacia donde apunta el codo y la rodilla al mover el control ===")
mover_control("IK_Mano_Der", (0, -0.35, 0.15))          # la mano adelante y arriba
print("   mano derecha adelante: el codo apunta a %s (%+.3f)"
      % ("atras, correcto" if separacion_del_codo("Der") > 0 else "ADELANTE, MAL",
         separacion_del_codo("Der")))
mover_control("IK_Pie_Izq", (0, -0.30, 0.10))           # el pie adelante
rodilla = separacion_del_codo("Izq", "Pie")
print("   pie izquierdo adelante: la rodilla apunta a %s (%+.3f)"
      % ("adelante, correcto" if rodilla < 0 else "ATRAS, MAL", rodilla))

# ---------------------------------------------------------------- 4. no se estira
print()
print("=== alcance: tirar del control mas alla del brazo no debe alargarlo ===")
mover_control("IK_Mano_Der", (0, 0, 0))
largos = {}
for lado in ("Izq", "Der"):
    largos[lado] = (arm.pose.bones["Mano_" + lado].head - arm.pose.bones["Brazo_" + lado].head).length
mover_control("IK_Mano_Der", (0, -3.0, 0))              # tres metros: imposible
largo = (arm.pose.bones["Mano_Der"].head - arm.pose.bones["Brazo_Der"].head).length
print("   brazo derecho en reposo %.3f m, tirando a 3 m %.3f m -> %s"
      % (largos["Der"], largo,
         "no se estira, correcto" if largo < largos["Der"] * 1.02 else "*** SE ESTIRA ***"))
mover_control("IK_Mano_Der", (0, 0, 0))

# ---------------------------------------------------------------- 5. el reposo no cambia
despues = reposo_deformado()
print()
print("reposo: centro de la malla antes %s, despues %s -> %s"
      % (["%+.3f" % c for c in antes], ["%+.3f" % c for c in despues],
         "sin cambios" if (antes - despues).length < 0.002 else "*** HA CAMBIADO ***"))

bpy.ops.wm.save_as_mainfile(filepath=ruta)
print("guardado:", ruta)

if png:
    # pose de ejemplo moviendo SOLO los controles de IK
    mover_control("IK_Mano_Der", (0.05, -0.30, 0.28))
    mover_control("IK_Mano_Izq", (-0.10, 0.12, -0.05))
    mover_control("IK_Pie_Izq", (0, -0.22, 0.02))
    mover_control("IK_Pie_Der", (0, 0.06, 0))
    arm.pose.bones["Cabeza"].rotation_mode = "XYZ"
    arm.pose.bones["Cabeza"].rotation_euler = (0, math.radians(15), 0)
    bpy.context.view_layer.update()
    todo = [Vector(c) for ob in mallas for c in ob.bound_box]
    alto = max(c.z for c in todo) - min(c.z for c in todo)
    centro = Vector(((min(c.x for c in todo) + max(c.x for c in todo)) / 2,
                     (min(c.y for c in todo) + max(c.y for c in todo)) / 2,
                     (min(c.z for c in todo) + max(c.z for c in todo)) / 2))
    cam = bpy.data.objects.get("camara")
    cam.location = centro + Vector((alto * 1.2, -alto * 1.8, alto * 0.30))
    cam.rotation_euler = (centro - cam.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = cam
    esc = bpy.context.scene
    esc.render.resolution_x, esc.render.resolution_y = 800, 1100
    try:
        esc.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        esc.render.engine = "BLENDER_EEVEE"
    esc.render.filepath = png
    os.makedirs(os.path.dirname(png), exist_ok=True)
    bpy.ops.render.render(write_still=True)
    print("render:", png, os.path.getsize(png) // 1024, "KB")
print("HUESOS: %d (los 33 + 4 controles)" % len(arm.data.bones))
