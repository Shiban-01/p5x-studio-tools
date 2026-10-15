"""Calcula/guarda la clave de descifrado de bundles (Unity 2022 ArchiveStorage) para uso propio.

No escribe en la app: guarda el resultado en _dl/clave_bundles.json.
"""
import json
import sys
import time
from pathlib import Path

import UnityPy
from UnityPy.helpers.ArchiveStorageManager import brute_force_key

METADATA = r"C:\Users\Lukas\Downloads\P5X\Client\pc\P5X_Data\il2cpp_data\Metadata\global-metadata.dat"
SALIDA = Path(r"C:\Users\Lukas\p5x-datamining\_dl\clave_bundles.json")
KEY_SIG = b"\n\x00$1#\n\x00$,\xc1\n\x00$7\xd3\n"
DATA_SIG = b"\x00\x01\x00\xc2\x06\xd1\x00\x02\x00\x00\x00\x01\x00\xb8\x00\x03"

if SALIDA.exists():
    clave = bytes(json.loads(SALIDA.read_text(encoding="utf-8"))["clave"])
    print("clave ya guardada:", clave.hex())
else:
    print("buscando clave (puede tardar)...", flush=True)
    t0 = time.time()
    clave = brute_force_key(METADATA, KEY_SIG, DATA_SIG)
    print("clave:", clave.hex() if clave else None, "(%.0f s)" % (time.time() - t0), flush=True)
    if not clave:
        raise SystemExit("no se encontro la clave")
    SALIDA.write_text(json.dumps({"clave": list(clave)}), encoding="utf-8")

UnityPy.set_assetbundle_decrypt_key(clave)
UnityPy.config.FALLBACK_UNITY_VERSION = "2022.3.49f1"

# comprobar con el bundle del bust-up de xiachuanling
for rel in ("076/uitex_changfu512a3bdb.bundle", "026/uitex_uaidaofu552d57a7.bundle"):
    ruta = r"C:\Users\Lukas\Downloads\P5X\Client\OuterPackage\Bundles\Windows\\" + rel.replace("/", "\\")
    env = UnityPy.load(ruta)
    from collections import Counter
    print(rel, "->", len(env.objects), dict(Counter(o.type.name for o in env.objects)))