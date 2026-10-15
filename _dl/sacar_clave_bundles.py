"""Saca la clave de descifrado de los bundles (Unity 2022 ArchiveStorage) desde global-metadata.dat.

Los bundles de P5X van cifrados con el esquema nuevo de UnityFS. La clave se deriva del
`global-metadata.dat` de IL2CPP (UnityPy sabe buscarla). Una vez sacada, se guarda para no repetir la
busqueda y se comprueba abriendo un bundle de verdad.
"""
import time
from pathlib import Path

import UnityPy
from UnityPy.helpers.ArchiveStorageManager import brute_force_key, set_assetbundle_decrypt_key

METADATA = r"C:\Users\Lukas\Downloads\P5X\Client\pc\P5X_Data\il2cpp_data\Metadata\global-metadata.dat"
BUNDLE = r"C:\Users\Lukas\Downloads\P5X\Client\OuterPackage\Bundles\Windows\106\shaders.bundle"
GUARDADA = Path(r"C:\Users\Lukas\p5x-datamining\_dl\clave_bundles.txt")

if GUARDADA.exists():
    clave = bytes.fromhex(GUARDADA.read_text().strip())
    print("clave ya guardada:", clave.hex())
else:
    print("buscando la clave en global-metadata.dat (puede tardar)...", flush=True)
    t0 = time.time()
    # las dos firmas las calcula UnityPy a partir del propio bundle cifrado y las imprime en el error
    key_sig = b"\x00#\xa8\xe9\x0a\x005\x01y\x1a\x0a\x00\x15\xc5\x0a\x00"
    data_sig = b"\x00\x01\x00@\x03Z\x00\x02\x08\x00B\x87\xb7\x00\x03\x0a"
    clave = brute_force_key(METADATA, key_sig, data_sig)
    print("clave: %s   (%.0f s)" % (clave.hex() if clave else None, time.time() - t0))
    if clave:
        GUARDADA.write_text(clave.hex())

if clave:
    set_assetbundle_decrypt_key(clave)
    from collections import Counter
    env = UnityPy.load(BUNDLE)
    print("bundle abierto:", len(env.objects), "objetos ->", dict(Counter(o.type.name for o in env.objects)))
    for o in env.objects:
        d = o.read()
        print("   %-12s %s" % (o.type.name, getattr(d, "m_Name", "?"))[:100])