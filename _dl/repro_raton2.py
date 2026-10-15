"""Reproduccion con RATON REAL (SendInput), coords con winfo_rootx/rooty."""
import sys, time, ctypes, traceback
sys.path.insert(0, r"C:/Users/Lukas/p5x-datamining/p5x_studio")
import tkinter as tk
from p5x_studio import ajustes, gui

u = ctypes.windll.user32
u.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]

def click(x, y, pausa=0.5):
    u.SetCursorPos(int(x), int(y)); time.sleep(0.1)
    u.mouse_event(0x0002, 0, 0, 0, 0); time.sleep(0.05)
    u.mouse_event(0x0004, 0, 0, 0, 0); time.sleep(pausa)

def caja(w):
    return w.winfo_rootx(), w.winfo_rooty(), w.winfo_width(), w.winfo_height()

ajustes.preparar_carpetas()
gui.messagebox.showinfo = lambda *a, **k: print("   [info]", a[1] if len(a) > 1 else "")
gui.messagebox.showwarning = lambda *a, **k: print("   [warning]", a[1] if len(a) > 1 else "")
gui.Aplicacion.comprobar_todo = lambda self: None
gui.Aplicacion.elegir_carpeta_juego = lambda self: print("   [OJO: clic cayo en elegir_carpeta_juego]")

raiz = tk.Tk()
app = gui.Aplicacion(raiz)
raiz.geometry("1020x700+0+0")
raiz.update(); raiz.lift(); raiz.attributes("-topmost", True); raiz.focus_force()
raiz.update()
app._catalogo = None; app._asegurar_catalogo(); app.datos_indice = {"ok": True}
app.filtrar(); raiz.update()
app.entrada_busqueda.delete(0, "end"); app.entrada_busqueda.insert(0, "skull")
app.filtrar(); raiz.update()
print("idioma:", app.combo_idioma.get(), "| ventana en", (raiz.winfo_rootx(), raiz.winfo_rooty()))
idx = next(i for i, p in enumerate(app.mostrar) if p["id"] == "skull")
print("skull idx:", idx, "trajes:", [t.get("clave") for t in app.mostrar[idx]["trajes"]])

x, y, w, h = caja(app.lista)
fila = h / max(app.lista.size(), 1)
print("lista caja:", (x, y, w, h), "filas:", app.lista.size(), "alto fila:", round(fila, 2))
click(x + 40, y + fila * idx + fila / 2)
print("tras clic en skull -> sel:", app.lista.curselection(),
      "personaje:", app._personaje_activo and app._personaje_activo["etiqueta"])

x, y, w, h = caja(app.combo_traje)
print("combo caja:", (x, y, w, h), "mapped:", app.fila_traje.winfo_ismapped())
click(x + 40, y + h / 2)
raiz.update()
pop = str(app.combo_traje.tk.call("ttk::combobox::PopdownWindow", app.combo_traje)) + ".f.l"
print("popdown mapped:", app.combo_traje.tk.call("winfo", "ismapped", pop),
      "size:", app.combo_traje.tk.call(pop, "size"))
px = app.combo_traje.tk.call("winfo", "rootx", pop); py = app.combo_traje.tk.call("winfo", "rooty", pop)
pw = app.combo_traje.tk.call("winfo", "width", pop); ph = app.combo_traje.tk.call("winfo", "height", pop)
print("popdown caja:", (px, py, pw, ph))
click(int(px) + 30, int(py) + int(ph) * 1.5 / 2)
raiz.update()
print("combo current:", app.combo_traje.current(), "traje:", app._traje_activo and app._traje_activo.get("clave"))
sel = app.lista.curselection()
print("curselection tras elegir traje:", sel)
print("RESULTADO:", "BUG REPRODUCIDO" if not sel else "sigue seleccionado")
raiz.destroy()