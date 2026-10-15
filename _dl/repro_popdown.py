"""Reproduccion fiel: la seleccion en el popdown del Combobox (el desplegable real) usa
la seleccion X y, con exportselection=1, vacia la del Listbox de personajes."""
import sys
sys.path.insert(0, r"C:/Users/Lukas/p5x-datamining/p5x_studio")
import tkinter as tk
from p5x_studio import gui

root = tk.Tk()
app = gui.Aplicacion(root)
root.update()
app._catalogo = None
app._asegurar_catalogo()
app.datos_indice = {"ok": True}
app.filtrar()
root.update()
app.entrada_busqueda.delete(0, "end")
app.entrada_busqueda.insert(0, "skull")
app.filtrar()
root.update()

idx = next(i for i, p in enumerate(app.mostrar) if len(p.get("trajes") or []) > 1)
app.lista.selection_clear(0, "end")
app.lista.selection_set(idx)
app.lista.activate(idx)
app.lista.event_generate("<<ListboxSelect>>")
root.update()
print("exportselection del Listbox:", app.lista.cget("exportselection"))
print("curselection tras elegir personaje:", app.lista.curselection())

# popdown real del Combobox de traje
popdown = app.combo_traje.tk.call("ttk::combobox::PopdownWindow", app.combo_traje)
pop_lb = str(popdown) + ".f.l"
print("popdown listbox:", pop_lb)
# forzar su creacion/relleno
app.combo_traje.event_generate("<Button-1>")
root.update()
print("items en popdown:", app.combo_traje.tk.call(pop_lb, "size"))
# el usuario pulsa el traje 1 DENTRO del desplegable
app.combo_traje.tk.call(pop_lb, "selection", "clear", 0, "end")
app.combo_traje.tk.call(pop_lb, "selection", "set", 1)
app.combo_traje.tk.call(pop_lb, "activate", 1)
root.update()
print("curselection del personaje TRAS marcar el traje en el popdown:", app.lista.curselection())
# ahora el combo aplica la eleccion (lo que hace la interaccion real)
app.combo_traje.current(1)
app.combo_traje.event_generate("<<ComboboxSelected>>")
root.update()
print("current del combo:", app.combo_traje.current(), "-> traje:", app._traje_activo.get("clave"))
print("curselection del personaje DESPUES de elegir traje:", app.lista.curselection())
sel = app.lista.curselection()
print("extraer diria:", "AVISO sin personaje" if not sel else "OK")
root.destroy()