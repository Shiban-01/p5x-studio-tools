"""Reproduce el bug: elegir traje deselecciona el personaje. Mide con evidencia real."""
import sys, time
sys.path.insert(0, r"C:/Users/Lukas/p5x-datamining/p5x_studio")
import tkinter as tk
from p5x_studio import gui

root = tk.Tk()
app = gui.Aplicacion(root)
root.update()
# esperar a que el hilo de comprobar_todo rellene la lista
for _ in range(80):
    root.update()
    if app.lista.size() > 0:
        break
    time.sleep(0.1)
root.update()
print("items en lista:", app.lista.size())
print("catalogo cargado:", len(app._catalogo or []))

# --- buscar 'skull' (multi-traje)
app.entrada_busqueda.delete(0, "end")
app.entrada_busqueda.insert(0, "skull")
app.filtrar()
root.update()
print("tras filtrar 'skull':", app.lista.size(), "resultados")
print("mostrar:", [p["etiqueta"] for p in app.mostrar][:5])

# localizar el indice del que tiene >1 traje
idx_multi = None
for i, p in enumerate(app.mostrar):
    if len(p.get("trajes") or []) > 1:
        idx_multi = i
        print("multi-traje idx", i, p["etiqueta"], [tr.get("clave") for tr in p["trajes"]])
        break

def seleccionar_personaje(i):
    app.lista.selection_clear(0, "end")
    app.lista.selection_set(i)
    app.lista.activate(i)
    app.lista.event_generate("<<ListboxSelect>>")
    root.update()

def elegir_traje(i):
    app.combo_traje.current(i)
    app.combo_traje.event_generate("<<ComboboxSelected>>")
    root.update()

print("\n=== FLUJO: elegir personaje (multi-traje) ===")
seleccionar_personaje(idx_multi)
print("curselection tras elegir personaje:", app.lista.curselection())
print("_personaje_activo:", app._personaje_activo["etiqueta"])
print("trajes activos:", len(app._trajes_activos), "fila visible:", bool(app.fila_traje.winfo_ismapped()))

print("\n=== elegir traje 1 ===")
elegir_traje(1)
print("curselection tras elegir traje:", app.lista.curselection())
print("_traje_activo:", app._traje_activo.get("clave"))

print("\n=== elegir traje 0 ===")
elegir_traje(0)
print("curselection tras elegir traje:", app.lista.curselection())

print("\n=== que diria extraer ===")
sel = app.lista.curselection()
print("sel:", sel, "->", "AVISO sin personaje" if not sel else "OK")

root.destroy()