import json, struct, sys
from pathlib import Path
import bpy
from mathutils import Matrix
ruta = sys.argv[sys.argv.index("--") + 1]
objetivo = sys.argv[sys.argv.index("--") + 2]
b=Path(ruta).read_bytes(); off=12; js=None
while off<len(b):
    ln,ty=struct.unpack_from('<II',b,off); off+=8; c=b[off:off+ln]; off+=ln
    if ty==0x4E4F534A: js=json.loads(c.decode('utf-8'))
def mul(A,B): return [[sum(A[i][k]*B[k][j] for k in range(4)) for j in range(4)] for i in range(4)]
def trs(n):
    t=n.get('translation',[0,0,0]); q=n.get('rotation',[0,0,0,1]); s=n.get('scale',[1,1,1])
    x,y,z,w=q
    R=[[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],[2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],[2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]]
    M=[[1.0 if i==j else 0.0 for j in range(4)] for i in range(4)]
    for i in range(3):
        for j in range(3): M[i][j]=R[i][j]*s[j]
        M[i][3]=t[i]
    return M
padres={}
for i,n in enumerate(js['nodes']):
    for c2 in n.get('children',[]): padres[c2]=i
def glob(i):
    M=trs(js['nodes'][i]); p=padres.get(i)
    while p is not None:
        M=mul(trs(js['nodes'][p]),M); p=padres.get(p)
    return M
CADENA=['t_persona','Bip01','Bip01 Pelvis','Bip01 Spine','Bip01 Spine1','Bip01 Spine2','Bip01 Neck','Bip01 Head']
bi=next(i for i,n in enumerate(js['nodes']) if n.get('name')==objetivo)
G=glob(bi)
sk=js['skins'][0]
k=sk['joints'].index(bi)
ibm=sk['inverseBindMatrices']
print('glTF nodo %s: global=' % objetivo, [round(G[i][3],4) for i in range(3)])
print('   nodo padre:', js['nodes'][padres[bi]].get('name') if padres.get(bi) is not None else None)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=ruta)
arm=next(o for o in bpy.data.objects if o.type=='ARMATURE')
for nm in CADENA:
    if nm not in arm.data.bones: continue
    bo2=arm.data.bones[nm]; pb2=arm.pose.bones[nm]
    i2=next((i for i,n in enumerate(js['nodes']) if n.get('name')==nm), None)
    G2=glob(i2) if i2 is not None else None
    print('%-16s REST t=%s   POSE t=%s   gltf t=%s' % (nm,
        [round(x,4) for x in bo2.matrix_local.translation],
        [round(x,4) for x in pb2.matrix.translation],
        [round(x,4) for x in G2[i][3] for i in (0,1,2)] if G2 else None))
    print('%-16s      padre rest=%s  padre gltf=%s' % ('', bo2.parent.name if bo2.parent else None,
        js['nodes'][padres[i2]].get('name') if padres.get(i2) is not None else None))

bo=arm.data.bones[objetivo]; pb=arm.pose.bones[objetivo]
print('Blender rest (edit) matrix_local:')
for r in bo.matrix_local: print('   ', [round(x,4) for x in r])
print('Blender pose matrix:')
for r in pb.matrix: print('   ', [round(x,4) for x in r])
dif = pb.matrix @ bo.matrix_local.inverted()
print('pose * rest^-1:')
for r in dif: print('   ', [round(x,4) for x in r])
