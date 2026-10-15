"""Anade al SUMMARY.json las armas largas y el FBX, con las cifras medidas."""
import json
import os

PAQUETE = r"C:\Users\Lukas\p5x-datamining\kotone_shiomi"
OBJ_DST = os.path.join(PAQUETE, "01_model", "obj", "weapons")

ARMAS = [
    ("weapon_02", "PC079_01_weapon_02_wholeexport_rig_PC079_01_weapon_02", "PC079_01_weapon_02"),
    ("weapon_03", "PC079_01_weapon_03_wholeexport_rig_PC079_01_weapon_03", "PC079_01_weapon_03"),
    ("weapon_04", "PC079_01_weapon_04_wholeexport_rig_PC079_01_weapon_04", "PC079_01_weapon_04"),
    ("weapon_04_01", "PC079_01_weapon_04_wholeexport_rig_PC079_01_weapon_04_01", "PC079_01_weapon_04"),
    ("weapon_04_02", "PC079_01_weapon_04_wholeexport_rig_PC079_01_weapon_04_02", "PC079_01_weapon_04"),
    ("weapon_05", "PC079_01_weapon_05_wholeexport_rig_PC079_01_weapon_05", "PC079_01_weapon_05"),
]


def medir(nombre):
    v, caras = [], 0
    for linea in open(os.path.join(OBJ_DST, nombre + ".obj"), encoding="utf-8", errors="replace"):
        if linea.startswith("v "):
            p = linea.split()
            v.append((float(p[1]), float(p[2]), float(p[3])))
        elif linea.startswith("f "):
            caras += len(linea.split()) - 3
    xs = [p[0] for p in v]
    ys = [p[1] for p in v]
    zs = [p[2] for p in v]
    return len(v), caras, [round(max(xs) - min(xs), 3), round(max(ys) - min(ys), 3), round(max(zs) - min(zs), 3)]


s = json.load(open(os.path.join(PAQUETE, "SUMMARY.json"), encoding="utf-8"))

largas = []
for nombre, fuente, tex in ARMAS:
    n, tri, tam = medir(nombre)
    largas.append({
        "name": nombre,
        "source": fuente,
        "vertices": n,
        "triangles": tri,
        "size_m": tam,
        "textures": tex + "_*",
    })

# se reconstruye el diccionario en el orden que se quiere leer
nuevo = {}
for clave in ("model", "parts"):
    nuevo[clave] = s[clave]
nuevo["long_weapons"] = largas
nuevo["files"] = {
    "fbx": "Kotone_Shiomi_full.fbx",
    "note": "FBX export of Kotone_Shiomi_full.glb, textures embedded (329 bones, no animation)",
}
nuevo["totals"] = dict(s["totals"], long_weapon_vertices=sum(a["vertices"] for a in largas))

with open(os.path.join(PAQUETE, "SUMMARY.json"), "w", encoding="utf-8", newline="\n") as f:
    json.dump(nuevo, f, indent=1, ensure_ascii=False)
    f.write("\n")

print("SUMMARY.json actualizado")
for a in largas:
    print("   %-14s %5d v %5d tri  %.3f x %.3f x %.3f m" % (a["name"], a["vertices"],
          a["triangles"], *a["size_m"]))
print("   total vertices de armas largas:", nuevo["totals"]["long_weapon_vertices"])