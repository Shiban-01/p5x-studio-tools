"""Empareja los 216 JSON de sombreado con los juegos de sprites del censo y compara sus parametros.

- Del JSON: UI-DialogShader-<ropa>-<personaje>  (la ropa puede llevar sufijo numerico: changfu01)
- De los sprites: <personaje>-<ropa>-<capa>     (capas: benti, toufa, yifu, lunkuo, zhi, yanN, zuiN...)

Aqui solo se empareja y se informa; no se renderiza nada.
"""
import difflib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

DL_DIR = Path(r"C:\Users\Lukas\p5x-datamining\_dl")
D_JSON = DL_DIR / "lihui_shader_json"
CENSO = DL_DIR / "censo_texturas.json"

CAPAS_CUERPO = ("benti", "shenti", "toufa", "yifu", "lunkuo", "zhi", "mianju", "zhengti")

# 1) JSON
jsons = {}
for f in sorted(D_JSON.glob("*.json")):
    d = json.loads(f.read_text(encoding="utf-8"))
    nombre = d.get("m_Name", f.stem)
    resto = nombre.replace("UI-DialogShader-", "", 1)
    if "-" in resto:
        ropa, personaje = resto.split("-", 1)
    else:
        ropa, personaje = resto, ""
    jsons[nombre] = {"fichero": f, "ropa": ropa, "personaje": personaje, "datos": d}

print("json leidos: %d" % len(jsons))

# 2) sprites del censo: (personaje, ropa) -> {capa: nombre, bundle}
#    El nombre no sigue una sola convencion: hay <personaje>-<ropa>-<capa> (changfu-benti) y
#    <personaje>-<ropa>-<capa>-<expresion> (lufeier-changfu-benti-tongchang), asi que la capa se
#    busca por el token que sea nombre de parte, y los ojos/boca por el sufijo -yanN / -zuiN.
filas = json.loads(CENSO.read_text(encoding="utf-8"))["filas"]
juegos = defaultdict(lambda: {"capas": {}, "bundles": set(), "cuerpo": False})
CUERPO = ("benti", "shenti", "zhengti")
for fila in filas:
    partes = fila["nombre"].split("-")
    if len(partes) < 3:
        continue
    personaje, ropa, cola = partes[0], partes[1], partes[2:]
    ultimo = re.sub(r"\d+$", "", cola[-1])
    if ultimo in ("yan", "zui"):
        if len(cola) < 2:
            continue
        capa = "%s-%s%s" % (cola[-2], ultimo, cola[-1][len(ultimo):])
    else:
        indices = [i for i, t in enumerate(cola) if t in CAPAS_CUERPO]
        if not indices:
            continue
        i = indices[-1]
        capa = cola[i]
        if i + 1 < len(cola) and cola[i + 1] in CAPAS_CUERPO:
            capa = "%s-%s" % (capa, cola[i + 1])
    clave = (personaje, ropa)
    # el bundle va POR CAPA: las capas de un mismo bust-up viven en bundles distintos
    # (063/uitex_s_changfu... para el cuerpo, 119/uitex_changfu... para los ojos)
    juegos[clave]["capas"][capa] = {"nombre": fila["nombre"], "bundle": fila["bundle"]}
    juegos[clave]["bundles"].add(fila["bundle"])
    if capa in CUERPO:
        juegos[clave]["cuerpo"] = True

print("juegos de sprites con bust-up: %d" % len(juegos))
con_cuerpo = sum(1 for v in juegos.values() if v["cuerpo"])
print("   de esos, con capa de cuerpo: %d (los demas son solo ojos/boca de otra ropa)" % con_cuerpo)

# indice auxiliar: personaje -> ropas disponibles
por_personaje = defaultdict(set)
for (personaje, ropa) in juegos:
    por_personaje[personaje].add(ropa)


def variantes(nombre):
    """Posibles grafias del mismo nombre (zhi/zhui y similares)."""
    v = {nombre}
    for a, b in (("zhi", "zhui"), ("zhui", "zhi"), ("ling", "lin"), ("lin", "ling")):
        if a in nombre:
            v.add(nombre.replace(a, b, 1))
    return v


def parecido(a, b):
    """Puntuacion de parecido entre el nombre del JSON y el del sprite (0 = nada).

    La subcadena solo vale si esta ANCLADA (prefijo o sufijo) y tiene 3 letras o mas: 'aqi' esta
    dentro de 'maqimu' pero no anclado, y emparejarlos seria un error silencioso. Los casos reales
    si estan anclados: lizi/duomicunlizi, suyu/xinjingsuyu, munei/muneixiong.
    """
    if a == b:
        return 3.0
    corto, largo = (a, b) if len(a) <= len(b) else (b, a)
    if len(corto) >= 3 and (largo.startswith(corto) or largo.endswith(corto)):
        return 2.0
    if abs(len(a) - len(b)) <= 2:
        r = difflib.SequenceMatcher(None, a, b).ratio()
        if r >= 0.85:
            return 1.0
    return 0.0


def emparejar(ropa_json, personaje_json):
    """Devuelve ((personaje, ropa), motivo, confianza) o (None, motivo, None).

    El JSON usa el nombre corto del personaje y los sprites el completo (lizi -> duomicunlizi,
    suyu -> xinjingsuyu), asi que se puntua por parecido y luego se elige la ropa.
    """
    ropa_sin_num = re.sub(r"\d+$", "", ropa_json)
    candidatos = []
    for grafia in variantes(personaje_json):
        for (p, r) in juegos:
            if not juegos[(p, r)]["cuerpo"]:
                continue          # sin capa de cuerpo no es un bust-up: solo ojos/boca de otra ropa
            s = parecido(grafia, p)
            if s >= 1.0:
                candidatos.append((s, p, r))
    if not candidatos:
        return None, "personaje no esta en los sprites (o no tiene bust-up con cuerpo)", None
    mejor = max(s for s, _, _ in candidatos)
    candidatos = [c for c in candidatos if c[0] == mejor]
    personajes = sorted({c[1] for c in candidatos})
    nivel_personaje = {3.0: "alta", 2.0: "media"}.get(mejor, "baja")
    exactos = [c for c in candidatos if c[2] == ropa_sin_num]
    if exactos:
        return (exactos[0][1], exactos[0][2]), "ropa exacta", nivel_personaje
    parecidas = [c for c in candidatos if c[2].startswith(ropa_sin_num[:5])]
    if parecidas:
        return (parecidas[0][1], parecidas[0][2]), "ropa parecida (%s)" % parecidas[0][2], "media"
    ropas = sorted({c[2] for c in candidatos})
    if len(ropas) == 1:
        return (candidatos[0][1], candidatos[0][2]), "unica ropa disponible (%s)" % ropas[0], "media"
    return None, "personaje %s: varias ropas y ninguna coincide: %s" % (
        "/".join(personajes), ", ".join(ropas)), None


emparejados, fallos = {}, []
for nombre, info in jsons.items():
    clave, motivo, confianza = emparejar(info["ropa"], info["personaje"])
    if clave:
        emparejados[nombre] = {"clave": clave, "motivo": motivo, "confianza": confianza}
    else:
        fallos.append((nombre, motivo))

# el alias puede forzar personaje+ropa para un JSON concreto; las capas se sacan del indice
ALIAS = DL_DIR / "alias_bustups.json"
if ALIAS.exists():
    alias = json.loads(ALIAS.read_text(encoding="utf-8"))
    aplicados = 0
    for nombre, arreglo in alias.items():
        clave = (arreglo["personaje"], arreglo["ropa"])
        if clave not in juegos:
            print("   AVISO alias: %s -> %s/%s no existe en los sprites" % (nombre, *clave))
            continue
        emparejados[nombre] = {"clave": clave, "motivo": "alias", "confianza": "alta"}
        fallos = [(n, m) for n, m in fallos if n != nombre]
        aplicados += 1
    print("alias aplicados: %d" % aplicados)

print()
print("=== emparejados: %d | sin emparejar: %d ===" % (len(emparejados), len(fallos)))
for nivel in ("alta", "media", "baja"):
    n = sum(1 for v in emparejados.values() if v["confianza"] == nivel)
    print("   confianza %-6s %d" % (nivel, n))
print()
for m, n in Counter(v["motivo"].split("(")[0] for v in emparejados.values()).most_common():
    print("   %-28s %d" % (m, n))

print()
print("=== emparejado con confianza BAJA (revisar) ===")
for nombre, v in sorted(emparejados.items()):
    if v["confianza"] == "baja":
        print("   %-50s -> %s/%s  (%s)" % (nombre, v["clave"][0], v["clave"][1], v["motivo"]))

print()
print("=== sin emparejar ===")
for nombre, motivo in fallos:
    print("   %-46s %s" % (nombre, motivo))

bundles = sorted({b for v in emparejados.values() for b in juegos[v["clave"]]["bundles"]})
print()
print("bundles necesarios para renderizar todos: %d" % len(bundles))
print("   %s" % ", ".join(b.split("/")[-1] for b in bundles[:8]))

# 3) comparacion de parametros de los 216
print()
print("=== parametros de los 216 JSON ===")
campos = ["EffectFactor", "Brightness", "Saturation", "Contrast", "GradientAlphaBottom",
          "GradientAlphaTop", "GraBrightness", "GraSaturation", "GraContrast", "Angle"]
print("%-22s %8s %8s %8s %8s" % ("campo", "min", "max", "media", "distintos"))
for c in campos:
    vals = [j["datos"].get(c) for j in jsons.values() if isinstance(j["datos"].get(c), (int, float))]
    if not vals:
        continue
    print("%-22s %8.3f %8.3f %8.3f %8d" % (c, min(vals), max(vals), sum(vals) / len(vals), len(set(vals))))

modos = Counter(j["datos"].get("gradientMode") for j in jsons.values())
print("%-22s %s" % ("gradientMode", dict(modos)))
blur = Counter(j["datos"].get("EnableFastBlur") for j in jsons.values())
print("%-22s %s" % ("EnableFastBlur", dict(blur)))
claves = Counter(int(j["datos"]["gradient"]["m_NumColorKeys"]) for j in jsons.values())
print("%-22s %s" % ("claves de color", dict(sorted(claves.items()))))
alfas = Counter(int(j["datos"]["gradient"]["m_NumAlphaKeys"]) for j in jsons.values())
print("%-22s %s" % ("claves de alfa", dict(sorted(alfas.items()))))

# guardar el emparejado para el lote
salida = Path(r"C:\Users\Lukas\p5x-datamining\_dl\emparejado_bustups.json")
salida.write_text(json.dumps(
    {"emparejados": {k: {"personaje": v["clave"][0], "ropa": v["clave"][1], "motivo": v["motivo"],
                         "confianza": v["confianza"],
                         "bundles": sorted(juegos[v["clave"]]["bundles"]),
                         "capas": juegos[v["clave"]]["capas"]}
                     for k, v in emparejados.items()},
     "fallos": fallos}, ensure_ascii=False, indent=1), encoding="utf-8")
print()
print("emparejado guardado en", salida)