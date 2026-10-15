"""Mide la geometria de la ventana de P5X Studio Tools (version publica, solo herramientas).

DPI-aware para que las medidas sean 1:1 con los pixeles. No usa mainloop: construye la ventana,
la dibuja con update() y mide. Salida por pantalla.
"""
import ctypes
import os
import sys

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    ctypes.windll.user32.SetProcessDPIAware()

sys.path.insert(0, r"C:/Users/Lukas/p5x-datamining/p5x_studio")
os.environ["P5X_STUDIO_SIN_INDICES"] = "1"

import tkinter as tk  # noqa: E402

from p5x_studio import ajustes, gui_tools  # noqa: E402

ajustes.CACHE.mkdir(parents=True, exist_ok=True)
ajustes.carpeta_herramientas()


def caja(w):
    x = y = 0
    p = w
    while p is not None:
        x += p.winfo_x()
        y += p.winfo_y()
        p = p.master
    return (x, y, x + w.winfo_width(), y + w.winfo_height())


def main():
    raiz = tk.Tk()
    app = gui_tools.VentanaHerramientas(raiz)
    # sin forzar geometria: se mide la que elige la propia app (adaptada a la pantalla)
    for _ in range(12):
        raiz.update_idletasks()
        raiz.update()
    print("ventana pedida: %dx%d  min: %s  pantalla_logica=%d"
          % (gui_tools.VENTANA_ANCHO, app._alto_que_cabe(), gui_tools.VENTANA_MIN,
             raiz.winfo_screenheight()))
    print("ventana real  : %dx%d  (x=%d y=%d)"
          % (raiz.winfo_width(), raiz.winfo_height(), raiz.winfo_rootx(), raiz.winfo_rooty()))
    p = app.panel
    print("panel         :", caja(p), "-> %dx%d" % (p.winfo_width(), p.winfo_height()))
    print("cuaderno      :", caja(p.cuaderno),
          "-> %dx%d" % (p.cuaderno.winfo_width(), p.cuaderno.winfo_height()))
    for nombre, tab in (("explorador", p.tab_explorador), ("inspector", p.tab_inspector),
                        ("buscador", p.tab_buscador), ("texturas", p.tab_texturas),
                        ("media", p.tab_media)):
        print("  tab %-11s:" % nombre, caja(tab), "-> %dx%d"
              % (tab.winfo_width(), tab.winfo_height()))
    # ¿cabe el contenido de cada pestana? Se mira el tamano de los widgets CLAVE (si un control
    # fijo queda a 1 px, es que se ha recortado de verdad)
    p.cuaderno.select(p.tab_explorador)
    for _ in range(4):
        raiz.update_idletasks(); raiz.update()
    print("  [explorador] arbol alto=%d  detalle alto=%d"
          % (p.arbol_explorador.winfo_height(), p.detalle.winfo_height()))
    p.cuaderno.select(p.tab_inspector)
    for _ in range(4):
        raiz.update_idletasks(); raiz.update()
    print("  [inspector] arbol alto=%d" % p.arbol_inspector.winfo_height())
    p.cuaderno.select(p.tab_buscador)
    for _ in range(4):
        raiz.update_idletasks(); raiz.update()
    print("  [buscador] arbol alto=%d  boton_indice alto=%d  progreso alto=%d  etiq alto=%d"
          % (p.arbol_recursos.winfo_height(), p.boton_indice.winfo_height(),
             p.progreso_indice.winfo_height(), p.etiq_indice.winfo_height()))
    p.cuaderno.select(p.tab_texturas)
    for _ in range(4):
        raiz.update_idletasks(); raiz.update()
    print("  [texturas] lista alto=%d  lienzo alto=%d"
          % (p.lista_imgs.winfo_height(), p.lienzo.winfo_height()))
    p.cuaderno.select(p.tab_media)
    for _ in range(4):
        raiz.update_idletasks(); raiz.update()
    cuerpo_media = p.lista_media.master
    print("  [media] tab alto=%d  lista alto=%d  panel_der alto=%d  boton_video alto=%d"
          % (p.tab_media.winfo_height(), p.lista_media.winfo_height(),
             p.boton_video.master.winfo_height(), p.boton_video.winfo_height()))
    # desglose del alto fijo de la pestana de video
    hijos = [w for w in p.tab_media.winfo_children()]
    print("  [media] hijos fijos:",
          [(w.winfo_height(), str(w)) for w in hijos])
    print("  [media] boton_audio alto=%d  etiq_sel alto=%d"
          % (p.boton_audio.winfo_height(), p.etiq_sel_media.winfo_height()))
    print("  [media] dentro del panel derecho:")
    for w in p.boton_video.master.winfo_children():
        print("      req=%d real=%d %s  texto=%r"
              % (w.winfo_reqheight(), w.winfo_height(), w.winfo_class(),
                 (w.cget("text") if "text" in w.keys() else "")[:40]))
    print("arbol explorad:", caja(p.arbol_explorador))
    print("detalle expl  :", caja(p.detalle))
    print("progreso ind  :", caja(p.progreso_indice))
    print("boton indice  :", caja(p.boton_indice))
    print("registro log  :", caja(app.registro),
          "-> %dx%d" % (app.registro.winfo_width(), app.registro.winfo_height()))
    print("combo idioma  :", caja(app.combo_idioma))
    print("etiq juego    :", caja(app.etiq_juego))
    raiz.destroy()


if __name__ == "__main__":
    main()
