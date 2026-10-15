# -*- coding: utf-8 -*-
"""exp_v4: regla final.
EMPAREJAMIENTO cue:
  N1 exacto  norm(stem)==norm(cue)
  N2 anagrama de PALABRAS con numeros en orden: multiconjunto de tokens NO numericos igual
     Y secuencia de tokens numericos identica  (caza el caso P3P/Event sin permutar indices)
PISTA en el banco:
  exacto norm(pista)==norm(cue)
  o sufijo de idioma: pista == cue + (_jp|_en|_cn|_zh|_ko)
Mapas: principal + zh + ja (el principal tiene prioridad).
Compara contra el baseline real del cache (142)."""
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
SUFIJOS_IDIOMA = ("jp", "en", "cn", "zh", "ko")


def tok(s):
    return re.findall(r"[a-z]+|[0-9]+", s.lower())


def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def nucleo_ms(s):
    return [x for x in tok(s) if not (x.isdigit() and len(x) == 4) and x not in AFIJOS]


def clave_ms(s):
    t = nucleo_ms(s)
    if len(t) < 2:
        return None
    palabras = tuple(sorted(x for x in t if not x.isdigit()))
    nums = tuple(x for x in t if x.isdigit())
    return (palabras, nums)


def info(acb, s):
    r = subprocess.run([VGM, "-I", "-s", str(s), str(acb)], capture_output=True, text=True,
                       timeout=120, creationflags=NOWIN)
    try:
        return json.loads(r.stdout.strip().splitlines()[0])
    except Exception:
        return None


_CACHE = {}


def streams_de(acb):
    if acb in _CACHE:
        return _CACHE[acb]
    base = info(acb, 1)
    out = []
    if base:
        total = int(base.get("streamInfo", {}).get("total", 1) or 1)
        for s in range(1, total + 1):
            d = info(acb, s) if s > 1 else base
            if not d:
                continue
            si = d.get("streamInfo", {})
            sr = float(d.get("sampleRate", 48000) or 48000)
            out.append((si.get("index", s), si.get("name", ""), float(d.get("playSamples", 0) or 0) / sr))
    _CACHE[acb] = out
    return out


def busca_acb(banco):
    for d in (MEDIA, BIN):
        p = d / (banco + ".acb")
        if p.is_file():
            return p
    return None


def pista_de_banco(acb, cue):
    sts = streams_de(acb)
    ncue = norm(cue)
    for (sidx, nombre, segs) in sts:
        if norm(nombre) == ncue:
            return {"subsong": sidx, "pista": nombre, "segundos": round(segs, 3), "via": "exacta"}
    for (sidx, nombre, segs) in sts:
        nn = norm(nombre)
        for suf in SUFIJOS_IDIOMA:
            if nn == ncue + suf:
                return {"subsong": sidx, "pista": nombre, "segundos": round(segs, 3), "via": "idioma"}
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
    idx_norm, idx_ms = {}, {}
    for c in cue_banco:
        idx_norm.setdefault(norm(c), []).append(c)
        k = clave_ms(c)
        if k:
            idx_ms.setdefault(k, []).append(c)

    usms = sorted(MEDIA.glob("*.usm")) + sorted(BIN.glob("*.usm"))
    res = {}
    for u in usms:
        stem = u.stem
        cands = []
        if norm(stem) in idx_norm:
            cands = [("exacto", c) for c in idx_norm[norm(stem)]]
        else:
            k = clave_ms(stem)
            if k and k in idx_ms:
                cands = [("anagrama", c) for c in idx_ms[k]]
        hit = None
        for nivel, cue in cands[:8]:
            acb = busca_acb(cue_banco[cue])
            if not acb:
                continue
            p = pista_de_banco(acb, cue)
            if p:
                hit = {"nivel": nivel, "cue": cue, "banco": cue_banco[cue], **p}
                break
        res[stem] = hit

    nuevo_ok = [s for s, v in res.items() if v]
    print("NUEVO resuelve a pista:", len(nuevo_ok))

    # baseline del cache
    est = json.load(open(RAIZ / "estado_audio_video.json", encoding="utf-8"))
    base = {s for s, v in est.items() if v.get("estado") in ("audio", "silencio")}
    print("baseline cache (audio+silencio):", len(base))
    ganan = [s for s in res if res[s] and s not in base]
    pierden = [s for s in base if not res.get(s)]
    print("GANAN:", len(ganan), " PIERDEN:", len(pierden))
    for s in ganan:
        h = res[s]
        print("  %-42s %-34s %-42s %8.2fs [%s/%s]" % (s, h["banco"], h["pista"], h["segundos"], h["nivel"], h["via"]))
    print("--- pierden ---")
    for s in pierden:
        print("  ", s, est.get(s))
    json.dump({"res": res, "ganan": ganan, "pierden": pierden},
              open(RAIZ / "exp_v4.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    t0 = time.time()
    main()
    print("en %.1fs" % (time.time() - t0))