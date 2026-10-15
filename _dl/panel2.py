import sys, tkinter as tk
sys.path.insert(0, r'C:\Users\Lukas\p5x-datamining\p5x_studio')
from p5x_studio import gui, idiomas, dependencias, sesion_unity, unity

idioma = sys.argv[1] if len(sys.argv) > 1 else "en"
dependencias.asegurar_dependencias = lambda cb=None: "python-simulado"
sesion_unity.resumen = lambda: {"editor_instalado": True, "licencia": True, "listo": True}
unity.buscar_proyecto = lambda: "proyecto_simulado"

raiz = tk.Tk()
app = gui.Aplicacion(raiz)
idiomas.activar(idioma)
raiz.after(300, app.comprobar_todo)
raiz.after(15000, raiz.quit)   # tope
raiz.mainloop()

texto = app.etiquetas_estado["indice"].cget("text")
print("idioma:", idiomas.idioma_actual())
print("panel indice ->", repr(texto))
print("entradas catalogo ->", len(app._asegurar_catalogo()))
print("entradas en la lista ->", len(getattr(app, "mostrar", [])))
print("estado_indice crudo ->", app._estado_ultimo.get("indice"))
raiz.destroy()
