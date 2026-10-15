"""Instala las armas largas de PC079_01 en el paquete y saca una preview de cada una.

Los OBJ salen de AssetStudio, que NO escribe material (se pidio solo -t Mesh), asi que el MTL se
genera aqui a partir de los .mat del juego: cada arma usa su propio juego de texturas _bc/_nm/_pk/
_stroke/_shadow/_darkcolor/_e, ya presentes en 02_textures/weapons/.

Los OBJ de AssetStudio vienen Z-arriba (el arma esta de pie). El rasterizador trabaja Y-arriba, asi
que se convierte (x, y, z) -> (x, z, -y). La V de las UV se voltea: es la convencion de Unity.

Uso:  python scripts/preview_armas.py
"""
import os
import shutil
import numpy as np
from PIL import Image

RAIZ = r"C:\Users\Lukas\p5x-datamining"
ORIGEN = os.path.join(RAIZ, "_dl", "armas_pc079")
PAQUETE = os.path.join(RAIZ, "kotone_shiomi")
OBJ_DST = os.path.join(PAQUETE, "01_model", "obj", "weapons")
TEX = os.path.join(PAQUETE, "02_textures", "weapons")
SAL = os.path.join(PAQUETE, "preview")

# fichero extraido -> nombre final en el paquete
ARMAS = [
    ("PC079_01_weapon_02_wholeexport_rig_PC079_01_weapon_02.obj", "weapon_02", "PC079_01_weapon_02"),
    ("PC079_01_weapon_03_wholeexport_rig_PC079_01_weapon_03.obj", "weapon_03", "PC079_01_weapon_03"),
    ("PC079_01_weapon_04_wholeexport_rig_PC079_01_weapon_04.obj", "weapon_04", "PC079_01_weapon_04"),
    ("PC079_01_weapon_04_wholeexport_rig_PC079_01_weapon_04_01.obj", "weapon_04_01", "PC079_01_weapon_04"),
    ("PC079_01_weapon_04_wholeexport_rig_PC079_01_weapon_04_02.obj", "weapon_04_02", "PC079_01_weapon_04"),
    ("PC079_01_weapon_05_wholeexport_rig_PC079_01_weapon_05.obj", "weapon_05", "PC079_01_weapon_05"),
]


def leer_obj(ruta):
    """Devuelve posiciones (Y-arriba), uv (V volteada) y triangulos."""
    v, vt, caras, uvs = [], [], [], []
    for linea in open(ruta, encoding="utf-8", errors="replace"):
        if linea.startswith("v "):
            p = linea.split()
            x, y, z = float(p[1]), float(p[2]), float(p[3])
            v.append((x, z, -y))                      # Z-arriba -> Y-arriba
        elif linea.startswith("vt "):
            p = linea.split()
            vt.append((float(p[1]), 1.0 - float(p[2])))
        elif linea.startswith("f "):
            idx = []
            for trozo in linea.split()[1:]:
                partes = trozo.split("/")
                vi = int(partes[0]) - 1
                ti = int(partes[1]) - 1 if len(partes) > 1 and partes[1] else 0
                idx.append((vi, ti))
            for k in range(1, len(idx) - 1):           # abanico
                caras.append((idx[0][0], idx[k][0], idx[k + 1][0]))
                uvs.append((idx[0][1], idx[k][1], idx[k + 1][1]))
    P = np.array(v, dtype=np.float64)
    T = np.array(vt, dtype=np.float64) if vt else np.zeros((len(P), 2))
    return P, T, np.array(caras, dtype=np.int64), np.array(uvs, dtype=np.int64)


def escribir_mtl(destino, nombre_mtl, base_textura):
    lineas = ["# Kotone Shiomi (PC079_01) - Persona 5: The Phantom X",
              "# material reconstruido desde los .mat del juego (AssetStudio no escribe material)",
              "",
              "newmtl mat0",
              "Ka 1.000 1.000 1.000",
              "Kd 1.000 1.000 1.000",
              "Ks 0.000 0.000 0.000",
              "d 1.0",
              "illum 1"]
    for sufijo, clave in (("_bc", "map_Kd"), ("_nm", "map_Bump"), ("_pk", "map_Pm"),
                          ("_stroke", "map_Ke"), ("_shadow", "map_d"), ("_e", "map_Ka")):
        f = base_textura + sufijo + ".png"
        if os.path.exists(os.path.join(TEX, f)):
            lineas.append("%s ../../../02_textures/weapons/%s" % (clave, f))
    open(destino, "w", encoding="utf-8", newline="\n").write("\n".join(lineas) + "\n")


def rasterizar(P, T, caras, uvs, textura, salida, yaw=0.0, pitch=0.0, ancho=560, alto=1000):
    cy, sy = np.cos(yaw), np.sin(yaw)
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    cp, sp = np.cos(pitch), np.sin(pitch)
    Rx = np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]])
    R = Rx @ Ry
    p = P @ R.T
    lo, hi = p.min(axis=0), p.max(axis=0)
    cen = (lo + hi) / 2
    esc = min(ancho / max(hi[0] - lo[0], 1e-6) * 0.82, alto / max(hi[1] - lo[1], 1e-6) * 0.94)
    print("   %.3f x %.3f x %.3f m" % tuple(hi - lo))

    img_out = np.zeros((alto, ancho, 3), dtype=np.float64)
    fondo = np.array([24, 24, 28]) / 255.0
    img_out[:] = fondo
    zbuf = np.full((alto, ancho), -1e9)
    luz = np.array([0.35, 0.55, 0.75])
    luz /= np.linalg.norm(luz)
    tex = None
    if textura and os.path.exists(textura):
        tex = np.array(Image.open(textura).convert("RGBA"))
    px = (p[:, 0] - cen[0]) * esc + ancho / 2
    py = alto / 2 - (p[:, 1] - cen[1]) * esc
    pz = p[:, 2]
    for tri, tuv in zip(caras, uvs):
        x, y, z = px[tri], py[tri], pz[tri]
        x0, x1 = int(max(0, np.floor(x.min()))), int(min(ancho - 1, np.ceil(x.max())))
        y0, y1 = int(max(0, np.floor(y.min()))), int(min(alto - 1, np.ceil(y.max())))
        if x1 < x0 or y1 < y0:
            continue
        area = (x[1] - x[0]) * (y[2] - y[0]) - (x[2] - x[0]) * (y[1] - y[0])
        if abs(area) < 1e-9:
            continue
        xs, ys = np.meshgrid(np.arange(x0, x1 + 1), np.arange(y0, y1 + 1))
        w0 = ((x[1] - xs) * (y[2] - ys) - (x[2] - xs) * (y[1] - ys)) / area
        w1 = ((x[2] - xs) * (y[0] - ys) - (x[0] - xs) * (y[2] - ys)) / area
        w2 = 1 - w0 - w1
        dentro = (w0 >= -0.002) & (w1 >= -0.002) & (w2 >= -0.002)
        if not dentro.any():
            continue
        zz = w0 * z[0] + w1 * z[1] + w2 * z[2]
        sub = zbuf[y0:y1 + 1, x0:x1 + 1]
        mejor = dentro & (zz > sub)
        if not mejor.any():
            continue
        if tex is not None:
            uu = (w0 * T[tuv[0], 0] + w1 * T[tuv[1], 0] + w2 * T[tuv[2], 0]) % 1.0
            vv = (w0 * T[tuv[0], 1] + w1 * T[tuv[1], 1] + w2 * T[tuv[2], 1]) % 1.0
            h, w = tex.shape[:2]
            sx = np.clip((uu * (w - 1)).astype(int), 0, w - 1)
            sy = np.clip((vv * (h - 1)).astype(int), 0, h - 1)
            tel = tex[sy, sx].astype(np.float64) / 255.0
            al = tel[..., 3:4]
            mezcla = tel[..., :3] * al + fondo * (1 - al)
        else:
            mezcla = np.broadcast_to(np.array([0.75, 0.25, 0.85]), (*xs.shape, 3))
        dst = img_out[y0:y1 + 1, x0:x1 + 1]
        m = mejor[..., None]
        dst[:] = np.where(m, mezcla, dst)
        sub[mejor] = zz[mejor]
    Image.fromarray((np.clip(img_out, 0, 1) * 255).astype(np.uint8)).save(salida)


print("=== instalar las armas en el paquete ===")
os.makedirs(OBJ_DST, exist_ok=True)
for fichero, destino, base_tex in ARMAS:
    origen = os.path.join(ORIGEN, fichero)
    if not os.path.exists(origen):
        print("   falta:", fichero)
        continue
    obj = os.path.join(OBJ_DST, destino + ".obj")
    shutil.copy2(origen, obj)
    escribir_mtl(os.path.join(OBJ_DST, destino + ".mtl"), destino + ".mtl", base_tex)
    print("   %-16s <- %s" % (destino + ".obj", fichero[:46]))

print("\n=== preview de cada arma ===")
n = 19
for fichero, destino, base_tex in ARMAS:
    if destino.endswith(("_01", "_02")) and destino.startswith("weapon_04"):
        continue                                       # las piezas sueltas van dentro de weapon_04
    P, T, caras, uvs = leer_obj(os.path.join(OBJ_DST, destino + ".obj"))
    print("  %s  (%d vertices, %d caras)" % (destino, len(P), len(caras)))
    rasterizar(P, T, caras, uvs, os.path.join(TEX, base_tex + "_bc.png"),
               os.path.join(SAL, "%02d_%s.png" % (n, destino)),
               yaw=np.radians(-22), pitch=np.radians(-4))
    n += 1

# hoja de contacto de las armas largas
largas = [f for f in sorted(os.listdir(SAL)) if f[3:].startswith("weapon_0") and f[:2] >= "19"]
ims = [Image.open(os.path.join(SAL, f)) for f in largas]
esc = 0.46
ims = [i.resize((int(i.width * esc), int(i.height * esc))) for i in ims]
W, H = sum(i.width for i in ims), max(i.height for i in ims)
hoja = Image.new("RGB", (W, H), (18, 18, 22))
x = 0
for i in ims:
    hoja.paste(i, (x, 0))
    x += i.width
hoja.save(os.path.join(SAL, "23_long_weapons_contact_sheet.png"))
print("\n  -> 23_long_weapons_contact_sheet.png  (%dx%d)  %s" % (W, H, ", ".join(largas)))