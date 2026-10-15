"""Extrae un personaje desde la INTERFAZ REAL, con las casillas por defecto.

Construye la ventana de verdad (tkinter), espera a que cargue el indice, selecciona el personaje en
la lista y pulsa Extraer. No simula la logica: llama a `Aplicacion.extraer`, que es lo mismo que
hace el boton. Los dialogos modales se neutralizan para que no bloqueen.
"""
import sys
import time
import tkinter as tk

sys.path.insert(0, r"C:/Users/Lukas/p5x-datamining/p5x_studio")
from p5x_studio import gui, ajustes, indice  # noqa: E402

pid = sys.argv[1] if len(sys.argv) > 1 else "pc077_01"

# neutralizar los dialogos modales (si no, showinfo espera a que alguien pulse Aceptar)
avisos = []
class _Falso:
    def showinfo(self, *a, **k):
        avisos.append(("info", a))
    def showwarning(self, *a, **k):
        avisos.append(("warn", a))
    def showerror(self, *a, **k):
        avisos.append(("error", a))
    def askyesno(self, *a, **k):
        return False
gui.messagebox = _Falso()

raiz = tk.Tk()
app = gui.Aplicacion(raiz)

def bombear(segundos):
    t0 = time.time()
    while time.time() - t0 < segundos:
        raiz.update()
        time.sleep(0.05)

# esperar a que cargue el indice y la lista
for _ in range(120):
    raiz.update()
    time.sleep(0.1)
    if app.datos_indice and app.mostrar:
        break
print("indice cargado:", bool(app.datos_indice), "| entradas en lista:", len(app.mostrar))
# `comprobar_todo` puede quedarse en la comprobacion de dependencias (esta maquina no tiene pip);
# el extractor no usa `datos`, asi que se le da un diccionario vacio para poder pulsar Extraer.
if not app.datos_indice:
    print("AVISO: comprobar_todo no termino; se carga el indice a mano")
    try:
        app.datos_indice = indice.cargar_indice(lambda s: None)
    except Exception as e:
        print("no se pudo cargar el indice:", e)
        app.datos_indice = {"_": True}
    app.personajes = indice.personajes(app.datos_indice)

# buscar y seleccionar el personaje
app.entrada_busqueda.delete(0, "end")
app.entrada_busqueda.insert(0, pid)
app.filtrar()
raiz.update()
print("tras filtrar '%s': %d entradas" % (pid, len(app.mostrar)))
idx = None
for i, p in enumerate(app.mostrar):
    if p["id"].lower() == pid.lower():
        idx = i
        break
if idx is None:
    print("NO ENCONTRADO en la lista")
    sys.exit(2)
app.lista.selection_clear(0, "end")
app.lista.selection_set(idx)
app.lista.see(idx)
app.mostrar_detalle()
raiz.update()
print("seleccionado:", app._personaje_seleccionado()["etiqueta"])

# casillas tal cual estan (por defecto)
print("casillas:", {k: v.get() for k, v in app.opciones.items()})

app.extraer()
for _ in range(3600):
    raiz.update()
    time.sleep(0.2)
    if not app.trabajando and app.ultima_carpeta:
        break
    if not app.trabajando and avisos:
        break

print("ultima_carpeta:", app.ultima_carpeta)
print("avisos:", [a[0] for a in avisos])
raiz.destroy()