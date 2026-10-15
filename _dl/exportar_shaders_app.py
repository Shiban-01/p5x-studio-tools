"""Vuelca a datos/shaders.json los parametros del shader de cada bust-up, para que la herramienta
pueda pintar el retrato con y sin shader sin depender de la carpeta _dl.

Uso:  exportar_shaders_app.py
"""
import json
from pathlib import Path

DL = Path(r"C:\Users\Lukas\p5x-datamining\_dl")
DESTINO = Path(r"C:\Users\Lukas\p5x-datamining\p5x_studio\p5x_studio\datos\shaders.json")


def parametros(ruta_json: Path) -> dict:
    d = json.loads(ruta_json.read_text(encoding="utf-8", errors="replace"))
    g = d["gradient"]
    n = int(g["m_NumColorKeys"])
    paradas = []
    for i in range(n):
        k = g["key%d" % i]
        paradas.append([round(g["ctime%d" % i] / 65535.0, 5), [k["r"], k["g"], k["b"]]])
    paradas.sort(key=lambda p: p[0])
    # Claves de ALFA del Gradient de Unity: estan en los indices m_NumColorKeys..+m_NumAlphaKeys-1
    # del array `key`, con tiempos `atime`. Antes no se extraian: el shader usa Gradient.Evaluate(t)
    # que devuelve (r, g, b, a) y el alfa modula la fuerza del degradado.
    nc = n
    na = int(g.get("m_NumAlphaKeys", 0))
    alfa_gradiente = []
    for i in range(na):
        idx = nc + i
        if idx < 8:
            alfa_gradiente.append([round(g.get("atime%d" % i, 0) / 65535.0, 5), g["key%d" % idx]["a"]])
    alfa_gradiente.sort(key=lambda p: p[0])
    # La rampa de alfa va de la posicion 0 a la 1 (lo escribe el codigo del juego, no los ficheros: la
    # de abajo es un `xorps` a 0.0 y la de arriba una constante del .rdata que vale 1.0, ambas leidas
    # en UIMultipleMaterial.Update, RVA 0x23C3DA0). Los valores son GradientAlphaBottom/Top.
    return {
        "effect_factor": d.get("EffectFactor", 1.0),
        "brillo": d.get("Brightness", 1.0),
        "saturacion": d.get("Saturation", 1.0),
        "contraste": d.get("Contrast", 1.0),
        "alfa_arriba": d.get("GradientAlphaTop", 1.0),
        "alfa_abajo": d.get("GradientAlphaBottom", 1.0),
        "alfa_pos_abajo": 0.0,
        "alfa_pos_arriba": 1.0,
        "gra_brillo": d.get("GraBrightness", 1.0),
        "gra_saturacion": d.get("GraSaturation", 1.0),
        "gra_contraste": d.get("GraContrast", 1.0),
        "desenfoque": int(d.get("EnableFastBlur", 0) or 0),
        "fuerza_desenfoque": d.get("BlurStrength", 0.0),
        "modo": d.get("gradientMode", 0.0),
        "angulo": d.get("Angle", 0.0),
        "centro": [d["Center"]["x"], d["Center"]["y"]],
        "proporcion": [d["Ratio"]["x"], d["Ratio"]["y"]],
        "paradas": paradas,
        "alfa_gradiente": alfa_gradiente,
    }


def main():
    emparejados = json.loads((DL / "emparejado_bustups.json").read_text(encoding="utf-8"))["emparejados"]
    carpeta = DL / "lihui_shader_json"
    por_bustup, sin_json, con_desenfoque = {}, [], []
    for clave in emparejados:
        f = carpeta / ("%s.json" % clave)
        if not f.exists():
            sin_json.append(clave)
            continue
        p = parametros(f)
        por_bustup[clave] = p
        if p["desenfoque"]:
            con_desenfoque.append(clave)

    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    DESTINO.write_text(json.dumps({"por_bustup": por_bustup}, ensure_ascii=False), encoding="utf-8")
    print("escrito:", DESTINO, "%.1f KB" % (DESTINO.stat().st_size / 1024))
    print("bust-ups con parametros: %d de %d" % (len(por_bustup), len(emparejados)))
    if sin_json:
        print("sin JSON de shader (%d): %s" % (len(sin_json), ", ".join(sorted(sin_json)[:8])))
    print("con EnableFastBlur=1: %d %s" % (len(con_desenfoque), sorted(con_desenfoque)[:6]))
    # cuantas paradas tiene cada uno (para saber si la correccion de hoy toca a muchos)
    cuenta = {}
    for p in por_bustup.values():
        cuenta[len(p["paradas"])] = cuenta.get(len(p["paradas"]), 0) + 1
    print("paradas por degradado:", dict(sorted(cuenta.items())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())