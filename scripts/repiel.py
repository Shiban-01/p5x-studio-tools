"""Rehace la PIEL apoyandose en el esqueleto original: esqueleto intacto, pesos nuevos y limpios.

Por que: medido, al girar el codo 90 grados habia 242 aristas de la malla del cuerpo que se estiraban
hasta 22 veces. La causa no es la cuenta de pesos (suman 1.000 exacto) sino que parte del peso vive en
huesos auxiliares del juego (`UpperArm_L_01/_02`, `Forearm_L_01/_02`, `Calf_L_*`, `toufa_*`, `peishi_*`)
cuyas posiciones de reposo no son consistentes con las de la cadena `Bip01`: al girar una articulacion
unos vertices se van con el auxiliar y sus vecinos con el Bip01, y la malla se desgarra.

La solucion: los huesos `Bip01` (los 54 del juego, en su sitio, derivados de las inversas de bind) son
los UNICOS que deforman. Sobre esa base se recalculan pesos suaves para el cuerpo y el pelo, y los
accesorios rigidos (brazalete, lanza, vaina, pistola) se atan al 100% a un hueso anatomico. La cara,
los ojos y los parpados conservan sus pesos del juego porque funcionan (y llevan los visemas).

Uso: blender --background --python repiel.py -- <blend_entrada> <blend_salida>
"""
import sys

import bpy

ARG = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ENTRADA = ARG[0]
SALIDA = ARG[1] if len(ARG) > 1 else ENTRADA.replace(".blend", "_repiel.blend")

bpy.ops.wm.open_mainfile(filepath=ENTRADA)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
mallas = {o.name: o for o in bpy.data.objects if o.type == "MESH" and o.data.vertices}

# ---------------------------------------------------------------- 1. solo los Bip01 deforman
DEFORM_OK = ("Bip01", "BN_")
apagados = 0
for b in arm.data.bones:
    if b.name.startswith(DEFORM_OK):
        b.use_deform = True
    else:
        if b.use_deform:
            apagados += 1
        b.use_deform = False
print("huesos que deforman:", sum(1 for b in arm.data.bones if b.use_deform), "| apagados:", apagados)

# ---------------------------------------------------------------- 2. props: rigidos a un hueso
RIGIDOS = {"Kotone_Brazalete": "Bip01 L UpperArm", "Kotone_Pistola": "Bip01 R Hand",
           "Kotone_Lanza": "Bip01 Spine", "Kotone_Vaina": "Bip01 Spine"}
for nombre, hueso in RIGIDOS.items():
    o = mallas.get(nombre)
    if not o:
        continue
    for g in list(o.vertex_groups):
        o.vertex_groups.remove(g)
    g = o.vertex_groups.new(name=hueso)
    g.add([v.index for v in o.data.vertices], 1.0, "REPLACE")
    print("  %-18s atado al 100%% a %s" % (nombre, hueso))

# ---------------------------------------------------------------- 3. cuerpo y pelo: pesos nuevos
AUTOMATICOS = ("Kotone_Cuerpo", "Kotone_Pelo")

# primero se les quitan los pesos viejos, para que no quede mezcla
for nombre in AUTOMATICOS:
    o = mallas.get(nombre)
    if o:
        for g in list(o.vertex_groups):
            o.vertex_groups.remove(g)

bpy.ops.object.select_all(action="DESELECT")
for nombre in AUTOMATICOS:
    if nombre in mallas:
        mallas[nombre].select_set(True)
arm.select_set(True)
bpy.context.view_layer.objects.active = arm
# pesos por calor de hueso: suaves a lo largo de cada articulacion
bpy.ops.object.parent_set(type="ARMATURE_AUTO")
for nombre in AUTOMATICOS:
    o = mallas.get(nombre)
    if o:
        print("  %-18s grupos nuevos: %d" % (nombre, len(o.vertex_groups)))

bpy.ops.wm.save_as_mainfile(filepath=SALIDA)
print("guardado:", SALIDA)