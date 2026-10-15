
import os, subprocess, sys, time, zipfile, shutil
from pathlib import Path
TMP = Path(os.environ["TMPDIR"]) / "zip_check"
shutil.rmtree(TMP, ignore_errors=True)
TMP.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(r"C:\Users\Lukas\Desktop\P5X-Studio-Tools-1.0.0-beta-win64.zip") as z:
    z.extractall(TMP)
raiz = TMP / "P5X Studio Tools"
print("descomprimido:", sorted(p.name for p in raiz.iterdir()))
sys.path.insert(0, r"C:\Users\Lukas\p5x-datamining\_dl")
from pilotar_exe import Piloto
env = dict(os.environ); env["P5X_STUDIO_UI_CDP"] = "9227"
proc = subprocess.Popen([str(raiz / "P5X Studio Tools.exe")], cwd=str(raiz), env=env,
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    time.sleep(16)
    with Piloto(9227) as p:
        print("titulo:", p.js("document.title"))
        print("pestanas:", p.js("document.querySelectorAll('#nav button').length"))
        print("bundles desde el disco:", p.js("document.querySelector('#foot-index') ? 'hay' : 'no'"))
        p.js("ir('bulk')"); time.sleep(2)
        print("pestana del bulk:", p.visible("#p-bulk"))
        print("filas de categorias:", p.filas("#bulk-categorias tr"))
        print("estimado:", p.texto("#bulk-estimado"))
        print("errores JS:", p.errores_js())
        # ni un rastro de rutas del equipo del autor dentro del .exe
        print("sin rutas del equipo en el binario:",
              b"C:\\Users\\Lukas\\p5x-datamining" not in (raiz / "P5X Studio Tools.exe").read_bytes())
finally:
    proc.terminate()
    try: proc.wait(timeout=10)
    except subprocess.TimeoutExpired: proc.kill()
shutil.rmtree(TMP, ignore_errors=True)
