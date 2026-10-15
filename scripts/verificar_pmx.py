"""Lector de PMX para verificar de verdad lo que se ha exportado (no fiarse del 'LISTO')."""
import struct
import sys


class Lector:
    def __init__(self, datos):
        self.d = datos
        self.i = 0

    def u8(self):
        v = self.d[self.i]
        self.i += 1
        return v

    def i32(self):
        v = struct.unpack_from("<i", self.d, self.i)[0]
        self.i += 4
        return v

    def u16(self):
        v = struct.unpack_from("<H", self.d, self.i)[0]
        self.i += 2
        return v

    def f(self):
        v = struct.unpack_from("<f", self.d, self.i)[0]
        self.i += 4
        return v

    def vec(self, n):
        return [self.f() for _ in range(n)]

    def idx(self, tam):
        if tam == 1:
            v = struct.unpack_from("<b", self.d, self.i)[0]
            self.i += 1
            return v
        if tam == 2:
            v = struct.unpack_from("<h", self.d, self.i)[0]
            self.i += 2
            return v
        return self.i32()

    def texto(self):
        n = self.i32()
        bruto = self.d[self.i:self.i + n]
        self.i += n
        return bruto.decode("utf-16-le" if self.enc == 0 else "utf-8", "replace")


def leer(ruta):
    datos = open(ruta, "rb").read()
    l = Lector(datos)
    magia = datos[:4].decode("ascii")
    ver = struct.unpack_from("<f", datos, 4)[0]
    l.i = 8
    globals_count = l.u8()          # PMX trae un byte con cuantos ajustes globales vienen (8)
    l.enc = l.u8()
    uv_extra, tam_v, tam_tex, tam_mat, tam_bone, tam_morph, tam_rb = (l.u8() for _ in range(7))
    print("magia %r | version %.1f | codificacion %s | indices: vertice %d, textura %d, material %d, hueso %d, morph %d"
          % (magia, ver, "UTF-16LE" if l.enc == 0 else "UTF-8", tam_v, tam_tex, tam_mat, tam_bone, tam_morph))
    nombre, nombre_en = l.texto(), l.texto()
    comentario = l.texto()
    l.texto()
    print("modelo: %r (%r)" % (nombre, nombre_en))
    print("comentario: %s" % comentario.replace("\n", " / ")[:160])

    nverts = l.i32()
    for _ in range(nverts):
        l.vec(3); l.vec(3)
        l.vec(2 + 4 * uv_extra)          # la UV base son 2 floats; cada UV extra son 4
        tipo = l.u8()
        if tipo == 0:                    # BDEF1
            l.f()
        elif tipo == 1:                  # BDEF2
            l.vec(2); l.vec(3)
        elif tipo == 2:                  # BDEF4: 4 pesos + 4 posiciones
            l.vec(4); l.vec(12)
        elif tipo == 3:                  # SDEF: 2 pesos + pos + C + R0 + R1
            l.vec(2); l.vec(12)
        elif tipo == 4:                  # QDEF: 4 pesos + 12 posiciones
            l.vec(4); l.vec(12)
        l.f()
    nfaces = l.i32()
    l.i += nfaces * tam_v
    ntex = l.i32()
    texturas = [l.texto() for _ in range(ntex)]
    print("vertices %d | indices de cara %d (=%d triangulos) | texturas %d" % (nverts, nfaces, nfaces // 3, ntex))
    for t in texturas[:14]:
        print("   textura: %s" % t)

    nmat = l.i32()
    mats = []
    for _ in range(nmat):
        nom, nom_en = l.texto(), l.texto()
        l.vec(4); l.vec(3); l.f(); l.vec(3)
        flags = l.u8()
        l.vec(4); l.f()
        tex = l.idx(tam_tex)
        esp = l.idx(tam_tex)
        l.u8()
        toon = l.u8()
        if toon == 1:
            l.idx(tam_tex)
        l.texto()
        caras = l.i32()
        mats.append((nom, tex, caras))
    print("materiales %d" % nmat)
    for m in mats:
        print("   %-28s textura indice %3d | caras %5d" % (m[0], m[1], m[2]))

    nbones = l.i32()
    huesos, iks = [], []
    for _ in range(nbones):
        nom, nom_en = l.texto(), l.texto()
        pos = l.vec(3)
        padre = l.idx(tam_bone)
        capa = l.i32()
        flags = l.u16()
        if flags & 0x0001:
            l.vec(3)
        if flags & 0x0100:
            l.idx(tam_bone); l.f()
        if flags & 0x0400:
            l.vec(3)
        if flags & 0x0800:
            l.vec(3); l.vec(3)
        if flags & 0x2000:
            l.i32()
        if flags & 0x0020:
            objetivo = l.idx(tam_bone)
            vueltas = l.i32()
            limite = l.f()
            nlinks = l.i32()
            enlaces = []
            for _ in range(nlinks):
                hueso = l.idx(tam_bone)
                tiene = l.u8()
                if tiene:
                    l.vec(3); l.vec(3)
                enlaces.append(hueso)
            iks.append((nom, objetivo, vueltas, limite, enlaces))
        huesos.append((nom, pos, padre, capa, flags))
    print("huesos %d" % nbones)
    print("   cadena estandar presente:", [n for n, _, _, _, _ in huesos
                                          if n in ("全ての親", "センター", "上半身", "上半身2", "下半身", "首", "頭",
                                                   "腕.左", "ひじ.左", "手首.左", "脚.左", "ひざ.左", "足首.左", "つま先.左",
                                                   "肩.左", "親指0.左", "人指1.左")])
    print("   IK definidos:", len(iks))
    for nom, obj, vueltas, limite, enlaces in iks:
        nombres_enl = [huesos[e][0] if 0 <= e < len(huesos) else e for e in enlaces]
        print("      %-12s -> objetivo %-12s vueltas %d | limite %.0f grados | enlaces %s"
              % (nom, huesos[obj][0] if 0 <= obj < len(huesos) else obj, vueltas,
                 __import__("math").degrees(limite), nombres_enl))
    nmorph = l.i32()
    morfos = []
    for _ in range(nmorph):
        nom, nom_en = l.texto(), l.texto()
        panel = l.u8()
        tipo = l.u8()
        n = l.i32()
        morfos.append((nom, tipo, n))
        for _ in range(n):
            if tipo in (1,):
                l.idx(tam_v); l.vec(3)
            elif tipo == 2:
                l.idx(tam_tex); l.u8(); l.vec(4); l.vec(3); l.f(); l.vec(3); l.u8(); l.vec(4); l.f()
            elif tipo == 3:
                l.idx(tam_mat); l.u8(); l.vec(4); l.vec(3); l.f(); l.vec(3); l.u8(); l.vec(4); l.f()
            elif tipo == 4:
                l.idx(tam_bone); l.vec(3); l.vec(4)
            elif tipo == 5:
                l.idx(tam_v); l.vec(2)
            elif tipo == 6:
                l.idx(tam_v); l.vec(2)
            elif tipo == 7:
                l.idx(tam_mat); l.u8(); l.vec(4)
            elif tipo == 8:
                l.idx(tam_bone); l.vec(3); l.vec(4)
            elif tipo == 9:
                l.idx(tam_mat); l.u8(); l.vec(4)
            elif tipo == 10:
                l.idx(tam_rb); l.u8(); l.vec(3); l.vec(3)
    print("morphs %d (tipo 1 = de vertices)" % nmorph)
    print("   ", [m[0] for m in morfos][:26])
    ncuadros = l.i32()
    cuadros = []
    for _ in range(ncuadros):
        nom, nom_en = l.texto(), l.texto()
        esp = l.u8()
        n = l.i32()
        items = []
        for _ in range(n):
            tipo = l.u8()
            items.append((tipo, l.idx(tam_bone) if tipo == 1 else l.idx(tam_morph)))
        cuadros.append((nom, len(items)))
    print("cuadros de visualizacion %d: %s" % (ncuadros, [c[0] for c in cuadros][:8]))


if __name__ == "__main__":
    leer(sys.argv[1])