"""Brute-force de la clave ASM (assetbundle encryption) de P5X via UnityPy."""
import UnityPy
from UnityPy.helpers import ArchiveStorageManager as ASM

UnityPy.config.FALLBACK_UNITY_VERSION = "2022.3.49f1"
META = r"C:/Users/Lukas/p5x-datamining/il2cpp/in2/global-metadata.dat"
BUNDLE = r"C:/Users/Lukas/p5x-datamining/_dl/scene_stage/role_i_wonder49ad32e2.bundle"

env = UnityPy.load(BUNDLE) if False else None
# leer firmas del bundle
with open(BUNDLE, "rb") as f:
    head = f.read(4096)
i = head.find(b"UnityFS")
print("UnityFS@", i)

key = ASM.brute_force_key(META,
    key_sig=b"\x00\x09\x1c\x00\x00\x1a\x00\xf0\x18\x00\x04CAB-2",
    data_sig=b"\x00\x01\x00\xb1\x01\x00\x01\x00\xb0\x00\x00Y\x90\x00\x03\x0e")
print("KEY:", key)
UnityPy.set_assetbundle_decrypt_key(key)
env = UnityPy.load(BUNDLE)
from collections import Counter
print(Counter(o.type.name for o in env.objects))
