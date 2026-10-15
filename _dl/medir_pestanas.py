"""Mide cada pestana del panel de herramientas al seleccionarla (las no activas miden 1x1)."""
import sys
import tkinter as tk
from tkinter import ttk
sys.path.insert(0, r"C:\Users\Lukas\p5x-datamining\p5x_studio")
from p5x_studio import ajustes, herramientas as H  # noqa: E402

ajustes.preparar_carpetas()
raiz = tk.Tk()
raiz.geometry("1020x701")
raiz.configure(bg=H.COLOR_FONDO)
st = ttk.Style()
st.theme_use("clam")
st.configure("TFrame", background=H.COLOR_FONDO)
st.configure("TLabel", background=H.COLOR_FONDO, foreground=H.COLOR_TEXTO)
st.configure("Titulo.TLabel", font=("Segoe UI Semibold", 17), foreground=H.COLOR_TEXTO)
st.configure("Suave.TLabel", foreground=H.COLOR_SUAVE)
st.configure("Panel.TFrame", background=H.COLOR_PANEL)
st.configure("Panel.TLabel", background=H.COLOR_PANEL, foreground=H.COLOR_TEXTO)
st.configure("SuavePanel.TLabel", background=H.COLOR_PANEL, foreground=H.COLOR_SUAVE)
nb = ttk.Notebook(raiz)
nb.pack(fill="both", expand=True)
panel = H.PanelHerramientas(nb)
nb.add(panel, text="  Herramientas  ")
raiz.update_idletasks()
raiz.update()

for tab, nombre in ((panel.tab_explorador, "Explorador"), (panel.tab_inspector, "Inspector"),
                    (panel.tab_buscador, "Buscador"), (panel.tab_texturas, "Texturas"),
                    (panel.tab_media, "Video/audio")):
    panel.cuaderno.select(tab)
    raiz.update_idletasks()
    raiz.update()
    print("%-12s %dx%d  (visible=%s)" % (nombre, tab.winfo_width(), tab.winfo_height(),
                                         bool(tab.winfo_ismapped())))
raiz.destroy()