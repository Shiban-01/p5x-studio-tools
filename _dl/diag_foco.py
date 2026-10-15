"""Comprueba si mover el foco al Combobox (o a su parte entry) vacia la seleccion del Listbox."""
import sys
sys.path.insert(0, r"C:/Users/Lukas/p5x-datamining/p5x_studio")
import tkinter as tk
from p5x_studio import ajustes, gui
ajustes.preparar_carpetas()
gui.Aplicacion.comprobar_todo = lambda self: None
raiz = tk.Tk(); app = gui.Aplicacion(raiz)
raiz.geometry("1020x701+0+0"); raiz.update()
app._catalogo=None; app._asegurar_catalogo(); app.datos_indice={"ok":True}; app.filtrar(); raiz.update()
app.entrada_busqueda.delete(0,"end"); app.entrada_busqueda.insert(0,"skull"); app.filtrar(); raiz.update()
lb = app.lista
lb.selection_set(0); lb.activate(0); raiz.update()
print("sel base:", lb.curselection())
# 1) foco a la entrada de busqueda
app.entrada_busqueda.focus_set(); raiz.update()
print("foco en entrada_busqueda:", lb.curselection())
lb.selection_set(0); raiz.update()
# 2) foco al combobox de traje
app.combo_traje.focus_set(); raiz.update()
print("foco en combo_traje:", lb.curselection())
lb.selection_set(0); raiz.update()
# 3) foco al combobox de idioma
app.combo_idioma.focus_set(); raiz.update()
print("foco en combo_idioma:", lb.curselection())
lb.selection_set(0); raiz.update()
# 4) foco a la categoria
app.combo_categoria.focus_set(); raiz.update()
print("foco en combo_categoria:", lb.curselection())
lb.selection_set(0); raiz.update()
# 5) abrir el popdown del traje (evento)
app.combo_traje.event_generate("<Button-1>"); raiz.update()
print("popdown abierto:", lb.curselection())
# 6) seleccionar en el popdown y cerrarlo
pop = str(app.combo_traje.tk.call("ttk::combobox::PopdownWindow", app.combo_traje)) + ".f.l"
app.combo_traje.tk.call(pop, "selection", "set", 1); raiz.update()
print("tras marcar en popdown:", lb.curselection())
app.combo_traje.event_generate("<Escape>"); raiz.update()
print("tras cerrar popdown:", lb.curselection())
raiz.destroy()