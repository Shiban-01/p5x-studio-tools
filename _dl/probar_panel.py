"""Prueba de la ventana del panel de herramientas, en solitario (sin gui.py).

Mide la geometria de cada pestana, ejercita el explorador, el buscador, el inspector y el
listado de video/audio, y deja una captura de pantalla completa.
"""
import sys
import time
import tkinter as tk
from tkinter import ttk

sys.path.insert(0, r"C:\Users\Lukas\p5x-datamining\p5x_studio")
from p5x_studio import ajustes, herramientas as H  # noqa: E402

ajustes.preparar_carpetas()
raiz = tk.Tk()
raiz.title("Herramientas (prueba)")
raiz.geometry("1020x701")
raiz.configure(bg=H.COLOR_FONDO)

st = ttk.Style()
try:
    st.theme_use("clam")
except tk.TclError:
    pass
st.configure("TFrame", background=H.COLOR_FONDO)
st.configure("TLabel", background=H.COLOR_FONDO, foreground=H.COLOR_TEXTO, font=("Segoe UI", 10))
st.configure("Titulo.TLabel", font=("Segoe UI Semibold", 17), foreground=H.COLOR_TEXTO)
st.configure("Suave.TLabel", foreground=H.COLOR_SUAVE, font=("Segoe UI", 9))
st.configure("Panel.TFrame", background=H.COLOR_PANEL)
st.configure("Panel.TLabel", background=H.COLOR_PANEL, foreground=H.COLOR_TEXTO)
st.configure("SuavePanel.TLabel", background=H.COLOR_PANEL, foreground=H.COLOR_SUAVE,
             font=("Segoe UI", 9))
st.configure("TButton", font=("Segoe UI", 10), padding=6)

nb = ttk.Notebook(raiz)
nb.pack(fill="both", expand=True)
panel = H.PanelHerramientas(nb, log=lambda s: print("LOG:", s))
nb.add(panel, text="  Herramientas  ")


def bombear(segundos):
    fin = time.time() + segundos
    while time.time() < fin:
        raiz.update_idletasks()
        raiz.update()
        time.sleep(0.02)


raiz.update_idletasks()
raiz.update()
print("ventana:", raiz.winfo_width(), "x", raiz.winfo_height())
print("pestanas:", nb.tabs(), "->", [nb.tab(t, "text") for t in nb.tabs()])

# --- explorador
panel.explorar()
bombear(0.3)
print("explorador filas (sin filtro):", len(panel.arbol_explorador.get_children()))
panel.combo_tipo.set("scn")
panel.ent_actor.delete(0, "end")
panel.ent_actor.insert(0, "chord")
panel.explorar()
bombear(0.3)
print("explorador scn+chord:", panel.etiq_explorador.cget("text"))
panel.combo_tipo.set("shared")
panel.ent_actor.delete(0, "end")
panel.ent_actor.insert(0, "chord")
panel.explorar()
bombear(0.3)
print("explorador shared+chord:", panel.etiq_explorador.cget("text"))
filas = panel.arbol_explorador.get_children()
if filas:
    panel.arbol_explorador.selection_set(filas[0])
    panel.detalle_explorador()
    bombear(0.2)
    print("detalle primeras lineas:",
          panel.detalle.get("1.0", "4.0").strip().replace("\n", " | ")[:160])

# --- buscador global
panel.ent_recurso.delete(0, "end")
panel.ent_recurso.insert(0, "chord_normal_face_bc")
panel.buscar_recurso()
bombear(0.3)
res = panel.arbol_recursos.get_children()
print("buscador resultados:", len(res), panel.etiq_recursos.cget("text"))
for r in res[:3]:
    print("   ", panel.arbol_recursos.item(r, "values"))

# --- inspector (lanza el motor en hilo)
panel.ent_ruta.delete(0, "end")
panel.ent_ruta.insert(0, "110/shared_merged_5c36cff7.bundle")
panel.abrir_inspector()
bombear(4)
print("inspector filas:", len(panel.arbol_inspector.get_children()),
      "estado:", panel.estado.cget("text"))
for r in panel.arbol_inspector.get_children()[:3]:
    print("   ", panel.arbol_inspector.item(r, "values"))

# --- video y audio
panel.comprobar_herramientas()
bombear(3)
for k, et in panel.etiquetas_herr.items():
    print("herr %-10s %s" % (k, et.cget("text")))
panel.listar_media()
bombear(0.5)
print("media:", panel.etiq_media.cget("text"))
print("lista media filas:", panel.lista_media.size())

# --- geometria de cada pestana
raiz.update_idletasks()
raiz.update()
for tab, nombre in ((panel.tab_explorador, "Explorador"), (panel.tab_inspector, "Inspector"),
                    (panel.tab_buscador, "Buscador"), (panel.tab_texturas, "Texturas"),
                    (panel.tab_media, "Video/audio")):
    print("pestana %-12s %dx%d en (%d,%d)" % (nombre, tab.winfo_width(), tab.winfo_height(),
                                              tab.winfo_x(), tab.winfo_y()))
print("arbol explorador:", panel.arbol_explorador.winfo_width(), "x",
      panel.arbol_explorador.winfo_height())
print("arbol inspector :", panel.arbol_inspector.winfo_width(), "x",
      panel.arbol_inspector.winfo_height())
print("lista media     :", panel.lista_media.winfo_width(), "x",
      panel.lista_media.winfo_height())

# --- captura de pantalla completa
try:
    from PIL import ImageGrab
    img = ImageGrab.grab()
    salida = r"C:\Users\Lukas\p5x-datamining\_dl\herr_panel_solo.png"
    img.save(salida)
    print("captura:", salida, img.size)
except Exception as e:
    print("no se pudo capturar:", e)

raiz.destroy()
print("OK")