"""Deja las texturas finales del mod: 1024x1024, DXT y VTF 7.4 (la version que lee L4D2).

Los PNG de origen son de 2048 y las VTF salian de 5,6 MB cada una (57 MB el mod). A 1024 y
comprimidas, el mod entero baja a unos 14 MB sin perdida apreciable a la vista.

Se escribe el TGA a mano (32 bits BGRA sin comprimir, origen abajo-izquierda) porque es lo que
espera vtex, y para los mapas de normales se deja al lado el .txt con "normal" "1", que es lo que
le pone el flag TEXTUREFLAGS_NORMAL.

Uso: python texturas_finales.py
"""
import glob
import os
import struct
import subprocess

from PIL import Image

RAIZ = r"C:\Users\Lukas\p5x-datamining\kotone_source"
ORIGEN = r"C:\Users\Lukas\p5x-datamining\kotone_artista\texturas"
VTEX_74 = r"C:\Program Files (x86)\Steam\steamapps\common\Portal\bin\vtex.exe"

MATERIALES = {
    "body01": ("PC079_01_body_bc.png", "PC079_01_body_lodlow_nm.png"),
    "body02": ("PC079_01_body_bc.png", "PC079_01_body_lodlow_nm.png"),
    "eye": ("PC079_01_eye_bc.png", None),
    "face": ("PC079_01_face_bc.png", None),
    "hair": ("PC079_01_hair_bc.png", None),
    "xiuzhang": ("PC079_01_xiuzhang_bc.png", "PC079_01_xiuzhang_nm.png"),
}
CON_ALFA = {"eye", "face", "hair"}          # llevan transparencia: alfa en la VTF y $alphatest
LADO = 1024


def escribir_tga(im, destino):
    """TGA 32 bits sin comprimir, BGRA, origen abajo-izquierda. Sin correccion de gamma."""
    im = im.convert("RGBA")
    ancho, alto = im.size
    pixeles = im.load()
    cabecera = struct.pack("<BBBHHBHHHHBB", 0, 0, 2, 0, 0, 0, 0, 0, ancho, alto, 32, 8)
    datos = bytearray()
    for y in range(alto - 1, -1, -1):
        fila = bytearray()
        for x in range(ancho):
            r, g, b, a = pixeles[x, y]
            fila += bytes((b, g, r, a))
        datos += fila
    open(destino, "wb").write(cabecera + bytes(datos))
    return ancho, alto


def info_vtf(ruta):
    d = open(ruta, "rb").read(32)
    if d[:4] != b"VTF\x00":
        return None
    mayor, menor, _ = struct.unpack("<III", d[4:16])
    ancho, alto = struct.unpack("<HH", d[16:20])
    flags = struct.unpack("<I", d[20:24])[0]
    return "%d.%d" % (mayor, menor), ancho, alto, flags


def main():
    trabajo = os.path.join(RAIZ, "texturas_trabajo")
    materiales = os.path.join(trabajo, "materials", "models", "kotone")
    salida = os.path.join(RAIZ, "materials", "models", "kotone")
    os.makedirs(materiales, exist_ok=True)
    os.makedirs(salida, exist_ok=True)
    open(os.path.join(trabajo, "gameinfo.txt"), "w").write(
        '"GameInfo"\n{\n\tgame\t"kotone"\n\tFileSystem\n\t{\n\t\tSteamAppId\t550\n'
        '\t\tToolsAppId\t563\n\t\tSearchPaths\n\t\t{\n\t\t\tGame\t|gameinfo_path|.\n\t\t}\n\t}\n}\n')

    print("--- 1) TGA de 1024, escritos a mano (BGRA, sin comprimir) ---")
    for material, (png_c, png_n) in MATERIALES.items():
        for clase, png in (("color", png_c), ("normal", png_n)):
            if png is None:
                continue
            im = Image.open(os.path.join(ORIGEN, png)).convert("RGBA")
            if max(im.size) > LADO:
                im = im.resize((LADO, LADO), Image.LANCZOS)
            destino = os.path.join(materiales, "%s_%s.tga" % (material, clase))
            a, al = escribir_tga(im, destino)
            if clase == "normal":
                open(destino[:-4] + ".txt", "w").write('"normal" "1"\n"bumpscale" "1.0"\n')
            print("   %-26s %dx%d  %6.2f MB" % (os.path.basename(destino), a, al,
                                                os.path.getsize(destino) / 1e6))

    print("--- 2) compilar con el vtex de Portal (VTF 7.4, el que lee L4D2) ---")
    for material, (png_c, png_n) in MATERIALES.items():
        for clase, png in (("color", png_c), ("normal", png_n)):
            if png is None:
                continue
            nombre = "%s_%s" % (material, clase)
            compresor = "-dxt1" if (clase == "color" and material not in CON_ALFA) else "-dxt5"
            cmd = [VTEX_74, "-mkdir", "-nopause", "-game", trabajo, "-outdir", materiales,
                   compresor, os.path.join(materiales, nombre + ".tga")]
            p = subprocess.run(cmd, capture_output=True, text=True)
            vtf = os.path.join(materiales, nombre + ".vtf")
            if not os.path.exists(vtf):
                print("   %-24s FALLO: %s" % (nombre, (p.stdout + p.stderr).strip()[-200:]))
                continue
            v, a, al, flags = info_vtf(vtf)
            print("   %-24s %-6s %5.2f MB  %dx%d  VTF %s  flags 0x%04X%s" %
                  (nombre, compresor, os.path.getsize(vtf) / 1e6, a, al, v, flags,
                   "  (mapa de normales)" if clase == "normal" else ""))

    print("--- 3) copiar VTF y VMT al arbol del mod ---")
    for viejo in glob.glob(os.path.join(salida, "*")):
        os.remove(viejo)
    total = 0
    for p in sorted(glob.glob(os.path.join(materiales, "*.vtf"))):
        destino = os.path.join(salida, os.path.basename(p))
        open(destino, "wb").write(open(p, "rb").read())
        total += os.path.getsize(destino)
    for material in MATERIALES:
        for base in (os.path.join(RAIZ, "modbuild", "materials", "models", "kotone"),
                     os.path.join(RAIZ, "materials", "models", "kotone")):
            origen = os.path.join(base, material + ".vmt")
            if os.path.exists(origen):
                open(os.path.join(salida, material + ".vmt"), "w").write(open(origen).read())
                break
    print("   total de las texturas del mod: %.1f MB" % (total / 1e6))
    for p in sorted(glob.glob(os.path.join(salida, "*"))):
        print("      %-30s %6.2f MB" % (os.path.basename(p), os.path.getsize(p) / 1e6))


if __name__ == "__main__":
    main()