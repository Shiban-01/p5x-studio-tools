"""Prueba de las funciones de datos de herramientas.py (sin abrir ventana)."""
import sys
import time
sys.path.insert(0, r"C:\Users\Lukas\p5x-datamining\p5x_studio")
from p5x_studio import herramientas as H  # noqa: E402

print("=== 1. catalogo de bundles ===")
t0 = time.time()
cat = H.catalogo_bundles()
print("bundles:", len(cat), "en %.2fs" % (time.time() - t0))
print("tipos:", H.tipos_de_bundle()[:8])

print("\n=== 2. explorador: filtro tipo=shared, actor=chord ===")
sel = [b for b in cat if b["tipo"] == "shared" and any("chord" in (a or "").lower() for a in b["actores"])]
print("coincidencias:", len(sel))
for b in sel[:3]:
    print("  ", b["ruta"], b["papel"], len(b["mallas"]), "mallas", len(b["texturas"]), "tex")

print("\n=== 3. buscador global: chord_normal_face_bc ===")
t0 = time.time()
rec = H.indice_recursos()
print("indice de recursos:", len(rec), "en %.2fs" % (time.time() - t0))
hits = [(n, t, r) for (n, t, r) in rec if "chord_normal_face_bc" in (n or "").lower()]
for h in hits:
    print("  ", h)
assert any(r == "110/shared_merged_5c36cff7.bundle" for _, _, r in hits), "no lo encontro!"
print("  -> encontrado en 110/shared_merged_5c36cff7.bundle: OK")

print("\n=== 4. inspector: listar_bundle ===")
t0 = time.time()
filas = H.listar_bundle("110/shared_merged_5c36cff7.bundle", lambda s: None)
print("recursos:", len(filas), "en %.2fs" % (time.time() - t0))
for f in filas[:4]:
    print("  ", f["tipo"], f["nombre"], f["pathid"])

print("\n=== 5. video y audio: listar ===")
m = H.listar_media()
print("carpeta:", m["carpeta"])
print("usm:", len(m["usm"]), " awb:", len(m["awb"]))
print("ejemplo usm:", m["usm"][0]["nombre"] if m["usm"] else None)

print("\n=== 6. herramientas externas ===")
est = H.estado_herramientas()
for k, v in est.items():
    print("  %-10s %s" % (k, v))