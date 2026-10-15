"""Arranca el .exe reconstruido y le hace una foto en cada idioma.

Evidencia de que el ejecutable de verdad trae el selector y arranca en el idioma guardado.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time

EXE = r"C:/Users/Lukas/p5x-datamining/p5x_studio/P5X Studio.exe"
CONFIG = r"C:/Users/Lukas/p5x-datamining/p5x_studio/config.json"
SALIDA = r"C:/Users/Lukas/p5x-datamining/_dl"


def fijar_idioma(codigo: str) -> None:
    datos = json.loads(open(CONFIG, encoding="utf-8").read())
    datos["idioma"] = codigo
    open(CONFIG, "w", encoding="utf-8").write(json.dumps(datos, ensure_ascii=False, indent=1))


def matar() -> None:
    subprocess.run(["taskkill", "/IM", "P5X Studio.exe", "/F"],
                   capture_output=True, text=True)


def foto(codigo: str) -> str:
    fijar_idioma(codigo)
    matar()
    time.sleep(1)
    proc = subprocess.Popen([EXE], cwd=os.path.dirname(EXE))
    time.sleep(14)  # arranque + relleno de la lista de personajes
    from PIL import ImageGrab
    img = ImageGrab.grab()
    ruta = os.path.join(SALIDA, "exe_%s.png" % codigo)
    img.save(ruta)
    matar()
    time.sleep(1)
    return ruta


def main():
    print("foto es:", foto("es"))
    print("foto en:", foto("en"))
    fijar_idioma("es")
    print("config restaurada a es")


if __name__ == "__main__":
    main()