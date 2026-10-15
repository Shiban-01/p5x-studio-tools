import sys, time, tkinter as tk
sys.path.insert(0, r'C:\Users\Lukas\p5x-datamining\p5x_studio')
from p5x_studio import gui, idiomas, dependencias, sesion_unity, unity

idioma = sys.argv[1] if len(sys.argv) > 1 else "en"

# simula el entorno externo para no tocar red/Unity durante la prueba del panel
dependencias.asegurar_dependencias = lambda cb=None: "python-simulado"
sesion_unity.resumen = lambda: {"editor_instalado": True, "licencia": True, "listo": True}
unity.buscar_proyecto = lambda: "proyecto_simulado"

raiz = tk.Tk()
app = gui.Aplicacion(raiz)
idiomas.activar(idioma)
app.comprobar_todo()

fin = time.time() + 60
while time.time() < fin:
    raiz.update()
    claves = [c[0] for c in app._estado_ultimo.values()]
    if app.etiquetas_estado["indice"].cget("text") != idiomas.t("comun_comprobando"):
        break
    time.sleep(0.1)
raiz.update()

print("idioma:", idiomas.idioma_actual())
print("panel indice ->", repr(app.etiquetas_estado["indice"].cget("text")))
print("fuente lista  ->", len(app._asegurar_catalogo()), "entradas (catalogo)")
print("total boton categoria ->", len(app.mostrar))
raiz.destroy()
