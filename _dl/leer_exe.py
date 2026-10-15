"""Lista/extrae el contenido interno de un .exe PyInstaller, para comparar builds.

Uso:
  python leer_exe.py listar <exe>
  python leer_exe.py extraer <exe> <nombre_interno> <destino>
  python leer_exe.py pyz <exe>            # lista los modulos del PYZ
"""
import sys

from PyInstaller.archive.readers import CArchiveReader, ZlibArchiveReader

accion = sys.argv[1]
exe = sys.argv[2]
r = CArchiveReader(exe)

if accion == "listar":
    for n in r.toc:
        print(n)
elif accion == "extraer":
    nombre, destino = sys.argv[3], sys.argv[4]
    datos = r.extract(nombre)
    open(destino, "wb").write(datos)
    print("escrito %s (%d bytes)" % (destino, len(datos)))
elif accion == "pyz":
    datos = r.extract("PYZ-00.pyz")
    open("C:/Users/Lukas/p5x-datamining/_dl/_tmp_pyz.pyz", "wb").write(datos)
    z = ZlibArchiveReader("C:/Users/Lukas/p5x-datamining/_dl/_tmp_pyz.pyz")
    for n in sorted(z.toc):
        if "p5x_studio" in n:
            print(n)
elif accion == "modulo":
    nombre, destino = sys.argv[3], sys.argv[4]
    datos = r.extract("PYZ-00.pyz")
    open("C:/Users/Lukas/p5x-datamining/_dl/_tmp_pyz.pyz", "wb").write(datos)
    z = ZlibArchiveReader("C:/Users/Lukas/p5x-datamining/_dl/_tmp_pyz.pyz")
    mod = z.extract(nombre)
    open(destino, "wb").write(mod)
    print("escrito %s (%d bytes)" % (destino, len(mod)))