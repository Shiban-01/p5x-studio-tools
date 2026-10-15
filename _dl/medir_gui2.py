"""Mide la ventana de P5X Studio a 1020x701 (el tamano justo) con el catalogo nuevo.

Los widgets miden 1x1 hasta que la ventana se dibuja, asi que se llama a update() antes de medir.
Comprueba que el boton «Extraer modelo» sigue dentro de la ventana y ensena las categorias.

Uso: python _dl/medir_gui2.py
"""
import sys
import tkinter as tk

sys.path.insert(0, r"C:\Users\Lukas\p5x-datamining\p5x_studio")
from p5x_studio import ajustes, catalogo, gui  # noqa: E402


def caja(w):
    """Coordenadas ABSOLUTAS dentro de la ventana (sumando los contenedores)."""
    x = y = 0
    p = w
    while p is not None:
        x += p.winfo_x()
        y += p.winfo_y()
        p = p.master
    return (x, y, x + w.winfo_width(), y + w.winfo_height())


def main() -> None:
    ajustes.preparar_carpetas()
    gui.Aplicacion.comprobar_todo = lambda self: None
    raiz = tk.Tk()
    app = gui.Aplicacion(raiz)
    raiz.geometry("1020x701+0+0")
    for _ in range(10):
        raiz.update_idletasks()
        raiz.update()

    alto = raiz.winfo_height()
    ancho = raiz.winfo_width()
    bx0, by0, bx1, by1 = caja(app.boton_extraer)
    print("ventana        :", (0, 0, ancho, alto), " geometry:", raiz.geometry())
    print("boton extraer  : (%d, %d, %d, %d)" % (bx0, by0, bx1, by1))
    print("  -> dentro de la ventana:", 0 <= by0 and by1 <= alto,
          " (ventana de %d px)" % alto)
    print("categorias     :", list(app.combo_categoria.cget("values")))
    print("categoria activa:", app.combo_categoria.get())

    app._asegurar_catalogo()
    app.filtrar()
    print("entradas en 'Todo':", len(app.mostrar))

    # filtrar por Escenarios y comprobar que salen entradas reales
    texto_esc = [v for v in app.combo_categoria.cget("values") if v.startswith("Escenarios")][0]
    app.combo_categoria.set(texto_esc)
    app.cambiar_categoria()
    print("escenarios en lista:", len(app.mostrar), " ejemplo:",
          app.mostrar[0]["etiqueta"] if app.mostrar else "-")

    # elegir skull y medir otra vez (aparece el selector de traje)
    app.combo_categoria.set([v for v in app.combo_categoria.cget("values")
                             if v.startswith("Todo")][0])
    app.cambiar_categoria()
    idx = next((i for i, p in enumerate(app.mostrar) if p["id"] == "skull"), None)
    if idx is not None:
        app.lista.selection_clear(0, "end")
        app.lista.selection_set(idx)
        app.mostrar_detalle()
        raiz.update_idletasks()
        raiz.update()
        bx0, by0, bx1, by1 = caja(app.boton_extraer)
        print("--- con skull (trajes=%d) ---" % len(app._trajes_activos))
        print("boton extraer  : (%d, %d, %d, %d)" % (bx0, by0, bx1, by1))
        print("  -> dentro de la ventana:", 0 <= by0 and by1 <= raiz.winfo_height())
        print("fila_traje     :", caja(app.fila_traje), " visible:", bool(app.fila_traje.winfo_ismapped()))
    raiz.destroy()


if __name__ == "__main__":
    main()