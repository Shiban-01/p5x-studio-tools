"""Traduce al ingles el contenido de los JSON del paquete y arregla los dos MTL sueltos.

Las claves y los valores en castellano (nombre de pieza, descripciones, rutas de los OBJ de
expresiones) pasan a ingles. Los nombres de asset del juego NO se tocan.

Uso: python traducir_json_kotone.py [--aplicar]
"""
import json
import os
import re
import sys

BASE = r"C:\Users\Lukas\p5x-datamining\kotone_shiomi"
APLICAR = "--aplicar" in sys.argv

CLAVES = {
    "modelo": "model", "piezas": "parts", "nombre": "name", "origen": "source",
    "triangulos": "triangles", "materiales": "materials", "huesos": "bones",
    "expresiones": "expressions", "totales": "totals", "texturas": "textures",
    "shader_origen": "source_shader", "usado_por": "used_by",
    "malla_de_origen": "source_mesh", "pieza": "part", "peso_frame": "frame_weight",
    "vertices_movidos": "moved_vertices", "desplazamiento_max": "max_displacement",
    "esqueleto": "skeleton", "total_huesos": "total_bones", "nota": "note",
    "padre": "parent", "pos": "position", "rot": "rotation", "esc": "scale",
    "juego": "game", "personaje": "character", "bundle_del_modelo": "model_bundle",
    "bundle_del_actor": "actor_bundle", "extraido_con": "extracted_with",
    "fecha": "date", "archivos_fuente": "source_files",
}

VALORES = {
    "cuerpo_body": "body", "arma_lanza": "weapon_spear", "arma_lanza_vaina": "weapon_spear_sheath",
    "arma_pistola": "weapon_pistol", "brazalete": "bracelet", "ojo": "eye", "parpado": "eyelid",
    "cara": "face", "pelo": "hair",
    "Persona 5: The Phantom X (cliente PC)": "Persona 5: The Phantom X (PC client)",
    "pos/rot/esc son LOCALES respecto al hueso padre; rot en cuaternion (x,y,z,w)":
        "pos/rot/scale are LOCAL to the parent bone; rot is a quaternion (x,y,z,w)",
    "P5X/Toon (propietario del juego; aqui solo los slots de textura)":
        "P5X/Toon (the game's proprietary shader; only the texture slots are listed here)",
    "AssetStudioModCLI (mallas OBJ + texturas PNG) y Unity 2022.3.49f1 (piel, huesos, "
    "expresiones y GLB)":
        "AssetStudioModCLI (OBJ meshes + PNG textures) and Unity 2022.3.49f1 (skin, bones, "
        "expressions and GLB)",
}
PARTES = {"cuerpo": "body", "cara": "face", "pelo": "hair", "ojo": "eye", "parpado": "eyelid",
          "brazalete": "bracelet", "lanza_vaina": "spear_sheath", "lanza": "spear",
          "pistola": "pistol"}
CARPETAS = {"/02_texturas/": "/02_textures/", "02_texturas/": "02_textures/",
            "cuerpo/": "body/", "armas/": "weapons/", "ojos/": "eyes/", "otros/": "other/"}


def archivo_en(nombre):
    base, ext = os.path.splitext(nombre)
    if base in PARTES:
        return PARTES[base] + ext
    for es, en in sorted(PARTES.items(), key=lambda kv: -len(kv[0])):
        if base.startswith(es + "_"):
            resto = base[len(es) + 1:]
            return (resto if resto.startswith(en) else en + "_" + resto) + ext
    return nombre


def ruta_en(texto):
    for es, en in CARPETAS.items():
        texto = texto.replace(es, en)
    partes = texto.split("/")
    partes[-1] = archivo_en(partes[-1])
    return "/".join(partes)


def traducir(nodo, dentro_de_obj=False):
    if isinstance(nodo, dict):
        salida = {}
        for clave, valor in nodo.items():
            nueva = CLAVES.get(clave, clave)
            if clave == "obj" and isinstance(valor, str):
                valor = ruta_en(valor)
            salida[nueva] = traducir(valor, dentro_de_obj or clave == "obj")
        return salida
    if isinstance(nodo, list):
        return [traducir(v, dentro_de_obj) for v in nodo]
    if isinstance(nodo, str):
        if nodo in VALORES:
            return VALORES[nodo]
        if dentro_de_obj:
            return ruta_en(nodo)
        for es, en in VALORES.items():
            if nodo == es:
                return en
        return nodo
    return nodo


JSONS = ["SUMMARY.json", "05_materials/materials.json", "04_expressions/expressions.json",
         "03_skeleton/bones.json", "06_origin/provenance.json"]

for rel in JSONS:
    ruta = os.path.join(BASE, rel.replace("/", os.sep))
    datos = json.load(open(ruta, encoding="utf-8"))
    nuevos = traducir(datos)
    texto = json.dumps(nuevos, ensure_ascii=False, indent=1) + "\n"
    if APLICAR:
        with open(ruta, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(texto)
    print("%-38s %d lineas" % (rel, texto.count("\n")))

# los dos MTL sueltos que apuntan a texturas que no existen: al menos la ruta, en ingles
for rel in ["01_model/obj/body.mtl", "01_model/obj/weapons/pistol.mtl"]:
    ruta = os.path.join(BASE, rel.replace("/", os.sep))
    if not os.path.exists(ruta):
        continue
    texto = open(ruta, encoding="utf-8").read()
    lineas = []
    for linea in texto.splitlines():
        m = re.match(r"^(map_Kd|map_Bump)\s+(.+?)\s*$", linea)
        if m:
            nueva_ruta = ruta_en(m.group(2).replace("\\", "/"))
            destino = os.path.join(os.path.dirname(ruta),
                                   nueva_ruta.replace("/", os.sep))
            if not os.path.exists(destino):
                lineas.append(m.group(1) + " " + nueva_ruta)
                lineas.append("# (missing in the client: %s)" % os.path.basename(nueva_ruta))
                continue
            lineas.append(m.group(1) + " " + nueva_ruta)
            continue
        lineas.append(linea)
    if APLICAR:
        with open(ruta, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(lineas) + "\n")
    print("%-38s arreglado" % rel)

if not APLICAR:
    print("\n(sin --aplicar: no se ha escrito nada)")