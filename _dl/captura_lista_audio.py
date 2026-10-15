"""Abre la app DESDE FUENTE (lee el _dl externo -> cache nuevo), va a la pestana de videos,
lista los .usm, situa la lista en el caso del usuario y en varios ganadores, y captura."""
import sys, time, tkinter as tk
sys.path.insert(0, r"C:\Users\Lukas\p5x-datamining\p5x_studio")
from p5x_studio import ajustes, gui  # noqa: E402

ajustes.preparar_carpetas()
gui.Aplicacion.comprobar_todo = lambda self: None
raiz = tk.Tk()
app = gui.Aplicacion(raiz)


def bombear(s):
    fin = time.time() + s
    while time.time() < fin:
        raiz.update_idletasks(); raiz.update(); time.sleep(0.02)


raiz.update_idletasks(); raiz.update()
bombear(2.0)
app.cuaderno.select(app.pestana_herramientas)
p = app.panel_herramientas
p.cuaderno.select(p.tab_media)
bombear(0.5)
p.listar_media()
bombear(0.4)
print("media:", p.etiq_media.cget("text"))
# contar estados pintados
from collections import Counter
c = Counter(m["estado"] for m in p._media_sel)
print("estados en la lista:", dict(c))
# situar la vista en el caso del usuario
idx = next((i for i, m in enumerate(p._media_sel) if m["nombre"].startswith("CG_P3P_Event_Main_05")), None)
if idx is not None:
    p.lista_media.see(idx)
    p.lista_media.selection_clear(0, "end")
    p.lista_media.selection_set(idx)
    p.detalle_media()
    bombear(0.3)
try:
    from PIL import ImageGrab
    raiz.lift(); raiz.attributes("-topmost", True); raiz.focus_force()
    bombear(1.2)
    img = ImageGrab.grab()
    out = r"C:\Users\Lukas\p5x-datamining\_dl\shot_lista_audio_ampliado.png"
    img.save(out)
    print("captura:", out, img.size)
    raiz.attributes("-topmost", False)
except Exception as e:
    print("no captura:", e)
raiz.destroy()
print("OK")
