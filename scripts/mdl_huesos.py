"""Lee la cabecera y la tabla de huesos de un modelo de Source (.mdl).

Da el version del modelo, el numero de huesos y, por cada hueso: nombre, padre, posicion y
rotacion de reposo. Es lo que hay que copiar para que las animaciones del juego encajen.

Uso: python mdl_huesos.py <modelo.mdl> [--json salida.json]
"""
import json
import struct
import sys

TAM_HUESO = 216


def leer_cadena(d, pos):
    fin = d.index(b"\x00", pos)
    return d[pos:fin].decode("ascii", "replace"), fin + 1


def leer_mdl(ruta):
    d = open(ruta, "rb").read()
    id_, version, checksum = struct.unpack("<III", d[:12])
    assert id_ == 0x54534449, "no es un .mdl (id 0x%08X)" % id_          # 'IDST'
    nombre, _ = leer_cadena(d, 12)
    (largo, ) = struct.unpack("<I", d[76:80])
    eye = struct.unpack("<3f", d[80:92])
    hmin = struct.unpack("<3f", d[104:116])
    hmax = struct.unpack("<3f", d[116:128])
    vmin = struct.unpack("<3f", d[128:140])
    vmax = struct.unpack("<3f", d[140:152])
    flags, numbones, boneindex = struct.unpack("<III", d[152:164])
    huesos = []
    for i in range(numbones):
        base = boneindex + i * TAM_HUESO
        off_nombre, = struct.unpack("<i", d[base:base + 4])
        nombre_h, _ = leer_cadena(d, base + off_nombre)
        padre, = struct.unpack("<i", d[base + 4:base + 8])
        pos = struct.unpack("<3f", d[base + 32:base + 44])
        quat = struct.unpack("<4f", d[base + 44:base + 60])
        rot = struct.unpack("<3f", d[base + 60:base + 72])
        huesos.append({"i": i, "nombre": nombre_h, "padre": padre,
                       "pos": [round(v, 4) for v in pos], "quat": [round(v, 5) for v in quat],
                       "rot": [round(v, 4) for v in rot]})
    return {"ruta": ruta, "nombre": nombre, "version": version, "checksum": checksum,
            "largo_declarado": largo, "tamano_real": len(d), "eye": eye,
            "hull_min": hmin, "hull_max": hmax, "view_bbmin": vmin, "view_bbmax": vmax,
            "flags": flags, "numbones": numbones, "huesos": huesos}


if __name__ == "__main__":
    m = leer_mdl(sys.argv[1])
    print("modelo %s | version %d | %d huesos | alto segun la caja: %.1f unidades" %
          (m["nombre"], m["version"], m["numbones"], m["view_bbmax"][2] - m["view_bbmin"][2]))
    print("  ojo: %.1f | caja del cuerpo: %.1f x %.1f x %.1f" %
          (m["eye"][2], m["hull_max"][0] - m["hull_min"][0], m["hull_max"][1] - m["hull_min"][1],
           m["hull_max"][2] - m["hull_min"][2]))
    for h in m["huesos"]:
        print("  %3d  %-34s padre %3d  pos %8.2f %8.2f %8.2f" %
              (h["i"], h["nombre"], h["padre"], h["pos"][0], h["pos"][1], h["pos"][2]))
    if len(sys.argv) > 3 and sys.argv[2] == "--json":
        json.dump(m, open(sys.argv[3], "w"), indent=1)
        print("guardado en", sys.argv[3])
