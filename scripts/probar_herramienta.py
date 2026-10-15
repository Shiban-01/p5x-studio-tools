"""Prueba de punta a punta: extrae un personaje con la herramienta y comprueba el resultado."""
import sys
import time
from pathlib import Path

sys.path.insert(0, r"C:\Users\Lukas\p5x-datamining\p5x_studio")
from p5x_studio import ajustes, indice, dependencias, extractor  # noqa: E402

SALIDA = Path(r"C:\Users\Lukas\p5x-datamining\_dl\prueba_herramienta")

print("1. indice")
t0 = time.time()
datos = indice.cargar_indice(lambda s: print("   " + s))
print("   cargado en %.1f s" % (time.time() - t0))

print("\n2. personajes que encuentra")
personajes = indice.personajes(datos)
print("   %d personajes" % len(personajes))
for p in personajes[:5]:
    print("      %-28s %d ficheros" % (p["etiqueta"], len(p["ficheros"])))

objetivo = next((p for p in personajes if p["id"] == "pc079"), None)
if not objetivo:
    print("   NO ENCUENTRA pc079")
    raise SystemExit(1)
print("   objetivo: %s -> %s" % (objetivo["etiqueta"], objetivo["ficheros"]))

print("\n3. motor de extraccion")
exe = dependencias.ruta_assetstudio()
print("   %s" % exe)
if not exe:
    print("   no hay motor; se intentaria descargar")
    raise SystemExit(1)

print("\n4. extraccion")
t0 = time.time()
carpeta = extractor.extraer_personaje(
    objetivo, datos, SALIDA,
    {"mallas": True, "texturas": True, "materiales": True, "esqueleto": True,
     "previas": True, "armas": True},
    log=lambda s: print("   " + s),
    progreso=lambda v: None,
    estado=lambda s: None)
print("   terminado en %.1f s" % (time.time() - t0))
print("   carpeta: %s" % carpeta)

print("\n5. que ha quedado dentro")
for sub in sorted(carpeta.rglob("*")):
    if sub.is_file():
        rel = sub.relative_to(carpeta)
        print("   %-62s %8.0f KB" % (str(rel)[:62], sub.stat().st_size / 1024))
print("\n   total: %.1f MB" % (sum(f.stat().st_size for f in carpeta.rglob("*") if f.is_file())
                               / 1048576))