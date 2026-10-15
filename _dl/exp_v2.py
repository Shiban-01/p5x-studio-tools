# -*- coding: utf-8 -*-
"""Experimento v2: nucleo = tokens sin anios de 4 digitos y sin afijos (en CUALQUIER
posicion, no solo extremos); comparacion por multiconjunto. Resuelve ademas banco y
pista reales con vgmstream para contar lo que de verdad empareja."""
import re, json, time, subprocess
from pathlib import Path

CLIENT = Path(r"C:/Users/Lukas/Downloads/P5X/Client")
MAPAS = [CLIENT / "bin/Media/Windows/CueInfoMap.txt",
         CLIENT / "bin/Media/Windows/zh_CueInfoMap.txt",
         CLIENT / "bin/Media/Windows/ja_CueInfoMap.txt"]
MEDIA = CLIENT / "OuterPackage/Media/Windows"
BIN = CLIENT / "bin/Media/Windows"
RAIZ = Path(r"C:/Users/Lukas/p5x-datamining/_dl")
VGM = r"C:/Users/Lukas/p5x-datamining/tools/vgmstream/vgmstream-cli.exe"
NOWIN = 0x08000000
AFIJOS = {"sfx", "anim", "login", "cg", "efx", "se", "v", "p"}


def tok(s):
    return re.findall(r"[a-z]+|[0-9]+", s.lower())


def nucleo_tokens(s):
    return [x for x in tok(s) if not (x.isdigit() and len(x) == 4) and x not in AFIJOS]


def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def clave_ms(s):
    t = nucleo_tokens(s)
    return "|".join(sorted(t)) if len(t) >= 2 else None


def info(acb, s):
    r = subprocess.run([VGM, "-I", "-s", str(s), str(acb)], capture_output=True, text=True,
                       timeout=120, creationflags=NOWIN)
    try:
        return json.loads(r.stdout.strip().splitlines()[0])
    except Exception:
        return None


_CACHE_ACB = {}


def streams_de(acb):
    if acb in _CACHE_ACB:
        return _CACHE_ACB[acb]
    base = info(acb, 1)
    if not base:
        _CACHE_ACB[acb] = []
        return []
    total = int(base.get("streamInfo", {}).get("total", 1) or 1)
    out = []
    for s in range(1, total + 1):
        d = info(acb, s) if s > 1 else base
        if not d:
            continue
        si = d.get("streamInfo", {})
        sr = float(d.get("sampleRate", 48000) or 48000)
        out.append((si.get("index", s), si.get("name", ""), float(d.get("playSamples", 0) or 0) / sr))
    _CACHE_ACB[acb] = out
    return out


def busca_acb(banco):
    for d in (MEDIA, BIN):
        p = d / (banco + ".acb")
        if p.is_file():
            return p
    return None


def main():
    cue_banco = {}
    for m in MAPAS:
        if not m.is_file():
            continue
        for linea in m.read_text(encoding="utf-8", errors="replace").splitlines():
            linea = linea.strip()
            if ":" in linea:
                cue, banco = linea.rsplit(":", 1)
                cue, banco = cue.strip(), banco.strip()
                if cue and banco:
                    cue_banco.setdefault(cue, banco)
    print("cues:", len(cue_banco))

    idx_norm, idx_ms = {}, {}
    for cue in cue_banco:
        idx_norm.setdefault(norm(cue), []).append(cue)
        k = clave_ms(cue)
        if k:
            idx_ms.setdefault(k, []).append(cue)

    usms = sorted(MEDIA.glob("*.usm")) + sorted(BIN.glob("*.usm"))
    print("usm:", len(usms))

    def candidatos(stem):
        """devuelve (nivel, [cues]) del mejor emparejamiento de nombre."""
        n = norm(stem)
        if n in idx_norm:
            return ("exacto", idx_norm[n])
        k = clave_ms(stem)
        if k and k in idx_ms:
            return ("multiset", idx_ms[k])
        return (None, [])

    filas = []
    for u in usms:
        stem = u.stem
        nivel, cues = candidatos(stem)
        # resolver banco+pista
        hit = None
        for cue in cues[:6]:
            banco = cue_banco[cue]
            acb = busca_acb(banco)
            if not acb:
                continue
            sts = streams_de(acb)
            ncue = norm(cue)
            for (sidx, nombre, segs) in sts:
                if norm(nombre) == ncue:
                    hit = {"cue": cue, "banco": banco, "subsong": sidx, "pista": nombre,
                           "segundos": round(segs, 3)}
                    break
            if not hit:
                for (sidx, nombre, segs) in sts:
                    nn = norm(nombre)
                    if ncue and (ncue in nn or nn in ncue):
                        hit = {"cue": cue, "banco": banco, "subsong": sidx, "pista": nombre,
                               "segundos": round(segs, 3)}
                        break
            if hit:
                break
        filas.append((stem, nivel, [c for c in cues[:6]], hit))

    json.dump([{"stem": s, "nivel": n, "cues": c, "hit": h} for s, n, c, h in filas],
              open(RAIZ / "exp_v2.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    con_hit = [f for f in filas if f[3]]
    print("usm que resuelven a PISTA real:", len(con_hit))
    from collections import Counter
    print("por nivel:", Counter(f[1] for f in con_hit))
    # caso del usuario
    for s, n, c, h in filas:
        if s == "CG_P3P_Event_Main_05_3_movie":
            print("CASO:", s, "nivel", n, "cues", c, "hit", h)


if __name__ == "__main__":
    t0 = time.time()
    main()
    print("en %.1fs" % (time.time() - t0))