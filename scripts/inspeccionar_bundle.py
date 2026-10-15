"""Mira dentro de un bundle de Unity sin extraer nada: que objetos trae y como se llaman.

Sirve para saber que es un modelo antes de ponerse a extraerlo: mallas, materiales, texturas,
esqueletos, animaciones y las rutas del contenedor.

Uso: python inspeccionar_bundle.py <bundle> [bundle2 ...]
"""
import sys

import UnityPy


def resumen(ruta):
    print("=" * 78)
    print(ruta)
    entorno = UnityPy.load(ruta)
    print("   objetos: %d" % len(entorno.objects))
    tipos = {}
    for obj in entorno.objects:
        try:
            datos = obj.read()
        except Exception as error:  # noqa: BLE001
            print("   [!] no se pudo leer %s: %s" % (obj.type.name, error))
            continue
        nombre = getattr(datos, "m_Name", "") or ""
        if nombre == "Base":
            nombre = ""
        tipos.setdefault(obj.type.name, []).append((nombre, obj.path_id, getattr(datos, "m_Size", None)))
    for tipo, lista in sorted(tipos.items(), key=lambda t: -len(t[1])):
        print("   %-22s %3d" % (tipo, len(lista)))
        for nombre, pid, tam in lista[:12]:
            extra = ""
            if tam:
                extra = " %.1f KB" % (tam / 1024)
            print("        %-42s path_id %-12d%s" % (nombre or "(sin nombre)", pid, extra))
        if len(lista) > 12:
            print("        ... y %d mas" % (len(lista) - 12))
    contenedor = getattr(entorno, "container", None) or {}
    if contenedor:
        print("   rutas del contenedor (%d):" % len(contenedor))
        for clave in sorted(contenedor)[:20]:
            print("        %s" % clave)


for ruta in sys.argv[1:]:
    resumen(ruta)