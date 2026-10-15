"""Compara, hueso a hueso, el mundo que calcula glb_rig con el que acaba teniendo el nodo del GLB.

Si no coinciden, la piel deforma la malla en reposo (estallido). Uso:
python medir_huesos_glb.py <dump> <glb>
"""
import json
import struct
import sys
from pathlib import Path

sys.path.insert(0, "C:/Users/Lukas/p5x-datamining/p5x_studio")
from p5x_studio import glb_rig  # noqa: E402

dump, glb = Path(sys.argv[1]), Path(sys.argv[2])

esq = glb_rig.Esqueleto(dump)
partes = glb_rig.listar_partes(dump)
for k, p in enumerate(partes):
    esq.aprender(dump, p, referencia=(k == 0))
esq.completar(lambda s: None)
idx, locales = esq.locales()
orden = [n for n in esq.orden if n in idx]

b = glb.read_bytes()
off, js, bin_ = 12, None, b""
while off < len(b):
    ln, ty = struct.unpack_from("<II", b, off)
    off += 8
    t = b[off:off + ln]
    off += ln
    if ty == 0x4E4F534A:
        js = json.loads(t.decode("utf-8"))


def mul(A, B):
    return [[sum(A[i][k] * B[k][j] for k in range(4)) for j in range(4)] for i in range(4)]


def trs(n):
    t = n.get("translation", [0, 0, 0])
    q = n.get("rotation", [0, 0, 0, 1])
    s = n.get("scale", [1, 1, 1])
    x, y, z, w = q
    R = [[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
         [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
         [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]]
    M = [[1.0 if i == j else 0.0 for j in range(4)] for i in range(4)]
    for i in range(3):
        for j in range(3):
            M[i][j] = R[i][j] * s[j]
        M[i][3] = t[i]
    return M


padres = {}
for i, n in enumerate(js["nodes"]):
    for c in n.get("children", []):
        padres[c] = i
por_nombre = {}
for i, n in enumerate(js["nodes"]):
    por_nombre.setdefault(n.get("name"), i)


def glob(i):
    M = trs(js["nodes"][i])
    p = padres.get(i)
    while p is not None:
        M = mul(trs(js["nodes"][p]), M)
        p = padres.get(p)
    return M


peores = []
R180 = [[-1.0, 0, 0, 0], [0, 1.0, 0, 0], [0, 0, -1.0, 0], [0, 0, 0, 1.0]]   # 180 grados en Y
peores2 = []
for nom in orden:
    if nom not in por_nombre:
        continue
    G = glob(por_nombre[nom])
    E = glb_rig.hornear(esq.mundo[nom])
    d = max(abs(G[i][j] - E[i][j]) for i in range(4) for j in range(4))
    peores.append((d, nom, esq.metodo.get(nom)))
    ER = mul(R180, E)
    d2 = max(abs(G[i][j] - ER[i][j]) for i in range(4) for j in range(4))
    peores2.append((d2, nom, esq.metodo.get(nom)))
peores.sort(reverse=True)
peores2.sort(reverse=True)
print("huesos comparados:", len(peores))
print("--- G vs hornear(mundo) ---")
for d, nom, met in peores[:6]:
    print("   %.4f  %-32s (%s)" % (d, nom, met))
print("   desajustados (>1e-3): %d de %d" % (sum(1 for d, _, _ in peores if d > 1e-3), len(peores)))
print("--- G vs R180Y*hornear(mundo) ---")
for d, nom, met in peores2[:6]:
    print("   %.4f  %-32s (%s)" % (d, nom, met))
print("   desajustados (>1e-3): %d de %d" % (sum(1 for d, _, _ in peores2 if d > 1e-3), len(peores2)))
print("por metodo (G vs E):", {m: sum(1 for d, _, mm in peores if mm == m and d > 1e-3) for m in set(x[2] for x in peores)})