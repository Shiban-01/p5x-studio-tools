"""Analisis de los 120 bust-ups: capas presentes/faltantes, su bundle, y el indice de dependencias.

Entradas (todas en _dl, ya medidas sobre el juego):
  emparejado_bustups.json  -> los 120 bust-ups (JSON shader -> personaje/ropa/capas)
  censo_texturas.json      -> todos los Sprite/Texture2D por bundle (del motor AssetStudioModCLI)
  zeus_manifest.json       -> zeusBundleManifest.txt (FlatBuffer) parseado: bundle -> deps
  p5x_studio/p5x_studio/datos/retratos.json -> los 80 bundles que el visor extrae

Salida:
  bustups_indice_informe.json
"""
import difflib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

DL = Path(r"C:\Users\Lukas\p5x-datamining\_dl")
REPO = Path(r"C:\Users\Lukas\p5x-datamining")
JUEGO = Path(r"C:\Users\Lukas\Downloads\P5X\Client\OuterPackage\Bundles\Windows")

emp = json.loads((DL / "emparejado_bustups.json").read_text(encoding="utf-8"))["emparejados"]
filas = json.loads((DL / "censo_texturas.json").read_text(encoding="utf-8"))["filas"]
man = json.loads((DL / "zeus_manifest.json").read_text(encoding="utf-8"))
man_by = {b["name"]: b for b in man["bundles"]}
retratos = set(json.loads((REPO / "p5x_studio/p5x_studio/datos/retratos.json")
                          .read_text(encoding="utf-8"))["bundles"])
disco = {p.name: p.relative_to(JUEGO).as_posix() for p in JUEGO.rglob("*.bundle")}

# --- clasificacion de capas (copia fiel de la logica del visor: bustups.partir_nombre/paso_de) ---
ORDEN = [("outline", ("lunkuo", "lunkuo1")), ("body", ("benti", "shenti", "zhengti")),
         ("arms", ("zhi", "shou", "bi")), ("clothes", ("yifu", "yifu1", "fu")),
         ("blush", ("saihong", "haixiu", "hongyun", "saihonghunluan")), ("face", ("cara", "lian")),
         ("eyes", ("yan", "yan1", "yan2", "yan3")), ("mouth", ("zui", "zui1", "zui2", "zui3")),
         ("marks", ("han", "lei")),
         ("mask", ("mask", "rmask", "lmask", "mianju", "mianju1", "mianju2")),
         ("hair", ("toufa", "toufa1")), ("glasses", ("yanjing", "mojing")), ("hat", ("maozi",))]
PARTES_BASE = ("benti", "shenti", "zhengti")
ALIAS = {"aochuncun": "aocunchun"}


def sin_copia(p): return re.sub(r"_\d+$", "", p or "")


def paso_de(p):
    limpio = "".join(c for c in sin_copia(p).lower() if not c.isdigit())
    for paso, nombres in ORDEN:
        if limpio in nombres:
            return paso
    return None


def partir(nombre, personaje, ropa):
    resto = nombre
    limpia = re.sub(r"\d+$", "", ropa or "")
    for pre in ("%s-%s-" % (personaje, ropa), "%s-%s-" % (personaje, limpia), "%s-" % personaje):
        if resto.startswith(pre):
            resto = resto[len(pre):]
            break
    trozos = [t for t in resto.split("-") if t]
    if not trozos:
        return "base", nombre
    if sin_copia(trozos[0]) in PARTES_BASE:
        if len(trozos) == 1:
            return "base", trozos[0]
        ult = trozos[-1]
        if paso_de(ult) is not None:
            return "base", ult
        return trozos[1], "cara"
    if len(trozos) >= 2:
        return trozos[0], trozos[1]
    return "base", trozos[0]


# indice por primer token (tal cual) para buscar variantes
por_token = defaultdict(list)
for f in filas:
    por_token[f["nombre"].split("-")[0]].append(f)

informe = {"bustups": {}, "resumen": {}}
for clave, v in sorted(emp.items()):
    per_crudo, ropa = v["personaje"], v["ropa"]
    per = ALIAS.get(per_crudo, per_crudo)
    # capas que el visor VE: de su emparejado + cualquier PNG del prefix en la carpeta
    pasos = defaultdict(list)
    # 1) las que trae el emparejado
    for capa in v["capas"].values():
        nombre = capa.get("nombre") if isinstance(capa, dict) else capa
        b = capa.get("bundle") if isinstance(capa, dict) else None
        exp, parte = partir(nombre, per, ropa)
        paso = paso_de(parte)
        if paso:
            pasos[paso].append({"nombre": nombre, "bundle": b})
    # 2) todas las del censo cuyo primer token = personaje (lo que hay en el bulk)
    for f in por_token.get(per, []):
        if f["tipo"] != "Sprite":
            continue
        exp, parte = partir(f["nombre"], per, ropa)
        paso = paso_de(parte)
        if paso:
            pasos[paso].append({"nombre": f["nombre"], "bundle": f["bundle"]})
    for k in pasos:  # dedup por nombre
        visto, out = set(), []
        for d in pasos[k]:
            if d["nombre"] not in visto:
                visto.add(d["nombre"]); out.append(d)
        pasos[k] = out

    requiere_cara = any(p in pasos for p in ("eyes", "mouth")) or "face" in pasos
    tiene_ojos = "eyes" in pasos
    tiene_boca = "mouth" in pasos
    tiene_cara = "face" in pasos
    tiene_mask = "mask" in pasos
    bundles_necesarios = sorted({d["bundle"] for lst in pasos.values() for d in lst if d["bundle"]})

    # si NO hay ojos/boca/cara: buscar donde esta la cara de verdad
    face_elsewhere = []
    if not (tiene_ojos or tiene_boca or tiene_cara):
        tokens_parecidos = [t for t in por_token
                            if difflib.SequenceMatcher(None, t, per_crudo).ratio() >= 0.82]
        for t in tokens_parecidos:
            for f in por_token[t]:
                nm = f["nombre"]
                es_cara = re.search(r"-(yan|zui)\d$", nm) or re.search(r"(mianju|mask)", nm, re.I)
                es_face_base = bool(re.search(r"-(benti|shenti|zhengti)-(tongchang|[a-z]+)$", nm)) and \
                    not re.search(r"-(lunkuo|toufa|yifu|zhi|mianju|mask)\b", nm)
                if es_cara or es_face_base:
                    face_elsewhere.append({"nombre": nm, "bundle": f["bundle"],
                                           "token": t, "tipo": f["tipo"]})

    bundles_cara = sorted({d["bundle"] for d in face_elsewhere})
    # deps declaradas por el manifiesto
    deps = {}
    for b in bundles_necesarios:
        n = b.split("/")[-1]
        e = man_by.get(n)
        deps[b] = [man["bundles"][i]["name"] for i in e["deps"]] if e else None

    informe["bustups"][clave] = {
        "personaje": per_crudo, "personaje_alias": per, "ropa": ropa,
        "pasos_presentes": {k: sorted({d["nombre"] for d in lst}) for k, lst in sorted(pasos.items())},
        "tiene_ojos": tiene_ojos, "tiene_boca": tiene_boca, "tiene_cara": tiene_cara,
        "tiene_mask": tiene_mask,
        "bundles_necesarios": bundles_necesarios,
        "bundles_en_retratos": {b: (b in retratos) for b in bundles_necesarios},
        "cara_en_otro_sitio": face_elsewhere[:40],
        "bundles_cara_en_otro_sitio": bundles_cara,
        "deps_manifiesto": deps,
    }

# resumen
bs = informe["bustups"]
sin_cara = [k for k, d in bs.items() if not (d["tiene_ojos"] or d["tiene_boca"] or d["tiene_cara"])]
con_cara = [k for k in bs if k not in sin_cara]
faltan_en_retratos = defaultdict(list)
for k, d in bs.items():
    for b, ok in d["bundles_en_retratos"].items():
        if not ok:
            faltan_en_retratos[b].append(k)
informe["resumen"] = {
    "total": len(bs),
    "con_cara": len(con_cara), "sin_cara": len(sin_cara),
    "lista_sin_cara": sin_cara,
    "bundles_necesarios_union": len({b for d in bs.values() for b in d["bundles_necesarios"]}),
    "bundles_del_visor_retratos": len(retratos),
    "bundles_necesarios_fuera_de_retratos": {b: len(v) for b, v in faltan_en_retratos.items()},
    "bundles_con_deps_en_manifiesto": sum(
        1 for d in bs.values() for b, ds in d["deps_manifiesto"].items() if ds),
    "manifiesto": {"fichero": "104/zeusBundleManifest.txt", "bundles": man["count"],
                   "con_dependencias": sum(1 for b in man["bundles"] if b["deps"]),
                   "aristas": sum(len(b["deps"]) for b in man["bundles"])},
}
(DL / "bustups_indice_informe.json").write_text(
    json.dumps(informe, ensure_ascii=False, indent=1), encoding="utf-8")

print("total bust-ups:", informe["resumen"]["total"])
print("con cara (ojos/boca/cara):", informe["resumen"]["con_cara"],
      "| SIN cara:", informe["resumen"]["sin_cara"])
print("bundles necesarios (union):", informe["resumen"]["bundles_necesarios_union"],
      "| en retratos.json:", len(retratos))
print("bundles necesarios que NO estan en retratos.json:",
      len(informe["resumen"]["bundles_necesarios_fuera_de_retratos"]))
for b, n in sorted(informe["resumen"]["bundles_necesarios_fuera_de_retratos"].items()):
    print("   %-46s afecta a %d bust-ups" % (b, n))
print("bundles con deps declaradas en manifiesto (entre los usados):",
      informe["resumen"]["bundles_con_deps_en_manifiesto"])
print("guardado:", DL / "bustups_indice_informe.json")