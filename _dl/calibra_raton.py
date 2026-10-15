import sys, time, ctypes
sys.path.insert(0, r"C:/Users/Lukas/p5x-datamining/p5x_studio")
import tkinter as tk
from p5x_studio import ajustes, gui
u = ctypes.windll.user32
ajustes.preparar_carpetas()
gui.Aplicacion.comprobar_todo = lambda self: None
raiz = tk.Tk(); app = gui.Aplicacion(raiz)
raiz.geometry("1020x700+0+0"); raiz.update()
raiz.lift(); raiz.attributes("-topmost", True); raiz.update()
app._catalogo=None; app._asegurar_catalogo(); app.datos_indice={"ok":True}; app.filtrar(); raiz.update()
app.entrada_busqueda.delete(0,"end"); app.entrada_busqueda.insert(0,"skull"); app.filtrar(); raiz.update()
print("window:", raiz.winfo_rootx(), raiz.winfo_rooty(), raiz.winfo_width(), raiz.winfo_height())
lb = app.lista
print("lista rootx/rooty/w/h:", lb.winfo_rootx(), lb.winfo_rooty(), lb.winfo_width(), lb.winfo_height(), "size:", lb.size())
hwnd = u.GetForegroundWindow()
print("foreground hwnd:", hwnd, "tk hwnd:", raiz.winfo_id())
for yy in range(lb.winfo_rooty()+5, lb.winfo_rooty()+lb.winfo_height(), 20):
    u.SetCursorPos(lb.winfo_rootx()+50, yy); time.sleep(0.05)
    p = u.GetCursorPos.__class__  # noop
    cur = ctypes.wintypes.POINT() if hasattr(ctypes,'wintypes') else None
    import ctypes.wintypes as wt
    pt = wt.POINT(); u.GetCursorPos(ctypes.byref(pt))
    u.mouse_event(0x0002,0,0,0,0); time.sleep(0.03); u.mouse_event(0x0004,0,0,0,0); time.sleep(0.25)
    raiz.update()
    print("  clic y=%d (cursor %d,%d) -> sel=%s" % (yy, pt.x, pt.y, lb.curselection()))
raiz.destroy()