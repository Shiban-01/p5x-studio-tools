#!/usr/bin/env python3
"""P5X - extrae TODA la banda sonora (y SFX) de los .awb a WAV.

Descubierto 2026-09: los .awb de P5X (AFS2, flags 0x02/0x04) contienen las
voces HCA concatenadas; NO usan tabla de offsets clasica. Se separan buscando
el magic 'HCA\x00'. Las que tienen bloque 'ciph' con datos = cifradas (la
mayoria esta sin cifrar - verificado). vgmstream las decodifica directo.

Uso:  python extract_all_audio.py [carpeta_awb] [salida]
Solo BGM/musica:  filtra con --musica (nombres BGM|Music|FilmBGM|Amb|Voc)
"""
import sys, subprocess, shutil
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

ROOT = Path(__file__).resolve().parent.parent
VGS = str(ROOT / "tools" / "vgmstream" / "vgmstream-cli.exe")
SRC = Path(r"C:/Users/Lukas/Downloads/P5X/Client/OuterPackage/Media/Windows")
OUT = ROOT / "media" / "soundtrack_wav"
args = [a for a in sys.argv[1:] if not a.startswith("--")]
MUSICA_ONLY = "--musica" in sys.argv
if args: SRC = Path(args[0])
if len(args) > 1: OUT = Path(args[1])
OUT.mkdir(parents=True, exist_ok=True)

import re
MUSIC_RE = re.compile(r"(?i)^(BGM|Music|FilmBGM|Amb|Voc|Login|Remain)")

def one(awb: Path):
    tag = awb.stem.strip().rstrip(". ")  # Windows no admite espacios/puntos al final de carpeta
    od = OUT / tag
    od.mkdir(exist_ok=True)
    data = awb.read_bytes()
    if data[:4] != b"AFS2":
        return f"skip (no AFS2) {tag}"
    pos = [m.start() for m in re.finditer(rb"HCA\x00", data)]
    if not pos:
        return f"sin-voz {tag}"
    n_ok = 0
    for i, p in enumerate(pos):
        end = pos[i+1] if i+1 < len(pos) else len(data)
        voz = data[p:end]
        if len(voz) < 500: continue
        dst = od / f"{tag}_{i:03d}.wav"
        if dst.exists() and dst.stat().st_size > 50_000:
            n_ok += 1; continue
        tmp = od / f".v{i}.hca"
        tmp.write_bytes(voz)
        r = subprocess.run([VGS, "-o", str(dst.with_suffix(".part")), str(tmp)],
                           capture_output=True)
        tmp.unlink(missing_ok=True)
        if r.returncode == 0 and dst.with_suffix(".part").exists() and dst.with_suffix(".part").stat().st_size > 50_000:
            dst.with_suffix(".part").rename(dst); n_ok += 1
        elif dst.with_suffix(".part").exists():
            dst.with_suffix(".part").unlink()
    return f"{tag}: {n_ok}/{len(pos)} voces -> {od.name}/"

def main():
    awbs = sorted(SRC.glob("*.awb"))
    if MUSICA_ONLY:
        awbs = [a for a in awbs if MUSIC_RE.match(a.stem)]
    print(f"{len(awbs)} .awb -> {OUT}\n(retomable: saltar lo ya extraido)")
    done = 0
    with ThreadPoolExecutor(4) as ex:
        for res in ex.map(one, awbs):
            done += 1
            if done % 5 == 0 or "sin-voz" in res or "skip" in res:
                print(f"[{done}/{len(awbs)}] {res}", flush=True)
    print(f"terminado: {done}/{len(awbs)} bancos procesados")

if __name__ == "__main__":
    main()
