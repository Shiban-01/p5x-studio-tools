"""Captura la ventana de P5X Studio con `skull` elegido, para ver el selector de traje.

Uso: python _dl/captura_gui.py
Salida: _dl/gui_traje.png
"""
import os
import sys
import tkinter as tk

sys.path.insert(0, r"C:\Users\Lukas\p5x-datamining\p5x_studio")
from p5x_studio import ajustes, gui  # noqa: E402


def caja_absoluta(w):
    """Coordenadas del widget en la PANTALLA (sumando las de todos sus contenedores)."""
    x = y = 0
    p = w
    while p is not None:
        x += p.winfo_x()
        y += p.winfo_y()
        p = p.master
    return x, y, x + w.winfo_width(), y + w.winfo_height()


def main() -> None:
    ajustes.preparar_carpetas()
    gui.Aplicacion.comprobar_todo = lambda self: None
    raiz = tk.Tk()
    app = gui.Aplicacion(raiz)
    raiz.update_idletasks()
    raiz.update()
    app._asegurar_catalogo()
    app.filtrar()
    for i, p in enumerate(app.mostrar):
        if p["id"] == "skull":
            app.lista.selection_clear(0, "end")
            app.lista.selection_set(i)
            app.mostrar_detalle()
            break
    raiz.update_idletasks()
    raiz.update()
    raiz.lift()
    raiz.attributes("-topmost", True)
    raiz.geometry("1020x701+0+0")
    for _ in range(12):
        raiz.update_idletasks()
        raiz.update()
    raiz.after(400, lambda: None)
    import time
    time.sleep(0.6)
    raiz.update()
    bx0, by0, bx1, by1 = caja_absoluta(app.boton_extraer)
    print("boton extraer en pantalla:", (bx0, by0, bx1, by1))
    try:
        from PIL import ImageGrab
        esc = float(os.environ.get("ESC", "1.25"))  # Windows escala la ventana si la app no es DPI-aware
        print("escalado de pantalla:", esc)
        img = ImageGrab.grab(bbox=(0, 0, int(1020 * esc), int(701 * esc)))
        x0, y0 = raiz.winfo_rootx(), raiz.winfo_rooty()
        img = ImageGrab.grab(bbox=(x0, y0, x0 + int(1020 * esc), y0 + int(701 * esc)))
        salida = r"C:\Users\Lukas\p5x-datamining\_dl\gui_traje.png"
        img.save(salida)
        print("captura:", salida, img.size)
        entera = ImageGrab.grab()
        salida2 = r"C:\Users\Lukas\p5x-datamining\_dl\gui_pantalla.png"
        entera.save(salida2)
        print("pantalla:", salida2, entera.size, "ventana en", (raiz.winfo_rootx(), raiz.winfo_rooty()))
    except Exception as e:
        print("no se pudo capturar:", e)
    raiz.destroy()


if __name__ == "__main__":
    main()