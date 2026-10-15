#!/usr/bin/env python
"""Lista TODAS las pistas (subsongs) de un .acb con vgmstream -I. Uso:
    python lista_pistas.py <banco.acb> [patron_substring]
Imprime: subsong  nombre  duracion_s  canales  encoding  ruta
"""
import json, subprocess, sys, re
from pathlib import Path

VGM = Path("C:/Users/Lukas/p5x-datamining/tools/vgmstream/vgmstream-cli.exe")


def info(acb, sub):
    r = subprocess.run([str(VGM), "-I", "-m", "-s", str(sub), str(acb)],
                       capture_output=True, text=True, timeout=120)
    try:
        return json.loads((r.stdout or "").strip().splitlines()[0])
    except Exception:
        return None


def main():
    acb = Path(sys.argv[1])
    patron = (sys.argv[2].lower() if len(sys.argv) > 2 else "")
    base = info(acb, 1)
    if not base:
        print("NO INFO", acb)
        return
    total = int(base["streamInfo"]["total"])
    print("BANCO: %s   total=%d" % (acb.name, total))
    for s in range(1, total + 1):
        d = info(acb, s)
        if not d:
            continue
        si = d.get("streamInfo", {})
        sr = float(d.get("sampleRate", 48000) or 48000)
        seg = float(d.get("playSamples", 0) or 0) / sr
        nom = si.get("name", "") or ""
        if patron and patron not in nom.lower():
            continue
        print("%3d  %-46s %9.3f s  %sch  %s" % (
            si.get("index", s), nom, seg, d.get("channels"), d.get("encoding")))


if __name__ == "__main__":
    main()