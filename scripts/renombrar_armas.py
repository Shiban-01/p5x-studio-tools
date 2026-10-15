"""Corrige el nombre de las armas: no hay lanza, son dos pistolas (una en la funda de la cadera).

El juego llama a la malla `PC079_01_qiang` (枪 = pistola) y a su funda `PC079_01_qiangtao`
(枪套 = funda). Se midio: 10x9x8 cm en la cadera dentro de la funda, y 13x16x2 cm la segunda, que
esta guardada en el origen y el juego coloca al usarla. Ninguna mide lo que una lanza.

  Kotone_Shiomi_weapon_spear.glb        -> Kotone_Shiomi_weapon_gun_01.glb      (la de la funda)
  Kotone_Shiomi_weapon_spear_sheath.glb -> Kotone_Shiomi_weapon_gun_holster.glb (la funda)
  Kotone_Shiomi_weapon_pistol.glb       -> Kotone_Shiomi_weapon_gun_02.glb      (la del origen)

Se usa --aplicar para ejecutar; sin el, solo muestra el plan.
"""
import json
import os
import sys

RAIZ = r"C:\Users\Lukas\p5x-datamining\kotone_shiomi"
APLICAR = "--aplicar" in sys.argv

# (nombre viejo, nombre nuevo) sin extension
PAREJAS = [
    ("Kotone_Shiomi_weapon_spear", "Kotone_Shiomi_weapon_gun_01"),
    ("Kotone_Shiomi_weapon_spear_sheath", "Kotone_Shiomi_weapon_gun_holster"),
    ("Kotone_Shiomi_weapon_pistol", "Kotone_Shiomi_weapon_gun_02"),
    ("weapon_spear_sheath", "weapon_gun_holster"),
    ("weapon_spear", "weapon_gun_01"),
    ("weapon_pistol", "weapon_gun_02"),
    ("spear_sheath", "gun_holster"),
    ("spear", "gun_01"),
    ("pistol", "gun_02"),
]


def traducir(nombre):
    """Cambia el nombre base segun las parejas (de mas larga a mas corta, para no pisarse)."""
    base, ext = os.path.splitext(nombre)
    for viejo, nuevo in PAREJAS:
        if base == viejo:
            return nuevo + ext
    for viejo, nuevo in PAREJAS:
        if base.endswith("_" + viejo):
            return base[: -len(viejo)] + nuevo + ext
    return None


plan = []
for raiz, dirs, fs in os.walk(RAIZ):
    for f in fs:
        nuevo = traducir(f)
        if nuevo and nuevo != f:
            plan.append((os.path.relpath(os.path.join(raiz, f), RAIZ),
                         os.path.relpath(os.path.join(raiz, nuevo), RAIZ)))

print("ficheros a renombrar: %d" % len(plan))
for a, b in plan:
    print("   %-56s -> %s" % (a, b))

if not APLICAR:
    print("\n(sin --aplicar: no se ha tocado nada)")
    sys.exit(0)

for a, b in plan:
    oa, ob = os.path.join(RAIZ, a), os.path.join(RAIZ, b)
    os.makedirs(os.path.dirname(ob), exist_ok=True)
    os.replace(oa, ob)

# referencias internas: mtllib de los OBJ y "name" de los JSON
tocados = 0
for raiz, _, fs in os.walk(RAIZ):
    for f in fs:
        if not f.endswith((".obj", ".json")):
            continue
        p = os.path.join(raiz, f)
        t = open(p, encoding="utf-8", errors="replace").read()
        nuevo_t = t
        for viejo, nuevo in PAREJAS:
            nuevo_t = nuevo_t.replace("mtllib " + viejo + ".mtl", "mtllib " + nuevo + ".mtl")
            nuevo_t = nuevo_t.replace('"name": "%s"' % viejo, '"name": "%s"' % nuevo)
        if nuevo_t != t:
            open(p, "w", encoding="utf-8", newline="\n").write(nuevo_t)
            tocados += 1
print("\nficheros con referencias internas corregidas: %d" % tocados)

# comprobacion
malos = []
for raiz, _, fs in os.walk(RAIZ):
    for f in fs:
        if "spear" in f.lower():
            malos.append(os.path.relpath(os.path.join(raiz, f), RAIZ))
print("ficheros que aun dicen 'spear' en el nombre: %d" % len(malos))
for m in malos:
    print("   ", m)