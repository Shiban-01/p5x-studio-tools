"""Lanza la corrida COMPLETA del bulk (todas las categorias) en la app del escritorio.

Se abre el .exe de verdad con el gancho de CDP, se pulsa el boton y se deja corriendo: el proceso se
suelta del padre (DETACHED), asi que sigue vivo cuando este script termina. El progreso se puede
mirar en la propia ventana (y se puede cancelar ahi mismo; lo hecho queda apuntado y se reanuda).
"""
import os
import subprocess
import sys
import time
from pathlib import Path

ESCRITORIO = Path(r"C:\Users\Lukas\Desktop\P5X Studio Tools")
sys.path.insert(0, r"C:\Users\Lukas\p5x-datamining\_dl")
from pilotar_exe import Piloto  # noqa: E402

entorno = dict(os.environ)
entorno["P5X_STUDIO_UI_CDP"] = "9226"
proc = subprocess.Popen(
    [str(ESCRITORIO / "P5X Studio Tools.exe")], cwd=str(ESCRITORIO), env=entorno,
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
)
print("app lanzada (pid %d)" % proc.pid)
time.sleep(18)

with Piloto(9226) as p:
    p.js("ir('bulk')")
    time.sleep(2)
    print("pestana del bulk:", p.visible("#p-bulk"))
    print("filas:", p.filas("#bulk-categorias tr"))
    marcadas = p.js("(() => [...document.querySelectorAll('#bulk-categorias input[data-cat]:checked')]"
                    ".map(i => i.dataset.cat).join(', '))()")
    print("categorias marcadas:", marcadas)
    print("estimado:", p.texto("#bulk-estimado"))
    print("destino:", p.js("document.querySelector('#bulk-destino').value"))
    print("libre:", p.texto("#bulk-libre"))
    p.pulsar("#bulk-empezar")
    print("\n--- arrancada, primeros 90 s ---")
    for i in range(9):
        time.sleep(10)
        print("  t=%ds  %s | %s" % (10 * (i + 1), p.texto("#bulk-estado").strip()[:40],
                                    (p.texto("#bulk-consola").strip().splitlines() or ["-"])[-1][:70]))
    ancho = p.js("document.querySelector('#bulk-prog-i').style.width")
    print("\nbarra de progreso: %s" % ancho)
    print("consola (ultimas lineas):")
    for l in p.texto("#bulk-consola").strip().splitlines()[-4:]:
        print("   %s" % l)
    print("errores JS:", p.errores_js())

print("\nla app se queda corriendo (este script no la cierra)")