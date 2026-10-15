"""Verifica que la EXTRACCION DE SIEMPRE sigue funcionando, dirigida desde la interfaz.

Abre la app de verdad (con la comprobacion de estado real, usando mainloop como en produccion),
espera al indice, elige un personaje pequeno en la lista y pulsa Extraer.
"""
import json
import sys
import time
from pathlib import Path
import tkinter as tk

sys.path.insert(0, r"C:\Users\Lukas\p5x-datamining\p5x_studio")
from p5x_studio import ajustes, dependencias, gui  # noqa: E402

ajustes.preparar_carpetas()
gui.messagebox.showinfo = lambda *a, **k: None       # sin dialogos modales en la prueba
gui.messagebox.showwarning = lambda *a, **k: None
# la comprobacion de librerias consulta PyPI (timeout 900 s sin red): se salta SOLO eso,
# el resto de comprobar_todo (juego, indice, Unity) se ejecuta de verdad.
dependencias.asegurar_dependencias = lambda progreso=None: dependencias.python_entorno()

raiz = tk.Tk()
app = gui.Aplicacion(raiz)
ESTADO = {"t0": time.time()}

print("pestanas:", [app.cuaderno.tab(t, "text") for t in app.cuaderno.tabs()])


def esperar_indice():
    if app.datos_indice is not None:
        print("indice cargado: %d personajes, catalogo %d entradas"
              % (len(app.personajes), len(app.mostrar)))
        return elegir()
    if time.time() - ESTADO["t0"] > 180:
        print("TIMEOUT esperando el indice")
        print(app.registro.get("1.0", "end"))
        return raiz.quit()
    raiz.after(300, esperar_indice)


def elegir():
    objetivo = "c1006"
    app.filtrar()
    idx = next((i for i, p in enumerate(app.mostrar) if p["id"] == objetivo), None)
    if idx is None:
        idx = 0
    app.lista.selection_clear(0, "end")
    app.lista.selection_set(idx)
    app.mostrar_detalle()
    p = app.mostrar[idx]
    ESTADO["p"] = p
    print("elegido:", p["etiqueta"], "| categoria:", p.get("categoria"),
          "| ficheros:", p["ficheros"])
    # opciones: geometria + texturas + materiales; sin esqueleto (Unity), fbx ni vistas previas
    for k, v in app.opciones.items():
        v.set(k in ("mallas", "texturas", "materiales"))
    ESTADO["t1"] = time.time()
    app.extraer()
    raiz.after(500, esperar_fin)


def esperar_fin():
    if (not app.trabajando) and app.ultima_carpeta:
        salida = Path(app.ultima_carpeta)
        print("extraccion terminada en %.1fs" % (time.time() - ESTADO["t1"]))
        print("DESTINO:", salida)
        res = json.loads((salida / "SUMMARY.json").read_text(encoding="utf-8"))
        nm = sum(len(v["mallas"]) for v in res["partes"].values())
        nt = sum(len(v["texturas"]) for v in res["partes"].values())
        print("RESUMEN: %d mallas, %d texturas, fbx=%s" % (nm, nt, res.get("fbx")))
        archivos = [f for f in salida.rglob("*") if f.is_file()]
        print("FICHEROS: %d, OCUPA: %.1f MB" % (
            len(archivos), sum(f.stat().st_size for f in archivos) / 1048576))
        for f in sorted(archivos)[:16]:
            print("   ", f.relative_to(salida))
        print("README:", (salida / "README.md").is_file())
        return raiz.quit()
    if (not app.trabajando) and not app.ultima_carpeta:
        print("la extraccion no dio resultado")
        print(app.registro.get("1.0", "end"))
        return raiz.quit()
    if time.time() - ESTADO["t1"] > 300:
        print("TIMEOUT en la extraccion")
        return raiz.quit()
    raiz.after(500, esperar_fin)


raiz.after(500, esperar_indice)
raiz.mainloop()
print("OK")