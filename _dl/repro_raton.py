"""Reproduccion con RATON REAL (SendInput). Comprueba si elegir el traje deselecciona."""
import sys, time, ctypes, traceback
sys.path.insert(0, r"C:/Users/Lukas/p5x-datamining/p5x_studio")
import tkinter as tk
from p5x_studio import ajustes, gui

u = ctypes.windll.user32
u.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]

def click(x, y, pausa=0.45):
    u.SetCursorPos(int(x), int(y))
    time.sleep(0.08)
    u.mouse_event(0x0002, 0, 0, 0, 0)  # LEFTDOWN
    time.sleep(0.05)
    u.mouse_event(0x0004, 0, 0, 0, 0)  # LEFTUP
    time.sleep(pausa)

def caja(w):
    x = y = 0; p = w
    while p is not None:
        x += p.winfo_x(); y += p.winfo_y(); p = p.master
    return x, y, x + w.winfo_width(), y + w.winfo_height()

ajustes.preparar_carpetas()
gui.messagebox.showinfo = lambda *a, **k: print("   [messagebox.showinfo]", a[1] if len(a) > 1 else "")
gui.messagebox.showwarning = lambda *a, **k: print("   [messagebox.showwarning]", a[1] if len(a) > 1 else "")
gui.Aplicacion.comprobar_todo = lambda self: None

raiz = tk.Tk()
app = gui.Aplicacion(raiz)
raiz.geometry("1020x700+0+0")
raiz.update()
app._catalogo = None; app._asegurar_catalogo(); app.datos_indice = {"ok": True}
app.filtrar(); raiz.update()

# instrumentar filtrar
_orig_filtrar = app.filtrar
def filtrar_traza():
    print("   >>> filtrar() llamado desde:", "".join(traceback.format_stack()[-3:-1]).strip().replace("\n", " | "))
    return _orig_filtrar()
app.filtrar = filtrar_traza
app.entrada_busqueda.delete(0, "end"); app.entrada_busqueda.insert(0, "skull")
filtrar_traza(); raiz.update()
print("idioma:", app.combo_idioma.get())
idx = next(i for i, p in enumerate(app.mostrar) if p["id"] == "skull")
print("skull en indice de lista:", idx, "trajes:", [t.get("clave") for t in app.mostrar[idx]["trajes"]])

x0, y0, x1, y1 = caja(app.lista)
alto = app.lista.winfo_height(); filas = app.lista.size()
fila = (y1 - y0) / max(filas, 1)
print("lista caja:", (x0, y0, x1, y1), "filas:", filas, "alto fila:", round(fila, 2))
click(x0 + 40, y0 + fila * idx + fila / 2)
print("tras clic en skull -> curselection:", app.lista.curselection(),
      "personaje:", app._personaje_activo and app._personaje_activo["etiqueta"])

cx0, cy0, cx1, cy1 = caja(app.combo_traje)
print("combo traje caja:", (cx0, cy0, cx1, cy1), "mapped:", app.fila_traje.winfo_ismapped())
click(cx0 + 40, cy0 + (cy1 - cy0) / 2)  # abrir desplegable
raiz.update()
pop = str(app.combo_traje.tk.call("ttk::combobox::PopdownWindow", app.combo_traje)) + ".f.l"
print("popdown mapped:", app.combo_traje.tk.call("winfo", "ismapped", pop),
      "size:", app.combo_traje.tk.call(pop, "size"))
px = app.combo_traje.tk.call("winfo", "rootx", pop); py = app.combo_traje.tk.call("winfo", "rooty", pop)
pw = app.combo_traje.tk.call("winfo", "width", pop); ph = app.combo_traje.tk.call("winfo", "height", pop)
print("popdown caja:", (px, py, pw, ph))
# clic en el SEGUNDO traje
click(int(px) + 30, int(py) + ph * 1.5 / 2 + 2)
raiz.update()
print("combo current:", app.combo_traje.current(), "traje:", app._traje_activo.get("clave"))
print("curselection tras elegir traje:", app.lista.curselection())
sel = app.lista.curselection()
print("RESULTADO:", "BUG REPRODUCIDO (sin personaje)" if not sel else "sigue seleccionado")
raiz.destroy()