"""Paso a paso con raton real, imprimiendo la seleccion tras cada clic."""
import sys, time, ctypes
sys.path.insert(0, r"C:/Users/Lukas/p5x-datamining/p5x_studio")
import tkinter as tk
from p5x_studio import ajustes, gui
u = ctypes.windll.user32

def click(x, y, p=0.6):
    u.SetCursorPos(int(x), int(y)); time.sleep(0.15)
    u.mouse_event(0x0002,0,0,0,0); time.sleep(0.06); u.mouse_event(0x0004,0,0,0,0); time.sleep(p)
def foco(raiz):
    u.SetForegroundWindow(int(raiz.frame(),16)); time.sleep(0.25)

def focus_actual():
    try:
        return raiz.tk.call("focus")
    except Exception as e:
        return "?" + str(e)

ajustes.preparar_carpetas()
gui.Aplicacion.comprobar_todo = lambda self: None
raiz = tk.Tk(); app = gui.Aplicacion(raiz)
raiz.geometry("1020x701+0+0"); raiz.update()
raiz.lift(); raiz.attributes("-topmost", True)
app._catalogo=None; app._asegurar_catalogo(); app.datos_indice={"ok":True}; app.filtrar(); raiz.update()
app.entrada_busqueda.delete(0,"end"); app.entrada_busqueda.insert(0,"skull"); app.filtrar(); raiz.update()
lb = app.lista
for _ in range(5):
    foco(raiz); raiz.update()
    x,y,w,h = lb.bbox(0)
    click(lb.winfo_rootx()+x+40, lb.winfo_rooty()+y+h/2); raiz.update()
    if lb.curselection() and app._personaje_activo and app._personaje_activo["id"]=="skull": break
print("A) tras clic skull: sel=", lb.curselection(), "foco=", focus_actual(), "traje visible:", app.fila_traje.winfo_ismapped())
cb = app.combo_traje
foco(raiz); raiz.update()
print("B) antes de abrir combo: sel=", lb.curselection(), "combo geom:", cb.winfo_rootx(), cb.winfo_rooty(), cb.winfo_width(), cb.winfo_height())
click(cb.winfo_rootx()+60, cb.winfo_rooty()+cb.winfo_height()/2); raiz.update()
pop = str(cb.tk.call("ttk::combobox::PopdownWindow", cb)) + ".f.l"
print("C) tras clic para abrir: sel=", lb.curselection(), "popdown mapped:", cb.tk.call("winfo","ismapped",pop), "foco=", focus_actual())
bx,by,bw,bh = cb.tk.call(pop,"bbox",1)
click(int(cb.tk.call("winfo","rootx",pop))+bx+40, int(cb.tk.call("winfo","rooty",pop))+by+bh/2); raiz.update()
print("D) tras clic en item 1: sel=", lb.curselection(), "combo=", cb.current(), "traje=", app._traje_activo and app._traje_activo.get("clave"), "foco=", focus_actual())
raiz.destroy()