"""Validador estricto de PMX. Busca lo que hace CRASHEAR a MMD, no lo que tolera un importador.

MMD (el programa original) es mucho menos tolerante que mmd_tools: se cae con indices fuera de rango,
con nombres repetidos, con la suma de caras de los materiales que no cuadra, o con una jerarquia de
huesos ciclica. Este script recorre el PMX entero y lo comprueba.

Uso:  python validar_pmx.py <modelo.pmx> [carpeta_del_modelo]
"""
import os
import struct
import sys


class L:
    def __init__(self, d):
        self.d = d
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
        v = struct.unpack_from("<%df" % n, self.d, self.i)
        self.i += 4 * n
        return v

    def txt(self):
        n = self.i32()
        s = self.d[self.i:self.i + n]
        self.i += n
        return s.decode(self.enc, "replace")

    def idx(self, kind):
        tam = self.tam[kind]
        if tam == 1:
            v = self.u8()
        elif tam == 2:
            v = self.u16()
        else:
            v = self.i32()
        return -1 if v == (1 << (8 * tam)) - 1 else v


def validar(ruta, carpeta=None):
    d = open(ruta, "rb").read()
    carpeta = carpeta or os.path.dirname(ruta)
    fallos, avisos = [], []

    def fallo(t):
        fallos.append(t)

    def aviso(t):
        avisos.append(t)

    l = L(d)
    magia = d[:4].decode("ascii", "replace")
    if magia != "PMX ":
        fallo("la cabecera no dice 'PMX ' (%r)" % magia)
    l.i = 4
    version = l.f()
    n_g = l.u8()
    valores = [l.u8() for _ in range(n_g)]
    l.enc = "utf-16-le" if valores[0] == 0 else "utf-8"
    uv_extra = valores[1]
    l.tam = {"vertice": valores[2], "textura": valores[3], "material": valores[4],
             "hueso": valores[5], "morph": valores[6], "cuerpo": valores[7]}
    print("PMX %.1f | codificacion %s | UV extra %d | tamanos de indice: %s"
          % (version, "UTF-16LE" if valores[0] == 0 else "UTF-8", uv_extra,
             ", ".join("%s=%d" % (k, v) for k, v in l.tam.items())))
    nombre, nombre_en, comentario = l.txt(), l.txt(), l.txt()
    l.txt()  # comentario en ingles
    print("nombre: %r | comentario: %r" % (nombre, comentario[:60]))

    # ---- vertices
    n_v = l.i32()
    tipos_peso = {}
    suma_mala = 0
    indice_malo = 0
    sin_peso = 0
    for _ in range(n_v):
        l.vec(3); l.vec(3); l.vec(2 + 4 * uv_extra)
        t = l.u8()
        tipos_peso[t] = tipos_peso.get(t, 0) + 1
        if t == 0:                                   # BDEF1: 1 indice, sin peso
            if l.idx("hueso") < 0:
                indice_malo += 1
        elif t == 1:                                 # BDEF2: 2 indices + 1 peso
            a, b, w = l.idx("hueso"), l.idx("hueso"), l.f()
            if a < 0 or b < 0:
                indice_malo += 1
            if abs(w + 0.0) < 1e-9 and w == 0.0:
                pass
        elif t == 2:                                 # BDEF4
            idxs = [l.idx("hueso") for _ in range(4)]
            ws = [l.f() for _ in range(4)]
            if any(i < 0 for i in idxs):
                indice_malo += 1
            if abs(sum(ws) - 1.0) > 0.01:
                suma_mala += 1
            if sum(ws) < 1e-6:
                sin_peso += 1
        elif t == 3:                                 # SDEF
            a, b = l.idx("hueso"), l.idx("hueso")
            l.f(); l.vec(3); l.vec(3); l.vec(3)
            if a < 0 or b < 0:
                indice_malo += 1
        elif t == 4:                                 # QDEF
            l.vec(4); l.vec(4)
        else:
            fallo("tipo de peso desconocido %d (el fichero se desalinea aqui)" % t)
            break
        l.f()                                        # edge scale
    print("vertices: %d | tipos de peso: %s" % (n_v, tipos_peso))
    if indice_malo:
        fallo("%d vertices con indice de hueso invalido" % indice_malo)
    if suma_mala:
        fallo("%d vertices cuyos pesos no suman 1" % suma_mala)
    if sin_peso:
        fallo("%d vertices sin ningun peso (MMD los manda al origen)" % sin_peso)

    # ---- caras
    n_i = l.i32()
    tri = n_i // 3
    malos = 0
    for _ in range(n_i):
        if l.idx("vertice") >= n_v:
            malos += 1
    if malos:
        fallo("%d indices de cara apuntan a vertices que no existen" % malos)
    print("caras: %d indices (%d triangulos)" % (n_i, tri))

    # ---- texturas
    n_t = l.i32()
    texturas = [l.txt() for _ in range(n_t)]
    print("texturas: %d" % n_t)
    for t in texturas:
        ruta_t = t.replace("\\", "/")
        p = os.path.normpath(os.path.join(carpeta, ruta_t))
        if not os.path.exists(p):
            fallo("falta el fichero de textura %r" % t)
        if ":" in ruta_t.split("/")[0] or ruta_t.startswith("/"):
            aviso("ruta de textura absoluta (MMD en otro equipo no la encontrara): %r" % t)

    # ---- materiales
    n_m = l.i32()
    suma_caras = 0
    for k in range(n_m):
        nom = l.txt(); l.txt()
        l.vec(4); l.vec(3); l.f(); l.vec(3)      # difuso RGBA (4 floats), especular, brillo, ambiente
        l.u8(); l.vec(4); l.f()
        it = l.idx("textura")
        ie = l.idx("textura")
        modo_esf = l.u8()
        modo_toon = l.u8()
        if modo_toon == 0:
            itn = l.idx("textura")
        else:
            itn = l.u8()
            if itn == 0 or itn > 10:
                fallo("material %r: toon interno fuera de rango (%d, debe ser 1..10)" % (nom, itn))
        l.txt()
        nc = l.i32()
        suma_caras += nc
        for etiqueta, ix in (("textura", it), ("esfera", ie)):
            if ix >= n_t:
                fallo("material %r: indice de %s fuera de rango (%d de %d)" % (nom, etiqueta, ix, n_t))
        if modo_toon == 0 and itn >= n_t:
            fallo("material %r: textura toon fuera de rango (%d de %d)" % (nom, itn, n_t))
    if suma_caras != n_i:
        fallo("la suma de caras de los materiales (%d) NO cuadra con las caras del modelo (%d): "
              "esto es crash seguro en MMD" % (suma_caras, n_i))
    print("materiales: %d | caras sumadas %d" % (n_m, suma_caras))

    # ---- huesos
    n_h = l.i32()
    huesos = []
    for k in range(n_h):
        nom, nom_en = l.txt(), l.txt()
        pos = l.vec(3)
        padre = l.idx("hueso")
        capa = l.i32()
        flags = l.u16()
        if flags & 0x0001:
            l.idx("hueso")
        else:
            l.vec(3)
        if flags & 0x0100 or flags & 0x0200:
            l.idx("hueso"); l.f()
        if flags & 0x0400:
            l.vec(3)
        if flags & 0x0800:
            l.vec(3); l.vec(3)
        if flags & 0x2000:
            l.i32()
        enlaces = []
        bucle = 0
        if flags & 0x0020:
            objetivo = l.idx("hueso")
            bucle = l.i32()
            l.f()
            n_e = l.i32()
            for _ in range(n_e):
                e = l.idx("hueso")
                if l.u8():
                    l.vec(3); l.vec(3)
                enlaces.append(e)
            if objetivo >= n_h:
                fallo("hueso %r: el IK apunta a un hueso que no existe" % nom)
            if bucle > 1000:
                aviso("hueso %r: bucle de IK enorme (%d)" % (nom, bucle))
            for e in enlaces:
                if e >= n_h:
                    fallo("hueso %r: enlace de IK invalido" % nom)
        huesos.append({"nombre": nom, "padre": padre, "flags": flags, "ik": enlaces, "capa": capa})
    print("huesos: %d | con IK: %d" % (n_h, sum(1 for h in huesos if h["flags"] & 0x0020)))
    repetidos = {}
    for h in huesos:
        repetidos[h["nombre"]] = repetidos.get(h["nombre"], 0) + 1
    dups = {k: v for k, v in repetidos.items() if v > 1}
    if dups:
        fallo("NOMBRES DE HUESO REPETIDOS (MMD se cae con esto): %s" % dups)
    for k, h in enumerate(huesos):
        if h["padre"] >= n_h:
            fallo("hueso %r: padre fuera de rango" % h["nombre"])
        # ciclo
        vistos, p = set(), h["padre"]
        while p >= 0 and p < n_h:
            if p in vistos or p == k:
                fallo("jerarquia ciclica en el hueso %r" % h["nombre"])
                break
            vistos.add(p)
            p = huesos[p]["padre"]

    # ---- morphs
    n_o = l.i32()
    nombres = []
    for k in range(n_o):
        nom = l.txt(); l.txt()
        panel = l.u8()
        tipo = l.u8()
        n_off = l.i32()
        nombres.append(nom)
        for _ in range(n_off):
            if tipo == 0:
                l.idx("morph"); l.f()
            elif tipo == 1:
                if l.idx("vertice") >= n_v:
                    fallo("morph %r: mueve un vertice que no existe" % nom)
                l.vec(3)
            elif tipo == 2:
                l.idx("hueso"); l.vec(3); l.vec(4)
            elif 3 <= tipo <= 7:
                l.idx("vertice"); l.vec(4)
            elif tipo == 8:
                l.idx("material"); l.u8(); l.vec(3); l.vec(3); l.f(); l.vec(3); l.vec(4); l.f()
                l.vec(4); l.vec(4); l.vec(4)
            elif tipo == 9:
                l.idx("morph"); l.f()
            elif tipo == 10:
                l.idx("cuerpo"); l.u8(); l.vec(3); l.vec(3)
            else:
                fallo("tipo de morph desconocido %d" % tipo)
                break
    print("morphs: %d" % n_o)
    dup_o = {k: nombres.count(k) for k in set(nombres) if nombres.count(k) > 1}
    if dup_o:
        fallo("NOMBRES DE EXPRESION REPETIDOS: %s" % dup_o)

    # ---- frames de pantalla
    nombres_frames = []
    n_f = l.i32()
    for _ in range(n_f):
        nombres_frames.append(l.txt()); l.txt()
        l.u8()
        n_it = l.i32()
        for _ in range(n_it):
            tipo = l.u8()
            ix = l.idx("hueso" if tipo == 0 else "morph")
            limite = n_h if tipo == 0 else n_o
            if ix >= limite:
                fallo("frame de pantalla: elemento %d de tipo %d fuera de rango" % (ix, tipo))

    # ---- cuerpos rigidos y juntas
    n_c = l.i32()
    for _ in range(n_c):
        l.txt(); l.txt()
        l.idx("hueso")
        l.u8(); l.u16(); l.u8()
        l.vec(3); l.vec(3); l.vec(3)
        l.vec(3); l.vec(3)
        l.f(); l.f(); l.f(); l.f(); l.f()
        l.u8()
    n_j = l.i32()
    for _ in range(n_j):
        l.txt(); l.txt()
        l.u8()
        l.idx("cuerpo"); l.idx("cuerpo")
        l.vec(3); l.vec(3); l.vec(3)     # pos, rot
        l.vec(3); l.vec(3)               # limite movil inferior/superior
        l.vec(3); l.vec(3)               # limite de giro inferior/superior
        l.vec(3); l.vec(3)               # constante elastica movil/giro
    print("frames de pantalla: %d | cuerpos rigidos: %d | juntas: %d" % (n_f, n_c, n_j))
    if n_f == 0:
        fallo("CERO frames de pantalla: MMD se CAE al cargar (su codigo de frames, el que referencia "
              "'表示･IK･外親'/'Disp/IK/OP'/'Facial', desreferencia una estructura que no existe)")
    else:
        for nombre_f in ("Root", "表情"):
            if nombre_f not in nombres_frames:
                aviso("falta el frame estandar %r (MMD lo crea solo, pero mejor tenerlo)" % nombre_f)
    print("bytes leidos: %d de %d%s" % (l.i, len(d), "  <-- SOBRAN BYTES" if l.i < len(d) else ""))
    if l.i < len(d):
        aviso("quedan %d bytes sin leer al final del fichero" % (len(d) - l.i))

    print("\n=== %s ===" % ("FALLOS: %d" % len(fallos) if fallos else "SIN FALLOS"))
    for f in fallos:
        print("  FALLO:", f)
    for a in avisos:
        print("  aviso:", a)
    return fallos


if __name__ == "__main__":
    validar(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
