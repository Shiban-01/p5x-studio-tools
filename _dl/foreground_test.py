import sys, time, ctypes
sys.path.insert(0, r"C:/Users/Lukas/p5x-datamining/p5x_studio")
import tkinter as tk
from p5x_studio import ajustes, gui
u = ctypes.windll.user32
ajustes.preparar_carpetas()
gui.Aplicacion.comprobar_todo = lambda self: None
raiz = tk.Tk(); app = gui.Aplicacion(raiz)
raiz.geometry("1020x700+0+0"); raiz.update()
raiz.lift(); raiz.attributes("-topmost", True)
try:
    hwnd = int(raiz.frame(), 16)
except Exception:
    hwnd = raiz.winfo_id()
print("frame hwnd:", hwnd)
u.SetForegroundWindow(hwnd); u.ShowWindow(hwnd, 5); time.sleep(0.3)
raiz.update()
app._catalogo=None; app._asegurar_catalogo(); app.datos_indice={"ok":True}; app.filtrar(); raiz.update()
app.entrada_busqueda.delete(0,"end"); app.entrada_busqueda.insert(0,"skull"); app.filtrar(); raiz.update()
u.SetForegroundWindow(hwnd); time.sleep(0.2); raiz.update()
lb = app.lista
print("lista rootx/rooty:", lb.winfo_rootx(), lb.winfo_rooty(), "h:", lb.winfo_height(), "size:", lb.size())
print("foreground:", u.GetForegroundWindow(), "tk frame:", hwnd)
u.SetCursorPos(lb.winfo_rootx()+60, lb.winfo_rooty()+20); time.sleep(0.15)
u.mouse_event(0x0002,0,0,0,0); time.sleep(0.06); u.mouse_event(0x0004,0,0,0,0); time.sleep(0.6)
raiz.update()
print("sel:", lb.curselection(), "personaje:", app._personaje_activo and app._personaje_activo["id"])
raiz.destroy()