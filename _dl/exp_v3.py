# -*- coding: utf-8 -*-
"""Comparacion rigurosa VIEJO vs NUEVO, ambos resolviendo banco+pista reales.
VIEJO = replica exacta de herramientas._puntua_cue (exacto / nucleo concatenado, afijos
        solo en extremos) + _pista_de_banco (nombre==cue, luego contiene).
NUEVO = multiconjunto de tokens (sin anios 4-dig y sin afijos en cualquier posicion).
Cache de bancos compartida para no repetir vgmstream."""
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
AFIJOS = ("sfx", "anim", "login", "cg", "efx", "se", "v", "p")
AFIJOS_SET = set(AFIJOS)


def tok(s):
    return re.findall(r"[a-z]+|[0-9]+", s.lower())


# ---------- VIEJO ----------
def nucleo_viejo(s):
    t = [x for x in tok(s) if not (x.isdigit() and len(x) == 4)]
    c = True
    while c and t:
        c = False
        if len(t) > 1 and t[0] in AFIJOS_SET:
            t = t[1:]; c = True
        if len(t) > 1 and t[-1] in AFIJOS_SET:
            t = t[:-1]; c = True
    return "".join(t)


def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def puntua_viejo(stem, cue):
    if norm(stem) == norm(cue):
        return 1.0
    ks, kc = nucleo_viejo(stem), nucleo_viejo(cue)
    if ks and kc and ks == kc:
        return 0.9
    return 0.0


# ---------- NUEVO ----------
def nucleo_nuevo(s):
    return [x for x in tok(s) if not (x.isdigit() and len(x) == 4) and x not in AFIJOS_SET]


def clave_nuevo(s):
    t = nucleo_nuevo(s)
    return "|".join(sorted(t)) if len(t) >= 2 else None


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
            return {"subsong": sidx, "pista": nombre, "segundos": round(segs, 3)}
    for (sidx, nombre, segs) in sts:
        nn = norm(nombre)
        if ncue and (ncue in nn or nn in ncue):
            return {"subsong": sidx, "pista": nombre, "segundos": round(segs, 3)}
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
    cues = list(cue_banco)
    idx_nuevo = {}
    for c in cues:
        k = clave_nuevo(c)
        if k:
            idx_nuevo.setdefault(k, []).append(c)
    usms = sorted(MEDIA.glob("*.usm")) + sorted(BIN.glob("*.usm"))

    res_v, res_n = {}, {}
    for i, u in enumerate(usms, 1):
        stem = u.stem
        # VIEJO
        cands = sorted(((puntua_viejo(stem, c), c) for c in cues if puntua_viejo(stem, c) > 0),
                       key=lambda x: -x[0])
        hitv = None
        for _, cue in cands[:3]:
            acb = busca_acb(cue_banco[cue])
            if not acb:
                continue
            p = pista_de_banco(acb, cue)
            if p:
                hitv = {"cue": cue, "banco": cue_banco[cue], **p}
                break
        res_v[stem] = hitv
        # NUEVO
        k = clave_nuevo(stem)
        ncands = idx_nuevo.get(k, [])
        hitn = None
        for cue in ncands[:6]:
            acb = busca_acb(cue_banco[cue])
            if not acb:
                continue
            p = pista_de_banco(acb, cue)
            if p:
                hitn = {"cue": cue, "banco": cue_banco[cue], **p}
                break
        res_n[stem] = hitn
        if i % 50 == 0:
            print("  %d/%d" % (i, len(usms)), flush=True)

    ov = sum(1 for v in res_v.values() if v)
    on = sum(1 for v in res_n.values() if v)
    print("VIEJO resuelve a pista:", ov)
    print("NUEVO resuelve a pista:", on)
    ganan = [s for s in res_n if res_n[s] and not res_v[s]]
    pierden = [s for s in res_v if res_v[s] and not res_n[s]]
    print("GANAN:", len(ganan), " PIERDEN:", len(pierden))
    print("--- GANAN (stem -> banco / pista / segs) ---")
    for s in ganan:
        h = res_n[s]
        print("  %-42s %-40s %-40s %8.2fs" % (s, h["banco"], h["pista"], h["segundos"]))
    print("--- PIERDEN ---")
    for s in pierden:
        print("  ", s, res_v[s], "->", res_n[s])
    json.dump({"viejo": res_v, "nuevo": res_n, "ganan": ganan, "pierden": pierden},
              open(RAIZ / "exp_v3.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    t0 = time.time()
    main()
    print("en %.1fs" % (time.time() - t0))