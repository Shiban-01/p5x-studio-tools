
"""Reparte el peso de los huesos auxiliares (reposo poco fiable) entre los Bip01 mas cercanos AL VERTICE.

A diferencia de las versiones anteriores, aqui no se decide por el nombre del hueso ni por su posicion
de reposo (que es justo lo que esta mal), sino por donde esta el vertice: el peso auxiliar se reparte
entre los dos huesos Bip01 cuya linea pasa mas cerca de ese vertice. Los pesos que ya apuntan a Bip01
se conservan tal cual: el reparto del juego se respeta.
"""
import sys
import bpy
from mathutils import Vector
ARG = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
bpy.ops.wm.open_mainfile(filepath=ARG[0])
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
obj = bpy.data.objects["Kotone_Cuerpo"]
CAND = [(b.name, b.head_local, b.tail_local) for b in arm.data.bones if b.name.startswith("Bip01") and b.use_deform]
def seg_dist(p, a, bb):
    ab = bb - a
    t = 0.0 if ab.length_squared == 0 else max(0.0, min(1.0, (p - a).dot(ab) / ab.length_squared))
    return (p - (a + ab * t)).length
def cercanos(p, cuantos=2, potencia=4.0):
    ds = sorted(((seg_dist(p, a, bb), n) for n, a, bb in CAND))[:cuantos]
    ps = [(n, 1.0 / max(d, 1e-4) ** potencia) for d, n in ds]
    t = sum(w for _, w in ps) or 1.0
    return [(n, w / t) for n, w in ps]
nombres = {g.index: g.name for g in obj.vertex_groups}
movidos = 0
for v in obj.data.vertices:
    propios = [(nombres.get(g.group, "?"), g.weight) for g in v.groups if g.weight > 0]
    bip = [(n, w) for n, w in propios if n.startswith("Bip01")]
    aux = sum(w for n, w in propios if not n.startswith("Bip01"))
    if aux <= 0:
        continue
    reparto = {}
    if bip:
        for n, w in bip:
            reparto[n] = reparto.get(n, 0.0) + w
    for n, w in cercanos(v.co):
        reparto[n] = reparto.get(n, 0.0) + aux * w
    mejores = sorted(reparto.items(), key=lambda kv: -kv[1])[:4]
    tot = sum(w for _, w in mejores) or 1.0
    for g in list(obj.vertex_groups):
        g.remove([v.index])
    for n, w in mejores:
        g = obj.vertex_groups.get(n) or obj.vertex_groups.new(name=n)
        g.add([v.index], w / tot, "REPLACE")
    movidos += 1
print("vertices con peso auxiliar repartido:", movidos)
sumas = [sum(g.weight for g in v.groups) for v in obj.data.vertices]
print("suma de pesos: min %.3f max %.3f | huesos/vertice max %d" % (min(sumas), max(sumas), max(len(v.groups) for v in obj.data.vertices)))
bpy.ops.wm.save_as_mainfile(filepath=ARG[1])
print("guardado:", ARG[1])
