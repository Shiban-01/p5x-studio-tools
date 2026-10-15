"""Comprime el paquete kotone_shiomi entero y comprueba el zip abriendolo.

El zip lleva la carpeta dentro (kotone_shiomi/...), de modo que al descomprimir no se mezcle con
lo que ya haya. Comprime en deflate; el contenido ya viene comprimido en su mayoria (PNG, GLB),
asi que la ganancia sera poca y lo importante es que no falta nada.
"""
import os
import shutil
import zipfile

ORIGEN = r"C:\Users\Lukas\p5x-datamining"
CARPETA = "kotone_shiomi"
DESTINO = os.path.join(ORIGEN, "kotone_shiomi")

print("=== comprimiendo ===")
zip_path = shutil.make_archive(DESTINO, "zip", root_dir=ORIGEN, base_dir=CARPETA)
print("   ->", zip_path)

original = sum(os.path.getsize(os.path.join(r, f))
               for r, _, fs in os.walk(DESTINO) for f in fs)
comprimido = os.path.getsize(zip_path)
print("   original:  %.1f MB   en %d ficheros"
      % (original / 1048576, sum(len(fs) for _, _, fs in os.walk(DESTINO))))
print("   zip:       %.1f MB   (%.0f%% del original)"
      % (comprimido / 1048576, 100.0 * comprimido / original))

print("\n=== verificacion: abrir el zip y contar ===")
with zipfile.ZipFile(zip_path) as z:
    malo = z.testzip()
    entradas = z.infolist()
    ficheros = [e for e in entradas if not e.is_dir()]
    print("   entradas: %d (%d ficheros, %d carpetas)"
          % (len(entradas), len(ficheros), len(entradas) - len(ficheros)))
    print("   integridad (testzip): %s" % ("todo correcto" if malo is None else "FALLO en " + malo))
    print("   contenido sin comprimir: %.1f MB" % (sum(e.file_size for e in ficheros) / 1048576))

    raices = sorted({e.filename.split("/")[1] for e in entradas if "/" in e.filename})
    print("   dentro de %s/: %s" % (CARPETA, ", ".join(raices)))

    print("\n=== comprobaciones concretas ===")
    nombres = {e.filename for e in entradas}
    clave = [
        (CARPETA + "/Kotone_Shiomi_full.fbx", "el FBX"),
        (CARPETA + "/README.md", "el README"),
        (CARPETA + "/SUMMARY.json", "el manifiesto"),
        (CARPETA + "/01_model/glb/Kotone_Shiomi_full.glb", "el modelo completo"),
        (CARPETA + "/01_model/obj/weapons/weapon_02.obj", "arma larga 02"),
        (CARPETA + "/01_model/obj/weapons/weapon_05.obj", "arma larga 05"),
        (CARPETA + "/preview/23_long_weapons_contact_sheet.png", "hoja de las armas largas"),
        (CARPETA + "/preview/11_hip_detail.png", "detalle de cadera"),
        (CARPETA + "/06_origin/provenance.json", "procedencia"),
    ]
    for ruta, etiqueta in clave:
        e = next((x for x in ficheros if x.filename == ruta), None)
        print("   %-28s %s" % (etiqueta, ("OK  %.2f MB" % (e.file_size / 1048576)) if e else "FALTA"))

    # ninguna entrada debe salirse de la carpeta
    raras = [e.filename for e in entradas if e.filename.startswith("/") or ".." in e.filename]
    print("\n   rutas sospechosas: %s" % (raras or "ninguna"))
