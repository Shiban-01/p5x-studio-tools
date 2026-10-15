"""Saca la clave de descifrado de los bundles a partir de global-metadata.dat del juego.

Los bundles de P5X vienen cifrados con la proteccion tipica de Unity: la clave se deriva del
global-metadata.dat del cliente. UnityPy la puede buscar por fuerza bruta con las firmas que el
propio error proporciona. Una vez obtenida se guarda, porque no cambia entre arranques.
"""
import json
import os
import time

import UnityPy
from UnityPy.helpers.ArchiveStorageManager import brute_force_key

METADATA = r"C:\Users\Lukas\Downloads\P5X\Client\pc\P5X_Data\il2cpp_data\Metadata\global-metadata.dat"
BUNDLE = r"C:\Users\Lukas\Downloads\P5X\Client\OuterPackage\Bundles\Windows\145\part_pc079_011ef29087.bundle"
SAL = r"C:\Users\Lukas\p5x-datamining\_dl\indice\clave_bundles.json"

KEY_SIG = b"\n\x00$1#\n\x00$,\xc1\n\x00$7\xd3\n"
DATA_SIG = b"\x00\x01\x00\xc2\x06\xd1\x00\x02\x00\x00\x00\x01\x00\xb8\x00\x03"

print("metadata: %s (%d MB)" % (os.path.basename(METADATA),
                                os.path.getsize(METADATA) / 1048576))
t0 = time.time()
with open(METADATA, "rb") as fp:
    clave = brute_force_key(fp, KEY_SIG, DATA_SIG)
print("clave obtenida en %.1f s: %r" % (time.time() - t0, clave))

UnityPy.set_assetbundle_decrypt_key(clave)
UnityPy.config.FALLBACK_UNITY_VERSION = "2022.3.49f1"

env = UnityPy.load(BUNDLE)
print("\nobjetos en el bundle: %d" % len(env.objects))
por_tipo = {}
for obj in env.objects:
    por_tipo[obj.type.name] = por_tipo.get(obj.type.name, 0) + 1
for t, n in sorted(por_tipo.items(), key=lambda x: -x[1])[:12]:
    print("   %-22s %d" % (t, n))

os.makedirs(os.path.dirname(SAL), exist_ok=True)
with open(SAL, "w", encoding="utf-8") as f:
    json.dump({"clave": list(clave), "metadata": METADATA}, f)
print("\nclave guardada en %s" % SAL)