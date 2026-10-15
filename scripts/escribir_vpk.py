"""Escribe un VPK version 1 (0x55AA1234), que es el formato de todo lo que L4D2 carga de verdad.

El vpk.exe que trae Steam escribe version 2 aunque venga de Portal, y el contenido propio del juego
igual que los 37 VPK del taller del usuario son version 1. Para que un addon no dependa de que el
motor acepte v2, se escribe v1 a mano.

Estructura v1:
    cabecera:  magic (0x55AA1234), version (1), tamano del arbol
    arbol:     extension -> carpeta -> fichero, cada nivel terminado en cadena vacia; por fichero:
               crc32, bytes de preload, indice de archivo (0x7FFF = va en este fichero), offset
               dentro de los datos, longitud, y terminador 0xFFFF
    datos:     el contenido de los ficheros, concatenado

Uso:  python escribir_vpk.py <carpeta> <salida.vpk>
"""
import os
import struct
import sys
import zlib

MAGIC = 0x55AA1234
SIN_ARCHIVO = 0x7FFF          # el contenido va en este mismo fichero, no en un trozo aparte


def cadena(texto):
    return texto.encode("utf-8") + b"\x00"


def recolectar(carpeta):
    """Devuelve {(extension, carpeta, nombre): ruta_real}, con rutas en formato Source (/)."""
    arbol = {}
    for base, _, ficheros in os.walk(carpeta):
        for f in ficheros:
            real = os.path.join(base, f)
            rel = os.path.relpath(real, carpeta).replace("\\", "/")
            trozos = rel.split("/")
            nombre = trozos[-1]
            carpeta_vpk = "/".join(trozos[:-1])
            if carpeta_vpk == "":
                # En el VPK, un fichero que va en la raiz se marca con un ESPACIO como carpeta.
                # La cadena vacia esta reservada para marcar el fin de una lista, y si se usa para
                # la raiz el arbol se descuadra entero (comprobado leyendo un VPK del taller que
                # tiene addoninfo.txt en la raiz).
                carpeta_vpk = " "
            if "." in nombre:
                nombre, ext = nombre.rsplit(".", 1)
            else:
                ext = " "
            arbol[(ext, carpeta_vpk, nombre)] = real
    return arbol


def main(carpeta, salida):
    arbol = recolectar(carpeta)
    if not arbol:
        raise SystemExit("no hay ficheros en %s" % carpeta)

    # --- arbol de directorios ---
    t = b""
    for ext in sorted({e for e, _, _ in arbol}):
        t += cadena(ext)
        for carpeta_vpk in sorted({c for e, c, _ in arbol if e == ext}):
            t += cadena(carpeta_vpk)
            for _, c, nombre in sorted((e, c, n) for e, c, n in arbol if e == ext and c == carpeta_vpk):
                datos = open(arbol[(ext, c, nombre)], "rb").read()
                t += cadena(nombre)
                t += struct.pack("<IHHIIH", zlib.crc32(datos) & 0xFFFFFFFF, 0, SIN_ARCHIVO, 0, 0, 0xFFFF)
            t += b"\x00"
        t += b"\x00"
    t += b"\x00"

    # --- datos: hay que calcular offsets, asi que se recorren en el mismo orden ---
    datos = b""
    posiciones = {}
    for ext in sorted({e for e, _, _ in arbol}):
        for carpeta_vpk in sorted({c for e, c, _ in arbol if e == ext}):
            for nombre in sorted(n for e, c, n in arbol if e == ext and c == carpeta_vpk):
                real = arbol[(ext, carpeta_vpk, nombre)]
                contenido = open(real, "rb").read()
                posiciones[(ext, carpeta_vpk, nombre)] = (len(datos), len(contenido))
                datos += contenido

    # --- reescribir el arbol ya con los offsets buenos ---
    t = b""
    for ext in sorted({e for e, _, _ in arbol}):
        t += cadena(ext)
        for carpeta_vpk in sorted({c for e, c, _ in arbol if e == ext}):
            t += cadena(carpeta_vpk)
            for nombre in sorted(n for e, c, n in arbol if e == ext and c == carpeta_vpk):
                real = arbol[(ext, carpeta_vpk, nombre)]
                contenido = open(real, "rb").read()
                off, largo = posiciones[(ext, carpeta_vpk, nombre)]
                t += cadena(nombre)
                t += struct.pack("<IHHIIH", zlib.crc32(contenido) & 0xFFFFFFFF, 0, SIN_ARCHIVO,
                                 off, largo, 0xFFFF)
            t += b"\x00"
        t += b"\x00"
    t += b"\x00"

    with open(salida, "wb") as f:
        f.write(struct.pack("<III", MAGIC, 1, len(t)))
        f.write(t)
        f.write(datos)

    print("VPK escrito: %s" % salida)
    print("  version 1 | %d ficheros | arbol %d bytes | datos %d bytes | total %d"
          % (len(arbol), len(t), len(datos), 12 + len(t) + len(datos)))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])