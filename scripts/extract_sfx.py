#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Extrae los SFX concretos que pide el timeline desde los .acb del cliente.

Los .acb de P5X son contenedores CRI ACB con varios streams HCA; vgmstream-cli
(-m metadata / -s indice) lista los nombres de stream y decodifica a WAV, asi que
no hace falta adivinar indices a mano.

Uso: python extract_sfx.py [nombre1 nombre2 ...]
"""
import re, subprocess, sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

ROOT = Path(__file__).resolve().parent.parent
VGS = str(ROOT / "tools" / "vgmstream" / "vgmstream-cli.exe")
SRC = Path(r"C:/Users/Lukas/Downloads/P5X/Client/OuterPackage/Media/Windows")
OUT = ROOT / "media" / "sfx_wav"
OUT.mkdir(parents=True, exist_ok=True)

# SFX que pide TL_P3P_Event_side_prologue_04_04 (ver _dl/audio_events.json)
QUERIDOS = sys.argv[1:] or [
    "SFX_FlashWhite_Short_01",
    "SFX_Foley_Steps_Flats_Concrete_Walk",
    "SFX_Foley_Steps_Man_Boot_Long_02",
]
# .acb candidatos (donde el grep encontro los nombres)
ACBS = ["Cinematic.acb", "Human_Male.acb", "Human_Female.acb", "Human_Crowd.acb"]


def meta(acb: Path, idx: int):
    """(nombre, duracion) del stream idx del .acb, o None si no existe."""
    try:
        r = subprocess.run([VGS, "-m", "-s", str(idx), str(acb)],
                           capture_output=True, text=True, timeout=60)
    except Exception:
        return None
    t = r.stdout + r.stderr
    if r.returncode != 0 or "stream name:" not in t:
        return None
    n = re.search(r"stream name:\s*(.+)", t)
    d = re.search(r"play duration:.*?\(([\d:.]+)\)", t)
    return (n.group(1).strip() if n else ""), (d.group(1) if d else "?")


def extrae(acb: Path, idx: int, destino: Path):
    r = subprocess.run([VGS, "-s", str(idx), "-o", str(destino), str(acb)],
                       capture_output=True, text=True, timeout=300)
    return r.returncode == 0 and destino.exists() and destino.stat().st_size > 100


def main():
    encontrados = {}
    for acb in ACBS:
        p = SRC / acb
        if not p.exists():
            print(f"[!] no existe {acb}")
            continue
        print(f"=== {acb} ===")
        idxs = []
        for i in range(1, 300):
            m = None if i > 1 else None
            pass
        # sondeo paralelo de indices
        with ThreadPoolExecutor(max_workers=8) as ex:
            res = list(ex.map(lambda i: (i, meta(p, i)), range(1, 260)))
        validos = [(i, m) for i, m in res if m]
        print(f"   streams validos: {len(validos)}")
        for i, (nombre, dur) in validos:
            if any(q.lower() in nombre.lower() for q in QUERIDOS):
                print(f"   [{i:3}] {nombre}  ({dur})")
                dst = OUT / (nombre + ".wav")
                if extrae(p, i, dst):
                    encontrados[nombre] = dst
                    print(f"        -> {dst.name} ({dst.stat().st_size // 1024} KB)")
    print("\n=== resumen ===")
    for q in QUERIDOS:
        hit = [k for k in encontrados if q.lower() in k.lower()]
        print(f"  {q:38} {'OK: ' + hit[0] if hit else 'NO ENCONTRADO'}")


if __name__ == "__main__":
    main()