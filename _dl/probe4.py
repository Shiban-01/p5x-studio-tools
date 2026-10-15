import sys
sys.path.insert(0, r"C:/Users/Lukas/p5x-datamining/p5x_studio")
from p5x_studio import herramientas as H
mapa = H._mapa_cues()
from collections import Counter
cnt = Counter()
ejemplos = {}
for cue, bancos in mapa.items():
    idiomas = tuple(sorted({H._idioma_de_banco(b) for b in bancos}))
    k = len(bancos)
    cnt[(len(bancos), idiomas)] += 1
    ejemplos.setdefault((len(bancos), idiomas), (cue, bancos))
for k, n in sorted(cnt.items(), key=lambda x:-x[1]):
    print("%4d  bancos=%d idiomas=%s  ej:%s" % (n, k[0], k[1], ejemplos[k]))
