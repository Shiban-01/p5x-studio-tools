#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Auditoria del pipeline de video: ¿tenemos TODOS los USM del cliente y estan BIEN?

Contar ficheros no basta: un MP4 truncado (wannacri que peta a medias, o el bug de
`Unknown element occurence 0`) figura como "extraido" sin serlo. Este script cruza:
  USM del cliente  <->  MP4 extraidos   por nombre,
y para cada MP4 comprueba con ffprobe: que abre, que dura > 0, que tiene pista de video
y que su tamano es coherente con el USM de origen (un VP9 bien decodificado no baja del
15% del USM; un MPEG-1 Sofdec si, por eso el umbral es configurable).

Uso:
    python scripts/audit_videos.py                 # informe
    python scripts/audit_videos.py --min-ratio 0.1
"""
import argparse
import glob
import json
import os
import subprocess
import sys

CLIENTE = r"C:\Users\Lukas\Downloads\P5X\Client"
MEDIA_DIRS = [os.path.join(CLIENTE, "OuterPackage", "Media", "Windows"),
              os.path.join(CLIENTE, "bin", "Media", "Windows")]
MP4_DIR = r"C:\Users\Lukas\p5x-datamining\media\videos_mp4"

ap = argparse.ArgumentParser()
ap.add_argument("--min-ratio", type=float, default=0.15)
ap.add_argument("--json", default=r"C:\Users\Lukas\p5x-datamining\_dl\audit_videos.json")
a = ap.parse_args()


def probe(p):
    """Devuelve (duracion, nº pistas video, nº pistas audio, error)."""
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                            "format=duration:stream=codec_type",
                            "-of", "json", p],
                           capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            return None, 0, 0, (r.stderr or "ffprobe fallo").strip()[:120]
        d = json.loads(r.stdout or "{}")
        dur = float(d.get("format", {}).get("duration", 0) or 0)
        tipos = [s.get("codec_type") for s in d.get("streams", [])]
        return dur, tipos.count("video"), tipos.count("audio"), None
    except Exception as e:
        return None, 0, 0, f"{type(e).__name__}: {e}"[:120]


def main():
    usm = []
    for d in MEDIA_DIRS:
        usm += glob.glob(os.path.join(d, "*.usm"))
    mp4 = glob.glob(os.path.join(MP4_DIR, "*.mp4"))
    stem = lambda p: os.path.splitext(os.path.basename(p))[0].lower()

    idx_usm = {stem(p): p for p in usm}
    idx_mp4 = {stem(p): p for p in mp4}
    # USM de 0 bytes no son extraibles: es un fichero que no se bajo, no un fallo del pipeline
    vacios = [n for n, p in idx_usm.items() if os.path.getsize(p) == 0]

    print(f"USM en el cliente : {len(idx_usm)}  ({len(vacios)} de 0 bytes)")
    print(f"MP4 extraidos     : {len(idx_mp4)}")
    print(f"USM sin MP4       : {sorted(set(idx_usm) - set(idx_mp4))}")
    print(f"MP4 sin USM       : {sorted(set(idx_mp4) - set(idx_usm))}")
    print()

    malos, sanos, sin_usm = [], 0, []
    for n, p in sorted(idx_mp4.items()):
        dur, nv, na, err = probe(p)
        size = os.path.getsize(p)
        u = idx_usm.get(n)
        u_size = os.path.getsize(u) if u else None
        ratio = (size / u_size) if u_size else None
        problema = []
        if err:
            problema.append(f"ffprobe: {err}")
        if not nv:
            problema.append("sin pista de video")
        if dur is not None and dur <= 0:
            problema.append("duracion 0")
        if ratio is not None and ratio < a.min_ratio:
            problema.append(f"ratio {ratio:.3f} (< {a.min_ratio})")
        if u is None:
            sin_usm.append(n)
        if problema:
            malos.append({"nombre": n, "dur": dur, "mb": round(size / 1e6, 3),
                          "usm_mb": round(u_size / 1e6, 3) if u_size else None,
                          "ratio": round(ratio, 3) if ratio else None,
                          "problemas": problema})
        else:
            sanos += 1

    print(f"=== MP4 auditados: {len(idx_mp4)}  ·  sanos: {sanos}  ·  con problema: {len(malos)} ===")
    for m in malos:
        print(f"   {m['nombre'][:44]:44} {m['mb']:8.3f} MB (USM {m['usm_mb']}) dur={m['dur']}"
              f"  -> {'; '.join(m['problemas'])}")
    if not malos:
        print("   (ninguno: todos abren, duran > 0 y tienen video)")

    print(f"\ntamano MP4 total: {sum(os.path.getsize(p) for p in mp4)/1e9:.2f} GB"
          f"  ·  USM total: {sum(os.path.getsize(p) for p in usm)/1e9:.2f} GB")
    json.dump({"faltan": sorted(set(idx_usm) - set(idx_mp4)), "malos": malos,
               "vacios": vacios, "sanos": sanos},
              open(a.json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"informe en {a.json}")


if __name__ == "__main__":
    sys.exit(main() or 0)