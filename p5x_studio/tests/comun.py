"""Utilidades de las pruebas de P5X Studio Tools.

No hay pytest a proposito (el proyecto no puede permitirse dependencias): cada prueba es un script
que llama a `comprobar(...)` y termina con `resumen()`. Si algo falla, el proceso sale con codigo 1
y se ve en el terminal; si todo pasa, imprime OK y sale con 0.
"""
import sys

FALLOS = []


def comprobar(condicion, mensaje):
    if condicion:
        print("  ok   %s" % mensaje)
    else:
        print("  FALLA %s" % mensaje)
        FALLOS.append(mensaje)


def resumen():
    if FALLOS:
        print("\n%d FALLO(S):" % len(FALLOS))
        for f in FALLOS:
            print("  - %s" % f)
        sys.exit(1)
    print("\nOK")
    sys.exit(0)
