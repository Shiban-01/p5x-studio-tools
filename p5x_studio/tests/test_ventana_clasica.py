"""Comprueba la ventana de dependencias de la interfaz CLASICA (la que se usa si no hay WebView2).

Es la que salva al usuario en un equipo sin WebView2, asi que no puede quedarse sin boton.
"""
import sys
import tkinter as tk
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun  # noqa: E402

sys.path.insert(0, "C:/Users/Lukas/p5x-datamining/p5x_studio")
from p5x_studio import dependencias, herramientas  # noqa: E402

comun.comprobar(hasattr(herramientas.PanelHerramientas, "descargar_dependencias"),
                "el panel clasico tiene el boton de dependencias")
comun.comprobar(hasattr(herramientas, "VentanaDependencias"),
                "existe la ventana de dependencias de la clasica")

raiz = tk.Tk()
raiz.withdraw()
try:
    v = herramientas.VentanaDependencias(raiz)
    comun.comprobar(v.consola.cget("state") == "disabled",
                    "la consola arranca de solo lectura (%s)" % v.consola.cget("state"))
    v.append("descargando motor")
    comun.comprobar("descargando motor" in v.consola.get("1.0", "end"),
                    "lo que pasa se ve en la consola")
    comun.comprobar(v.consola.cget("state") == "disabled",
                    "la consola vuelve a quedar de solo lectura")
    comun.comprobar(str(dependencias.peso_aproximado_mb()) in v.peso.cget("text"),
                    "la ventana ensena el peso (%r)" % v.peso.cget("text"))
    entradas = []
    def recorre(w):
        for h in w.winfo_children():
            if isinstance(h, (tk.Entry, tk.Spinbox)):
                entradas.append(h)
            recorre(h)
    recorre(v)
    comun.comprobar(entradas == [], "no hay ningun campo donde escribir (%d)" % len(entradas))
finally:
    raiz.destroy()

comun.resumen()
