# -*- coding: utf-8 -*-
"""Experimento: mide cuantos .usm mas emparejan si el nucleo del cue se compara por
MULTICONJUNTO de tokens (insensible al orden) en vez de por concatenacion ordenada.
No toca nada; solo mide y volca candidatos."""
import re, json, time
from collections import Counter
from pathlib import Path

CLIENT = Path(r"C:/Users/Lukas/Downloads/P5X/Client")
MAPAS = [CLIENT / "bin/Media/Windows/CueInfoMap.txt",
         CLIENT / "bin/Media/Windows/zh_CueInfoMap.txt",
         CLIENT / "bin/Media/Windows/ja_CueInfoMap.txt"]
MEDIA = CLIENT / "OuterPackage/Media/Windows"
BIN = CLIENT / "bin/Media/Windows"
RAIZ = Path(r"C:/Users/Lukas/p5x-datamining/_dl")

AFIJOS = ("sfx", "anim", "login", "cg", "efx", "se", "v", "p")


def tok(s):
    return re.findall(r"[a-z]+|[0-9]+", s.lower())


def nucleo_tokens(s):
    t = [x for x in tok(s) if not (x.isdigit() and len(x) == 4)]
    c = True
    while c and t:
        c = False
        if len(t) > 1 and t[0] in AFIJOS:
            t = t[1:]; c = True
        if len(t) > 1 and t[-1] in AFIJOS:
            t = t[:-1]; c = True
    return t


def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def clave_multiset(s):
    t = nucleo_tokens(s)
    if len(t) < 2:
        return None
    return "|".join(sorted(t))


def main():
    # --- leer mapas ---
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
    print("cues totales en los 3 mapas:", len(cue_banco))

    idx_norm = {}
    idx_ms = {}
    for cue in cue_banco:
        idx_norm.setdefault(norm(cue), []).append(cue)
        k = clave_multiset(cue)
        if k:
            idx_ms.setdefault(k, []).append(cue)

    usms = sorted(MEDIA.glob("*.usm")) + sorted(BIN.glob("*.usm"))
    print("usm:", len(usms))

    viejo_ok = nuevo_ok = 0
    ganan = []
    solo_viejo = []
    for u in usms:
        stem = u.stem
        # viejo: nucleo concatenado
        ks = "".join(nucleo_tokens(stem))
        v_cands = [c for c in cue_banco if "".join(nucleo_tokens(c)) == ks] if ks else []
        v_hit = bool(v_cands)
        if v_hit:
            viejo_ok += 1
        # nuevo: multiset
        kms = clave_multiset(stem)
        n_cands = list(idx_ms.get(kms, [])) if kms else []
        if not n_cands and norm(stem) in idx_norm:
            n_cands = idx_norm[norm(stem)]
        n_hit = bool(n_cands)
        if n_hit:
            nuevo_ok += 1
        if n_hit and not v_hit:
            ganan.append((stem, [(c, cue_banco[c]) for c in n_cands[:4]]))
        if v_hit and not n_hit:
            solo_viejo.append((stem, v_cands[:3]))
    print("viejo (nucleo concatenado) empareja:", viejo_ok)
    print("nuevo (multiset) empareja:", nuevo_ok)
    print("ganan con multiset:", len(ganan))
    print("solo con viejo (regresion):", len(solo_viejo))
    for s, c in solo_viejo[:20]:
        print("   REG", s, c)
    print("--- primeros 40 que ganan ---")
    for s, c in ganan[:40]:
        print("  ", s, "->", c)
    json.dump({"ganan": [[s, c] for s, c in ganan],
               "solo_viejo": [[s, c] for s, c in solo_viejo]},
              open(RAIZ / "exp_multiset.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)


if __name__ == "__main__":
    t0 = time.time()
    main()
    print("en %.1fs" % (time.time() - t0))