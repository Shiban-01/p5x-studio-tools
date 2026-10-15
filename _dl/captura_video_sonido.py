# -*- coding: utf-8 -*-
"""Captura de la pestana Video y audio extrayendo un .usm CON sonido desde la interfaz."""
import os, sys, time
import tkinter as tk

sys.path.insert(0, r"C:\Users\Lukas\p5x-datamining\p5x_studio")
from p5x_studio import ajustes, gui  # noqa: E402

SALIDA = r"C:/Users/Lukas/p5x-datamining/_dl/gui_video_con_sonido.png"


def main():
    ajustes.preparar_carpetas()
    gui.Aplicacion.comprobar_todo = lambda self: None
    raiz = tk.Tk()
    app = gui.Aplicacion(raiz)
    raiz.geometry("1020x701+20+20")
    raiz.update_idletasks(); raiz.update()
    app.cuaderno.select(app.pestana_herramientas)
    pan = app.panel_herramientas
    pan.cuaderno.select(pan.tab_media)
    raiz.update_idletasks(); raiz.update()
    pan.listar_media()
    raiz.update_idletasks(); raiz.update()
    # elegir CG_wonder_swimsuit
    for i, m in enumerate(pan._media_sel):
        if m["nombre"] == "CG_wonder_swimsuit.usm":
            pan.lista_media.selection_clear(0, "end")
            pan.lista_media.selection_set(i)
            pan.lista_media.see(i)
            pan.detalle_media()
            break
    raiz.update_idletasks(); raiz.update()
    # extraer a MP4 CON sonido desde el propio boton de la interfaz
    pan.extraer_video_sel()
    t0 = time.time()
    while pan.trabajando or time.time() - t0 < 3:
        raiz.update_idletasks(); raiz.update()
        time.sleep(0.1)
        if time.time() - t0 > 120:
            break
    for _ in range(20):
        raiz.update_idletasks(); raiz.update(); time.sleep(0.05)
    raiz.lift(); raiz.attributes("-topmost", True); raiz.update()
    x0, y0 = raiz.winfo_rootx(), raiz.winfo_rooty()
    from PIL import ImageGrab
    ancho = raiz.winfo_width() or 1020
    alto = raiz.winfo_height() or 701
    esc = float(os.environ.get("ESC", "1.5"))  # la app es DPI-unaware: la ventana real es 1.5x
    print("rootx/y", x0, y0, "logico", ancho, alto)
    img = ImageGrab.grab()  # pantalla completa y luego recorta: evita cortar el panel derecho
    img = img.crop((x0, y0, min(x0 + int(ancho * esc) + 30, img.width),
                    min(y0 + int(alto * esc) + 30, img.height)))
    img.save(SALIDA)
    print("captura ->", SALIDA, img.size, "ventana", ancho, alto)


if __name__ == "__main__":
    main()