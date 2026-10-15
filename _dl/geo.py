import sys, tkinter as tk
sys.path.insert(0, r'C:\Users\Lukas\p5x-datamining\p5x_studio')
from p5x_studio import gui, idiomas

idioma = sys.argv[1] if len(sys.argv) > 1 else "en"
raiz = tk.Tk()
app = gui.Aplicacion(raiz)
idiomas.activar(idioma)
raiz.update_idletasks(); raiz.update()
raiz.geometry("1020x701")
raiz.update_idletasks(); raiz.update()
b = app.boton_extraer
y0 = b.winfo_rooty() - raiz.winfo_rooty()
print("idioma:", idiomas.idioma_actual(), "| texto boton:", b.cget("text"))
print("ventana:", raiz.winfo_width(), "x", raiz.winfo_height())
print("boton_extraer y:", y0, "->", y0 + b.winfo_height(), "(alto", b.winfo_height(), ")")
raiz.destroy()
