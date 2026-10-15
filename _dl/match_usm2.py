# -*- coding: utf-8 -*-
"""Emparejamiento usm <-> cue de CueInfoMap.txt, ESTRICTO. Solo analisis."""
import glob, os, re, json

CLIENT = r"C:/Users/Lukas/Downloads/P5X/Client"
MEDIA = CLIENT + "/OuterPackage/Media/Windows"
BIN = CLIENT + "/bin/Media/Windows"

AFIJOS = ("sfx", "anim", "login", "cg", "efx", "se", "v", "p")

def tokens(s):
    return re.findall(r"[a-z]+|[0-9]+", s.lower())

def nucleo(s):
    t = [x for x in tokens(s) if not (x.isdigit() and len(x) == 4)]
    cambiado = True
    while cambiado and t:
        cambiado = False
        if len(t) > 1 and t[0] in AFIJOS:
            t = t[1:]; cambiado = True
        if len(t) > 1 and t[-1] in AFIJOS:
            t = t[:-1]; cambiado = True
    return "".join(t)

def score(stem, cue):
    ns = re.sub(r"[^a-z0-9]", "", stem.lower())
    nc = re.sub(r"[^a-z0-9]", "", cue.lower())
    if ns == nc:
        return 1.0
    ks, kc = nucleo(stem), nucleo(cue)
    if not ks or not kc:
        return 0.0
    if ks == kc:
        return 0.9
    return 0.0

def carga_mapa():
    cue2bank = {}
    for l in open(BIN + "/CueInfoMap.txt", encoding="utf-8", errors="replace"):
        l = l.strip()
        if ":" in l:
            c, b = l.rsplit(":", 1)
            cue2bank.setdefault(c.strip(), b.strip())
    return cue2bank

def main():
    stems = sorted(os.path.splitext(os.path.basename(p))[0] for p in glob.glob(MEDIA + "/*.usm"))
    stems += sorted(os.path.splitext(os.path.basename(p))[0] for p in glob.glob(BIN + "/*.usm"))
    cue2bank = carga_mapa()
    cues = list(cue2bank)
    res, fuertes, nada = {}, [], []
    for s in stems:
        cands = sorted(((score(s, c), c, cue2bank[c]) for c in cues if score(s, c) > 0), reverse=True)
        res[s] = cands[:3]
        (fuertes if cands else nada).append(s)
    print("usm totales:", len(stems))
    print("con match estricto:", len(fuertes), " sin match:", len(nada))
    print("\n--- todos los matches estrictos ---")
    for s in fuertes:
        print("  %-40s -> %s" % (s, res[s][0]))
    json.dump({s: [(sc, c, b) for sc, c, b in v] for s, v in res.items()},
              open(r"C:/Users/Lukas/p5x-datamining/_dl/map_usm_cue.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("\nescrito _dl/map_usm_cue.json")

if __name__ == "__main__":
    main()