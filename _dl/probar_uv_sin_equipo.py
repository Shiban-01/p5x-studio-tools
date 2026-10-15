"""Ensayo de "equipo ajeno": aqui se finge que el equipo NO tiene uv ni nada instalado.

Por que existe: en la prueba de fuego salio que wannacri necesita `uv` para montar su entorno de
Python, y que `uv` estaba en el PATH de este equipo. En otro equipo puede no haberlo, y entonces la
extraccion de video (la funcion principal) se cae. Ahora la app se baja su propio uv a tools/uv/.

Esta prueba se corre con el PATH y el USERPROFILE capados (desde el shell), de modo que no se pueda
encontrar ningun uv del equipo, y monta todo en una carpeta vacia de verdad.
"""
import sys
import time
from pathlib import Path

RAIZ = "C:/Users/Lukas/p5x-datamining/p5x_studio"
sys.path.insert(0, RAIZ)
from p5x_studio import dependencias  # noqa: E402

DESTINO = Path(sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\Lukas\p5x-datamining\_dl\ajeno")
if DESTINO.exists():
    import shutil
    shutil.rmtree(DESTINO, ignore_errors=True)
DESTINO.mkdir(parents=True, exist_ok=True)

PASOS = []


def paso(nombre, ok, detalle=""):
    PASOS.append((nombre, bool(ok), str(detalle)))
    print(("  ok   " if ok else "  FALLA ") + nombre + (("  -- " + str(detalle)) if detalle else ""),
          flush=True)


print("=" * 78)
print("ENSAYO DE EQUIPO AJENO (sin uv, sin nada instalado)")
print("=" * 78)
print("PATH y USERPROFILE capados; todo se monta en %s\n" % DESTINO)

paso("el equipo de verdad no tiene uv a mano", dependencias._uv_externo() is None,
     "uv del equipo: %s" % dependencias._uv_externo())
paso("y la app tampoco trae uno todavia", dependencias._uv() is None)

# a partir de aqui la app solo cuenta con lo que se baje
dependencias.carpeta_tools = lambda: DESTINO / "tools"
dependencias.carpeta_motor = lambda: DESTINO / "engine"

t0 = time.time()
lineas = []
try:
    u = dependencias.asegurar_uv(progreso=lineas.append)
    paso("se baja su propio uv", u.is_file(), "%s (%.0f s)" % (u.name, time.time() - t0))
    paso("uv funciona", dependencias._uv() is not None, str(dependencias._uv()))
except Exception as e:  # noqa: BLE001
    paso("se baja su propio uv", False, repr(e))

t0 = time.time()
try:
    w = dependencias.asegurar_wannacri(progreso=lineas.append)
    paso("con ese uv monta wannacri", w.is_file(), "%s (%.0f s)" % (w.name, time.time() - t0))
except Exception as e:  # noqa: BLE001
    paso("con ese uv monta wannacri", False, repr(e))

# que wannacri arranque de verdad
import subprocess  # noqa: E402
try:
    r = subprocess.run([str(w), "--help"], capture_output=True, text=True, timeout=120)
    visto = (r.stdout or "") + (r.stderr or "")
    paso("wannacri contesta", r.returncode == 0 or "usage" in visto.lower(), visto.strip()[:60])
except Exception as e:  # noqa: BLE001
    paso("wannacri contesta", False, repr(e))

print("\n=== lo que ha quedado en la carpeta (solo lo bajado) ===")
for sub in sorted(DESTINO.rglob("*")):
    if sub.is_dir() and sub.parent == DESTINO / "tools":
        peso = sum(f.stat().st_size for f in sub.rglob("*") if f.is_file()) / 1e6
        print("  %-14s %6.1f MB" % (sub.name, peso))
total = sum(f.stat().st_size for f in DESTINO.rglob("*") if f.is_file()) / 1e6
print("  %-14s %6.1f MB" % ("TOTAL", total))
print("\nlog de la descarga:")
for l in lineas:
    print("   ", l)

bien = sum(1 for _n, ok, _d in PASOS if ok)
print("\nRESUMEN: %d comprobaciones, %d bien, %d fallos" % (len(PASOS), bien, len(PASOS) - bien))
sys.exit(0 if bien == len(PASOS) else 1)
