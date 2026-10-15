"""Saca, con el Python de la app, un retrato con y sin shader y lo pone al lado de la captura del juego."""
import sys
import time
from pathlib import Path

sys.path.insert(0, r"C:\Users\Lukas\p5x-datamining\p5x_studio")
from PIL import Image  # noqa: E402

from p5x_studio import bustups  # noqa: E402

CARPETA = Path(r"C:\Users\Lukas\Desktop\P5X Studio Tools\extracted\portraits")
SALIDA = Path(r"C:\Users\Lukas\p5x-datamining\_dl\prueba_sombreado")
CLAVES = [("UI-DialogShader-changfu01-xiachuanling", "arreglo_shader_xiachuanling"),
          ("UI-DialogShader-changfu01-lizi", "arreglo_shader_lizi"),
          ("UI-DialogShader-changfu01-jianajun", "arreglo_shader_jianajun")]
SALIDA.mkdir(parents=True, exist_ok=True)

for clave, nombre in CLAVES:
    t = time.time()
    a = bustups.montar(clave, None, CARPETA, guardar=True)
    t_sin = time.time() - t
    t = time.time()
    b = bustups.montar(clave, None, CARPETA, guardar=True, shader=True)
    t_con = time.time() - t
    if not (a.get("ok") and b.get("ok")):
        print("%-40s no monta" % clave)
        continue
    print("%-42s montar %.2f s | con shader %.2f s | shader %s"
          % (clave.replace("UI-DialogShader-", ""), t_sin, t_con, b.get("shader")))
    sin = Image.open(a["ruta"]).convert("RGBA")
    con = Image.open(b["ruta"]).convert("RGBA")
    ancho = sin.size[0] + con.size[0]
    tira = Image.new("RGBA", (ancho, max(sin.size[1], con.size[1])), (24, 26, 32, 255))
    tira.alpha_composite(sin, (0, 0))
    tira.alpha_composite(con, (sin.size[0], 0))
    tira.convert("RGB").save(SALIDA / ("%s.png" % nombre))
    print("    tira: %s" % (SALIDA / ("%s.png" % nombre)))