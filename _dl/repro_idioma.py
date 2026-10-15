"""Comprueba que cambiar de idioma con personaje+traje elegidos pierde la seleccion (filtrar borra la lista)."""
import sys
sys.path.insert(0, r"C:/Users/Lukas/p5x-datamining/p5x_studio")
import tkinter as tk
from p5x_studio import gui

root = tk.Tk()
app = gui.Aplicacion(root)
root.update()
app._catalogo = None; app._asegurar_catalogo(); app.datos_indice = {"ok": True}
app.filtrar(); root.update()
app.entrada_busqueda.delete(0, "end"); app.entrada_busqueda.insert(0, "skull")
app.filtrar(); root.update()
idx = next(i for i, p in enumerate(app.mostrar) if p["id"] == "skull")
app.lista.selection_clear(0, "end"); app.lista.selection_set(idx); app.lista.activate(idx)
app.lista.event_generate("<<ListboxSelect>>"); root.update()
app.combo_traje.current(1); app.combo_traje.event_generate("<<ComboboxSelected>>"); root.update()
print("ANTES: idioma=%s sel=%s personaje=%s traje=%s" % (
    app.combo_idioma.get(), app.lista.curselection(),
    app._personaje_activo and app._personaje_activo["id"],
    app._traje_activo and app._traje_activo.get("clave")))

# cambiar de idioma (el combo tiene bind <<ComboboxSelected>>)
otros = [v for v in app.combo_idioma.cget("values") if v != app.combo_idioma.get()]
app.combo_idioma.set(otros[0])
app.combo_idioma.event_generate("<<ComboboxSelected>>")
root.update()
print("DESPUES: idioma=%s sel=%s personaje=%s traje=%s" % (
    app.combo_idioma.get(), app.lista.curselection(),
    app._personaje_activo and app._personaje_activo["id"],
    app._traje_activo and app._traje_activo.get("clave")))
print("busqueda conservada:", repr(app.entrada_busqueda.get()))
print("RESULTADO:", "BUG (sin personaje tras cambiar idioma)" if not app.lista.curselection() else "ok")
root.destroy()