"""Aisla POR QUE el clic real en el desplegable vacia la seleccion del Listbox."""
import sys, time, ctypes
sys.path.insert(0, r"C:/Users/Lukas/p5x-datamining/p5x_studio")
import tkinter as tk
from p5x_studio import ajustes, gui
u = ctypes.windll.user32

def click(x, y, p=0.5):
    u.SetCursorPos(int(x), int(y)); time.sleep(0.12)
    u.mouse_event(0x0002,0,0,0,0); time.sleep(0.06); u.mouse_event(0x0004,0,0,0,0); time.sleep(p)

ajustes.preparar_carpetas()
gui.Aplicacion.comprobar_todo = lambda self: None
raiz = tk.Tk(); app = gui.Aplicacion(raiz)
raiz.geometry("1020x701+0+0"); raiz.update()
raiz.lift(); raiz.attributes("-topmost", True); u.SetForegroundWindow(int(raiz.frame(),16)); time.sleep(0.3); raiz.update()
app._catalogo=None; app._asegurar_catalogo(); app.datos_indice={"ok":True}; app.filtrar(); raiz.update()
app.entrada_busqueda.delete(0,"end"); app.entrada_busqueda.insert(0,"skull"); app.filtrar(); raiz.update()
u.SetForegroundWindow(int(raiz.frame(),16)); time.sleep(0.2); raiz.update()
lb = app.lista
print("exportselection lista:", lb.cget("exportselection"), "| exportselection entrada:", app.entrada_busqueda.cget("exportselection"))
x,y,w,h = lb.bbox(0)
click(lb.winfo_rootx()+x+40, lb.winfo_rooty()+y+h/2)
print("tras clic en skull: sel=", lb.curselection(), "foco=", raiz.focus_get())
cb = app.combo_traje
click(cb.winfo_rootx()+60, cb.winfo_rooty()+cb.winfo_height()/2)
raiz.update()
print("tras abrir combo: sel=", lb.curselection(), "foco=", raiz.focus_get())
pop = str(cb.tk.call("ttk::combobox::PopdownWindow", cb)) + ".f.l"
print("popdown exportselection:", cb.tk.call(pop,"cget","-exportselection"), "mapped:", cb.tk.call("winfo","ismapped",pop))
bx,by,bw,bh = cb.tk.call(pop,"bbox",1)
click(int(cb.tk.call("winfo","rootx",pop))+bx+40, int(cb.tk.call("winfo","rooty",pop))+by+bh/2)
raiz.update()
print("tras elegir traje: sel=", lb.curselection(), "foco=", raiz.focus_get(), "combo=", cb.current())
# comprobar si re-seleccionar manualmente sobrevive
lb.selection_set(0); raiz.update()
print("re-seleccion manual: sel=", lb.curselection())
# simular perdida de foco (pasar foco a la entrada)
app.entrada_busqueda.focus_set(); raiz.update()
print("tras mover foco a la entrada: sel=", lb.curselection())
raiz.destroy()