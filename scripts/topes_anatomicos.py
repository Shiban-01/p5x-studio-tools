"""Normaliza los ejes del maniqui y pone topes humanos, para que no se puedan hacer posturas imposibles.

1. Orienta el eje del hueso (su "roll") para que DOBLAR sea siempre el mismo eje (local X) en todas
   las articulaciones. Asi posar deja de ser adivinar: X dobla, Y gira sobre si mismo, Z desvia.
2. Mide, articulacion por articulacion, hacia donde lleva cada eje (adelante, atras, arriba, afuera)
   y con que signo.
3. Pone los topes con rangos humanos: el codo y la rodilla doblan en un solo sentido y casi no tienen
   doblez lateral; los hombros y caderas tienen flexion amplia, giro moderado y abduccion limitada.
4. Deja una pose de ejemplo natural y la comprueba midiendo cada articulacion.

Uso: blender --background --python topes_anatomicos.py -- <blend_maniqui> [png_prueba]
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

# ---------------------------------------------------------------- 1. ejes
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode="EDIT")
for eb in arm.data.edit_bones:
    d2 = (eb.tail - eb.head).normalized()
    if eb.parent is None:
        eje = Vector((0, 1, 0))
    else:
        d1 = (eb.parent.tail - eb.parent.head).normalized()
        eje = d1.cross(d2)
        if eje.length < 1e-4:                       # hueso recto con su padre: un eje estable
            eje = d2.cross(Vector((0, 0, 1)))
            if eje.length < 1e-4:
                eje = d2.cross(Vector((0, 1, 0)))
    eb.align_roll(eje.normalized().cross(d2))       # Z = X x Y  =>  X queda en el eje de doblez
bpy.ops.object.mode_set(mode="OBJECT")

# ---------------------------------------------------------------- 2. medir los ejes
for pb in arm.pose.bones:                           # fuera topes viejos y poses viejas
    for c in list(pb.constraints):
        if c.type == "LIMIT_ROTATION":
            pb.constraints.remove(c)
    pb.rotation_mode = "XYZ"
    pb.rotation_euler = (0, 0, 0)
    pb.location = (0, 0, 0)
    pb.scale = (1, 1, 1)
bpy.context.view_layer.update()


def hijos(hueso):
    return [b.name for b in arm.data.bones if b.parent and b.parent.name == hueso]


def probar(hueso, indice, grados=10):
    """Suelta el hueso +-grados por un eje y devuelve el desplazamiento y la posicion de la punta."""
    pb = arm.pose.bones[hueso]
    cola = hijos(hueso)
    punta = cola[0] if cola else hueso
    base = (arm.matrix_world @ arm.pose.bones[punta].tail).copy()
    salida = {}
    for signo in (1, -1):
        pb.rotation_euler = [0, 0, 0]
        pb.rotation_euler[indice] = math.radians(grados) * signo
        bpy.context.view_layer.update()
        pos = (arm.matrix_world @ arm.pose.bones[punta].tail).copy()
        salida[signo] = (pos - base, pos)
    pb.rotation_euler = [0, 0, 0]
    bpy.context.view_layer.update()
    return salida


def criterio(hueso, desp, pos_punta):
    """Cuanto de humano tiene un movimiento, segun la articulacion.

    No vale "siempre adelante": el codo lleva la mano adelante, pero la rodilla lleva el PIE ATRAS, y
    los dedos se curvan hacia la palma, no hacia adelante. Con un criterio unico, la rodilla salia con
    el tope del reves (hiperextension) y los dedos tambien.
    """
    if hueso.startswith("Dedo"):                        # la punta se acerca a la muneca
        mano = arm.pose.bones["Mano_" + ("Izq" if hueso.endswith("Izq") else "Der")].head
        return (mano - pos_punta).normalized().dot(desp)
    if hueso.startswith("Pantorrilla"):                 # la rodilla lleva el pie atras
        return desp.y
    if hueso.startswith(("DedoPie", "Pie")):            # el pie dobla los dedos hacia la espinilla
        return desp.z
    return -desp.y                                      # lo demas: hacia adelante


def describir(d, hueso=""):
    """Traduce un desplazamiento a palabras: adelante/atras (Y), arriba/abajo (Z), afuera (X)."""
    es_izq = hueso.endswith("Izq")
    partes = []
    if d.y < -0.004:
        partes.append("adelante")
    if d.y > 0.004:
        partes.append("atras")
    if d.z > 0.004:
        partes.append("arriba")
    if d.z < -0.004:
        partes.append("abajo")
    if abs(d.x) > 0.004:
        partes.append("afuera" if d.x * (1 if es_izq else -1) > 0 else "adentro")
    return "/".join(partes) or "apenas se mueve"


print("=== hacia donde lleva cada eje (10 grados) ===")
for hueso in ("Brazo_Der", "Antebrazo_Der", "Mano_Der", "Muslo_Der", "Pantorrilla_Der",
              "Pie_Der", "Dedo2_Der", "Cuello", "Cabeza", "Columna_1"):
    hueso_es_izq = hueso.endswith("Izq")
    texto = []
    for indice, nombre in enumerate("XYZ"):
        d = probar(hueso, indice)
        largo = {s: round(v[0].length, 3) for s, v in d.items()}
        pos = describir(d[1][0])
        neg = describir(d[-1][0])
        texto.append("%s:+%s(%s) -%s(%s)" % (nombre, largo[1], pos, largo[-1], neg))
    print("   %-16s %s" % (hueso, "  ".join(texto)))

# ---------------------------------------------------------------- 3. topes humanos
# (flexion_adelante, extension_atras, giro_sobre_si, abduccion, aduccion) en grados.
# El signo del doblez se decide midiendo: +X si al girar +10 la punta va adelante, -X si va atras.
TOPE = {
    "Muslo":       (120, 25, 40, 45, 25),
    "Pantorrilla": (150, 0, 15, 6, 6),          # rodilla: un solo sentido, casi nada lateral
    "Brazo":       (165, 55, 80, 160, 40),
    "Antebrazo":   (150, 0, 80, 6, 6),          # codo: un solo sentido, casi nada lateral
    "Mano":        (70, 70, 85, 20, 20),
    "Pie":         (45, 45, 15, 20, 20),
    "Dedo":        (95, 5, 15, 10, 10),
    "DedoPie":     (60, 20, 10, 10, 10),
    "Cuello":      (45, 45, 60, 30, 30),
    "Cabeza":      (35, 35, 60, 30, 30),
    "Columna_1":   (30, 30, 30, 20, 20),
    "Columna_2":   (30, 30, 30, 20, 20),
    "Pecho":       (30, 30, 30, 20, 20),
    "Cadera":      (40, 20, 25, 25, 25),
}
print()
print("=== topes puestos y signo medido ===")
for hueso in [b.name for b in arm.data.bones]:
    if hueso == "Raiz":
        continue
    clave = next((k for k in TOPE if hueso.startswith(k)), None)
    if clave is None:
        continue
    flex, ext, giro, abd, adu = TOPE[clave]
    pb = arm.pose.bones[hueso]
    # el sentido de la flexion se mide con el criterio de ESA articulacion, no con una regla general
    d = probar(hueso, 0)
    positivo_es_flexion = (criterio(hueso, d[1][0], d[1][1])
                           > criterio(hueso, d[-1][0], d[-1][1]))
    if positivo_es_flexion:
        x_min, x_max = -ext, flex
    else:
        x_min, x_max = -flex, ext
    # en Z, el lado positivo se reserva para la abduccion (la que separa el miembro del cuerpo)
    dz = probar(hueso, 2)
    _dx = abs(dz[1][0].x) + abs(dz[-1][0].x)
    fuera_positivo = (dz[1][0].x * (1 if hueso.endswith("Izq") else -1) > 0
                      if _dx > 0.002 else True)
    c = pb.constraints.new("LIMIT_ROTATION")
    c.owner_space = "LOCAL"
    for indice, nombre in enumerate("XYZ"):
        setattr(c, "use_limit_" + nombre.lower(), True)
    c.min_x, c.max_x = math.radians(x_min), math.radians(x_max)
    c.min_y, c.max_y = math.radians(-giro), math.radians(giro)
    if fuera_positivo:
        c.min_z, c.max_z = math.radians(-adu), math.radians(abd)
    else:
        c.min_z, c.max_z = math.radians(-abd), math.radians(adu)
    sentido = describir(d[1 if positivo_es_flexion else -1][0], hueso)
    print("   %-16s X %+4d..%+4d (la flexion lleva la punta %-16s) Y +-%3d  Z %+4d..%+4d"
          % (hueso, x_min, x_max, sentido, giro,
             int(math.degrees(c.min_z)), int(math.degrees(c.max_z))))

# ---------------------------------------------------------------- 4. pose de ejemplo
# Solo se usa X (doblez), con el signo que se acaba de medir, y dentro de los topes. Nada de giros.
G = math.radians
POSE = {"Columna_1": 5, "Columna_2": 4, "Pecho": 3, "Cuello": -6, "Cabeza": -4,
        "Brazo_Der": 75, "Antebrazo_Der": 60, "Mano_Der": -10,
        "Brazo_Izq": -25, "Antebrazo_Izq": 35,
        "Muslo_Izq": 30, "Pantorrilla_Izq": 40, "Pie_Izq": -18,
        "Muslo_Der": -12, "Pantorrilla_Der": 12}
def angulo_articulacion(hueso):
    """Cuanto doblan estas dos piezas entre si, ahora mismo."""
    b = arm.data.bones[hueso]
    if b.parent is None:
        return None
    p = arm.pose.bones[b.parent.name]
    return (p.tail - p.head).normalized().angle((arm.pose.bones[hueso].tail
                                                 - arm.pose.bones[hueso].head).normalized())


def punta_de(hueso):
    return (hijos(hueso) or [hueso])[0]


reposo = {h: (angulo_articulacion(h),
              (arm.matrix_world @ arm.pose.bones[punta_de(h)].tail).copy()) for h in POSE}

# Primera pasada: medir el sentido de la flexion de cada articulacion SIN nada posado. Hacerlo
# dentro del bucle de posado no vale: cuando le tocaba a la rodilla, el muslo ya estaba girado y la
# medicion se hacia en un sistema girado, con lo que el sentido salia al reves (la rodilla doblaba
# hacia adelante).
SIGNOS = {}
for hueso in POSE:
    d = probar(hueso, 0)
    SIGNOS[hueso] = 1 if criterio(hueso, d[1][0], d[1][1]) > criterio(hueso, d[-1][0], d[-1][1]) else -1

for hueso, grados in POSE.items():
    pb = arm.pose.bones[hueso]
    pb.rotation_mode = "XYZ"
    pb.rotation_euler = (G(grados) * SIGNOS[hueso], 0, 0)
bpy.context.view_layer.update()

print()
print("=== cada articulacion EN AISLAMIENTO (lo unico concluyente: en la pose compuesta la punta")
print("    de una articulacion la mueve tambien la de al lado, y salen falsos avisos) ===")


def esperado(hueso, grados):
    """Que deberia hacer esta articulacion con este valor, si el rig es humano."""
    flex = grados > 0
    if hueso.startswith("Antebrazo"):
        return "adelante" if flex else "BLOQUEADO"
    if hueso.startswith("Pantorrilla"):
        return "atras" if flex else "BLOQUEADO"
    if hueso.startswith("DedoPie"):
        return "arriba" if flex else "BLOQUEADO"
    if hueso.startswith("Dedo"):
        return "palma" if flex else "BLOQUEADO"
    if hueso.startswith(("Brazo", "Muslo")):
        return "adelante" if flex else "atras"
    return None


fallos = 0
for hueso, grados in POSE.items():
    for h in POSE:
        arm.pose.bones[h].rotation_euler = (0, 0, 0)
    bpy.context.view_layer.update()
    antes_ang, antes_punta = reposo[hueso] if False else (
        angulo_articulacion(hueso),
        (arm.matrix_world @ arm.pose.bones[punta_de(hueso)].tail).copy())
    arm.pose.bones[hueso].rotation_euler = (G(grados) * SIGNOS[hueso], 0, 0)
    bpy.context.view_layer.update()
    delta = math.degrees(abs(angulo_articulacion(hueso) - antes_ang))
    direccion = describir((arm.matrix_world @ arm.pose.bones[punta_de(hueso)].tail) - antes_punta,
                          hueso)
    quien = esperado(hueso, grados)
    if quien is None:
        veredicto = ""
    elif quien == "BLOQUEADO":
        veredicto = ("BLOQUEADO, correcto (el tope no deja)" if delta < 2.0
                     else "*** DEJA DOBLAR AL REVES (%0.f grados) ***" % delta)
        if delta >= 2.0:
            fallos += 1
    elif quien == "palma":
        veredicto = "curva hacia la palma (ver aparte)"
    elif quien in direccion:
        veredicto = "correcto (%s)" % quien
    else:
        veredicto = "*** MAL: deberia ir %s ***" % quien
        fallos += 1
    print("   %-16s pide %+4d  dobla %5.1f  la punta va %-22s %s"
          % (hueso, grados, delta, direccion, veredicto))
for h in POSE:
    arm.pose.bones[h].rotation_euler = (0, 0, 0)
bpy.context.view_layer.update()
print("fallos: %d" % fallos)

print()
print("=== lo que el rig YA NO deja hacer: pedirle a cada articulacion el sentido imposible ===")
PROHIBIDO = {"Pantorrilla_Izq": -40, "Pantorrilla_Der": -40, "Antebrazo_Der": -50,
             "Antebrazo_Izq": -50, "Dedo2_Der": -30, "DedoPie_Izq": -25}
for hueso, grados in PROHIBIDO.items():
    for h in PROHIBIDO:
        arm.pose.bones[h].rotation_euler = (0, 0, 0)
    bpy.context.view_layer.update()
    antes = angulo_articulacion(hueso)
    arm.pose.bones[hueso].rotation_euler = (G(grados) * SIGNOS.get(hueso, 1), 0, 0)
    bpy.context.view_layer.update()
    delta = math.degrees(abs(angulo_articulacion(hueso) - antes))
    print("   %-16s pido %+4d (imposible)  doblo %4.1f  %s"
          % (hueso, grados, delta,
             "el tope lo impide, correcto" if delta < 6.0 else "*** LO PERMITE ***"))
for h in PROHIBIDO:
    arm.pose.bones[h].rotation_euler = (0, 0, 0)
bpy.context.view_layer.update()

# que ningun vertice se quede sin peso y que en reposo la deformacion sea nula
sin_peso = 0
for ob in mallas:
    for v in ob.data.vertices:
        if sum(e.weight for e in v.groups) < 0.99:
            sin_peso += 1
print("vertices sin peso completo: %d" % sin_peso)

bpy.ops.wm.save_as_mainfile(filepath=ruta)
print("guardado:", ruta)

if png:
    # la pose de ejemplo se aplica SOLO para el render: el fichero guardado queda en reposo
    for hueso, grados in POSE.items():
        arm.pose.bones[hueso].rotation_euler = (G(grados) * SIGNOS[hueso], 0, 0)
    bpy.context.view_layer.update()
    todo = [Vector(c) for ob in mallas for c in ob.bound_box]
    alto = max(c.z for c in todo) - min(c.z for c in todo)
    centro = Vector(((min(c.x for c in todo) + max(c.x for c in todo)) / 2,
                     (min(c.y for c in todo) + max(c.y for c in todo)) / 2,
                     (min(c.z for c in todo) + max(c.z for c in todo)) / 2))
    cam = bpy.data.objects.get("camara")
    cam.location = centro + Vector((alto * 1.1, -alto * 1.8, alto * 0.28))
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
