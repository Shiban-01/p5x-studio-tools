"""Lector minimo de FBX (binario 7.x y ASCII) para verificar sin Blender.

Comprueba lo que importa para que el modelo sirva:
  - version del FBX (Blender importa 7.x binario sin problema)
  - cuantos nodos 'Model' hay (huesos/mallas), 'Deformer' con 'Skin'/'Cluster' (pesos)
  - cuantos 'Geometry' y si traen 'LayerElementUV' (UVs) y 'Shape' (blendshapes = expresiones)
  - cuantos 'AnimationStack' (clips) y 'AnimationCurveNode' (canales animados)
  - nombres de los clips y de los huesos, para compararlos con el esqueleto del juego

Uso:  python verificar_fbx.py <fichero.fbx> [otro.fbx ...]
"""
import struct
import sys
import os
from collections import Counter

FBX_BIN = b"Kaydara FBX Binary  \x00"


class Nodo:
    __slots__ = ("nombre", "props", "hijos")

    def __init__(self, nombre):
        self.nombre = nombre
        self.props = []
        self.hijos = []

    def buscar(self, nombre):
        return [h for h in self.hijos if h.nombre == nombre]

    def texto(self):
        return next((p for p in self.props if isinstance(p, str)), None)


def leer_nodo(datos, pos, version):
    """Devuelve (nodo, nueva_pos) o (None, pos) al llegar al centinela de fin."""
    if version >= 7500:
        fin, nprops, plen, nlen = struct.unpack_from("<QQQB", datos, pos)
        pos += 25
    else:
        fin, nprops, plen, nlen = struct.unpack_from("<IIIB", datos, pos)
        pos += 13
    if fin == 0:
        return None, pos
    nombre = datos[pos:pos + nlen].decode("utf-8", "replace")
    pos += nlen
    n = Nodo(nombre)

    def prop(tipo, p):
        if tipo == b"Y":
            return struct.unpack_from("<h", datos, p)[0], p + 2
        if tipo == b"C":
            return bool(datos[p]), p + 1
        if tipo == b"I":
            return struct.unpack_from("<i", datos, p)[0], p + 4
        if tipo == b"F":
            return struct.unpack_from("<f", datos, p)[0], p + 4
        if tipo == b"D":
            return struct.unpack_from("<d", datos, p)[0], p + 8
        if tipo == b"L":
            return struct.unpack_from("<q", datos, p)[0], p + 8
        if tipo in (b"f", b"d", b"l", b"i", b"b"):
            largo, cod, comp = struct.unpack_from("<IIB", datos, p)
            p += 13
            fmt = {b"f": "f", b"d": "d", b"i": "i", b"b": "b", b"l": "q"}[tipo]
            vals = struct.unpack_from("<" + fmt * largo, datos, p)
            return (list(vals), p + struct.calcsize(fmt) * largo)
        if tipo in (b"S", b"R"):
            largo = struct.unpack_from("<I", datos, p)[0]
            p += 4
            crudo = datos[p:p + largo]
            p += largo
            return (crudo.decode("utf-8", "replace") if tipo == b"S" else crudo), p
        raise ValueError("tipo de propiedad desconocido: " + repr(tipo))

    for _ in range(nprops):
        tipo = datos[pos:pos + 1]
        pos += 1
        v, pos = prop(tipo, pos)
        n.props.append(v)

    # hijos hasta que el hijo empiece en/despues del fin
    while pos < fin:
        hijo, pos2 = leer_nodo(datos, pos, version)
        if hijo is None:
            break
        n.hijos.append(hijo)
        pos = pos2
    return n, fin


def leer_binario(datos):
    version = struct.unpack_from("<I", datos, 23)[0]
    pos = 27
    raiz = Nodo("(raiz)")
    while pos < len(datos):
        n, pos2 = leer_nodo(datos, pos, version)
        if n is None:
            break
        raiz.hijos.append(n)
        pos = pos2
    return raiz, version


def leer_ascii(texto):
    """Parser muy sencillo de FBX ASCII: solo nombres de nodos y valores entre comillas."""
    import re
    raiz = Nodo("(raiz)")
    pila = [raiz]
    for linea in texto.splitlines():
        s = linea.strip()
        if not s or s.startswith(";"):
            continue
        if s.startswith("}"):
            if len(pila) > 1:
                pila.pop()
            continue
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:", s)
        if m:
            n = Nodo(m.group(1))
            vals = re.findall(r'"([^"]*)"', s)
            n.props = vals
            pila[-1].hijos.append(n)
            if s.rstrip().endswith("{"):
                pila.append(n)
            continue
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*\{", s)
        if m:
            n = Nodo(m.group(1))
            pila[-1].hijos.append(n)
            pila.append(n)
    return raiz, 0


def recorrer(nodo):
    yield nodo
    for h in nodo.hijos:
        yield from recorrer(h)


def analizar(ruta):
    datos = open(ruta, "rb").read()
    if datos[:len(FBX_BIN)] == FBX_BIN:
        raiz, version = leer_binario(datos)
        tipo = "binario"
    else:
        raiz, version = leer_ascii(datos.decode("utf-8", "replace"))
        tipo = "ascii"

    todos = list(recorrer(raiz))
    cuenta = Counter(n.nombre for n in todos)

    def nombres(nombre, limite=40):
        v = [n.texto() for n in todos if n.nombre == nombre]
        v = [x for x in v if x]
        return v[:limite]

    modelos = nombres("Model")
    stacks = nombres("AnimationStack")
    geometrias = nombres("Geometry")
    shapes = nombres("Shape")

    # Deformers: Skin + Cluster (huesos con pesos)
    clusters = [n for n in todos if n.nombre == "Cluster"]
    skin_mallas = [n for n in todos if n.nombre == "Skin"]

    # huesos: nodos Model con Limb o con Type == "LimbNode"
    huesos = []
    mallas = []
    for n in todos:
        if n.nombre != "Model":
            continue
        tipos = [p for p in n.props if isinstance(p, str)]
        if any(t.lower() == "limbnode" for t in tipos):
            huesos.append(n.texto())
        elif any(t.lower() == "mesh" for t in tipos):
            mallas.append(n.texto())

    print(f"\n===== {os.path.basename(ruta)} =====")
    print(f"  tipo: {tipo}   version FBX: {version}   tamano: {len(datos)/1e6:.2f} MB")
    print(f"  nodos: {len(todos)}")
    print(f"  modelos (Model): {cuenta.get('Model', 0)}   con Type=LimbNode (huesos): {len(huesos)}"
          f"   con Type=Mesh (mallas): {len(mallas)}")
    print(f"  deformers/Cluster (huesos con pesos): {len(clusters)}   Skin: {len(skin_mallas)}")
    print(f"  Geometry: {cuenta.get('Geometry', 0)}   LayerElementUV: {cuenta.get('LayerElementUV', 0)}"
          f"   Shape (blendshapes): {len(shapes)}   BlendShapeChannel: {cuenta.get('BlendShapeChannel', 0)}")
    print(f"  AnimationStack (clips): {cuenta.get('AnimationStack', 0)}   "
          f"AnimationCurveNode: {cuenta.get('AnimationCurveNode', 0)}   "
          f"AnimationCurve: {cuenta.get('AnimationCurve', 0)}")
    if stacks:
        print(f"  nombres de clips: {stacks}")
    if geometrias:
        print(f"  geometrias: {geometrias[:12]}{' ...' if len(geometrias) > 12 else ''}")
    if shapes:
        print(f"  expresiones (Shape): {shapes[:25]}")
    if huesos:
        print(f"  primeros huesos: {huesos[:14]}")
    return {
        "fichero": ruta, "tipo": tipo, "version": version,
        "huesos": len(huesos), "clusters": len(clusters), "uvs": cuenta.get("LayerElementUV", 0),
        "shapes": len(shapes), "clips": cuenta.get("AnimationStack", 0),
        "curvas": cuenta.get("AnimationCurve", 0), "stacks": stacks,
    }


if __name__ == "__main__":
    res = []
    for ruta in sys.argv[1:]:
        if os.path.isdir(ruta):
            for f in sorted(os.listdir(ruta)):
                if f.lower().endswith(".fbx"):
                    res.append(analizar(os.path.join(ruta, f)))
        else:
            res.append(analizar(ruta))