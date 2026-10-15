"""Retoque del sombreado: mide, por bust-up, cuanto cambia el shader y con que parametros.

Para cada bust-up emparejado monta el retrato SIN sombrear, le aplica el shader con SU JSON y compara
los dos: color medio, y el color de las zonas claras (que es donde el tinte calido se nota y donde
canta si el degradado se esta aplicando de mas).

Uso:  retoque_shader.py [n]      (n = cuantos bust-ups, por defecto 12; 0 = los 120)
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

DL = Path(r"C:\Users\Lukas\p5x-datamining\_dl")
sys.path.insert(0, str(DL))
sys.path.insert(0, r"C:\Users\Lukas\p5x-datamining\p5x_studio")
import sombreado_lihui as S  # noqa: E402
from p5x_studio import bustups  # noqa: E402

CARPETA = Path(r"C:\Users\Lukas\Desktop\P5X Studio Tools\extracted\portraits")
LUM = np.array([0.2125, 0.7154, 0.0721], dtype=np.float32)


def color_de_zona(im, umbral=210, minimo=200):
    """Color medio de los pixeles claros (donde el tinte calido canta) y su luminancia."""
    a = np.asarray(im.convert("RGBA"), dtype=np.float32)
    vis = a[..., 3] > 128
    rgb = a[..., :3] / 255.0
    lum = (rgb * LUM).sum(-1)
    claros = vis & (lum > umbral / 255.0)
    if claros.sum() < minimo:
        return None, lum[vis].mean() if vis.any() else 0.0, 0
    return rgb[claros].mean(0), lum[vis].mean(), int(claros.sum())


def tinte(rgb):
    """Cuanto de calido: R-B y el matiz en grados."""
    r, g, b = rgb
    return r - b, (r - g), (g - b)


def main():
    cuantos = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    datos = json.loads((DL / "emparejado_bustups.json").read_text(encoding="utf-8"))["emparejados"]
    lista = sorted(datos.items())
    if cuantos:
        lista = lista[:cuantos]

    print("%-40s | %-22s | %-24s | %s" % ("bust-up", "JSON (params clave)", "claro sin shader", "claro con shader"))
    print("-" * 128)
    filas = []
    for clave, info in lista:
        r = bustups.montar(clave, None, CARPETA, guardar=True)
        if not r.get("ok"):
            print("%-40s | no monta: %s" % (clave.replace("UI-DialogShader-", ""), r.get("error")))
            continue
        crudo = Image.open(r["ruta"]).convert("RGBA")
        p = S.leer_parametros(DL / "lihui_shader_json" / ("%s.json" % clave))
        sombreado = S.sombrear_imagen(crudo, p)

        c0, l0, n0 = color_de_zona(crudo)
        c1, l1, n1 = color_de_zona(sombreado)
        params = "EF %.2f B %.2f S %.2f C %.2f | GraB %.2f GraS %.2f GraC %.2f" % (
            p["effect_factor"], p["brillo"], p["saturacion"], p["contraste"],
            p["gra_brillo"], p["gra_saturacion"], p["gra_contraste"])

        def fmt(c):
            if c is None:
                return "(sin claros)"
            return "#%02X%02X%02X  calido %+.3f" % (int(c[0] * 255), int(c[1] * 255), int(c[2] * 255),
                                                    float(c[0] - c[2]))
        print("%-40s | %-22s | %-24s | %s" % (clave.replace("UI-DialogShader-", ""), params[:22], fmt(c0), fmt(c1)))
        if c0 is not None and c1 is not None:
            filas.append((clave, c0, c1, l0, l1))

    if filas:
        d_calido = np.array([float(c1[0] - c1[2]) - float(c0[0] - c0[2]) for _, c0, c1, _, _ in filas])
        d_lum = np.array([float(l1) - float(l0) for _, _, _, l0, l1 in filas])
        print()
        print("de %d bust-ups con zonas claras:" % len(filas))
        print("   calidez (R-B) que SUMA el shader: media %+.3f | min %+.3f | max %+.3f"
              % (d_calido.mean(), d_calido.min(), d_calido.max()))
        print("   luminancia que cambia el shader : media %+.3f | min %+.3f | max %+.3f"
              % (d_lum.mean(), d_lum.min(), d_lum.max()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())