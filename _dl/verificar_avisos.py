"""Verifica: aviso sin personaje (ES/EN), y que el desplegable de traje se oculta con 1 traje.
Tambien que cambiar de idioma conserva personaje+traje (con eventos de interfaz)."""
import sys
sys.path.insert(0, r"C:/Users/Lukas/p5x-datamining/p5x_studio")
import tkinter as tk
from p5x_studio import ajustes, gui

avisos = []
gui.messagebox.showinfo = lambda *a, **k: avisos.append(("info", a[1] if len(a) > 1 else ""))
gui.messagebox.showwarning = lambda *a, **k: avisos.append(("warn", a[1] if len(a) > 1 else ""))
gui.Aplicacion.comprobar_todo = lambda self: None

raiz = tk.Tk(); app = gui.Aplicacion(raiz)
raiz.geometry("1020x701+0+0"); raiz.update()
app._catalogo=None; app._asegurar_catalogo(); app.datos_indice={"ok":True}; app.filtrar(); raiz.update()

print("=== aviso SIN personaje, en cada idioma ===")
for idioma, esperado in (("Español", "Primero elige un personaje"), ("English", "First pick a character")):
    app.combo_idioma.set(idioma); app.combo_idioma.event_generate("<<ComboboxSelected>>"); raiz.update()
    avisos.clear()
    app.boton_extraer.invoke(); raiz.update()
    print("   %-8s -> %r" % (idioma, avisos[-1][1] if avisos else "(sin aviso)"))

print("=== desplegable de traje: 2 trajes vs 1 ===")
def elegir(pid):
    idx = next(i for i,p in enumerate(app.mostrar) if p["id"]==pid)
    app.lista.selection_clear(0,"end"); app.lista.selection_set(idx); app.lista.activate(idx)
    app.lista.event_generate("<<ListboxSelect>>"); raiz.update()
app.filtrar(); raiz.update()
elegir("skull")
print("   skull (2 trajes) -> visible:", bool(app.fila_traje.winfo_ismapped()))
elegir("n_yiyuan")
print("   n_yiyuan (1 traje) -> visible:", bool(app.fila_traje.winfo_ismapped()))

print("=== cambiar de idioma conserva personaje + traje ===")
elegir("skull")
app.combo_traje.current(1); app.combo_traje.event_generate("<<ComboboxSelected>>"); raiz.update()
print("   antes: sel=%s traje=%s idioma=%s" % (app.lista.curselection(),
      app._traje_activo.get("clave"), app.combo_idioma.get()))
otro = "English" if app.combo_idioma.get() != "English" else "Español"
app.combo_idioma.set(otro); app.combo_idioma.event_generate("<<ComboboxSelected>>"); raiz.update()
print("   despues: sel=%s traje=%s idioma=%s -> extraer=%s" % (
    app.lista.curselection(), app._traje_activo.get("clave"), app.combo_idioma.get(),
    "ok" if app._personaje_seleccionado() is not None else "SIN PERSONAJE"))
raiz.destroy()