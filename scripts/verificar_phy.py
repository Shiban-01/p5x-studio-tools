"""Comprueba un .phy (la fisica del ragdoll) y su vinculo con el .mdl.

El .phy guarda las cajas convexas del ragdoll. La cabecera (16 bytes) declara cuantas son, y el
checksum tiene que ser el mismo que el del .mdl: es lo que Source comprueba para aceptar la fisica.

Uso:  python verificar_phy.py <fichero.phy> [otro.phy ...]

Aviso: el recorrido por DENTRO de cada caja no se intenta. Los bloques por solido no tienen el
tamano que uno supone y se acaba leyendo basura; el dato fiable es el numero de cajas de la
cabecera y el checksum. Para comparar con un modelo del juego, extrae su .phy del VPK y pasalo
como segundo argumento.
"""
import os
import struct
import sys


def cabecera(d):
    tam, ident, solidos, checksum = struct.unpack("<iiii", d[:16])
    return tam, ident & 0xFFFFFFFF, solidos, checksum & 0xFFFFFFFF


def main(rutas):
    for ruta in rutas:
        if not os.path.exists(ruta):
            print("=== %s ===\n  no existe\n" % ruta)
            continue
        d = open(ruta, "rb").read()
        tam, ident, solidos, checksum = cabecera(d)
        print("=== %s ===" % ruta)
        print("  %d bytes | cabecera de %d | identificador 0x%08X | cajas de colision %d | checksum 0x%08X"
              % (len(d), tam, ident, solidos, checksum))
        mdl = os.path.splitext(ruta)[0] + ".mdl"
        if os.path.exists(mdl):
            m = open(mdl, "rb").read()
            _, version, chk = struct.unpack("<iii", m[:12])
            print("  modelo al lado: %s version %d | checksum del modelo 0x%08X | %s"
                  % (m[:4].decode("ascii", "replace"), version, chk & 0xFFFFFFFF,
                     "COINCIDEN (Source aceptara la fisica)" if (chk & 0xFFFFFFFF) == checksum
                     else "NO COINCIDEN (el juego ignorara la fisica)"))
        print()


if __name__ == "__main__":
    main(sys.argv[1:] or ["kotone_source/gamedir/models/survivors/survivor_producer.phy"])