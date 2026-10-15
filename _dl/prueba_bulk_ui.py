"""Prueba de punta a punta del bulk pasando por la VENTANA (no por Python a pelo).

Arranca la app de verdad con el gancho de CDP, entra en la pestana nueva, comprueba la tabla de
categorias con los numeros reales, marca solo Effects, lanza la extraccion (con
P5X_STUDIO_BULK_LIMITE=2 para que tarde segundos) y mira lo que ha quedado en el disco.
"""
import shutil
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(r"C:\Users\Lukas\p5x-datamining\p5x_studio")
sys.path.insert(0, r"C:\Users\Lukas\p5x-datamining\_dl")
from pilotar_exe import Piloto  # noqa: E402

DESTINO = RAIZ / "extracted" / "textures"
fallos = []


def paso(que, bien, extra=""):
    print(("  ok    " if bien else "  FALLA ") + que + ("   [%s]" % extra if extra else ""))
    if not bien:
        fallos.append(que)


PY = RAIZ / ".venv" / "Scripts" / "python.exe"
entorno = dict(__import__("os").environ)
entorno.update({"P5X_STUDIO_UI": "web", "P5X_STUDIO_UI_CDP": "9224", "P5X_STUDIO_BULK_LIMITE": "2"})
proc = subprocess.Popen([str(PY), "-c", "from p5x_studio import ui; ui.arrancar()"], cwd=str(RAIZ),
                        env=entorno, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
try:
    time.sleep(16)
    with Piloto(9224) as p:
        print("1) LA PESTANA")
        p.pulsar('button[data-p="bulk"]')
        time.sleep(2)
        paso("la pestana abre", p.visible("#p-bulk"))
        filas = p.filas("#bulk-categorias tr")
        paso("salen las categorias", filas >= 6, "%d filas" % filas)
        print("      tabla: %s" % p.js(
            "(() => [...document.querySelectorAll('#bulk-categorias tr')].map(r => "
            "[...r.children].map(c => c.textContent.trim()).join(' | ')).join(' /// '))()")[:330])
        # los bundles por categoria tienen que sumar los 16.535 del catalogo
        suma = p.js("""(() => [...document.querySelectorAll('#bulk-categorias tr')]
              .reduce((a, r) => a + parseInt(r.children[2].textContent.replace(/,/g, ''), 10), 0))()""")
        paso("los bundles por categoria suman los 16.535 del catalogo", suma == 16535, str(suma))
        est = p.texto("#bulk-estimado")
        paso("dice el tamano estimado", "Estimated" in est and "MB" in est, est[:60])
        print("      destino: %s" % p.js("document.querySelector('#bulk-destino').value"))
        print("      libre:   %s" % p.texto("#bulk-libre"))
        paso("trae puesto el destino por defecto",
             "extracted" in (p.js("document.querySelector('#bulk-destino').value") or ""),
             p.js("document.querySelector('#bulk-destino').value"))
        paso("ensena el sitio libre del disco", "free" in p.texto("#bulk-libre"),
             p.texto("#bulk-libre")[:50])

        print("\\n2) LA SELECCION")
        p.pulsar("#bulk-todo")            # desmarca todo
        time.sleep(0.4)
        paso("'All' desmarca todo de golpe", not p.js(
            "document.querySelectorAll('#bulk-categorias input[data-cat]:checked').length"))
        p.js("""(() => { const i = document.querySelector('#bulk-categorias input[data-cat="effects"]');
                  i.checked = true; i.dispatchEvent(new Event('change')); return true; })()""")
        time.sleep(0.4)
        paso("marcar Effects actualiza el estimado", "3,788" in p.texto("#bulk-estimado"),
             p.texto("#bulk-estimado")[:60])

        print("\\n3) LA EXTRACCION")
        if DESTINO.exists():
            shutil.rmtree(DESTINO, ignore_errors=True)
        # se destilda "reanudar": el manifiesto ya tiene esos bundles de la pasada anterior y, sin
        # esto, la corrida se los saltaria (que es justo lo que tiene que hacer, pero no lo que
        # queremos medir aqui)
        p.js("(() => { const c = document.querySelector('#bulk-reanudar'); c.checked = false; return true; })()")
        p.pulsar("#bulk-empezar")
        t0 = time.time()
        listo = False
        while time.time() - t0 < 300:
            time.sleep(2)
            if p.js("document.querySelector('#bulk-empezar').disabled === false"):
                listo = True
                break
        paso("la tarea termina sola", listo, "%.0f s" % (time.time() - t0))
        consola = p.texto("#bulk-consola")
        print("      consola: %s" % consola.replace("\\n", " / ")[:300])
        paso("la consola cuenta lo que pasa", "bulk" in consola.lower() or "Effects" in consola, "")
        paso("la consola va en ingles", not any(w in consola.lower() for w in
             (" de ", "listo", "aprox", "ficheros", "hecho:", "descargando")), "")
        estado = p.texto("#bulk-estado")
        paso("avisa del final", "Done" in estado, estado[:70])

        pngs = list(DESTINO.rglob("*.png")) if DESTINO.exists() else []
        paso("los PNG estan en el disco", len(pngs) > 0, "%d ficheros" % len(pngs))
        paso("ordenados por categoria y conjunto",
             all(f.parent.parent != DESTINO for f in pngs) and
             all("Effects" in f.parts for f in pngs),
             str(pngs[0].relative_to(DESTINO)) if pngs else "-")
        p.pulsar("#bulk-abrir")  # no debe reventar (abre el explorador)
        time.sleep(1)

        errores = p.js("(window.__errores || []).length")
        paso("sin errores de JavaScript", not errores, str(errores))
finally:
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()

print("\\n" + ("TODO BIEN" if not fallos else "%d FALLOS: %s" % (len(fallos), fallos)))
sys.exit(1 if fallos else 0)