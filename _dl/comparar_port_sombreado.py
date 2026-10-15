"""Comprueba que el sombreado de la app (p5x_studio.sombreado) da lo mismo que el de referencia.

Compara, pixel a pixel, el modulo de la app (sin numpy, con tablas) contra sombreado_lihui.py
(con numpy) para los mismos parametros.
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

DL = Path(r"C:\Users\Lukas\p5x-datamining\_dl")
APP = Path(r"C:\Users\Lukas\p5x-datamining\p5x_studio")
sys.path.insert(0, str(DL))
sys.path.insert(0, str(APP))
import exportar_shaders_app  # noqa: E402
import sombreado_lihui as S  # noqa: E402
from p5x_studio import bustups, sombreado  # noqa: E402

CARPETA = Path(r"C:\Users\Lukas\Desktop\P5X Studio Tools\extracted\portraits")
CLAVES = ["UI-DialogShader-changfu01-xiachuanling", "UI-DialogShader-changfu01-lizi",
          "UI-DialogShader-changfu-xindaozhen", "UI-DialogShader-changfu01-jianajun"]


for clave in CLAVES:
    r = bustups.montar(clave, None, CARPETA, guardar=True)
    if not r.get("ok"):
        print("%-44s no monta" % clave)
        continue
    montaje = Image.open(r["ruta"]).convert("RGBA")
    ruta_json = DL / "lihui_shader_json" / ("%s.json" % clave)
    p_ref = S.leer_parametros(ruta_json)
    # para traducir los parametros, la misma funcion que usa el exportador: si se deriva aqui a mano,
    # el comparador se queda con las reglas viejas y despues acusa al port de diferencias que no son
    p_app = exportar_shaders_app.parametros(ruta_json)
    # los parametros del JSON empaquetado, que son los que usara la herramienta
    p_emb = sombreado.parametros(clave)

    ref = S.sombrear_imagen(montaje, p_ref)
    mio = sombreado.sombrear(montaje, p_app)

    a = np.asarray(ref, dtype=np.int16)
    b = np.asarray(mio, dtype=np.int16)
    dif = np.abs(a[..., :3] - b[..., :3])
    print("%-44s %s" % (clave.replace("UI-DialogShader-", ""), montaje.size))
    print("    diferencia media %.2f/255   maxima %d   p99 %.1f" % (dif.mean(), dif.max(), np.percentile(dif, 99)))

    if p_emb:
        mio2 = sombreado.sombrear(montaje, p_emb)
        c = np.asarray(mio2, dtype=np.int16)
        dif2 = np.abs(c[..., :3] - a[..., :3])
        print("    con los parametros empaquetados, contra la referencia: media %.2f/255  maxima %d"
              % (dif2.mean(), dif2.max()))
    else:
        print("    OJO: sin parametros empaquetados para esta clave")