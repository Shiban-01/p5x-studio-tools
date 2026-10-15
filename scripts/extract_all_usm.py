#!/usr/bin/env python3
"""P5X - extrae TODOS los videos .usm a MP4 (desencripta VP9 + mux con ffmpeg).

Descubierto 2026-09: los USM de P5X usan cifrado Sofdec Prime 2 que SOLO
implementa WannaCRI (usmbreak/MueruTools = cifrado antiguo, no sirve).
Llave verificada build global: 1729401234202.

OJO con las carpetas: los USM viven en **DOS** sitios del cliente:
  OuterPackage/Media/Windows  (347: CGs, actividades, efectos)
  bin/Media/Windows          (5: la familia REMAIN-CG1, p.ej. la pantalla del logo de SEGA)
Mirar solo la primera costo 5 videos sin extraer durante meses. El defecto ya cubre las dos.

Uso:  python extract_all_usm.py [carpeta(s)_usm] [salida]  [num_workers]
      (varias carpetas separadas por ';'  ->  "C:/.../OuterPackage/Media/Windows;C:/.../bin/Media/Windows")
"""
import sys, os, subprocess, shutil
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

ROOT = Path(__file__).resolve().parent.parent
PY = str(ROOT / "tools" / "env" / "Scripts" / "python.exe")
KEY = os.environ.get("P5X_USM_KEY", "1729401234202")
DEFAULT_SRCS = [Path(r"C:/Users/Lukas/Downloads/P5X/Client/OuterPackage/Media/Windows"),
                Path(r"C:/Users/Lukas/Downloads/P5X/Client/bin/Media/Windows")]
SRCS = ([Path(p) for p in sys.argv[1].split(";") if p.strip()]
        if len(sys.argv) > 1 else DEFAULT_SRCS)
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "media" / "videos_mp4"
WORKERS = int(sys.argv[3]) if len(sys.argv) > 3 else 3
OUT.mkdir(parents=True, exist_ok=True)
FFMPEG = shutil.which("ffmpeg")

def convert(usm: Path) -> str:
    stem = usm.stem
    dst = OUT / f"{stem}.mp4"
    if dst.exists() and dst.stat().st_size > 10_000:
        return f"skip {stem}"
    # Marcador de catalogo: hay USM con cabecera valida pero SIN carga de video (p.ej.
    # CG_yugao_2_1.usm, 3 KB, frente a los 5-16 MB de sus hermanos). WannaCRI saca un .ivf
    # de 0 bytes y no es un fallo nuestro. Se saltan para no llenar la salida de basura.
    if usm.stat().st_size < 8_192:
        return f"STUB-sin-video {stem} ({usm.stat().st_size} bytes)"
    tmp = OUT / f".tmp_{stem}"
    tmp.mkdir(exist_ok=True)
    try:
        cmd = [PY, "-m", "wannacri", "extractusm", str(usm), "-k", KEY, "-o", str(tmp)]
        subprocess.run(cmd, capture_output=True)
        found = list(tmp.rglob("*.ivf")) or list(tmp.rglob("*.avi")) or list(tmp.rglob("*.sfv"))
        if not found:
            # clips de build CN: string literals en GBK (no shift-jis); WannaCRI
            # no signaliza error con exit-code, asi que probamos por salida vacia
            subprocess.run(cmd + ["-e", "gbk"], capture_output=True)
            found = list(tmp.rglob("*.ivf")) or list(tmp.rglob("*.avi")) or list(tmp.rglob("*.sfv"))
        ivf = found[0] if found else None
        if ivf is None:
            return f"NO-VIDEO {stem}"
        # forzar formato de salida (la extension .part no se autodetecta)
        if FFMPEG:
            # los .ivf traen su cabecera; los .avi tambien; los .sfv crudos necesitan
            # que se los declare como mpeg con nombre .mpg para que ffmpeg los lea
            src_in = ivf
            if ivf.suffix == ".sfv":
                src_in = tmp / "raw.mpg"
                shutil.copy(ivf, src_in)
            r = subprocess.run([FFMPEG, "-y", "-v", "error", "-i", str(src_in),
                                "-c", "copy", "-f", "mp4", str(dst.with_suffix(".tmp.mp4"))], capture_output=True)
            if r.returncode == 0 and dst.with_suffix(".tmp.mp4").stat().st_size > 1000:
                dst.with_suffix(".tmp.mp4").rename(dst)
            else:
                if ivf.stat().st_size > 1000:
                    shutil.copy(ivf, dst.with_suffix(".ivf"))
                return f"ffmpeg-fallo->ivf {stem} {r.stderr.decode()[:80]}"
            return f"OK {stem}"
        if ivf.stat().st_size > 1000:
            shutil.copy(ivf, dst.with_suffix(".ivf"))
        return f"OK-ivf {stem}"
    except subprocess.CalledProcessError as e:
        return f"ERROR {stem}: {e.stderr.decode(errors='replace')[:120]}"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

def main():
    usms = []
    for d in SRCS:
        if not d.exists():
            print(f"AVISO: no existe {d}")
            continue
        hallados = sorted(d.rglob("*.usm"))
        print(f"  {d} -> {len(hallados)} .usm")
        usms += hallados
    usms = sorted(set(usms))
    print(f"\n{len(usms)} archivos .usm en total -> {OUT} ({WORKERS} workers)"
          f"\nCTRL-C cancela; retomar vuelve a lanzar (saltar los .mp4 ya hechos)")
    done = 0
    with ThreadPoolExecutor(WORKERS) as ex:
        try:
            for res in ex.map(convert, usms):
                done += 1
                print(f"[{done}/{len(usms)}] {res}", flush=True)
        except KeyboardInterrupt:
            print("cancelado")
    print("terminado")

if __name__ == "__main__":
    main()
