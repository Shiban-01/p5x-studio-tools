import sys, json, shutil
from pathlib import Path
sys.path.insert(0, 'C:/Users/Lukas/p5x-datamining/p5x_studio')
from p5x_studio import rig_unitypy, ajustes, catalogo, glb_rig
from p5x_studio.extractor import _es_del_traje

RAIZ = ajustes.carpeta_bundles()
e = next(x for x in catalogo.personajes() if x['id'] == 'closer')
T = next(t for t in e['trajes'] if t['clave'] == 'normal')
base = [RAIZ / f for f in T['ficheros'] if 'role_' not in f]
claves = [t['clave'] for t in e['trajes']]
filtro = lambda n: _es_del_traje(n, 'closer', 'normal', claves)

for rig in ['140/role__uniform5f23c883.bundle', '049/role_swimsuit1d754547.bundle',
            '125/role_er_thiefeba4741.bundle', '092/role_swimsuit3b8c3cd.bundle']:
    etq = rig.split('/')[-1][:18]
    dump = Path('C:/Users/Lukas/p5x-datamining/_dl/probe_rig/' + etq)
    shutil.rmtree(dump, ignore_errors=True)
    fich = base + [RAIZ / rig]
    rig_unitypy.volcar(fich, dump, 'CLOSER', log=lambda s: None, filtro=filtro)
    st = glb_rig.construir(dump, dump / 'x.glb', 'CLOSER', texturas=[Path('C:/Users/Lukas/p5x-datamining/p5x_studio/modelos_extraidos/closer_closer_normal')], log=lambda s: None)
    print(etq, 'huesos', st['huesos'], 'mallas', st['mallas'], 'mb', st['mb'])