"""Sonda: que expone UnityPy de una malla del juego, para escribir el exportador con datos reales.

Interesa saber si trae vertices, normales, UVs y submallas ya separadas, y en que sistema de
coordenadas vienen, porque de eso depende el OBJ que se genere.
"""
import UnityPy

# los bundles del juego vienen sin la cadena de version de Unity, y sin esto UnityPy se niega a
# abrirlos. La version real del cliente (2022.3.49f1) se lee de la cabecera del bundle de indice.
UnityPy.config.FALLBACK_UNITY_VERSION = "2022.3.49f1"

BUNDLE = r"C:\Users\Lukas\Downloads\P5X\Client\OuterPackage\Bundles\Windows\145\part_pc079_011ef29087.bundle"

env = UnityPy.load(BUNDLE)
print("objetos: %d" % len(env.objects))

vistos = 0
for obj in env.objects:
    if obj.type.name != "Mesh":
        continue
    m = obj.read()
    vistos += 1
    if vistos > 3:
        continue
    print("\n--- Malla: %s" % getattr(m, "m_Name", "?"))
    campos = [c for c in dir(m) if not c.startswith("_")]
    utiles = [c for c in campos if any(p in c.lower() for p in
              ("vertex", "normal", "uv", "submesh", "index", "bindpose", "blend", "shape"))]
    print("   campos utiles: %s" % utiles)
    for c in utiles[:12]:
        try:
            v = getattr(m, c)
            if isinstance(v, (list, tuple)):
                print("      %-24s lista de %d" % (c, len(v)))
            else:
                print("      %-24s %s" % (c, str(v)[:70]))
        except Exception as e:
            print("      %-24s (error %s)" % (c, e))
    # la via cruda: m_VertexData trae los canales
    vd = getattr(m, "m_VertexData", None)
    if vd is not None:
        print("   m_VertexData: %s" % type(vd).__name__)
        for c in dir(vd):
            if c.startswith("_"):
                continue
            try:
                v = getattr(vd, c)
                if isinstance(v, (list, tuple)):
                    print("      %-24s lista de %d" % (c, len(v)))
                elif not callable(v):
                    print("      %-24s %s" % (c, str(v)[:70]))
            except Exception:
                pass
print("\nmallas encontradas: %d" % vistos)