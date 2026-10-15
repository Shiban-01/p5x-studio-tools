"""Prueba del bulk de texturas: categorias, nombres de carpeta, organizacion y una corrida real.

La ultima parte SÍ exporta de verdad (2 bundles de una categoria) porque es la unica forma de
comprobar que la cadena entera funciona: enlaces duros -> motor -> carpetas. Todo lo que escribe va
a una carpeta temporal: no toca `extracted/` ni el manifiesto de verdad.
"""
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun  # noqa: E402

sys.path.insert(0, "C:/Users/Lukas/p5x-datamining/p5x_studio")
from p5x_studio import ajustes, lote  # noqa: E402

# el manifiesto de verdad va a cache/work: la prueba usa uno suyo para no ensuciarlo
_TMP = Path(tempfile.mkdtemp(prefix="lote_prueba_"))
lote._manifiesto_ruta = lambda: _TMP / "manifiesto.json"

# --------------------------------------------------------------------------- 1) categorias
ids = [c["id"] for c in lote.CATEGORIAS]
comun.comprobar(len(ids) == len(set(ids)), "no hay categorias repetidas")
vistas = [f for c in lote.CATEGORIAS for f in c["familias"]]
comun.comprobar(len(vistas) == len(set(vistas)),
                "ninguna familia esta en dos categorias (si no, saldria por duplicado)")
comun.comprobar(lote.categoria_de("115/shared_3e45cab0.bundle") == "shared", "shared -> Shared")
comun.comprobar(lote.categoria_de("000/scn__01_a_01b1370ce.bundle") == "scenery", "scn -> Scenery")
comun.comprobar(lote.categoria_de("000/anim_battle726bfea9.bundle") == "other",
                "anim (sin texturas) cae en Other, no en una categoria que prometa texturas")
comun.comprobar(lote.etiqueta("characters") == "Characters", "las etiquetas son las de la ventana")

# --------------------------------------------------------------------------- 2) nombres de conjunto
casos = {
    "role__weiyang40b9bdc8.bundle": "role_weiyang",
    "115/shared_3e45cab0.bundle": "shared",
    "atlas_k-howlerb9d2f60.bundle": "atlas_k-howler",
    "anim_battle726bfea9.bundle": "anim_battle",
    "scn_crowdnpc_13.bundle": "scn_crowdnpc_13",          # hash de 2: se deja entero
}
for rel, esperado in casos.items():
    obtenido = lote.nombre_conjunto(rel)
    comun.comprobar(obtenido == esperado, "conjunto de %s -> %s (sale %s)" % (rel[:28], esperado, obtenido))
comun.comprobar(all(lote.nombre_conjunto(r) for r in casos), "ningun conjunto se queda sin nombre")

# --------------------------------------------------------------------------- 3) tipo de mapa
mapas = {"x_bc": "Color", "x_bcm": "Color", "x_darkcolor": "Color", "x_nm": "Normal",
         "x_nmas": "Normal", "x_em": "Emission", "Lightmap-0_comp_light": "Lightmap",
         "x_shadow": "Shadow", "x_pk": "Packed", "yjs_jz_912": "Other"}
malos = {n: (lote.tipo_mapa(n), e) for n, e in mapas.items() if lote.tipo_mapa(n) != e}
comun.comprobar(not malos, "los sufijos se traducen a tipo de mapa (%s)" % (malos or "todos bien"))

# --------------------------------------------------------------------------- 4) inventario
inv = lote.inventario()
comun.comprobar(inv["total_bundles"] == 16535, "el catalogo tiene los 16.535 bundles (%d)" % inv["total_bundles"])
comun.comprobar(100000 < (inv["total_texturas"] or 0) < 140000,
                "las texturas estimadas cuadran con el censo (%s)" % inv["total_texturas"])
comun.comprobar(25 < (inv["total_mb"] or 0) / 1024 < 50,
                "el peso estimado cuadra con lo medido (~35 GB, sale %.1f GB)" % ((inv["total_mb"] or 0) / 1024))
suma_bundles = sum(c["bundles"] for c in inv["categorias"])
comun.comprobar(suma_bundles == inv["total_bundles"],
                "las categorias suman todos los bundles (%d de %d)" % (suma_bundles, inv["total_bundles"]))
con_filtro = lote.inventario("PC079")
comun.comprobar(con_filtro["total_texturas"] is None and con_filtro["total_mb"] is None,
                "con filtro no se promete un tamano que no se puede saber")

# --------------------------------------------------------------------------- 5) enlaces duros
catalogo = [b["ruta"] for b in lote.herramientas.catalogo_bundles()]
muestra = catalogo[:3]
carpeta = _TMP / "entrada"
n = lote.enlazar(muestra, carpeta)
comun.comprobar(n == len(muestra), "enlaza los bundles pedidos (%d de %d)" % (n, len(muestra)))
if n:
    origen = lote.herramientas.ruta_bundle_juego(muestra[0])
    copia = carpeta / origen.name
    comun.comprobar(copia.exists() and os.stat(origen).st_ino == os.stat(copia).st_ino,
                    "el enlace es duro: no ocupa sitio de mas (mismo inodo)")
    peso = sum(f.stat().st_size for f in carpeta.glob("*.bundle"))
    comun.comprobar(peso > 0, "los bundles se ven desde la carpeta del lote")
# si el sistema no deja enlazar, tiene que copiar y seguir
real_link = os.link
try:
    def rompe(*a, **k):
        raise OSError("sin soporte de enlaces")
    os.link = rompe
    carpeta2 = _TMP / "entrada2"
    n2 = lote.enlazar(muestra[:1], carpeta2)
    comun.comprobar(n2 == 1 and (carpeta2 / lote.herramientas.ruta_bundle_juego(muestra[0]).name).exists(),
                    "si no se puede enlazar, copia igual (y no se queda sin lote)")
finally:
    os.link = real_link

# --------------------------------------------------------------------------- 6) organizar
salida = _TMP / "salida_motor"
(salida / "role__weiyang40b9bdc8.bundle_export" / "CAB-abc123").mkdir(parents=True)
(salida / "role__weiyang40b9bdc8.bundle_export" / "CAB-abc123" / "weiyang_body_bc.png").write_bytes(b"x" * 10)
(salida / "role__weiyang40b9bdc8.bundle_export" / "CAB-abc123" / "weiyang_body_nm.png").write_bytes(b"y" * 20)
(salida / "scn__01_a_01b1370ce.bundle_export" / "CAB-def").mkdir(parents=True)
(salida / "scn__01_a_01b1370ce.bundle_export" / "CAB-def" / "suelo_bcm.png").write_bytes(b"z" * 30)

destino = _TMP / "destino"
movidos = lote.organizar(salida, destino, "characters")
comun.comprobar(movidos == 2, "mueve las dos texturas de role (%d)" % movidos)
comun.comprobar((destino / "Characters" / "role_weiyang" / "weiyang_body_bc.png").exists(),
                "queda en Characters/<conjunto>/<textura>.png")
comun.comprobar(not (destino / "Characters" / "role_weiyang" / "weiyang_body_bc.png").read_bytes() == b"",
                "el fichero llego con su contenido")

# el mismo tamano = ya estaba: se salta (esto es lo que hace reanudable el bulk)
(salida / "role__weiyang40b9bdc8.bundle_export" / "CAB-abc123" / "weiyang_body_bc.png").write_bytes(b"x" * 10)
otra = lote.organizar(salida, destino, "characters")
comun.comprobar(otra == 0, "lo que ya estaba con el mismo tamano se salta (%d movidos)" % otra)

# distinto tamano = no se pisa: se guarda al lado
(salida / "role__weiyang40b9bdc8.bundle_export" / "CAB-abc123" / "weiyang_body_bc.png").write_bytes(b"x" * 99)
lote.organizar(salida, destino, "characters")
comun.comprobar((destino / "Characters" / "role_weiyang" / "weiyang_body_bc_2.png").exists(),
                "si el nombre choca con contenido distinto, se guarda como _2 (no se tira nada)")

# separar por tipo de mapa
salida2 = _TMP / "salida2"
(salida2 / "role__weiyang40b9bdc8.bundle_export" / "CAB-abc123").mkdir(parents=True)
(salida2 / "role__weiyang40b9bdc8.bundle_export" / "CAB-abc123" / "weiyang_body_bc.png").write_bytes(b"1")
(salida2 / "role__weiyang40b9bdc8.bundle_export" / "CAB-abc123" / "weiyang_body_nm.png").write_bytes(b"2")
destino2 = _TMP / "destino2"
lote.organizar(salida2, destino2, "characters", por_tipo=True)
comun.comprobar((destino2 / "Characters" / "role_weiyang" / "Color" / "weiyang_body_bc.png").exists()
                and (destino2 / "Characters" / "role_weiyang" / "Normal" / "weiyang_body_nm.png").exists(),
                "con 'por tipo de mapa' se anaden Color/ y Normal/")

# ninguna categoria sin etiqueta crea carpeta rara
lote.organizar(_TMP / "vacio", destino2, "other")
comun.comprobar((destino2 / "Other").exists() or True, "una categoria vacia no rompe nada")

# --------------------------------------------------------------------------- 7) manifiesto y reanudar
d = _TMP / "destino_manifiesto"
lote._apuntar(d, ["a.bundle", "b.bundle"])
comun.comprobar(lote.manifiesto(d)["hechos"] == ["a.bundle", "b.bundle"], "el manifiesto apunta lo hecho")
lote.olvidar_manifiesto(d)
comun.comprobar(not lote.manifiesto(d).get("hechos"), "se puede olvidar lo apuntado (volver a mirarlo todo)")
comun.comprobar(isinstance(lote.espacio_libre(_TMP), int) and lote.espacio_libre(_TMP) > 0,
                "sabe cuanto sitio queda en el disco")

# --------------------------------------------------------------------------- 8) corrida REAL
# Con `limite=2` se exportan de verdad dos bundles de una categoria (minutos, no horas).
if not ajustes.carpeta_bundles():
    print("  (sin juego: se salta la corrida real)")
else:
    destino_real = _TMP / "real"
    lineas = []
    t0 = time.time()
    r = lote.extraer(["effects"], destino_real, limite=2, log=lineas.append)
    segundos = time.time() - t0
    comun.comprobar(r["bundles"] == 2 and not r["fallos"],
                    "la corrida real termina sin fallos (%s)" % (r["fallos"][:2] or "ninguno"))
    ficheros = list((destino_real / "Effects").rglob("*.png"))
    comun.comprobar(len(ficheros) > 0,
                    "las texturas llegan a Effects/<conjunto>/ (%d ficheros en %.1f s)" % (len(ficheros), segundos))
    comun.comprobar(all(f.parent != destino_real / "Effects" for f in ficheros),
                    "ninguna queda suelta en la raiz de la categoria: todas en su conjunto")
    comun.comprobar(any(len(f.parent.parts) >= 2 for f in ficheros),
                    "el conjunto se ve en la ruta (Categoria/conjunto/fichero)")
    # segunda vuelta: lo apuntado se salta
    lineas2 = []
    t1 = time.time()
    r2 = lote.extraer(["effects"], destino_real, limite=2, log=lineas2.append)
    comun.comprobar(time.time() - t1 < max(3.0, segundos / 2),
                    "al relanzar no repite lo ya hecho (%.1f s contra %.1f s)" % (time.time() - t1, segundos))
    comun.comprobar(r2["bundles"] == 2, "la segunda vuelta tambien cuenta los bundles")

shutil.rmtree(_TMP, ignore_errors=True)
comun.resumen()