# -*- coding: utf-8 -*-
"""Verifica que cada cue emparejado exista como pista con nombre dentro del .acb de su banco.
Construye _dl/indice_audio.json : usm -> {banco, acb, subsong, pista, segundos}
"""
import glob, os, re, json, subprocess, time

CLIENT = r"C:/Users/Lukas/Downloads/P5X/Client"
MEDIA = CLIENT + "/OuterPackage/Media/Windows"
BIN = CLIENT + "/bin/Media/Windows"
VGM = r"C:/Users/Lukas/p5x-datamining/tools/vgmstream/vgmstream-cli.exe"
NO_WIN = 0x08000000

def busca_acb(banco):
    for d in (MEDIA, BIN):
        p = os.path.join(d, banco + ".acb")
        if os.path.isfile(p):
            return p
    return None

def info(acb, s):
    r = subprocess.run([VGM, "-I", "-s", str(s), acb], capture_output=True, text=True,
                       timeout=120, creationflags=NO_WIN)
    try:
        return json.loads(r.stdout.strip().splitlines()[0])
    except Exception:
        return None

def streams_de(acb):
    """devuelve lista (index, nombre, segundos) de todas las pistas del acb"""
    base = info(acb, 1)
    if not base:
        return []
    total = base.get("streamInfo", {}).get("total", 1)
    out = []
    for s in range(1, total + 1):
        d = info(acb, s)
        if not d:
            continue
        si = d.get("streamInfo", {})
        out.append((si.get("index", s), si.get("name", ""), d.get("playSamples", 0) / 48000.0,
                    d.get("sampleRate", 48000)))
    return out

def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())

def main():
    mapa = json.load(open(r"C:/Users/Lukas/p5x-datamining/_dl/map_usm_cue.json", encoding="utf-8"))
    bancos = {}
    for usm, cands in mapa.items():
        if cands:
            bancos.setdefault(cands[0][2], None)
    print("bancos implicados:", len(bancos))
    idx_banco = {}
    t0 = time.time()
    sin_acb = []
    for i, b in enumerate(sorted(bancos), 1):
        acb = busca_acb(b)
        if not acb:
            sin_acb.append(b)
            continue
        idx_banco[b] = (acb, streams_de(acb))
        if i % 25 == 0:
            print("  ... %d/%d  (%.0fs)" % (i, len(bancos), time.time() - t0))
    print("bancos sin .acb:", len(sin_acb), sin_acb[:20])

    # empareja cue -> pista por nombre normalizado
    salida, ok, mal = {}, 0, 0
    for usm, cands in mapa.items():
        if not cands:
            continue
        sc, cue, banco = cands[0]
        if banco not in idx_banco:
            salida[usm] = {"banco": banco, "error": "sin_acb", "cue": cue}
            mal += 1
            continue
        acb, sts = idx_banco[banco]
        ncue = norm(cue)
        hit = None
        for (sidx, nombre, segs, sr) in sts:
            if norm(nombre) == ncue:
                hit = (sidx, nombre, segs, sr)
                break
        if not hit:  # segundo intento: el nombre de pista contiene/contiene el cue
            for (sidx, nombre, segs, sr) in sts:
                if ncue and (ncue in norm(nombre) or norm(nombre) in ncue):
                    hit = (sidx, nombre, segs, sr)
                    break
        if hit:
            salida[usm] = {"banco": banco, "acb": acb, "cue": cue,
                           "subsong": hit[0], "pista": hit[1],
                           "segundos": round(hit[2], 3), "sr": hit[3]}
            ok += 1
        else:
            salida[usm] = {"banco": banco, "acb": acb, "cue": cue, "error": "pista_no_hallada",
                           "pistas": [n for _, n, _, _ in sts][:8]}
            mal += 1
    print("usm con pista localizada:", ok, " sin localizar:", mal)
    json.dump(salida, open(r"C:/Users/Lukas/p5x-datamining/_dl/indice_audio.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("escrito _dl/indice_audio.json")
    for u, v in list(salida.items())[:12]:
        print("  ", u, "->", {k: v[k] for k in v if k != "acb"})

if __name__ == "__main__":
    main()