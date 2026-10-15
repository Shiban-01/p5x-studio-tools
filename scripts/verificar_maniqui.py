"""Comprueba que los topes de codo y rodilla dejan doblar hacia donde dobla un cuerpo.

Para cada articulacion: suelta el tope, gira +30 y -30 grados por el eje medido, y mira hacia donde
se mueve la punta de la cadena. El cuerpo mira a -Y, asi que
  - el codo es correcto si la mano va hacia -Y (adelante), y
  - la rodilla si el pie va hacia +Y (atras).
Despues vuelve a poner el tope y confirma que ese lado es el permitido.
"""
import math
import sys
import bpy

from mathutils import Vector

bpy.ops.wm.open_mainfile(filepath=sys.argv[sys.argv.index("--") + 1])
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
print("HUESOS: %d" % len(arm.data.bones))
print("nombres:", ", ".join(b.name for b in arm.data.bones))

# hacia donde mira el personaje: la nariz frente al centro de la cabeza
cabeza = arm.data.bones["Cabeza"]
nariz = arm.data.bones.get("BN_nose")
if nariz:
    print("nariz Y=%+.3f  cabeza Y=%+.3f  => mira a %s"
          % (nariz.head_local.y, cabeza.head_local.y,
             "-Y (adelante)" if nariz.head_local.y < cabeza.head_local.y else "+Y"))

CASOS = [("Antebrazo_Izq", "Mano_Izq", -1, "mano"),
         ("Antebrazo_Der", "Mano_Der", -1, "mano"),
         ("Pantorrilla_Izq", "Pie_Izq", +1, "pie"),
         ("Pantorrilla_Der", "Pie_Der", +1, "pie")]

for hueso, punta, esperado, etiqueta in CASOS:
    pb = arm.pose.bones[hueso]
    con = next((c for c in pb.constraints if c.type == "LIMIT_ROTATION"), None)
    if con is None:
        print("%-16s SIN TOPE" % hueso)
        continue
    ejes = [e for e in "xyz" if getattr(con, "use_limit_" + e)]
    eje = [e for e in ejes if abs(getattr(con, "max_" + e) - getattr(con, "min_" + e)) > 1.0]
    eje = eje[0] if eje else ejes[0]
    indice = "xyz".index(eje)
    rango = (round(math.degrees(getattr(con, "min_" + eje))),
             round(math.degrees(getattr(con, "max_" + eje))))
    con.mute = True
    reposo = arm.matrix_world @ arm.pose.bones[punta].tail
    medido = {}
    for signo in (1, -1):
        pb.rotation_euler = [0, 0, 0]
        pb.rotation_euler[indice] = math.radians(30) * signo
        bpy.context.view_layer.update()
        d = (arm.matrix_world @ arm.pose.bones[punta].tail) - reposo
        medido[signo] = d
        print("   %-16s %+d grados -> %s se mueve (%+.2f, %+.2f, %+.2f)"
              % (hueso, signo * 30, etiqueta, d.x, d.y, d.z))
    pb.rotation_euler = [0, 0, 0]
    con.mute = False
    natural = max(medido, key=lambda s: medido[s].y * esperado)
    permitido = rango[1] > 0 if natural > 0 else rango[0] < 0
    print("   %-16s natural el signo %+d (va a %s) | rango %s | %s"
          % (hueso, natural, "+Y atras" if medido[natural].y > 0 else "-Y adelante", rango,
             "CORRECTO" if permitido else "*** AL REVES: HAY QUE CAMBIAR EL SIGNO ***"))
