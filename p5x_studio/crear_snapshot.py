import sys, json
sys.path.insert(0, ".")
from p5x_studio import motor

bundles = motor.listar_bundles()
snapshot = {}
for b in bundles:
    nombre = b.get("fichero", b.get("id", ""))
    snapshot[nombre] = {
        "id": b.get("id", ""),
        "tipo": b.get("tipo", ""),
        "mb": b.get("mb", 0),
    }

out = "../_dl/bundles_conocidos.json"
with open(out, "w", encoding="utf-8") as f:
    json.dump(snapshot, f, ensure_ascii=False, indent=1)
print(f"Snapshot creado: {len(snapshot)} bundles -> {out}")
