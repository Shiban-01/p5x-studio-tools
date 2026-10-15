"""Extraccion de punta a punta en los dos idiomas, con evidencia real.

Extrae un personaje pequeno (PC069_01) una vez en espanol y otra en ingles, y comprueba:
  - que la extraccion termina y produce el paquete completo (mallas, texturas, README, FBX...);
  - que el registro de mensajes sale en el idioma activo;
  - que el README.md y el LEEME salen en el idioma activo;
  - que en el paquete ingles NO queda espanol.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sys

sys.path.insert(0, r"C:/Users/Lukas/p5x-datamining/p5x_studio")

from p5x_studio import ajustes, catalogo, extractor, idiomas

DESTINO = r"C:/Users/Lukas/p5x-datamining/_dl/prueba_idioma"
OBJETIVO = "pc069_01"

OPCIONES = {"mallas": True, "texturas": True, "armas": True, "esqueleto": False,
            "previas": True, "fbx": True}


def extraer(codigo: str, etiqueta: str) -> dict:
    idiomas.activar(codigo)
    p = next((x for x in catalogo.personajes() if x["id"] == OBJETIVO), None)
    if p is None:
        raise SystemExit("no encuentro %s en el catalogo" % OBJETIVO)
    datos = {}
    salida_dir = os.path.join(DESTINO, etiqueta)
    shutil.rmtree(salida_dir, ignore_errors=True)
    log: list[str] = []
    marcas: list[str] = []
    ruta = extractor.extraer_personaje(
        p, datos, salida_dir, OPCIONES,
        log=log.append,
        progreso=lambda v: marcas.append(str(v)),
        estado=lambda s: marcas.append("estado: " + s),
        base=None, traje=None)
    resumen = json.loads(open(os.path.join(ruta, "SUMMARY.json"), encoding="utf-8").read())
    readme = open(os.path.join(ruta, "README.md"), encoding="utf-8").read()
    n_obj = sum(len(f) for _, _, f in os.walk(ruta) if False) or 0
    ficheros = []
    for raiz, _, fs in os.walk(ruta):
        for f in fs:
            ficheros.append(os.path.relpath(os.path.join(raiz, f), ruta))
    return {
        "idioma": codigo,
        "carpeta": os.path.basename(ruta),
        "n_ficheros": len(ficheros),
        "tiene_fbx": any(f.endswith(".fbx") for f in ficheros),
        "tiene_readme": "README.md" in ficheros,
        "tiene_mallas": sum(1 for f in ficheros if f.endswith(".obj")),
        "tiene_texturas": sum(1 for f in ficheros if f.endswith(".png")),
        "tiene_previas": sum(1 for f in ficheros if f.startswith("preview")),
        "duracion_s": resumen.get("duracion_segundos"),
        "log": log,
        "marcas": marcas,
        "readme_cabecera": readme.splitlines()[:14],
        "readme": readme,
    }


def main():
    informe = {}
    for codigo, etiqueta in (("es", "espanol"), ("en", "ingles")):
        r = extraer(codigo, etiqueta)
        r.pop("readme")
        informe[etiqueta] = r
    # el README ingles, para inspeccionarlo
    readme_en = open(os.path.join(DESTINO, "ingles",
                                  informe["ingles"]["carpeta"], "README.md"),
                     encoding="utf-8").read()
    informe["readme_ingles"] = readme_en

    # --- rastro de espanol en el paquete ingles ---
    es_unicos = {v for k, v in idiomas.ES.items() if v != idiomas.EN.get(k)}
    def rastros(texto):
        return sorted({v for v in es_unicos if len(v) > 6 and v in texto})
    informe["espanol_en_readme_ingles"] = rastros(readme_en)
    informe["espanol_en_log_ingles"] = sorted({s for s in informe["ingles"]["log"]
                                               if any(v in s for v in es_unicos if len(v) > 6)})
    informe["espanol_en_log_espanol"] = len(informe["espanol"]["log"])
    print(json.dumps(informe, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()