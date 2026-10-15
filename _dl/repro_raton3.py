"""Flujo fiel con raton real: elegir skull (multi-traje) y elegir el traje en el desplegable."""
import sys, time, ctypes, traceback
import ctypes.wintypes as wt
sys.path.insert(0, r"C:/Users/Lukas/p5x-datamining/p5x_studio")
import tkinter as tk
from p5x_studio import ajustes, gui

u = ctypes.windll.user32
def click(x, y, pausa=0.6):
    u.SetCursorPos(int(x), int(y)); time.sleep(0.12)
    u.mouse_event(0x0002, 0, 0, 0, 0); time.sleep(0.06)
    u.mouse_event(0x0004, 0, 0, 0, 0); time.sleep(pausa)

ajustes.preparar_carpetas()
gui.Aplicacion.comprobar_todo = lambda self: None
raiz = tk.Tk(); app = gui.Aplicacion(raiz)
raiz.geometry("1020x700+0+0"); raiz.update()
raiz.lift(); raiz.attributes("-topmost", True); raiz.update()
app._catalogo=None; app._asegurar_catalogo(); app.datos_indice={"ok":True}; app.filtrar(); raiz.update()
app.entrada_busqueda.delete(0,"end"); app.entrada_busqueda.insert(0,"skull"); app.filtrar(); raiz.update()

_log = []
_orig = app.filtrar
def filtrar_log():
    _log.append("".join(traceback.format_stack()[-3:-1]))
    return _orig()
app.filtrar = filtrar_log

idx = next(i for i,p in enumerate(app.mostrar) if p["id"]=="skull")
lb = app.lista; fila = lb.winfo_height()/max(lb.size(),1)
print("=== 1) clic en skull (fila %d) ===" % idx)
click(lb.winfo_rootx()+60, lb.winfo_rooty()+fila*idx+fila/2)
print("   sel:", lb.curselection(), "personaje:", app._personaje_activo and app._personaje_activo["id"])
print("   fila traje visible:", bool(app.fila_traje.winfo_ismapped()))

print("=== 2) clic en el desplegable de traje ===")
cb = app.combo_traje
click(cb.winfo_rootx()+60, cb.winfo_rooty()+cb.winfo_height()/2)
raiz.update()
pop = str(cb.tk.call("ttk::combobox::PopdownWindow", cb)) + ".f.l"
print("   popdown mapped:", cb.tk.call("winfo","ismapped",pop), "size:", cb.tk.call(pop,"size"),
      "rooty:", cb.tk.call("winfo","rooty",pop), "h:", cb.tk.call("winfo","height",pop))

print("=== 3) clic en el SEGUNDO traje (uniform) ===")
px = int(cb.tk.call("winfo","rootx",pop)); py = int(cb.tk.call("winfo","rooty",pop))
ph = int(cb.tk.call("winfo","height",pop))
click(px+40, py + ph*1.5/2)
raiz.update()
print("   combo current:", cb.current(), "traje:", app._traje_activo and app._traje_activo.get("clave"))
print("   sel:", lb.curselection())
print("   filtrar() llamado durante la interaccion:", len(_log))
for t in _log: print("     ", t.replace("\n"," | ")[:200])
print("RESULTADO:", "BUG REPRODUCIDO (personaje deseleccionado)" if not lb.curselection() else "sigue seleccionado")
raiz.destroy()