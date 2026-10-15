"""Comprueba el paso del bulk sobre el .exe PUBLICADO (el del escritorio), sin borrar nada.

Es la comprobacion que quedo mal escrita en la prueba de fuego (miraba la carpeta entera, y en
`extracted/textures/` tambien escribe la herramienta de texturas de UN bundle, que las deja sueltas).
Aqui solo se mira lo que escribe el bulk: `extracted/textures/<Categoria>/<conjunto>/*.png`.
"""
import os
import subprocess
import sys
import time
from pathlib import Path

ESCRITORIO = Path(r"C:\Users\Lukas\Desktop\P5X Studio Tools")
sys.path.insert(0, r"C:\Users\Lukas\p5x-datamining\_dl")
from pilotar_exe import Piloto  # noqa: E402

FALLOS = []


def paso(que, bien, extra=""):
    print(("  ok    " if bien else "  FALLA ") + que + ("   [%s]" % extra if extra else ""))
    if not bien:
        FALLOS.append(que)


entorno = dict(os.environ)
entorno.update({"P5X_STUDIO_UI_CDP": "9225", "P5X_STUDIO_BULK_LIMITE": "2"})
proc = subprocess.Popen([str(ESCRITORIO / "P5X Studio Tools.exe")], cwd=str(ESCRITORIO), env=entorno,
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    time.sleep(16)
    with Piloto(9225) as p:
        paso("la ventana del .exe abre", bool(p.js("document.title")))
        p.js("ir('bulk')")
        time.sleep(2)
        paso("la pestana del bulk esta en el .exe publicado", p.visible("#p-bulk"))
        filas = p.filas("#bulk-categorias tr")
        suma = p.js("(() => [...document.querySelectorAll('#bulk-categorias tr')]"
                    ".reduce((a, r) => a + parseInt(r.children[2].textContent.replace(/,/g, ''), 10), 0))()")
        paso("la tabla suma los 16.535 bundles", suma == 16535, "%d filas, %s" % (filas, suma))
        p.pulsar("#bulk-todo")
        p.js('''(() => { const i = document.querySelector('#bulk-categorias input[data-cat="effects"]');
                     i.checked = true; i.dispatchEvent(new Event('change'));
                     document.querySelector('#bulk-reanudar').checked = false; return true; })()''')
        time.sleep(0.5)
        p.pulsar("#bulk-empezar")
        for _ in range(60):
            time.sleep(5)
            if p.js("document.querySelector('#bulk-empezar').disabled === false"):
                break
        carpeta = ESCRITORIO / "extracted" / "textures"
        propias = sorted((carpeta / "Effects").rglob("*.png")) if (carpeta / "Effects").exists() else []
        paso("extrae de verdad y las deja en el disco", len(propias) > 0, "%d PNG" % len(propias))
        paso("ordenadas en <Categoria>/<conjunto>/",
             bool(propias) and all(len(f.relative_to(carpeta).parts) >= 3 for f in propias),
             str(propias[0].relative_to(carpeta)) if propias else "-")
        paso("ninguna suelta en la raiz de la categoria (todas dentro de su conjunto)",
             all(f.parent != carpeta / "Effects" for f in propias))
        print("      ejemplo: %s" % (str(propias[0].relative_to(carpeta)) if propias else "-"))
        consola = p.texto("#bulk-consola")
        paso("la consola va en ingles", " de " not in consola,
             consola.strip().splitlines()[-1][:60] if consola.strip() else "")
        paso("avisa del final", "Done" in p.texto("#bulk-estado"), p.texto("#bulk-estado").strip()[:40])
        paso("sin errores de JavaScript", p.errores_js() == [], p.errores_js())
finally:
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()

print("\n" + ("TODO BIEN" if not FALLOS else "%d FALLOS: %s" % (len(FALLOS), FALLOS)))
sys.exit(1 if FALLOS else 0)