"""Harness de captura: monta la pestana Herramientas -> Video y audio con los estilos reales,
rellena la lista de videos (con distintivos) y guarda una captura PNG de la ventana.

Uso: shot_badge.py <indice_scroll> <indice_sel> <salida.png>
"""
import sys, time, tkinter as tk

# DPI: sin esto, tkinter da coordenadas logicas y ImageGrab devuelve pixeles fisicos, y la
# captura sale recortada por la derecha en pantallas con escalado.
import ctypes
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

sys.path.insert(0, "C:/Users/Lukas/p5x-datamining/p5x_studio")
from p5x_studio import gui, herramientas  # noqa: E402
from PIL import ImageGrab  # noqa: E402

idx = int(sys.argv[1]) if len(sys.argv) > 1 else 0
sel = int(sys.argv[2]) if len(sys.argv) > 2 else idx
out = sys.argv[3] if len(sys.argv) > 3 else "C:/Users/Lukas/p5x-datamining/_dl/shot_badge.png"
if len(sys.argv) > 4:
    from p5x_studio import idiomas
    idiomas._ACTIVO["v"] = sys.argv[4]

root = tk.Tk()
root.title("P5X Studio — Video y audio")
root.geometry("1020x686+0+0")
root.configure(bg=herramientas.COLOR_FONDO)


class _D:
    pass


_d = _D()
_d.raiz = root
gui.Aplicacion._estilo(_d)          # mismos estilos que la app real

panel = herramientas.PanelHerramientas(root)
panel.pack(fill="both", expand=True)
panel.cuaderno.select(panel.tab_media)
panel.listar_media()

lb = panel.lista_media
lb.see(idx)
lb.selection_clear(0, "end")
lb.selection_set(sel)
lb.activate(sel)
panel.detalle_media()

root.attributes("-topmost", True)
root.update()
root.lift()
root.focus_force()
for _ in range(6):
    root.update()
    time.sleep(0.15)

x, y = root.winfo_rootx(), root.winfo_rooty()
w, h = root.winfo_width(), root.winfo_height()
full = ImageGrab.grab()
if x + w <= full.width and y + h <= full.height:
    img = full.crop((x, y, x + w, y + h))
else:
    img = full
img.save(out)
print("saved", out, "win", (w, h), "img", img.size)
root.destroy()