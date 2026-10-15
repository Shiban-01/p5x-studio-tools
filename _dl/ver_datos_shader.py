
import re
import UnityPy
B = r"C:\Users\Lukas\p5x-datamining\game_dump\fileContentOut\Bundles\Windows\106\shaders.bundle"
env = UnityPy.load(B)
chico = [o for o in env.objects if o.type.name == "Shader" and len(o.get_raw_data()) < 60000][:2]
for o in chico:
    raw = o.get_raw_data()
    print("path_id", o.path_id, "bytes", len(raw))
    print("  primeros 96 bytes:", raw[:96])
    print("  ascii al principio:", re.findall(rb"[\x20-\x7e]{4,40}", raw[:400])[:6])
    print("  nombres en el fichero:", [s for s in re.findall(rb"[\x20-\x7e]{5,60}", raw) if b"/" in s][:8])
