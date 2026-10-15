"""Mide la geometria de la interfaz real: construye la ventana y anota las posiciones.

Los widgets miden 1x1 hasta que la ventana se dibuja, asi que hay que llamar a update() antes de
medir (es el fallo clasico de estas comprobaciones).
"""
import sys
import tkinter as tk

sys.path.insert(0, r"C:/Users/Lukas/p5x-datamining/p5x_studio")
from p5x_studio import gui, ajustes  # noqa: E402

raiz = tk.Tk()
app = gui.Aplicacion(raiz)
for _ in range(6):
    raiz.update()

alto_ventana = raiz.winfo_height()
ancho_ventana = raiz.winfo_width()
top = raiz.winfo_rooty()

def rel(w):
    return w.winfo_rooty() - top, w.winfo_rooty() - top + w.winfo_height()

b = app.boton_extraer
y0, y1 = rel(b)
print("VENTANA ancho=%d alto=%d" % (ancho_ventana, alto_ventana))
print("BOTON EXTRAER x=%d..%d  y=%d..%d  (h=%d)" %
      (b.winfo_rootx() - raiz.winfo_rootx(), b.winfo_rootx() - raiz.winfo_rootx() + b.winfo_width(),
       y0, y1, b.winfo_height()))
print("PIE (marco de la barra) y=%s" % (rel(app.boton_extraer.master),))
print("PROGRESO y=%s" % (rel(app.progreso),))
print("CHECKBOXES:")
for k, v in app.opciones.items():
    print("   %-12s = %s" % (k, v.get()))
print("CASILLAS DIBUJADAS (widgets):")
for w in app.opciones:
    pass
# posiciones de las casillas reales: buscarlas por texto no es fiable; se mide el panel de opciones
raiz.destroy()