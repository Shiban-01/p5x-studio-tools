"""Indice propio de los ficheros del juego: que es cada bundle y que lleva dentro.

Dos pasadas, porque el juego tiene 16.535 bundles y abrirlos todos costaria dias:

  PASADA 1 (segundos): el nombre de cada bundle ya codifica su tipo y su contenido. Se cataloga
  todo: carpeta, tipo, nombre logico, hash y tamano. Esto es el indice de ficheros.

  PASADA 2 (minutos, solo los de modelo): abrir cada `part_*` y anotar los NOMBRES DE MALLA que
  lleva dentro. Hace falta porque el nombre del bundle no delata el contenido: `part_l_normal`
  guarda a `n_GuitarGirl`, y `part_itargirl` tambien. Esto es el indice de contenido.

Uso:
    python scripts/indice_juego.py                 # pasada 1, completa
    python scripts/indice_juego.py --contenido     # pasada 2, sobre los de modelo
    python scripts/indice_juego.py --contenido --todos   # pasada 2 sobre part_+role_+tl_
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BUNDLES = Path(r"C:/Users/Lukas/Downloads/P5X/Client/OuterPackage/Bundles/Windows")
MOTOR = RAIZ / "p5x_studio/motor/AssetStudioModCLI_net9_win64/AssetStudioModCLI.exe"
SALIDA = RAIZ / "_dl/indice_juego"
TRABAJO = SALIDA / "mallas"

# tipo -> que es. El nombre del bundle empieza por el tipo y le sigue el contenido.
TIPOS = {
    "part": "modelo de personaje o pieza",
    "role": "actor: huesos, animadores y datos de montaje",
    "tl": "timeline o escena de historia",
    "scn": "escenario",
    "anim": "animaciones",
    "atlas": "atlas de texturas (arte 2D, interfaz)",
    "uitex": "texturas de interfaz",
    "ui": "interfaz",
    "efx": "efectos",
    "shared": "recursos compartidos",
    "shaders": "shaders",
    "i18n": "traducciones",
    "tmpfontmat": "fuentes temporales",
    "spinetest": "pruebas de Spine",
}

PATRON = re.compile(r"^(?P<tipo>[a-z0-9]+)_(?P<nombre>.+)(?P<hash>[0-9a-f]{8,})\.bundle$", re.I)


def pasada1() -> dict:
    """Cataloga todos los bundles por nombre. Es instantaneo: no abre ninguno."""
    print("   PASADA 1: catalogando por nombre...")
    t0 = time.time()
    ficheros = []
    for carpeta in sorted(BUNDLES.iterdir()):
        if not carpeta.is_dir():
            continue
        for f in sorted(carpeta.glob("*.bundle")):
            m = PATRON.match(f.name)
            tipo = m.group("tipo").lower() if m else "?"
            nombre = m.group("nombre") if m else f.stem
            ficheros.append({
                "carpeta": carpeta.name,
                "fichero": f.name,
                "tipo": tipo,
                "que_es": TIPOS.get(tipo, "sin clasificar"),
                "nombre": nombre,
                "hash": m.group("hash") if m else "",
                "mb": round(f.stat().st_size / 1048576, 2),
            })
    por_tipo = Counter(f["tipo"] for f in ficheros)
    datos = {
        "carpeta_bundles": str(BUNDLES),
        "total": len(ficheros),
        "mb_total": round(sum(f["mb"] for f in ficheros), 1),
        "por_tipo": dict(por_tipo.most_common()),
        "ficheros": ficheros,
    }
    SALIDA.mkdir(parents=True, exist_ok=True)
    (SALIDA / "indice_ficheros.json").write_text(
        json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")

    # resumen legible
    lineas = ["# Que hay en el juego", "",
              "Total: **%d bundles**, %.1f GB" % (len(ficheros), datos["mb_total"]), "",
              "| tipo | cuantos | que es |", "|---|---|---|"]
    for tipo, n in por_tipo.most_common():
        lineas.append("| `%s_` | %d | %s |" % (tipo, n, TIPOS.get(tipo, "sin clasificar")))
    (SALIDA / "QUE_HAY.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")

    print("   %d bundles en %.1f s" % (len(ficheros), time.time() - t0))
    for tipo, n in por_tipo.most_common(12):
        print("      %-10s %5d   %s" % (tipo + "_", n, TIPOS.get(tipo, "?")))
    return datos


def pasada2(datos: dict, todos: bool) -> None:
    """Abre los bundles de modelo y anota los nombres de malla que llevan dentro."""
    # `shared_` faltaba y es donde vive lo importante: las TEXTURAS de los personajes. Las mallas
    # del modelo base `n_GuitarGirl` estan en `part_l_normal`, pero sus texturas estan en
    # `shared_7aad509` y `shared_3b8e0d36`. Sin abrir los `shared_` el indice no ve las texturas.
    prefijos = ("part_", "role_", "tl_", "shared_") if todos else ("part_", "shared_")
    objetivo = [f for f in datos["ficheros"] if f["fichero"].startswith(prefijos)]
    print("   PASADA 2: abriendo %d bundles de modelo..." % len(objetivo))
    TRABAJO.mkdir(parents=True, exist_ok=True)

    contenido: dict[str, dict] = {}
    if (SALIDA / "indice_contenido.json").is_file():
        contenido = json.loads((SALIDA / "indice_contenido.json").read_text(encoding="utf-8"))
    t0 = time.time()
    nuevos = 0
    for i, f in enumerate(objetivo, 1):
        clave = "%s/%s" % (f["carpeta"], f["fichero"])
        if clave in contenido:
            continue
        destino = TRABAJO / Path(f["fichero"]).stem
        if not destino.exists():
            orden = [str(MOTOR), str(BUNDLES / f["carpeta"] / f["fichero"]),
                     "-m", "export", "-t", "mesh", "-o", str(destino),
                     "--log-level", "Error", "-r", "--unity-version", "2022.3.49f1"]
            try:
                subprocess.run(orden, capture_output=True, text=True, timeout=600,
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            except Exception:
                contenido[clave] = {"error": "no se pudo abrir"}
                continue
        mallas = sorted({p.stem for p in destino.rglob("*.obj")})
        # el personaje va en el nombre de la malla: `n_GuitarGirl_...` o `PC079_01_...`
        quien = sorted({m.split("_")[0].upper() for m in mallas if m})[:6]
        contenido[clave] = {"tipo": f["tipo"], "nombre": f["nombre"],
                            "mallas": mallas[:60], "n_mallas": len(mallas),
                            "contiene": quien}
        nuevos += 1
        if nuevos % 20 == 0:
            (SALIDA / "indice_contenido.json").write_text(
                json.dumps(contenido, ensure_ascii=False, indent=1), encoding="utf-8")
            print("      ... %d/%d  (%.0f s)" % (i, len(objetivo), time.time() - t0))

    (SALIDA / "indice_contenido.json").write_text(
        json.dumps(contenido, ensure_ascii=False, indent=1), encoding="utf-8")
    print("   %d bundles abiertos (%d nuevos) en %.0f s" % (len(contenido), nuevos, time.time() - t0))


def main() -> None:
    datos = pasada1()
    if "--contenido" in sys.argv:
        pasada2(datos, "--todos" in sys.argv)


if __name__ == "__main__":
    main()