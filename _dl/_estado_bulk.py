
import sys, time
sys.path.insert(0, r"C:\Users\Lukas\p5x-datamining\_dl")
from pilotar_exe import Piloto
with Piloto(9226) as p:
    print("estado:", p.texto("#bulk-estado").strip())
    print("barra :", p.js("document.querySelector('#bulk-prog-i').style.width"))
    print("consola:")
    for l in p.texto("#bulk-consola").strip().splitlines()[-5:]:
        print("   " + l)
    print("errores JS:", p.errores_js())
