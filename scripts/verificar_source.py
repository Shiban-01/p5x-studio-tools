"""Verifica el modelo de Source ya compilado leyendo el .mdl.

Lee lo que de verdad acaba dentro del fichero: version, huesos, materiales, cuantas partes tiene el
cuerpo (Source parte el modelo si pasa de 21845 vertices), los attachment (ojos, manos) y los
hitboxes del conjunto por defecto.

Uso: python verificar_source.py <modelo.mdl> [carpeta_de_la_que_sacar_los_nombres]
"""
import struct
import sys

CAB = {  # offsets de la cabecera studiohdr, en bytes
    "id": 0, "version": 4, "nombre": 12, "largo": 76, "hull_min": 104, "hull_max": 116,
    "flags": 152, "numbones": 156, "boneindex": 160, "numhitboxsets": 172, "hitboxsetindex": 176,
    "numtextures": 204, "textureindex": 208, "numcdtextures": 212, "cdtextureindex": 216,
    "numbodyparts": 232, "bodypartindex": 236, "numattachments": 240, "attachmentindex": 244,
}


def cadena(d, pos):
    fin = d.index(b"\x00", pos)
    return d[pos:fin].decode("ascii", "replace")


def main(ruta):
    d = open(ruta, "rb").read()
    entero = lambda o: struct.unpack("<i", d[o:o + 4])[0]
    nombre = cadena(d, CAB["nombre"])
    version = entero(CAB["version"])
    print("=== %s ===" % ruta)
    print("nombre interno  : %s" % nombre)
    print("version         : %d  (L4D2 y Source 2013 usan la 49)" % version)
    print("tamano          : %.1f MB" % (len(d) / 1e6))
    print("hull            : %.1f x %.1f x %.1f unidades" % (
        struct.unpack("<3f", d[CAB["hull_max"]:CAB["hull_max"] + 12])[0]
        - struct.unpack("<3f", d[CAB["hull_min"]:CAB["hull_min"] + 12])[0],
        struct.unpack("<3f", d[CAB["hull_max"] + 4:CAB["hull_max"] + 16])[0]
        - struct.unpack("<3f", d[CAB["hull_min"] + 4:CAB["hull_min"] + 16])[0],
        struct.unpack("<3f", d[CAB["hull_max"] + 8:CAB["hull_max"] + 20])[0]
        - struct.unpack("<3f", d[CAB["hull_min"] + 8:CAB["hull_min"] + 20])[0]))
    print("huesos          : %d" % entero(CAB["numbones"]))

    # --- materiales y texturas ---
    nt, ti = entero(CAB["numtextures"]), entero(CAB["textureindex"])
    print("materiales      : %d" % nt)
    for i in range(nt):
        base = ti + i * 64
        off = entero(base)
        flags = entero(base + 4)
        print("   %-28s flags 0x%04X" % (cadena(d, base + off), flags))

    # --- carpetas de materiales ($cdmaterials) ---
    try:
        ncd, ci = entero(CAB["numcdtextures"]), entero(CAB["cdtextureindex"])
        offs = struct.unpack("<%di" % ncd, d[ci:ci + 4 * ncd])
        carpetas = []
        for o in offs:
            try:
                carpetas.append(cadena(d, ci + o))
            except ValueError:
                carpetas.append("(no legible)")
        print("carpetas de material: %d -> %s" % (ncd, ", ".join(carpetas)))
    except Exception as e:
        print("carpetas de material: no se pudieron leer (%s)" % e)

    # --- partes del cuerpo: Source corta el modelo si pasa de 21845 vertices ---
    np, pi = entero(CAB["numbodyparts"]), entero(CAB["bodypartindex"])
    trozos = []
    for i in range(np):
        base = pi + i * 16                     # mstudiobodyparts_t: sznameindex, nummodels, base, modelindex
        nom = cadena(d, base + entero(base))
        nm = entero(base + 4)
        mi = entero(base + 12)
        for j in range(nm):
            # mstudiomodel_t: nombre incrustado de 64 bytes, y el numero de vertices en +80
            mb = base + mi + j * 148
            trozos.append((nom, cadena(d, mb), entero(mb + 80), 0))
    print("partes del cuerpo: %d parte(s), %d trozo(s) de malla" % (np, len(trozos)))
    for nom, sub, nverts, _ in trozos:
        print("   parte %-14s malla %-20s %6d vertices" % (nom, sub, nverts))

    # --- attachment: los ojos son obligatorios para Garry's Mod ---
    na, ai = entero(CAB["numattachments"]), entero(CAB["attachmentindex"])
    print("attachment      : %d" % na)
    for i in range(na):
        base = ai + i * 92                 # mstudioattachment_t: 60 bytes + 8 enteros de relleno
        nom = cadena(d, base + entero(base))
        hueso = entero(base + 8)
        print("   %-22s al hueso %d" % (nom, hueso))

    # --- hitboxes ---
    nh, hi = entero(CAB["numhitboxsets"]), entero(CAB["hitboxsetindex"])
    print("conjuntos de hitbox: %d" % nh)
    for i in range(nh):
        base = hi + i * 12
        nom = cadena(d, base + entero(base))
        cuantas = entero(base + 4)
        idx = entero(base + 8)
        print("   %-14s %d cajas" % (nom, cuantas))
        grupos = {}
        for k in range(cuantas):
            caja = base + idx + k * 68         # mstudiobbox_t: bone, group, min(3f), max(3f), hitboxnameindex...
            hueso = entero(caja)
            grupo = entero(caja + 4)
            grupos.setdefault(grupo, []).append(hueso)
        for g in sorted(grupos):
            print("      grupo de impacto %-2d -> %d hueso(s)" % (g, len(grupos[g])))


if __name__ == "__main__":
    main(sys.argv[1])