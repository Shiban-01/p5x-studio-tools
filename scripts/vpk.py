"""Lector de VPK (version 2) para sacar ficheros de los pak01 de L4D2.

Formato: cabecera (magic 0x55AA1234, version, tree_size, ...), arbol de rutas con entradas
(crc, bytes de precarga, indice de archivo, offset, longitud) y luego los datos, que estan o en el
propio _dir.vpk (indice 0x7FFF) o en el trozo pak01_NNN.vpk correspondiente.

Comprobacion de que funciona: un .mdl extraido tiene que empezar por 'IDST'.

Uso: python vpk.py <pak01_dir.vpk> <listar|extraer> [patron] [carpeta_salida]
"""
import os
import struct
import sys


def leer_arbol(ruta_dir):
    d = open(ruta_dir, "rb").read()
    magic, version, tree_size = struct.unpack("<III", d[:12])
    assert magic == 0x55AA1234, "no es un VPK (magic 0x%08X)" % magic
    if version == 2:
        cabecera = 28
    else:
        cabecera = 12
    arbol = d[cabecera:cabecera + tree_size]
    base = ruta_dir[:-len("_dir.vpk")]
    entradas = []
    i = 0

    def cadena(pos):
        fin = arbol.index(b"\x00", pos)
        return arbol[pos:fin].decode("utf-8", "replace"), fin + 1

    while i < len(arbol):
        ext, i = cadena(i)
        if ext == "":
            break
        while i < len(arbol):
            carpeta, i = cadena(i)
            if carpeta == "":
                break
            while i < len(arbol):
                nombre, i = cadena(i)
                if nombre == "":
                    break
                crc, preload, indice, offset, largo, term = struct.unpack("<IHHIIH", arbol[i:i + 18])
                i += 18
                precarga = arbol[i:i + preload]
                i += preload
                entradas.append({
                    "ruta": ("%s/%s.%s" % (carpeta, nombre, ext)).lstrip("/"),
                    "crc": crc, "precarga": precarga, "archivo": indice,
                    "offset": offset, "largo": largo, "base": base,
                })
    return version, entradas


def leer_entrada(e):
    datos = e["precarga"]
    if e["largo"] > 0:
        if e["archivo"] == 0x7FFF:
            ruta = e["base"] + "_dir.vpk"
        else:
            ruta = "%s_%03d.vpk" % (e["base"], e["archivo"])
        with open(ruta, "rb") as f:
            f.seek(e["offset"])
            datos += f.read(e["largo"])
    return datos


if __name__ == "__main__":
    vpk = sys.argv[1]
    accion = sys.argv[2] if len(sys.argv) > 2 else "listar"
    patron = sys.argv[3] if len(sys.argv) > 3 else ""
    version, entradas = leer_arbol(vpk)
    print("VPK version %d con %d ficheros" % (version, len(entradas)))
    if accion == "listar":
        for e in entradas:
            if patron.lower() in e["ruta"].lower():
                print("   %-58s %8d bytes (trozo %s)" % (e["ruta"], e["largo"] + len(e["precarga"]),
                                                         "dir" if e["archivo"] == 0x7FFF else e["archivo"]))
    else:
        salida = sys.argv[4] if len(sys.argv) > 4 else "extraido"
        n = 0
        for e in entradas:
            if patron.lower() not in e["ruta"].lower():
                continue
            destino = os.path.join(salida, e["ruta"])
            os.makedirs(os.path.dirname(destino), exist_ok=True)
            datos = leer_entrada(e)
            open(destino, "wb").write(datos)
            firma = datos[:4].decode("ascii", "replace") if datos[:4].isascii() else repr(datos[:4])
            print("   %-58s %8d bytes  empieza por %r" % (e["ruta"], len(datos), firma))
            n += 1
        print("extraidos:", n)
