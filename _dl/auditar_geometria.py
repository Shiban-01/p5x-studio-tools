"""Auditoria de geometria: ningun widget mapeado de la app debe salirse de la ventana."""
import sys
import tkinter as tk
sys.path.insert(0, r"C:\Users\Lukas\p5x-datamining\p5x_studio")
from p5x_studio import ajustes, gui  # noqa: E402

ajustes.preparar_carpetas()
gui.Aplicacion.comprobar_todo = lambda self: None
raiz = tk.Tk()
app = gui.Aplicacion(raiz)
raiz.update_idletasks()
raiz.update()
p = app.panel_herramientas
p.explorar()
raiz.update_idletasks()
raiz.update()


def caja_abs(w):
    # coordenadas RELATIVAS a la ventana (se suma hasta el hijo del toplevel, sin su offset de
    # pantalla; si no, winfo_x del root (su posicion en pantalla) contamina la medida)
    x = y = 0
    q = w
    while q is not None and q is not raiz:
        x += q.winfo_x()
        y += q.winfo_y()
        q = q.master
    return x, y, x + w.winfo_width(), y + w.winfo_height()


def todos(w):
    yield w
    for c in w.winfo_children():
        yield from todos(c)


def auditar(nombre):
    W, H = raiz.winfo_width(), raiz.winfo_height()
    fuera = []
    for w in todos(raiz):
        if not w.winfo_ismapped():
            continue
        try:
            x0, y0, x1, y1 = caja_abs(w)
        except tk.TclError:
            continue
        if x0 < 0 or y0 < 0 or x1 > W or y1 > H:
            fuera.append((str(w), w.winfo_class(), (x0, y0, x1, y1)))
    print("%-14s ventana %dx%d -> %s" % (nombre, W, H,
                                         "TODO DENTRO" if not fuera else "%d FUERA" % len(fuera)))
    for f in fuera[:12]:
        print("      FUERA:", f)


auditar("Extraccion")
for tab, nombre in ((p.tab_explorador, "Explorador"), (p.tab_inspector, "Inspector"),
                    (p.tab_buscador, "Buscador"), (p.tab_texturas, "Texturas"),
                    (p.tab_media, "Video/audio")):
    app.cuaderno.select(app.pestana_herramientas)
    p.cuaderno.select(tab)
    raiz.update_idletasks()
    raiz.update()
    auditar(nombre)

# el boton extraer, con la ventana en su tamano real
app.cuaderno.select(app.pestana_extraccion)
raiz.update_idletasks()
raiz.update()
print("boton extraer (abs):", caja_abs(app.boton_extraer))
raiz.destroy()