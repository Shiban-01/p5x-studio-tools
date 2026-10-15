"""
Audita la malla compilada de Source (.vvd + .dx90.vtx) buscando indices fuera de rango.

Por que: un .mdl puede tener los 82 huesos, los checksums cuadrados y las versiones correctas,
y aun asi hacer caer el motor SIN MENSAJE si dentro de la geometria hay un indice que no existe.
El motor lee fuera de rango y revienta en la pantalla de carga sin escribir nada en la consola:
exactamente el sintoma que tenemos.

Uso:
    python auditar_malla.py <modelo.mdl>            # audita el modelo y su .vvd/.dx90.vtx
    python auditar_malla.py --comparar <a.mdl> <b.mdl>

FORMATO (deducido y verificado contra el survivor_producer del propio juego, que es valido).
En el .vtx TODOS los offsets son RELATIVOS a su bloque padre:

    cabecera            36  version, vertCacheSize, maxBonesPorTira(short), maxBonesPorTri(short),
                            maxBonesPorVertice, checksum, numLODs, matReplacementListOff,
                            numBodyParts, bodyPartOffset
    bodyPartHeader       8  numModels, modelOffset
    modelHeader          8  numLODs, lodOffset
    modelLODHeader      12  numMeshes, meshOffset, switchPoint(float)
    meshHeader           9  numStripGroups, stripGroupHeaderOffset, flags(1 byte)
    stripGroupHeader    25  numVerts, vertOffset, numIndices, indexOffset, numStrips, stripOffset, flags
    stripHeader         27  numIndices, indexOffset, numVerts, vertOffset, numBones(short),
                            flags(1 byte), numBoneStateChanges, boneStateChangeOffset
    vertex               9  ranura[3], numBones, origMeshVertID(short), indiceDeCambio[3]

  Direcciones: vertices = grupo + grupo.vertOffset + tira.vertOffset
               indices  = grupo + grupo.indexOffset + tira.indexOffset
               cambios  = tira + tira.boneStateChangeOffset
  Cada cambio de hueso son dos enteros: (ranura, huesoDelModelo). El hueso del modelo es el que
  tiene que existir en el .mdl; los indices del vertice apuntan a la LISTA DE CAMBIOS, no al modelo.

En el .vvd cada vertice son 48 bytes:
    pesos[3](float) + huesos[3](byte) + numBones(byte) + padding(3)   (16)
    posicion(3 float) + normal(3 float) + coordenadas UV(2 float)      (32)
"""
import struct
import sys
import os

FALLOS = []
AVISOS = []
LIMITE_QUEJAS = 25


def fallo(txt):
    FALLOS.append(txt)
    if len(FALLOS) <= LIMITE_QUEJAS:
        print("   *** FALLO: " + txt)


def aviso(txt):
    AVISOS.append(txt)
    if len(AVISOS) <= LIMITE_QUEJAS:
        print("   aviso: " + txt)


def dentro(d, off, n, etq):
    if off < 0 or off + n > len(d):
        fallo("%s: %d + %d se sale del fichero (%d bytes)" % (etq, off, n, len(d)))
        return False
    return True


def i32(d, o):
    return struct.unpack_from("<i", d, o)[0]


def u16(d, o):
    return struct.unpack_from("<H", d, o)[0]


def i16(d, o):
    return struct.unpack_from("<h", d, o)[0]


def leer_mdl(ruta):
    d = open(ruta, "rb").read()
    return {"datos": d, "version": i32(d, 4), "checksum": i32(d, 8),
            "nombre": d[12:76].split(b"\x00")[0].decode("latin1"), "flags": struct.unpack_from("<I", d, 152)[0],
            "numhuesos": i32(d, 156), "off_huesos": i32(d, 160)}


def nombres_huesos(mdl):
    d, out = mdl["datos"], []
    o0 = mdl["off_huesos"]
    for i in range(mdl["numhuesos"]):
        out.append(d[o0 + i * 216:o0 + i * 216 + 32].split(b"\x00")[0].decode("latin1"))
    return out


def auditar_vvd(ruta, mdl, vtx_verts=None):
    print("\n=== .vvd (vertices con pesos y huesos) ===")
    if not os.path.exists(ruta):
        return fallo("no existe %s" % ruta)
    d = open(ruta, "rb").read()
    version, checksum = i32(d, 4), i32(d, 8)
    numlods = i32(d, 12)
    lodverts = [i32(d, 16 + 4 * i) for i in range(8)]
    numfixups, off_fixups, off_verts = i32(d, 48), i32(d, 52), i32(d, 56)
    total = lodverts[0]
    print("   version=%d checksum=%s numLODs=%d vertices=%s"
          % (version, hex(checksum & 0xFFFFFFFF), numlods, lodverts[:max(numlods, 1)]))
    print("   numFixups=%d tablaEn=%d datosEn=%d (%d bytes)"
          % (numfixups, off_fixups, off_verts, len(d)))
    if checksum != mdl["checksum"]:
        fallo("checksum del .vvd (%s) != del .mdl (%s)"
              % (hex(checksum & 0xFFFFFFFF), hex(mdl["checksum"] & 0xFFFFFFFF)))
    if numlods > 0 and lodverts[numlods - 1] == 0:
        aviso("el ultimo LOD declarado tiene 0 vertices")

    if numfixups > 0:
        if dentro(d, off_fixups, numfixups * 12, ".vvd fixups"):
            suma = 0
            for i in range(numfixups):
                lod, origen, cuantos = struct.unpack_from("<iii", d, off_fixups + i * 12)
                suma += cuantos
                if not (0 <= lod < 8):
                    fallo("fixup %d: LOD %d fuera de rango" % (i, lod))
                if origen < 0 or origen + cuantos > total:
                    fallo("fixup %d: vertices %d..%d fuera del bufer (%d)"
                          % (i, origen, origen + cuantos, total))
            print("   %d fixups suman %d vertices (el bufer declara %d) -> %s"
                  % (numfixups, suma, total, "OK" if suma == total else "DESCUADRA"))
    else:
        aviso("no hay tabla de fixups (numFixups=0)")

    esperado = total * 48
    disponible = len(d) - off_verts
    print("   datos de vertices: %d bytes esperados, %d disponibles" % (esperado, disponible))
    if not dentro(d, off_verts, esperado, ".vvd vertices"):
        return
    malos_hueso = 0
    malas_suma = 0
    maxhueso = -1
    for i in range(total):
        o = off_verts + i * 48
        peso = struct.unpack_from("<3f", d, o)
        hueso = d[o + 12:o + 15]
        nusos = d[o + 15]
        if nusos > 3:
            fallo("vertice %d: numBones=%d" % (i, nusos))
        for k in range(min(nusos, 3)):
            if hueso[k] >= mdl["numhuesos"]:
                malos_hueso += 1
            if hueso[k] > maxhueso:
                maxhueso = hueso[k]
        suma = sum(peso[:min(max(nusos, 1), 3)])
        if abs(suma - 1.0) > 0.02:
            malas_suma += 1
    if malos_hueso:
        fallo("%d pesos apuntan a un hueso inexistente (el modelo tiene %d huesos)"
              % (malos_hueso, mdl["numhuesos"]))
    else:
        print("   todos los huesos de los pesos existen  OK")
    if malas_suma:
        aviso("%d vertices con pesos que no suman 1,0" % malas_suma)
    print("   hueso mas alto referenciado: %d de %d" % (maxhueso, mdl["numhuesos"] - 1))
    if vtx_verts is not None and vtx_verts != total:
        fallo("el .vtx recorre %d vertices y el .vvd declara %d" % (vtx_verts, total))


def auditar_vtx(ruta, mdl):
    print("\n=== .dx90.vtx ===")
    if not os.path.exists(ruta):
        return fallo("no existe %s" % ruta), None
    d = open(ruta, "rb").read()
    version = i32(d, 0)
    maxb_tira, maxb_tri = u16(d, 8), u16(d, 10)
    maxb_vert = i32(d, 12)
    checksum, numlods = i32(d, 16), i32(d, 20)
    numbp, off_bp = i32(d, 28), i32(d, 32)
    print("   version=%d maxBones/vértice=%d maxBones/tira=%d maxBones/tri=%d"
          % (version, maxb_vert, maxb_tira, maxb_tri))
    print("   checksum=%s numLODs=%d numBodyParts=%d" % (hex(checksum & 0xFFFFFFFF), numlods, numbp))
    if checksum != mdl["checksum"]:
        fallo("checksum del .vtx != del .mdl")
    if maxb_vert > 3:
        fallo("maxBonesPorVertice=%d: Source usa como maximo 3" % maxb_vert)

    total_tiras = total_verts = total_indices = 0
    peor_hueso = -1
    grupos_malos = 0
    if not dentro(d, off_bp, numbp * 8, ".vtx bodyparts"):
        return None, None
    for bp in range(numbp):
        pos_bp = off_bp + bp * 8
        nummodelos, off_modelos = i32(d, pos_bp), i32(d, pos_bp + 4)
        pos_modelos = pos_bp + off_modelos
        if not dentro(d, pos_modelos, nummodelos * 8, ".vtx modelos"):
            continue
        for mo in range(nummodelos):
            pos_mod = pos_modelos + mo * 8
            numlod_m, off_lod = i32(d, pos_mod), i32(d, pos_mod + 4)
            pos_lod = pos_mod + off_lod
            if not (0 < numlod_m <= 8):
                fallo("modelo %d: numLODs=%d" % (mo, numlod_m))
                continue
            if not dentro(d, pos_lod, numlod_m * 12, ".vtx LODs"):
                continue
            for lo in range(numlod_m):
                a_lod = pos_lod + lo * 12
                nummallas, off_malla, _ = struct.unpack_from("<iif", d, a_lod)
                pos_malla = a_lod + off_malla
                if not dentro(d, pos_malla, nummallas * 9, ".vtx mallas"):
                    continue
                for ma in range(nummallas):
                    a_malla = pos_malla + ma * 9
                    numgrupos, off_grupo = i32(d, a_malla), i32(d, a_malla + 4)
                    pos_grupo = a_malla + off_grupo
                    if not dentro(d, pos_grupo, numgrupos * 25, ".vtx grupos"):
                        continue
                    for gr in range(numgrupos):
                        g = pos_grupo + gr * 25
                        nverts, g_ov, nindices, g_oi, ntiras, g_ot = struct.unpack_from("<6i", d, g)
                        a_verts = g + g_ov
                        a_indices = g + g_oi
                        a_tiras = g + g_ot
                        if not (dentro(d, a_verts, nverts * 9, ".vtx vertices")
                                and dentro(d, a_indices, nindices * 2, ".vtx indices")
                                and dentro(d, a_tiras, ntiras * 27, ".vtx tiras")):
                            grupos_malos += 1
                            continue
                        for k in range(nindices):
                            if u16(d, a_indices + k * 2) >= nverts:
                                fallo("grupo (verts=%d): el indice %d vale %d y se sale"
                                      % (nverts, k, u16(d, a_indices + k * 2)))
                                break
                        for ti in range(ntiras):
                            t = a_tiras + ti * 27
                            nind_t, oi_t, nvert_t, ov_t = struct.unpack_from("<4i", d, t)
                            ncambios, oc_t = i32(d, t + 19), i32(d, t + 23)
                            av = g + g_ov + ov_t          # vertices de la tira
                            ai = g + g_oi + oi_t          # indices de la tira
                            ac = t + oc_t                 # cambios de hueso de la tira
                            total_tiras += 1
                            total_verts += nvert_t
                            total_indices += nind_t
                            if nvert_t > nverts or nind_t > nindices:
                                fallo("tira %d: pide %d verts/%d indices y el grupo tiene %d/%d"
                                      % (total_tiras - 1, nvert_t, nind_t, nverts, nindices))
                                continue
                            if ncambios < 1:
                                fallo("tira %d: 0 cambios de hueso" % (total_tiras - 1))
                                continue
                            if not dentro(d, ac, ncambios * 8, ".vtx cambios"):
                                continue
                            huesos_tira = [struct.unpack_from("<ii", d, ac + c * 8)[1] for c in range(ncambios)]
                            for h in huesos_tira:
                                if not (0 <= h < mdl["numhuesos"]):
                                    fallo("tira %d: un cambio apunta al hueso %d (el modelo tiene %d)"
                                          % (total_tiras - 1, h, mdl["numhuesos"]))
                                if h > peor_hueso:
                                    peor_hueso = h
                            if not dentro(d, av, nvert_t * 9, ".vtx vertices de la tira"):
                                continue
                            for v in range(nvert_t):
                                o = av + v * 9
                                nusos = d[o + 3]
                                idx_cambio = struct.unpack_from("<3b", d, o + 6)
                                if nusos > 3:
                                    fallo("tira %d vertice %d: numBones=%d" % (total_tiras - 1, v, nusos))
                                    continue
                                for k in range(min(max(nusos, 0), 3)):
                                    if not (0 <= idx_cambio[k] < ncambios):
                                        fallo("tira %d vertice %d: apunta al cambio de hueso %d y la tira tiene %d"
                                              % (total_tiras - 1, v, idx_cambio[k], ncambios))
                            for k in range(nind_t):
                                if u16(d, ai + k * 2) >= nvert_t:
                                    fallo("tira %d: indice %d vale %d y la tira tiene %d vertices"
                                          % (total_tiras - 1, k, u16(d, ai + k * 2), nvert_t))
                                    break

    print("   recorrido: %d tiras, %d vertices, %d indices, %d grupos ilegibles"
          % (total_tiras, total_verts, total_indices, grupos_malos))
    print("   hueso mas alto citado por los cambios: %d de %d" % (peor_hueso, mdl["numhuesos"] - 1))
    return total_verts, d


def auditar(mdl_ruta, comparar=False):
    base, _ = os.path.splitext(mdl_ruta)
    mdl = leer_mdl(mdl_ruta)
    print("=== %s ===" % mdl["nombre"])
    print("   version=%d huesos=%d flags=0x%X %d bytes"
          % (mdl["version"], mdl["numhuesos"], mdl["flags"], len(mdl["datos"])))
    vtx_verts, _ = auditar_vtx(base + ".dx90.vtx", mdl)
    auditar_vvd(base + ".vvd", mdl, vtx_verts)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    for ruta in sys.argv[1:]:
        auditar(ruta)
        print("\n" + "=" * 64)
    if FALLOS:
        print("RESULTADO: %d fallo(s)" % len(FALLOS))
        for f in FALLOS[:LIMITE_QUEJAS]:
            print("   - " + f)
    else:
        print("RESULTADO: malla coherente (%d avisos)" % len(AVISOS))
    return 1 if FALLOS else 0


if __name__ == "__main__":
    sys.exit(main())
