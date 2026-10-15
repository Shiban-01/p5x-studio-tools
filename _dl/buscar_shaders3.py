
import subprocess, sys, xml.etree.ElementTree as ET
from pathlib import Path
from collections import Counter
sys.path.insert(0, r"C:\Users\Lukas\p5x-datamining\p5x_studio")
from p5x_studio import herramientas
D = Path(r"C:\Users\Lukas\Downloads\P5X\Client\pc\P5X_Data")
sal = Path(r"C:\Users\Lukas\AppData\Local\hermes\cache\scratch\listas")
sal.mkdir(parents=True, exist_ok=True)
for f in ["globalgamemanagers.assets", "sharedassets0.assets", "level0", "level1"]:
    p = D / f
    if not p.exists():
        print(f, "-> no existe"); continue
    x = sal / (f + ".xml")
    x.unlink(missing_ok=True)
    r = subprocess.run([str(herramientas._ruta_motor()), str(p), "-m", "info", "--export-asset-list", "xml",
                        "-o", str(sal), "--log-level", "Error", "--unity-version", herramientas.UNITY],
                       capture_output=True, text=True, timeout=600)
    # el motor escribe assets.xml: lo renombro si hace falta
    auto = sal / "assets.xml"
    if auto.exists():
        auto.replace(x)
    if not x.exists():
        print(f, "-> sin lista:", (r.stdout or r.stderr)[-200:]); continue
    raiz = ET.parse(str(x)).getroot()
    filas = [( (a.findtext("Type") or "").strip(), (a.findtext("Name") or "").strip()) for a in raiz.findall("Asset")]
    print("%-28s %5d assets  %s" % (f, len(filas), dict(Counter(t for t, _ in filas).most_common(6))))
    for t, n in filas:
        if t in ("Shader", "Material"):
            print("      %-9s %s" % (t, n))
