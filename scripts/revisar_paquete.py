"""Revision final del paquete kotone_shiomi: coherencia de nombres y referencias."""
import json, os, re

BASE = r"C:\Users\Lukas\p5x-datamining\kotone_shiomi"
t = open(os.path.join(BASE, "README.md"), encoding="utf-8").read()

# inventario real
en_paquete = set()
for raiz, _, fs in os.walk(BASE):
    for f in fs:
        en_paquete.add(f.lower())

print("=== ficheros que cita el README y no estan ===")
citados = set(re.findall(r"`([^`]+\.(?:glb|obj|mtl|json|txt|bin|fbx|png|md))`", t))
citados |= set(re.findall(r"\((preview/[^)]+\.png)\)", t))
fuera = []
for c in sorted(citados):
    if "*" in c or "<" in c:
        continue
    if os.path.basename(c).lower() not in en_paquete:
        fuera.append(c)
print("   %d de %d" % (len(fuera), len(citados)))
for f in fuera:
    print("   ", f)

print("\n=== nombres de las armas en todo el paquete ===")
for pat in ["weapon_gun", "weapon_spear", "gun_01", "gun_02", "gun_holster", "spear"]:
    hits = [os.path.relpath(os.path.join(r, f), BASE) for r, _, fs in os.walk(BASE) for f in fs if pat in f.lower()]
    print("   %-14s %d ficheros" % (pat, len(hits)))

print("\n=== SUMMARY.json: nombres de pieza ===")
s = json.load(open(os.path.join(BASE, "SUMMARY.json"), encoding="utf-8"))
def piezas(o, acc):
    if isinstance(o, dict):
        if "name" in o and "vertices" in o:
            acc.append((o["name"], o.get("vertices")))
        for v in o.values():
            piezas(v, acc)
    elif isinstance(o, list):
        for v in o:
            piezas(v, acc)
acc = []
piezas(s, acc)
for n, v in acc:
    print("   %-28s %s verts" % (n, v))

print("\n=== referencias internas de los OBJ de armas ===")
d = os.path.join(BASE, "01_model", "obj", "weapons")
for f in sorted(os.listdir(d)):
    if f.endswith(".obj"):
        primera = [l.strip() for l in open(os.path.join(d, f), encoding="utf-8")][:3]
        mtl = [l for l in primera if l.startswith("mtllib")]
        ok = os.path.exists(os.path.join(d, mtl[0].split()[1])) if mtl else False
        print("   %-20s %-24s %s" % (f, mtl[0] if mtl else "sin mtllib", "OK" if ok else "ROTO"))

print("\n=== preview/ ===")
pv = os.path.join(BASE, "preview")
print("   raiz: %d PNG" % len([f for f in os.listdir(pv) if f.endswith(".png")]))
for sub in sorted(os.listdir(pv)):
    p = os.path.join(pv, sub)
    if os.path.isdir(p):
        print("   %-16s %d ficheros" % (sub + "/", len(os.listdir(p))))