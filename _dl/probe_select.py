import sys
sys.path.insert(0, r"C:/Users/Lukas/p5x-datamining/p5x_studio")
import tkinter as tk
from p5x_studio import gui
root = tk.Tk()
app = gui.Aplicacion(root)
root.update()
app._catalogo=None; app._asegurar_catalogo(); app.datos_indice={"ok":True}; app.filtrar(); root.update()
app.entrada_busqueda.delete(0,"end"); app.entrada_busqueda.insert(0,"skull"); app.filtrar(); root.update()
idx = next(i for i,p in enumerate(app.mostrar) if len(p.get("trajes") or [])>1)
app.lista.selection_clear(0,"end"); app.lista.selection_set(idx); app.lista.activate(idx)
app.lista.event_generate("<<ListboxSelect>>"); root.update()
print("sel tras personaje:", app.lista.curselection(), "personaje:", app._personaje_activo["etiqueta"])
pop = str(app.combo_traje.tk.call("ttk::combobox::PopdownWindow", app.combo_traje)) + ".f.l"
app.combo_traje.event_generate("<Button-1>"); root.update()
print("popdown mapped:", app.combo_traje.tk.call("winfo","ismapped",pop))
try:
    app.combo_traje.tk.call("::ttk::combobox::Select", app.combo_traje, pop, 1)
    print("Select llamado")
except Exception as e:
    print("Select fallo:", e)
root.update()
print("combo current:", app.combo_traje.current(), "traje:", app._traje_activo.get("clave"))
print("sel tras elegir traje:", app.lista.curselection())
root.destroy()