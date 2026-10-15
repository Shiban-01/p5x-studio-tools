"""Busca un termino en las cabeceras de TODOS los bundles y dice cuales lo contienen.

Los bundles de Unity guardan el indice de rutas de sus assets ("assets/...") sin comprimir al
principio del fichero, asi que buscando ahi se sabe que bundles hablan de un modelo sin extraer nada.

Uso: python buscar_en_bundles.py <carpeta_de_bundles> <termino> [termino2 ...]
     [--bytes N]  cuantos bytes de cada fichero mirar (por defecto 262144)
"""
import os
import sys

carpeta = sys.argv[1]
resto = sys.argv[2:]
limite = 262144
if "--bytes" in resto:
    i = resto.index("--bytes")
    limite = int(resto[i + 1])
    resto = resto[:i] + resto[i + 2:]
terminos = [t.lower().encode() for t in resto]

encontrados = []
total = 0
for raiz, _, ficheros in os.walk(carpeta):
    for nombre in ficheros:
        if not nombre.endswith(".bundle"):
            continue
        ruta = os.path.join(raiz, nombre)
        total += 1
        try:
            with open(ruta, "rb") as f:
                trozo = f.read(limite)
        except OSError:
            continue
        bajo = trozo.lower()
        for termino in terminos:
            pos = bajo.find(termino)
            if pos < 0:
                continue
            # sacar la cadena de texto que rodea la coincidencia: suele ser la ruta del asset
            ini = max(0, trozo.rfind(b"\x00", 0, pos) + 1)
            fin = trozo.find(b"\x00", pos)
            cadena = trozo[ini:fin if fin > 0 else pos + 80]
            try:
                cadena = cadena.decode("utf-8", "replace")
            except Exception:  # noqa: BLE001
                cadena = repr(cadena)
            encontrados.append((ruta, termino.decode(), os.path.getsize(ruta), cadena.strip()))
            break

print("bundles mirados: %d (primeros %d KB de cada uno)" % (total, limite // 1024))
print("coincidencias: %d" % len(encontrados))
for ruta, termino, tam, cadena in sorted(encontrados, key=lambda e: -e[2]):
    print("  %8.2f MB  %-58s  %r" % (tam / 1048576, ruta.split(os.sep)[-1], cadena[:110]))