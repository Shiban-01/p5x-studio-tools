"""Pasa el paquete kotone_shiomi a nombres en ingles, sin tocar el contenido.

Renombra carpetas y ficheros, arregla las referencias internas de los OBJ/MTL (mtllib y map_Kd /
map_Bump, que apuntaban a rutas que ya no existian) y deja un registro de la migracion para poder
volver atras.

Uso: python renombrar_paquete_ingles.py [--aplicar]
     Sin --aplicar solo dice lo que haria.
"""
import os
import re
import sys

RAIZ = r"C:\Users\Lukas\p5x-datamining\kotone_shiomi"
APLICAR = "--aplicar" in sys.argv

CARPETAS = {
    "01_modelo": "01_model",
    "01_modelo/obj/cuerpo": "01_model/obj/body",
    "01_modelo/obj/cara": "01_model/obj/face",
    "01_modelo/obj/pelo": "01_model/obj/hair",
    "01_modelo/obj/armas": "01_model/obj/weapons",
    "02_texturas": "02_textures",
    "02_texturas/cuerpo": "02_textures/body",
    "02_texturas/cara": "02_textures/face",
    "02_texturas/pelo": "02_textures/hair",
    "02_texturas/armas": "02_textures/weapons",
    "02_texturas/ojos": "02_textures/eyes",
    "02_texturas/otros": "02_textures/other",
    "03_esqueleto": "03_skeleton",
    "04_expresiones": "04_expressions",
    "05_materiales": "05_materials",
    "06_origen": "06_origin",
    "preview/blender_oscuro": "preview/blender_dark",
    "preview/cabeza": "preview/head",
    "preview/cabeza_partes": "preview/head_parts",
}

PARTES = {"cuerpo": "body", "cara": "face", "pelo": "hair", "ojo": "eye", "parpado": "eyelid",
          "brazalete": "bracelet", "lanza_vaina": "spear_sheath", "lanza": "spear",
          "pistola": "pistol", "arma_": "weapon_"}

PREVIEWS = {
    "00_hoja_de_contacto.png": "00_contact_sheet.png",
    "01_frente.png": "01_front.png",
    "02_lado_derecho.png": "02_right_side.png",
    "03_tres_cuartos.png": "03_three_quarter.png",
    "04_espalda.png": "04_back.png",
    "05_cara_primer_plano.png": "05_face_closeup.png",
    "06_comparacion_con_el_sprite.png": "06_comparison_with_sprite.png",
    "07_glb_nuevo_vs_anterior.png": "07_glb_new_vs_old.png",
    "08_glb_nuevo_frente.png": "08_glb_new_front.png",
    "09_glb_nuevo_cara.png": "09_glb_new_face.png",
    "10_glb_nuevo_perfil.png": "10_glb_new_profile.png",
    "11_comparacion_torso.png": "11_torso_comparison.png",
    "12_brazalete_zoom.png": "12_bracelet_zoom.png",
    "cabeza_frente.png": "head_front.png",
    "cabeza_perfil.png": "head_profile.png",
    "cabeza_tres_cuartos.png": "head_three_quarter.png",
    "cabeza_cara_ojos_parpado.png": "head_face_eyes_eyelid.png",
    "cabeza_cuerpo.png": "head_body.png",
    "cabeza_pelo.png": "head_hair.png",
    "cabeza_sin_pelo.png": "head_without_hair.png",
    "cabeza_todos.png": "head_all.png",
    "hoja_cabeza_partes.png": "00_contact_sheet_head_parts.png",
}
PREVIEWS_RENDER = {
    "blender_01_frente.png": "blender_01_front.png",
    "blender_02_perfil_der.png": "blender_02_right_profile.png",
    "blender_03_espalda.png": "blender_03_back.png",
    "blender_04_perfil_izq.png": "blender_04_left_profile.png",
    "blender_05_cara.png": "blender_05_face.png",
}


def parte_en(texto):
    """Traduce el nombre de una parte (suelto o compuesto)."""
    if texto in PARTES:
        return PARTES[texto]
    if texto.startswith("arma_"):
        return "weapon_" + PARTES.get(texto[len("arma_"):], texto[len("arma_"):])
    if texto == "cuerpo_body":
        return "body"
    return texto


def nombre_en(nombre):
    """Traduce el nombre de un fichero de modelo o textura."""
    base, ext = os.path.splitext(nombre)
    if base.startswith("Kotone_Shiomi_"):
        resto = base[len("Kotone_Shiomi_"):]
        if resto == "completo":
            return "Kotone_Shiomi_full" + ext
        for es, en in PARTES.items():
            if resto == es:
                return "Kotone_Shiomi_" + en + ext
    if base.startswith("huesos_"):
        return "bones_" + parte_en(base[len("huesos_"):]) + ext
    if base == "huesos":
        return "bones" + ext
    if base == "esqueleto_arbol":
        return "skeleton_tree" + ext
    if base.startswith("esqueleto_"):
        return "skeleton_" + base[len("esqueleto_"):] + ext
    if base == "expresiones":
        return "expressions" + ext
    if base == "materiales":
        return "materials" + ext
    if base == "procedencia":
        return "provenance" + ext
    if base == "tabla_texturas":
        return "texture_table" + ext
    if base == "RESUMEN":
        return "SUMMARY" + ext
    if base.startswith("cuerpo_body_mat"):
        return "body_mat" + base[len("cuerpo_body_mat"):] + ext
    # nombre exacto de parte (antes que los prefijos, o "lanza_vaina" caeria en "lanza_")
    if base in PARTES or base.startswith("arma_"):
        return parte_en(base) + ext
    # expresiones: <malla>_<morph>.obj -> se quita el prefijo si el morph ya lo lleva
    for es, en in sorted(PARTES.items(), key=lambda kv: -len(kv[0])):
        if base.startswith(es + "_"):
            resto = base[len(es) + 1:]
            if resto.startswith(en):
                return resto + ext
            return en + "_" + resto + ext
    return None


def ruta_nueva(rel):
    """Traduce una ruta relativa entera (carpeta + fichero)."""
    rel = rel.replace("/", os.sep)
    carpeta, nombre = os.path.split(rel)
    carpeta_en = carpeta
    for es, en in sorted(CARPETAS.items(), key=lambda kv: -len(kv[0])):
        es = es.replace("/", os.sep)
        if carpeta == es:
            carpeta_en = en.replace("/", os.sep)
            break
    if os.path.basename(carpeta) in PREVIEWS:
        carpeta_en = carpeta
    nuevo = PREVIEWS.get(nombre) or PREVIEWS_RENDER.get(nombre) or nombre_en(nombre)
    if nuevo is None:
        nuevo = nombre
    return os.path.join(carpeta_en, nuevo)


# ---------------------------------------------------------------- 1. plan
plan = []
for raiz, _, ficheros in os.walk(RAIZ):
    for f in ficheros:
        absoluto = os.path.join(raiz, f)
        rel = os.path.relpath(absoluto, RAIZ)
        destino = ruta_nueva(rel)
        if destino != rel:
            plan.append((rel, destino))

carpetas = []
for raiz, subdirs, _ in os.walk(RAIZ):
    for d in subdirs:
        absoluto = os.path.join(raiz, d)
        rel = os.path.relpath(absoluto, RAIZ)
        destino = ruta_nueva(rel)
        if destino != rel:
            carpetas.append((rel, destino))

print("ficheros a renombrar: %d" % len(plan))
destinos = {}
for rel, destino in plan:
    destinos.setdefault(destino.lower(), []).append(rel)
choques = {d: o for d, o in destinos.items() if len(o) > 1}
if choques:
    print("*** COLISIONES (no se aplicara nada) ***")
    for d, o in choques.items():
        print("   %s <- %s" % (d, o))
    sys.exit(1)
for rel, destino in plan:
    print("   %-52s -> %s" % (rel, destino))
print("carpetas a renombrar: %d" % len(carpetas))
for rel, destino in carpetas:
    print("   %-52s -> %s" % (rel, destino))

if not APLICAR:
    print("\n(sin --aplicar: no se ha tocado nada)")
    sys.exit(0)

# ---------------------------------------------------------------- 2. renombrar ficheros y carpetas
for rel, destino in plan:
    origen = os.path.join(RAIZ, rel)
    fin = os.path.join(RAIZ, destino)
    os.makedirs(os.path.dirname(fin), exist_ok=True)
    os.replace(origen, fin)
for rel, destino in sorted(carpetas, key=lambda kv: -kv[0].count(os.sep)):
    origen = os.path.join(RAIZ, rel)
    fin = os.path.join(RAIZ, destino)
    if not os.path.isdir(origen):
        continue
    if os.path.isdir(fin):
        # La carpeta nueva ya existe (la creo el mover los ficheros): se fusiona en vez de fallar.
        for raiz2, _, ficheros in os.walk(origen):
            for f in ficheros:
                src = os.path.join(raiz2, f)
                dst = os.path.join(fin, os.path.relpath(src, origen))
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                os.replace(src, dst)
        for raiz2, subdirs2, _ in os.walk(origen, topdown=False):
            for d in subdirs2:
                try:
                    os.rmdir(os.path.join(raiz2, d))
                except OSError:
                    pass
        try:
            os.rmdir(origen)
        except OSError:
            print("   [!] no se pudo borrar %s (queda algo dentro)" % rel)
    else:
        os.makedirs(os.path.dirname(fin), exist_ok=True)
        os.replace(origen, fin)

# ---------------------------------------------------------------- 3. referencias dentro de OBJ/MTL
RAIZ_EN = RAIZ
texturas = {}
for raiz, _, ficheros in os.walk(os.path.join(RAIZ_EN, "02_textures")):
    for f in ficheros:
        texturas[f.lower()] = os.path.join(raiz, f)

tocados = 0
for raiz, _, ficheros in os.walk(RAIZ_EN):
    for f in ficheros:
        if not f.lower().endswith((".obj", ".mtl")):
            continue
        ruta = os.path.join(raiz, f)
        crudo = open(ruta, "r", encoding="utf-8", errors="replace").read()
        lineas = []
        cambios = 0
        for linea in crudo.splitlines():
            m = re.match(r"^(mtllib\s+)(.+?)\s*$", linea)
            if m:
                objetivo = nombre_en(os.path.basename(m.group(2))) or os.path.basename(m.group(2))
                nueva = m.group(1) + objetivo
                cambios += nueva != linea
                lineas.append(nueva)
                continue
            m = re.match(r"^(map_Kd|map_Bump|map_Ka|map_Ks|bump)\s+(.+?)\s*$", linea)
            if m:
                base = os.path.basename(m.group(2).replace("\\", "/"))
                real = texturas.get(base.lower())
                if real:
                    rel = os.path.relpath(real, os.path.dirname(ruta)).replace(os.sep, "/")
                    nueva = "%s %s" % (m.group(1), rel)
                    cambios += nueva != linea
                    lineas.append(nueva)
                    continue
            if linea.startswith("#") and "materiales del juego" in linea:
                nueva = ("# Kotone Shiomi (PC079_01) - the game's materials (P5X/Toon shader slots)")
                cambios += 1
                lineas.append(nueva)
                continue
            lineas.append(linea)
        if cambios:
            with open(ruta, "w", encoding="utf-8", newline="\n") as fh:
                fh.write("\n".join(lineas) + "\n")
            tocados += 1
print("\nOBJ/MTL con referencias arregladas: %d" % tocados)

# ---------------------------------------------------------------- 4. registro de la migracion
registro = os.path.join(RAIZ_EN, "_migration_es_to_en.txt")
with open(registro, "w", encoding="utf-8", newline="\n") as fh:
    fh.write("# kotone_shiomi: migracion de nombres es -> en (30-09-2026)\n")
    fh.write("# original -> nuevo, para poder volver atras\n\n")
    for rel, destino in sorted(plan) + sorted(carpetas):
        fh.write("%s -> %s\n" % (rel, destino))
print("registro:", registro)