# -*- coding: utf-8 -*-
"""Emparejamiento usm <-> cue de CueInfoMap.txt. Solo analisis, no escribe nada."""
import glob, os, re, json, sys

CLIENT = r"C:/Users/Lukas/Downloads/P5X/Client"
MEDIA = CLIENT + "/OuterPackage/Media/Windows"
BIN = CLIENT + "/bin/Media/Windows"

def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())

def strip_digits(s):
    return re.sub(r"[0-9]", "", s)

AFFIJOS = ("sfx", "anim", "login", "cg", "efx", "ui", "v", "p")

def limpia(n):
    """quita prefijos/sufijos de rol para comparar el nucleo del nombre"""
    cambiado = True
    while cambiado:
        cambiado = False
        for a in AFFIJOS:
            if n.startswith(a) and len(n) > len(a) + 3:
                n = n[len(a):]; cambiado = True
            if n.endswith(a) and len(n) > len(a) + 3:
                n = n[:-len(a)]; cambiado = True
    return n

def carga_mapa():
    cue2bank = {}
    for l in open(BIN + "/CueInfoMap.txt", encoding="utf-8", errors="replace"):
        l = l.strip()
        if ":" in l:
            c, b = l.rsplit(":", 1)
            cue2bank.setdefault(c.strip(), b.strip())
    return cue2bank

def score(stem, cue):
    ns, nc = norm(stem), norm(cue)
    if ns == nc:
        return 1.0
    if strip_digits(ns) == strip_digits(nc):
        return 0.95
    ls, lc = limpia(ns), limpia(nc)
    if ls == lc:
        return 0.9
    if strip_digits(ls) == strip_digits(lc):
        return 0.88
    if ls and lc and (ls in lc or lc in ls):
        return 0.75
    if strip_digits(ls) and strip_digits(lc) and (strip_digits(ls) in strip_digits(lc) or strip_digits(lc) in strip_digits(ls)):
        return 0.7
    return 0.0

def main():
    stems = sorted(os.path.splitext(os.path.basename(p))[0]
                   for p in glob.glob(MEDIA + "/*.usm"))
    stems += sorted(os.path.splitext(os.path.basename(p))[0]
                    for p in glob.glob(BIN + "/*.usm"))
    cue2bank = carga_mapa()
    cues = list(cue2bank)
    res = {}
    for s in stems:
        cands = []
        for c in cues:
            sc = score(s, c)
            if sc > 0:
                cands.append((sc, c, cue2bank[c]))
        cands.sort(reverse=True)
        res[s] = cands[:3]
    fuertes = [s for s, c in res.items() if c and c[0][0] >= 0.88]
    medias = [s for s, c in res.items() if c and 0.7 <= c[0][0] < 0.88]
    debiles = [s for s, c in res.items() if c and c[0][0] < 0.7]
    nada = [s for s, c in res.items() if not c]
    print("usm totales:", len(stems))
    print("match fuerte(>=0.88):", len(fuertes))
    print("match medio(0.70-0.88):", len(medias))
    print("match debil(<0.70):", len(debiles))
    print("sin match:", len(nada))
    print("\n--- ejemplos fuertes ---")
    for s in fuertes[:30]:
        print("  %-40s -> %s" % (s, res[s][0]))
    print("\n--- ejemplos medios ---")
    for s in medias[:20]:
        print("  %-40s -> %s" % (s, res[s][0]))
    json.dump({s: [(sc, c, b) for sc, c, b in v] for s, v in res.items()},
              open(r"C:/Users/Lukas/p5x-datamining/_dl/map_usm_cue.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("\nescrito _dl/map_usm_cue.json")

if __name__ == "__main__":
    main()