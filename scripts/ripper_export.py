#!/usr/bin/env python3
"""P5X -> Unity: prepara y exporta cinematicas (tl_*) seleccionadas.

Flujo por escena:
 1. copia tl_X + bundles relacionados (role_/scn_/efx_/atlas_/anim_/shared_/p_) a un staging
 2. desofusca (prefijo hash en cada bundle)
 3. POST /LoadFolder -> AssetRipper
 4. POST /Export/UnityProject -> <out>/Proyecto_<tl>
Requiere AssetRipper.GUI.Free --headless corriendo (default 127.0.0.1:57973).

Uso: python ripper_export.py tl_005 [tl_01_15 ...]   (o --all-tl N para N bundles tl al azar)
"""
import sys, os, re, shutil, time, subprocess, urllib.request, urllib.parse
from pathlib import Path

BUNDLES = Path("C:/Users/Lukas/Downloads/P5X/Client/OuterPackage/Bundles/Windows")
ROOT = Path(__file__).resolve().parent.parent
STAGE = ROOT / "_dl" / "stage"
OUT = ROOT / "unity_projects"
BASE = "http://127.0.0.1:57973"

def http(path, data=None):
    body = urllib.parse.urlencode(data).encode() if data else None
    req = urllib.request.Request(BASE + path, data=body)
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k): return None
    op = urllib.request.build_opener(NoRedirect)
    try: return op.open(req, timeout=600).status
    except urllib.error.HTTPError as e: return e.code

def hash_offset(name):
    n = 0
    for c in name: n = (n * 131 + ord(c)) & 0xFFFFFFFF
    return (n & 0x7FFFFFFF) % 32 + 8

def stage_and_export(names, outdir: Path):
    if STAGE.exists(): shutil.rmtree(STAGE)
    STAGE.mkdir(parents=True)
    copied = 0
    for stem in names:
        src = next(BUNDLES.rglob(stem + ".bundle"), None)
        if not src: continue
        dst = STAGE / src.name
        dst.write_bytes(src.read_bytes()[hash_offset(src.name):])
        copied += 1
    print(f"  staged {copied} bundles (desofuscados)")
    print("  reset:", http("/Reset"))
    print("  load:", http("/LoadFolder", {"Path": str(STAGE)}))
    time.sleep(1)
    outdir.mkdir(parents=True, exist_ok=True)
    print("  export:", http("/Export/UnityProject", {"Path": str(outdir), "CreateSubfolder": "false"}))
    return outdir / "ExportedProject"

def related(tl_stem):
    """bundles relacionados: el propio tl + prefijos comunes que podrian contener sus deps"""
    rel = [tl_stem]
    for b in BUNDLES.rglob("*.bundle"):
        s = b.stem
        if s == tl_stem: continue
        if re.match(r"^(role_|roletiny_|scn_|efx_|atlas_|anim_|shared_|p_|ui|uitex_)", s):
            rel.append(s)
    return rel  # optimizado abajo por prefijo del tl

if __name__ == "__main__":
    args = sys.argv[1:]
    if not args: sys.exit("uso: ripper_export.py <tl_nombre...>")
    for tl in args:
        src = next(BUNDLES.rglob(tl + ".bundle"), None)
        if not src:
            print("no existe", tl); continue
        # token del personaje: tl_pc063+hash(8hex) -> "pc063"; role_pc063_02+hash -> "pc063_0"
        core = re.sub(r"^(tl|role|part|scn|efx|anim|atlas|uitex)_", "", tl)
        core = re.sub(r"[0-9a-f]{8}$", "", core)  # quita hash sufijo (8 hex)
        toks = [t for t in re.split(r"[_0-9]+", core) if len(t) >= 4 and not re.fullmatch(r"[0-9a-f]{6,}", t)]
        # y el ID tipo PC063/8402 (letras+digits, 4+ chars, ej "pc063", "e_wonder"->wonder)
        m = re.search(r"([a-zA-Z]+\d{2,})", core)
        if m: toks.append(m.group(1))
        names = [tl]
        if toks:
            for b in BUNDLES.rglob("*.bundle"):
                s = b.stem.lower()
                if any(t.lower() in s for t in toks):
                    names.append(b.stem)
        out = OUT / tl
        print(f"== {tl}: {len(names)} bundles candidatos (tokens {toks})")
        prj = stage_and_export(names, out)
        print("   ->", prj, "OK" if prj.exists() else "FALLO")
